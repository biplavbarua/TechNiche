from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.core.rag import query_legal_assistant
from app.core.crawler import crawl_and_ingest
from app.ingest import index, ingest_case_from_url
import time
from fastapi.middleware.cors import CORSMiddleware
from pydantic import HttpUrl

app = FastAPI(title="Legal AI Assistant API")

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
        return JSONResponse(content=result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/query")
def query_assistant(request: QueryRequest):
    try:
        if not request.query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        result = query_legal_assistant(request.query)
        return JSONResponse(content=result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cases")
def get_cases():
    """
    Fetch all ingested cases by doing a generic search.
    """
    try:
        from app.core.rag import index, EMBED_MODEL, pc
        
        # Perform similarity search using inference
        embedding = pc.inference.embed(
            model=EMBED_MODEL,
            inputs=["law case judgment summary"],
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
                fields = match.metadata or {}
                
                case_data = {
                    "id": match.id,
                    "title": fields.get("title", "Unknown Case"),
                    "url": fields.get("url", ""),
                    "judgment_date": fields.get("ai_judgment_date", fields.get("date", "Unknown")),
                    "domain": fields.get("ai_legal_domain", fields.get("domain", "General")),
                    "summary": fields.get("ai_summary", fields.get("text", "No summary available.")),
                    "status": fields.get("status", "active"),
                }
                cases.append(case_data)
        
        # Sort alphabetically by title
        cases.sort(key=lambda x: x["title"])
        return {"cases": cases}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

