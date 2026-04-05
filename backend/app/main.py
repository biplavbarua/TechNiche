from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, HttpUrl
from app.core.rag import query_legal_assistant, EMBED_MODEL
from app.core.crawler import crawl_and_ingest
from app.ingest import ingest_case_from_url
from app.utils.pinecone import get_pinecone_index, get_pinecone_client
import time
import os
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
