from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl
from app.core.rag import query_legal_assistant, EMBED_MODEL
from app.core.crawler import crawl_and_ingest
from app.ingest import ingest_case_from_url, ingest_case_from_file, _get_plain_converter, _get_ocr_converter
from app.core.extraction import extract_legal_metadata
from app.utils.pinecone import get_pinecone_index, get_pinecone_client
import time
import os
import tempfile
import traceback
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify Pinecone connection on startup
    try:
        index = get_pinecone_index()
        # Get the index stats to verify connection
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

class AnalysisRequest(BaseModel):
    idea: str = Field(..., min_length=5, description="The abstract idea to analyze")

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, description="The user query")

class CrawlRequest(BaseModel):
    url: HttpUrl = Field(..., description="The URL to crawl for related cases")

class LearnRequest(BaseModel):
    url: HttpUrl = Field(..., description="The Wikipedia URL to learn from")

@app.get("/")
def read_root():
    return {"status": "Legal AI Backend is running"}

@app.get("/api/health/diagnostics")
def run_diagnostics():
    import traceback
    import requests
    from app.ingest import process_and_store_document
    results = {}
    
    # 1. Test IndianKanoon Reachability (Check if Render IP is blocked)
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        resp = requests.get("https://indiankanoon.org/doc/1712542/", headers=headers, timeout=10)
        results["indian_kanoon_status"] = resp.status_code
    except Exception as e:
        results["indian_kanoon_status"] = f"Error: {e}"
        
    # 2. Test Full Ingestion Pipeline (Memory/Pinecone/Embeddings)
    try:
        dummy_text = "# Minerva Mills Ltd v Union of India (1980)\\n\\n## Held\\nParliament has no power to abrogate the fundamental rights."
        meta = {"title": "Diagnostic Test", "url": "test", "status": "active"}
        
        # We will capture stdout/stderr to see what process_and_store_document prints
        import io, sys
        old_stdout = sys.stdout
        old_stderr = sys.stderr
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
        results["ingestion_pipeline_error"] = f"Error: {e}\\n{traceback.format_exc()}"
        
    return results

@app.post("/api/crawl")
def crawl_url(request: CrawlRequest):
    """
    Autonomous Learning Endpoint.
    Crawls the given URL for more cases and ingests them.
    """
    # 1. Scout for new cases
    cases = crawl_and_ingest(str(request.url), limit=3)
    ingested_count = 0
    
    # 2. Ingest found cases
    for case in cases:
        success = ingest_case_from_url(case['url'], title=case['title'])
        if success:
            ingested_count += 1
            # Politeness delay
            time.sleep(2)
            
    return {"message": f"Successfully scouted and learned {ingested_count} new potential cases.", "cases": cases}

@app.get("/api/health/ik_api")
def test_ik_api():
    import os
    import requests
    ik_token = os.environ.get("IK_API_TOKEN", "").strip()
    if not ik_token:
        return {"error": "IK_API_TOKEN not found"}
    
    docid = "257876"
    api_url = f"https://api.indiankanoon.org/doc/{docid}/"
    api_headers = {
        "Authorization": f"Token {ik_token}",
        "Accept": "application/json"
    }
    try:
        api_resp = requests.post(api_url, headers=api_headers, timeout=10)
        return {
            "status_code": api_resp.status_code,
            "response": api_resp.text[:500]
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/learn/url")
def learn_from_url(request: LearnRequest):
    """
    Manually learn from a specific URL.
    """
    success = ingest_case_from_url(str(request.url))
    if success:
        return {"message": "Successfully ingested content from verified URL.", "url": str(request.url)}
    else:
        raise HTTPException(status_code=400, detail="Failed to ingest content. Check URL or content accessibility.")


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


@app.post("/api/learn/file")
async def learn_from_file(file: UploadFile = File(...)):
    """
    Ingest a local file (PDF, DOCX, XLSX, PPTX, image, ZIP, …) into the
    knowledge base.

    The file is converted to clean Markdown by MarkItDown before being
    chunked, embedded, and stored in Pinecone.  For PDF/DOCX/PPTX/XLSX
    the OCR plugin is used automatically so scanned documents work too.
    """
    if file.content_type not in _SUPPORTED_UPLOAD_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Supported: PDF, DOCX, XLSX, PPTX, images, ZIP, TXT, HTML, CSV, JSON, EPub."
            ),
        )

    # Write to a named temp file so MarkItDown can detect the extension
    suffix = Path(file.filename).suffix if file.filename else ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        title = Path(file.filename).stem.replace("_", " ").replace("-", " ") if file.filename else None
        success = ingest_case_from_file(tmp_path, title=title)
    finally:
        # Always clean up the temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if success:
        return {
            "message": f"Successfully ingested '{file.filename}'.",
            "file_name": file.filename,
            "content_type": file.content_type,
        }
    else:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Failed to ingest '{file.filename}'. "
                "The file may be empty, corrupt, or contain no extractable text."
            ),
        )

@app.post("/api/analyze")
def analyze_idea(request: AnalysisRequest):
    result = query_legal_assistant(request.idea)
    return JSONResponse(content=result)

@app.post("/api/query")
def query_assistant(request: QueryRequest):
    result = query_legal_assistant(request.query)
    return JSONResponse(content=result)

@app.get("/api/cases")
def get_cases():
    """
    Fetch all ingested cases by doing a generic search.
    """
    pc = get_pinecone_client()
    index = get_pinecone_index()
    
    # Perform similarity search using inference to find cases
    embedding = pc.inference.embed(
        model=EMBED_MODEL,
        inputs=["law case judgment summary research document"],
        parameters={"input_type": "query"}
    )
    
    search_results = index.query(
        namespace="__default__",
        vector=embedding[0]['values'],
        top_k=100,
        filter={"chunk_index": {"$eq": 0}},
        include_metadata=True
    )
    
    cases = []
    if search_results and hasattr(search_results, 'matches'):
        for match in search_results.matches:
            meta = match.metadata
            cases.append({
                "id": match.id,
                "title": meta.get("title", "Unknown Case"),
                "url": meta.get("url", ""),
                "score": match.score
            })
    
    return {"cases": cases}
