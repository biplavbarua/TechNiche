import csv
import os
import sys
import hashlib
import logging
import time
from datetime import date, datetime
from pathlib import Path

from app.core.scraper import fetch_case_text
from app.core.extraction import extract_legal_metadata
from app.utils.pinecone import get_pinecone_index
from dotenv import load_dotenv

# ─── Setup ────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# The embedding model hosted by Pinecone (Integrated Inference)
EMBED_MODEL = "llama-text-embed-v2"

# ─── Chunking ────────────────────────────────────────────────────────────────

CHUNK_SIZE = 1500      # characters per chunk
CHUNK_OVERLAP = 200    # overlap between consecutive chunks
MAX_CHUNKS = 15        # safety cap per document


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Splits text into overlapping chunks using a sliding window.
    
    Unlike the previous text[:9000] truncation which permanently discarded
    80%+ of long judgments, this preserves the entire document across
    multiple indexed chunks — each inheriting parent metadata.
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    while start < len(text) and len(chunks) < MAX_CHUNKS:
        end = start + chunk_size
        chunk = text[start:end]
        
        # Only add non-trivial chunks (skip trailing whitespace fragments)
        if len(chunk.strip()) > 50:
            chunks.append(chunk)
        
        start += chunk_size - overlap
    
    return chunks


# ─── Deduplication ───────────────────────────────────────────────────────────

def generate_deterministic_id(text: str, chunk_index: int = 0) -> str:
    """
    Generates a deterministic document ID using SHA-256.
    
    The previous implementation used Python's built-in hash() which is
    randomly seeded per session (Python 3.3+), meaning the same document
    ingested in two different sessions would get two different IDs — 
    creating silent duplicates in the database.
    """
    content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    return f"doc_{content_hash}_chunk{chunk_index}"


def is_pinecone_available() -> bool:
    """Verifies Pinecone connection by checking index stats."""
    try:
        index = get_pinecone_index()
        stats = index.describe_index_stats()
        return stats is not None
    except Exception as e:
        logger.error(f"Pinecone availability check failed: {e}")
    return False


def is_url_already_ingested(url: str) -> bool:
    """
    Checks if a URL has already been ingested by querying Pinecone metadata.
    
    This prevents the duplicate-flooding problem where train_bot.py or
    repeated /api/learn/url calls would store the same case N times.
    """
    try:
        from app.utils.pinecone import get_pinecone_client
        index = get_pinecone_index()
        pc = get_pinecone_client()
        # Generate a dummy embedding from the URL text to use with query()
        embeddings = pc.inference.embed(
            model=EMBED_MODEL,
            inputs=[url],
            parameters={"input_type": "query"}
        )
        search_results = index.query(
            namespace="",
            vector=embeddings[0].values,
            top_k=1,
            filter={"url": {"$eq": url}},
            include_metadata=True,
        )
        if search_results and search_results.matches:
            return True
    except Exception as e:
        logger.debug(f"URL dedup check failed (non-critical): {e}")
    return False


# ─── Temporal Conflict Resolution ────────────────────────────────────────────

