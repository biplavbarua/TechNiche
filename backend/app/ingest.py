import csv
import os
import sys
import hashlib
import logging
import time
from datetime import date, datetime

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
    """Verifies Pinecone connection by attempting to list or search."""
    try:
        index = get_pinecone_index()
        # Attempt a minimal search or list operation
        results = index.list(prefix=None, limit=1)
        if results:
            return True
        search_results = index.search(
            namespace="__default__",
            query={
                "top_k": 1,
                "inputs": {"text": "test query"},
            },
            model=EMBED_MODEL,
        )
        if search_results:
            return True
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
        index = get_pinecone_index()
        # Pinecone doesn't support direct metadata-only filtering on list,
        # so we do a dummy search with a filter instead.
        search_results = index.search(
            namespace="__default__",
            query={
                "top_k": 1,
                "inputs": {"text": url},
                "filter": {"url": {"$eq": url}}
            },
            model=EMBED_MODEL,
        )
        if search_results and hasattr(search_results, 'result') and search_results.result.hits:
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
                    namespace="__default__"
                )
            except Exception as e:
                logger.error(f"Failed to mark record {record_id} as overruled: {e}")

        logger.info(
            f"TEMPORAL CONFLICT RESOLVED: Marked {len(ids_to_update)} chunks of "
            f"'{case_name}' as 'overruled' by '{new_case_title}'."
        )


def _find_case_in_db(case_name: str) -> list | None:
    """
    Semantic search to find a case by name in Pinecone using Integrated Embeddings.
    Uses the serverless result.hits format (not the legacy Pod 'matches' key).
    """
    try:
        index = get_pinecone_index()
        search_results = index.search(
            namespace="__default__",
            query={
                "top_k": 5,
                "inputs": {"text": case_name},
                "filter": {"status": {"$eq": "active"}}
            }
        )

        # Serverless Pinecone returns hits under result.hits, not 'matches'
        hits = []
        if hasattr(search_results, 'result') and search_results.result and hasattr(search_results.result, 'hits'):
            hits = search_results.result.hits or []

        # Only return high-confidence matches (score > 0.7)
        confident_matches = [
            {"_id": hit.get("_id"), "metadata": hit.get("fields", {})}
            for hit in hits if hit.get("_score", 0) > 0.7
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
        
        # ── Upsert chunks to Pinecone using Integrated Embeddings ──
        records = []
        for i, chunk in enumerate(chunks):
            chunk_id = doc_id if (doc_id and i == 0) else generate_deterministic_id(chunk, i)
            
            # Each chunk inherits parent metadata + chunk index
            chunk_metadata = {**metadata, "chunk_index": i, "total_chunks": len(chunks)}
            
            records.append({
                "_id": chunk_id,
                "text": chunk,  # Pinecone Integrated Embeddings reads from the "text" field
                **chunk_metadata,
            })
        
        # Upsert in batches of 96 (Pinecone's recommended batch size for integrated embeddings)
        BATCH_SIZE = 96
        stored_count = 0
        for batch_start in range(0, len(records), BATCH_SIZE):
            batch = records[batch_start:batch_start + BATCH_SIZE]
            index.upsert_records(namespace="__default__", records=batch)
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
