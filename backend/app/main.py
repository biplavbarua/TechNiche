from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.core.rag import query_legal_assistant, EMBED_MODEL
from app.core.crawler import crawl_and_ingest
from app.ingest import ingest_case_from_url
from app.utils.pinecone import get_pinecone_index, get_pinecone_client
import time
import os
from fastapi.middleware.cors import CORSMiddleware
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

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    idea: str

class QueryRequest(BaseModel):
    query: str

class CrawlRequest(BaseModel):
    url: str

class LearnRequest(BaseModel):
    url: str

@app.get("/")
def read_root():
    return {"status": "Legal AI Backend is running"}

@app.post("/api/crawl")
def crawl_url(request: CrawlRequest):
    """
    Autonomous Learning Endpoint.
    Crawls the given URL for more cases and ingests them.
    """
    try:
        # 1. Scout for new cases
        cases = crawl_and_ingest(request.url, limit=3)
        ingested_count = 0
        
        # 2. Ingest found cases
        for case in cases:
            success = ingest_case_from_url(case['url'], title=case['title'])
            if success:
                ingested_count += 1
                # Politeness delay
                time.sleep(2)
                
        return {"message": f"Successfully scouted and learned {ingested_count} new potential cases.", "cases": cases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/learn/url")
def learn_from_url(request: LearnRequest):
    """
    Manually learn from a specific URL.
    """
    try:
        success = ingest_case_from_url(request.url)
        if success:
            return {"message": "Successfully ingested content from verified URL.", "url": request.url}
        else:
            raise HTTPException(status_code=400, detail="Failed to ingest content. Check URL or content accessibility.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
def analyze_idea(request: AnalysisRequest):
    try:
        if not request.idea:
            raise HTTPException(status_code=400, detail="Idea cannot be empty")
        
        result = query_legal_assistant(request.idea)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
def query_assistant(request: QueryRequest):
    try:
        if not request.query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        result = query_legal_assistant(request.query)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cases")
def get_cases():
    """
    Fetch all ingested cases by doing a generic search.
    """
    try:
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
    except Exception as e:
        print(f"Error fetching cases: {e}")
        return {"cases": [], "error": str(e)}
