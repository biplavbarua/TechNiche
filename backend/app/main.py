from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.core.rag import query_legal_assistant
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

@app.post("/api/analyze")
def analyze_idea(request: AnalysisRequest):
    try:
        if not request.idea:
            raise HTTPException(status_code=400, detail="Idea cannot be empty")
        
        result = query_legal_assistant(request.idea)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
