from fastapi import FastAPI, HTTPException, Request, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl
from app.core.rag import query_legal_assistant, EMBED_MODEL
from app.core.crawler import crawl_and_ingest
from app.ingest import ingest_case_from_url, ingest_case_from_file, _get_plain_converter, _get_ocr_converter
from app.core.extraction import extract_legal_metadata
from app.utils.pinecone import get_pinecone_index, get_pinecone_client
import time
import os
import uuid
import tempfile
import traceback
import threading
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from typing import Literal

# ─── In-memory Task Registry ────────────────────────────────────────────────
# Stores status of background ingestion jobs. Thread-safe via Lock.
# Keys: task_id (str), Values: dict with status/result/error
_task_registry: dict[str, dict] = {}
_task_lock = threading.Lock()


def _set_task(task_id: str, status: Literal["pending", "running", "done", "failed"], **kwargs):
    with _task_lock:
        _task_registry[task_id] = {"status": status, "task_id": task_id, **kwargs}


def _get_task(task_id: str) -> dict | None:
    with _task_lock:
        return _task_registry.get(task_id)


# ─── Background Workers ──────────────────────────────────────────────────────

def _run_url_ingestion(task_id: str, url: str, force: bool = False):
    """Background worker: fetch, embed and store a case from a URL."""
    _set_task(task_id, "running", url=url, started_at=time.time())
    try:
        from app.ingest import is_url_already_ingested
        if not force and is_url_already_ingested(url):
            _set_task(task_id, "done", url=url,
                      message="URL already in knowledge base (skipped). Use force=true to re-ingest.")
            return
        
        # Call with force=True since we already handled dedup above
        from app.ingest import ingest_case_from_url
        success = ingest_case_from_url(url)
        if success:
            _set_task(task_id, "done", url=url, message="Successfully ingested content from verified URL.")
        else:
            _set_task(task_id, "failed", url=url,
                      error="process_and_store_document returned False. Check Render logs for details.")
    except Exception as e:
        _set_task(task_id, "failed", url=url, error=str(e), trace=traceback.format_exc())


def _run_file_ingestion(task_id: str, tmp_path: str, original_filename: str, title: str | None):
    """Background worker: convert, embed and store a case from a temp file."""
    _set_task(task_id, "running", file_name=original_filename, started_at=time.time())
    try:
        success = ingest_case_from_file(tmp_path, title=title)
        if success:
            _set_task(task_id, "done", file_name=original_filename, message=f"Successfully ingested '{original_filename}'.")
        else:
            _set_task(task_id, "failed", file_name=original_filename, error="Ingestion returned False. File may be empty, corrupt, or contain no extractable text.")
    except Exception as e:
        _set_task(task_id, "failed", file_name=original_filename, error=str(e), trace=traceback.format_exc())
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ─── FastAPI App ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify Pinecone connection on startup
    try:
        index = get_pinecone_index()
        stats = index.describe_index_stats()
        print(f"Connected to Pinecone index: {os.getenv('PINECONE_INDEX_NAME')}")
        print(f"Total vector count: {stats['total_vector_count']}")
    except Exception as e:
        print(f"Warning: Could not connect to Pinecone on startup: {e}")
    yield

app = FastAPI(title="Legal AI Assistant API", lifespan=lifespan)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "Validation Error", "detail": exc.errors(), "code": 422},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "Client Error" if exc.status_code < 500 else "Server Error", "detail": str(exc.detail), "code": exc.status_code},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc), "code": 500},
    )

# Allow CORS for frontend
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Pydantic Models ──────────────────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    idea: str = Field(..., min_length=5, description="The abstract idea to analyze")

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="The user query")

class CrawlRequest(BaseModel):
    url: HttpUrl = Field(..., description="The URL to crawl for related cases")

class LearnRequest(BaseModel):
    url: HttpUrl = Field(..., description="The IndianKanoon URL to learn from")
    force: bool = Field(False, description="If true, bypass dedup check and re-ingest")

# ─── Core Endpoints ───────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"status": "Legal AI Backend is running"}