def parse_date_safe(date_str: str) -> date | None:
    """Attempts to parse a date string in multiple formats. Returns None on failure."""
    if not date_str or date_str == "UNKNOWN":
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def resolve_legal_conflicts(new_metadata: dict, index=None):
    """
    Temporal conflict resolution — ensures newer judgments overrule older ones.
    
    When a new case overrules prior cases, this function:
    1. Finds the overruled cases in the vector database.
    2. VERIFIES that the new case is chronologically newer (date comparison).
    3. Only then marks old cases as 'overruled' with provenance metadata.
    
    This prevents hallucinated overruling (LLM claiming A overrules B
    when B is actually the newer decision) and provides an auditable trail.
    """
    overrules_str = new_metadata.get("ai_overrules_cases", "")
    if not overrules_str:
        return
    
    if index is None:
        index = get_pinecone_index()
    new_case_title = new_metadata.get("title", new_metadata.get("ai_case_name", "Unknown Case"))
    new_case_date_str = new_metadata.get("ai_judgment_date", "UNKNOWN")
    new_case_date = parse_date_safe(new_case_date_str)
    
    overruled_cases = [c.strip() for c in overrules_str.split(",") if c.strip()]
    
    for case_name in overruled_cases:
        # ── Step 1: Find the old case in the DB via semantic search ──
        results = _find_case_in_db(case_name)
        
        if not results:
            logger.info(f"Overruled case '{case_name}' not found in DB. Skipping (it may not have been ingested yet).")
            continue
        
        # ── Step 2: Temporal verification ──
        old_meta = results[0].get("metadata", {}) if results else {}
        
        if new_case_date:
            old_case_date_str = old_meta.get("ai_judgment_date", "UNKNOWN")
            old_case_date = parse_date_safe(old_case_date_str)
            
            if old_case_date and new_case_date <= old_case_date:
                logger.warning(
                    f"TEMPORAL REJECTION: '{new_case_title}' ({new_case_date}) attempted to overrule "
                    f"'{case_name}' ({old_case_date}), but the new case is NOT chronologically newer. "
                    f"Halting overrule to prevent data corruption."
                )
                continue
        else:
            logger.warning(
                f"TEMPORAL WARNING: No parseable date for '{new_case_title}'. "
                f"Proceeding with overrule based on LLM assertion only (lower confidence)."
            )
        
        # ── Step 3: Mark as overruled with provenance ──
        # Use direct set_metadata update — no fetch+merge needed for serverless.
        # Pinecone's update() merges only the specified keys, preserving the rest.
        ids_to_update = [hit["_id"] for hit in results]

        for record_id in ids_to_update:
            try:
                index.update(
                    id=record_id,
                    set_metadata={
                        "status": "overruled",
                        "overruled_by": new_case_title,
                        "overruled_on": new_case_date.isoformat() if new_case_date else "UNKNOWN",
                    },
                    namespace=""
                )
            except Exception as e:
                logger.error(f"Failed to mark record {record_id} as overruled: {e}")

        logger.info(
            f"TEMPORAL CONFLICT RESOLVED: Marked {len(ids_to_update)} chunks of "
            f"'{case_name}' as 'overruled' by '{new_case_title}'."
        )


def _find_case_in_db(case_name: str) -> list | None:
    """
    Semantic search to find a case by name in Pinecone using explicit embeddings.
    """
    try:
        from app.utils.pinecone import get_pinecone_client
        index = get_pinecone_index()
        pc = get_pinecone_client()

        embeddings = pc.inference.embed(
            model=EMBED_MODEL,
            inputs=[case_name],
            parameters={"input_type": "query"}
        )

        search_results = index.query(
            namespace="",
            vector=embeddings[0].values,
            top_k=5,
            filter={"status": {"$eq": "active"}},
            include_metadata=True,
        )

        # Only return high-confidence matches (score > 0.7)
        confident_matches = [
            {"_id": match.id, "metadata": match.metadata or {}}
            for match in (search_results.matches or [])
            if match.score > 0.7
        ]
        return confident_matches if confident_matches else None
    except Exception as e:
        logger.error(f"Semantic search failed for '{case_name}': {e}")

    return None


# ─── Document Processing ────────────────────────────────────────────────────

