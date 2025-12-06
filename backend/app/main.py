from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.core.rag import query_legal_assistant
from app.core.crawler import crawl_and_ingest
from app.ingest import get_embedding, collection
import time
from fastapi.middleware.cors import CORSMiddleware

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

@app.post("/api/crawl")
def crawl_url(request: CrawlRequest):
    """
    Autonomous Learning Endpoint.
    Crawls the given URL for more cases and ingests them.
    """
    try:
        cases = crawl_and_ingest(request.url, limit=3)
        ingested_count = 0
        
        for case in cases:
            # Re-using ingestion logic (simplified)
            embedding = get_embedding(case['title']) # Naive: embedding title for quick check
            # Real impl would fetch text
            if embedding:
                collection.add(
                    documents=[f"Case Title: {case['title']} (Autonomously Learned)"],
                    metadatas=[{"title": case['title'], "url": case['url']}],
                    ids=[f"auto_{int(time.time())}_{ingested_count}"],
                    embeddings=[embedding]
                )
                ingested_count += 1
                
        return {"message": f"Successfully scouted and learned {ingested_count} new potential cases.", "cases": cases}
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