@app.post("/api/query")
def query_assistant(request: QueryRequest):
    result = query_legal_assistant(request.query)
    return JSONResponse(content=result)

@app.post("/api/analyze")
def analyze_idea(request: AnalysisRequest):
    result = query_legal_assistant(request.idea)
    return JSONResponse(content=result)

# ─── Ingestion Endpoints (Non-Blocking) ──────────────────────────────────────

@app.post("/api/learn/url", status_code=202)
def learn_from_url(request: LearnRequest, background_tasks: BackgroundTasks):
    """
    Queue an IndianKanoon URL for ingestion.

    Returns 202 Accepted immediately with a task_id.
    Poll GET /api/tasks/{task_id} to check progress.
    The actual fetch → embed → store pipeline runs in the background,
    bypassing Render's 30-second HTTP gateway timeout.
    """
    task_id = str(uuid.uuid4())
    url = str(request.url)
    _set_task(task_id, "pending", url=url, queued_at=time.time())
    background_tasks.add_task(_run_url_ingestion, task_id, url, request.force)
    return {
        "message": "Ingestion queued. Poll /api/tasks/{task_id} for status.",
        "task_id": task_id,
        "url": url,
    }


@app.get("/api/tasks/{task_id}")
def get_task_status(task_id: str):
    """
    Poll the status of a background ingestion job.

    Returns one of: pending | running | done | failed
    """
    task = _get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")
    return task


# ─── File Upload Endpoint (Non-Blocking) ─────────────────────────────────────

# Supported file types for upload ingestion
_SUPPORTED_UPLOAD_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",        # .xlsx
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",# .pptx
    "application/msword",          # legacy .doc
    "text/plain",
    "text/html",
    "text/csv",
    "application/json",
    "application/epub+zip",
    "image/jpeg",
    "image/png",
    "application/zip",
}


