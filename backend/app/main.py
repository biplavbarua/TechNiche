from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.core.rag import query_legal_assistant
from app.core.crawler import crawl_and_ingest
from app.ingest import collection, ingest_case_from_url
import time
from fastapi.middleware.cors import CORSMiddleware
from pydantic import HttpUrl

app = FastAPI(title="Legal AI Assistant API")

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for demo; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    idea: str

@app.get("/")
def read_root():
    return {"status": "Legal AI Backend is running"}

class CrawlRequest(BaseModel):
    url: str

class LearnRequest(BaseModel):
    url: str

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
            # Check if likely already exists is handled inside ingest, but doing it here saves a fetch call
            # We will just call our robust function
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
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