def process_and_store_document(text: str, metadata: dict, doc_id: str = None):
    """
    Refined ingestion pipeline:
    1. Extracts high-fidelity legal metadata via LLM.
    2. Resolves temporal conflicts (new cases overrule old ones).
    3. Splits text into overlapping chunks (sliding window).
    4. Stores each chunk in Pinecone with full parent metadata + chunk lineage.
    """
    try:
        index = get_pinecone_index()
        
        # ── Step 1: Legal extraction & Enrichment ──
        # Pydantic-validated structured extraction of case name, date, domain,
        # and overruled/upheld relationships before any data enters the DB.
        ai_metadata = extract_legal_metadata(text)

        # FIX 4 — Abort guard: if extraction fails, do NOT store unvalidated data.
        # Storing chunks with blank metadata silently pollutes the DB with unjoinable
        # records that can never be correctly cited or temporally resolved.
        if not ai_metadata:
            logger.warning(
                f"Extraction returned no metadata for '{metadata.get('title', 'Untitled')}'. "
                f"Aborting ingestion to prevent unvalidated data entering the DB."
            )
            return False

        metadata["ai_case_name"] = ai_metadata.get("case_name", "UNKNOWN")
        metadata["ai_judgment_date"] = ai_metadata.get("judgment_date", "UNKNOWN")
        metadata["ai_overrules_cases"] = ", ".join(ai_metadata.get("overrules_cases", []))
        metadata["ai_upholds_cases"] = ", ".join(ai_metadata.get("upholds_cases", []))
        metadata["ai_legal_domain"] = ai_metadata.get("legal_domain", "General")

        # Store validated date as ISO string for Pinecone compatibility
        validated_date = ai_metadata.get("validated_date")
        if validated_date:
            metadata["ai_validated_date"] = (
                validated_date.isoformat() if hasattr(validated_date, 'isoformat') else str(validated_date)
            )

        # Temporal conflict resolution (now with actual date comparison)
        resolve_legal_conflicts(metadata)

        # ── Sliding-window chunking (replaces text[:9000] truncation) ──
        chunks = chunk_text(text)
        
        if not chunks:
            logger.warning(f"No valid chunks produced for document: {metadata.get('title', 'Untitled')}")
            return False
        
        # ── Upsert chunks to Pinecone with externally generated embeddings ──
        # We generate embeddings via pc.inference.embed() (same as the query path
        # in rag.py) and then use index.upsert() — this works regardless of whether
        # the index has Integrated Inference configured.
        from app.utils.pinecone import get_pinecone_client
        pc = get_pinecone_client()

        records = []
        for i, chunk in enumerate(chunks):
            chunk_id = doc_id if (doc_id and i == 0) else generate_deterministic_id(chunk, i)
            chunk_metadata = {**metadata, "chunk_index": i, "total_chunks": len(chunks)}
            records.append({
                "_id": chunk_id,
                "text": chunk,
                **chunk_metadata,
            })

        BATCH_SIZE = 96
        stored_count = 0
        for batch_start in range(0, len(records), BATCH_SIZE):
            batch = records[batch_start:batch_start + BATCH_SIZE]

            # Extract text for embedding
            texts = [rec["text"] for rec in batch]
            
            # Generate embeddings externally
            embeddings = pc.inference.embed(
                model=EMBED_MODEL,
                inputs=texts,
                parameters={"input_type": "passage"}
            )

            # Build upsert vectors
            vectors = []
            for i, rec in enumerate(batch):
                vec_id = rec["_id"]
                # Build clean metadata dict (exclude _id, keep text for retrieval)
                meta = {k: v for k, v in rec.items() if k != "_id"}
                vectors.append({
                    "id": vec_id,
                    "values": embeddings[i].values,
                    "metadata": meta,
                })

            index.upsert(vectors=vectors, namespace="")
            stored_count += len(batch)
        
        source = metadata.get('url', 'Unknown Source')
        logger.info(f"Stored {stored_count}/{len(chunks)} chunks for: {metadata.get('title', 'Untitled')} from {source}")
        return True

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        import traceback
        traceback.print_exc()
        return False


# ─── URL-Based Ingestion ─────────────────────────────────────────────────────

def ingest_case_from_url(url: str, title: str = None) -> bool:
    """
    Fetches content from a URL and ingests it into the knowledge base.
    Now with URL-based deduplication to prevent re-ingesting the same case.
    """
    logger.info(f"Ingesting from URL: {url}")
    
    # Dedup check: skip if this URL is already in the database
    if is_url_already_ingested(url):
        logger.info(f"URL already ingested, skipping: {url}")
        return False
    
    text_content = fetch_case_text(url)
    if not text_content:
        logger.warning(f"Failed to fetch content for {url}")
        return False
    
    if not title:
        title = text_content.split('\n')[0][:100] if text_content else "Untitled Legal Case"
        
    metadata = {
        "title": title,
        "url": url,
        "source": "autonomous_learning",
        "ingested_at": str(time.time()),
        "status": "active"
    }
    
    return process_and_store_document(text_content, metadata)


# ─── File-Based Ingestion ──────────────────────────────────────────────

# File types that may contain scanned/image content needing OCR vision.
_OCR_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}

# Shared plain MarkItDown converter (no LLM, fast for text-native files).
_md_plain = None
# OCR-capable MarkItDown converter (uses vision LLM, initialised on demand).
_md_ocr = None


def _get_plain_converter():
    """Lazy-init a plain MarkItDown converter (no LLM required)."""
    global _md_plain
    if _md_plain is None:
        try:
            from markitdown import MarkItDown
            _md_plain = MarkItDown()
            logger.info("MarkItDown plain converter initialised.")
        except ImportError:
            logger.error(
                "markitdown is not installed. "
                "Run: pip install 'markitdown[pdf,docx,html,xlsx,pptx]'"
            )
    return _md_plain