@app.post("/api/learn/file", status_code=202)
async def learn_from_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    Queue a file for ingestion into the knowledge base.

    Accepts PDF, DOCX, XLSX, PPTX, images, ZIP, TXT, HTML, CSV, JSON, EPub.
    Returns 202 Accepted immediately with a task_id.
    Poll GET /api/tasks/{task_id} to check progress.
    """
    if file.content_type not in _SUPPORTED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Supported: PDF, DOCX, XLSX, PPTX, images, ZIP, TXT, HTML, CSV, JSON, EPub."
            ),
        )

    # Write to a named temp file so MarkItDown can detect the extension.
    # The background worker is responsible for deleting it after processing.
    suffix = Path(file.filename).suffix if file.filename else ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    title = Path(file.filename).stem.replace("_", " ").replace("-", " ") if file.filename else None
    task_id = str(uuid.uuid4())
    _set_task(task_id, "pending", file_name=file.filename, queued_at=time.time())
    background_tasks.add_task(_run_file_ingestion, task_id, tmp_path, file.filename, title)

    return {
        "message": "File ingestion queued. Poll /api/tasks/{task_id} for status.",
        "task_id": task_id,
        "file_name": file.filename,
    }


# ─── Crawl Endpoint ──────────────────────────────────────────────────────────

@app.post("/api/crawl", status_code=202)
def crawl_url(request: CrawlRequest, background_tasks: BackgroundTasks):
    """
    Scout related cases from a URL and queue them for ingestion.
    Returns 202 Accepted immediately.
    """
    task_id = str(uuid.uuid4())

    def _run_crawl(task_id: str, url: str):
        _set_task(task_id, "running", url=url, started_at=time.time())
        try:
            cases = crawl_and_ingest(url, limit=3)
            ingested_count = 0
            for case in cases:
                success = ingest_case_from_url(case['url'], title=case['title'])
                if success:
                    ingested_count += 1
                    time.sleep(2)
            _set_task(task_id, "done", url=url, ingested_count=ingested_count, cases=cases)
        except Exception as e:
            _set_task(task_id, "failed", url=url, error=str(e), trace=traceback.format_exc())

    _set_task(task_id, "pending", url=str(request.url), queued_at=time.time())
    background_tasks.add_task(_run_crawl, task_id, str(request.url))
    return {"message": "Crawl queued.", "task_id": task_id, "url": str(request.url)}


# ─── Cases List Endpoint ──────────────────────────────────────────────────────

@app.get("/api/cases")
def get_cases():
    """
    Fetch all ingested cases by doing a generic semantic search.
    Returns the first chunk (chunk_index==0) of every ingested document.
    """
    pc = get_pinecone_client()
    index = get_pinecone_index()

    embedding = pc.inference.embed(
        model=EMBED_MODEL,
        inputs=["law case judgment summary research document"],
        parameters={"input_type": "query"}
    )

    # Use empty namespace "" — consistent with the upsert namespace in ingest.py
    search_results = index.query(
        namespace="",
        vector=embedding[0]['values'],
        top_k=100,
        filter={"chunk_index": {"$eq": 0}},
        include_metadata=True
    )

    cases = []
    if search_results and hasattr(search_results, 'matches'):
        for match in search_results.matches:
            meta = match.metadata
            # Strip leading markdown heading markers (## / ###) from titles
            # These appear when the first chunk of a doc starts with a heading
            raw_title = meta.get("title", "Unknown Case")
            clean_title = raw_title.lstrip("#").strip().split("\n")[0][:120]
            cases.append({
                "id": match.id,
                "title": clean_title,
                "url": meta.get("url", ""),
                "score": match.score,
                "legal_domain": meta.get("ai_legal_domain", ""),
                "judgment_date": meta.get("ai_judgment_date", ""),
            })

    return {"cases": cases}


# ─── Diagnostic Endpoints ─────────────────────────────────────────────────────

@app.get("/api/health/diagnostics")
def run_diagnostics():
    import requests
    from app.ingest import process_and_store_document
    results = {}

    # 1. Test IndianKanoon Reachability
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        resp = requests.get("https://indiankanoon.org/doc/1712542/", headers=headers, timeout=10)
        results["indian_kanoon_status"] = resp.status_code
    except Exception as e:
        results["indian_kanoon_status"] = f"Error: {e}"

    # 2. Test Full Ingestion Pipeline
    try:
        dummy_text = "# Minerva Mills Ltd v Union of India (1980)\n\n## Held\nParliament has no power to abrogate the fundamental rights."
        meta = {"title": "Diagnostic Test", "url": "test", "status": "active"}
        import io, sys
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        success = process_and_store_document(dummy_text, meta, doc_id="diag_123")
        stdout_val = sys.stdout.getvalue()
        stderr_val = sys.stderr.getvalue()
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        results["ingestion_pipeline_success"] = success
        results["ingestion_pipeline_stdout"] = stdout_val
        results["ingestion_pipeline_stderr"] = stderr_val
    except Exception as e:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        results["ingestion_pipeline_error"] = f"Error: {e}\n{traceback.format_exc()}"

    return results


@app.get("/api/health/ik_api")
def test_ik_api():
    import requests
    from app.core.scraper import fetch_case_text

    results = {}
    ik_token = os.environ.get("IK_API_TOKEN", "").strip()
    if not ik_token:
        results["error"] = "IK_API_TOKEN not found"
        return results

    docid = "257876"
    api_url = f"https://api.indiankanoon.org/doc/{docid}/"
    api_headers = {
        "Authorization": f"Token {ik_token}",
        "Accept": "application/json"
    }
    try:
        api_resp = requests.post(api_url, headers=api_headers, timeout=10)
        results["api_test"] = {
            "status_code": api_resp.status_code,
            "response": api_resp.text[:500]
        }
    except Exception as e:
        results["api_test"] = {"error": str(e)}

    try:
        text = fetch_case_text("https://indiankanoon.org/doc/257876/")
        results["fetch_case_text_length"] = len(text)
        results["fetch_case_text_preview"] = text[:500]
        ai_meta = extract_legal_metadata(text[:25000])
        results["extraction_test"] = ai_meta
    except Exception as e:
        results["fetch_case_text_error"] = str(e)
        results["fetch_case_text_trace"] = traceback.format_exc()

    return results