def _get_ocr_converter():
    """
    Lazy-init a MarkItDown instance with the markitdown-ocr plugin enabled.

    Uses the same OpenRouter client as extraction.py and reuses the first
    vision-capable model from the EXTRACTION_MODELS cascade
    (nvidia/nemotron-nano-12b-v2-vl:free).

    Falls back to the plain converter if the OCR plugin is not installed or
    no OPENROUTER_API_KEY is configured.
    """
    global _md_ocr
    if _md_ocr is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.warning(
                "OPENROUTER_API_KEY not set — OCR plugin requires a vision LLM. "
                "Falling back to plain MarkItDown (text-layer PDF only)."
            )
            return _get_plain_converter()
        try:
            from markitdown import MarkItDown
            from openai import OpenAI
            llm_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
            _md_ocr = MarkItDown(
                enable_plugins=True,
                llm_client=llm_client,
                # First vision-capable model in the existing cascade
                llm_model="nvidia/nemotron-nano-12b-v2-vl:free",
            )
            logger.info("MarkItDown OCR converter initialised with vision LLM.")
        except ImportError as e:
            logger.warning(
                f"markitdown-ocr plugin not installed ({e}). "
                "Run: pip install markitdown-ocr. Falling back to plain converter."
            )
            return _get_plain_converter()
    return _md_ocr


def ingest_case_from_file(file_path: str, title: str = None) -> bool:
    """
    Converts a local file to clean Markdown via MarkItDown and ingests it
    into the Pinecone knowledge base.

    Supports: PDF, DOCX, XLSX, PPTX, images (JPEG/PNG), ZIP archives,
    EPub, HTML, and plain text.

    For PDF/DOCX/PPTX/XLSX files the OCR-capable converter is used so that
    scanned or image-heavy documents (e.g. older High Court orders) are
    handled correctly. Plain text-native files use the fast plain converter.

    Args:
        file_path: Absolute or relative path to the file to ingest.
        title:     Optional display title. Defaults to the first non-empty
                   line of the extracted text.

    Returns:
        True if ingestion succeeded, False otherwise.
    """
    path = Path(file_path).resolve()
    logger.info(f"Ingesting from file: {path}")

    if not path.exists():
        logger.error(f"File not found: {path}")
        return False

    # Choose converter based on whether the file may need OCR
    ext = path.suffix.lower()
    converter = _get_ocr_converter() if ext in _OCR_EXTENSIONS else _get_plain_converter()

    if converter is None:
        logger.error("No MarkItDown converter available. Cannot process file.")
        return False

    try:
        result = converter.convert(str(path))
        text_content = result.text_content or ""
    except Exception as e:
        logger.error(f"MarkItDown conversion failed for {path}: {e}")
        return False

    if not text_content or len(text_content.strip()) < 100:
        logger.warning(f"Conversion produced insufficient text (<100 chars) for: {path}")
        return False

    if not title:
        # Use the first non-empty line as the document title
        title = next(
            (line.lstrip("# ").strip() for line in text_content.splitlines() if line.strip()),
            path.name,
        )

    metadata = {
        "title": title,
        "url": f"file://{path}",
        "source": "file_upload",
        "file_name": path.name,
        "file_type": ext.lstrip("."),
        "ingested_at": str(time.time()),
        "status": "active",
    }

    return process_and_store_document(text_content, metadata)


# ─── CSV Bulk Ingestion ──────────────────────────────────────────────────────

def ingest_data():
    """Reads cases.csv, scrapes text, and stores in Pinecone using Integrated Embeddings."""
    
    # Use relative path from the project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    csv_path = os.path.join(project_root, "legacy", "cases.csv")
        
    if not os.path.exists(csv_path):
        logger.error(f"CSV file not found at {csv_path}")
        return

    logger.info(f"Reading cases from {csv_path}...")
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        idx = 0
        for row in reader:
            url = row['case_url']
            title = row['case_title']
            
            logger.info(f"Processing: {title}")
            
            text_content = fetch_case_text(url)
            if not text_content:
                logger.warning(f"Failed to fetch content for {url}")
                idx += 1
                continue
            
            metadata = {
                "title": title, 
                "url": url, 
                "author": row.get('case_author', ''),
                "status": "active"
            }
            
            success = process_and_store_document(text_content, metadata, doc_id=str(idx))
            
            if success:
                time.sleep(4)
            
            idx += 1
            
    logger.info("Ingestion Complete!")

if __name__ == "__main__":
    ingest_data()
