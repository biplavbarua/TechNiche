# Phase 02: Error Handling & Input Validation - Research

## Context
Goal: Ensure no raw exceptions reach the client and that inputs are strictly validated.

## Findings
1. **Current Error Handling:**
   In `backend/app/main.py`, practically all major API endpoints have a generic `try-except` block matching:
   ```python
   except Exception as e:
       raise HTTPException(status_code=500, detail=str(e))
   ```
   This exposes internal Python tracebacks/error string representations directly to clients.

2. **Current Input Validation:**
   In `backend/app/main.py`:
   ```python
   class AnalysisRequest(BaseModel):
       idea: str

   class QueryRequest(BaseModel):
       query: str

   class CrawlRequest(BaseModel):
       url: str

   class LearnRequest(BaseModel):
       url: str
   ```
   Endpoints check things like `if not request.idea:` manually instead of relying on Pydantic's powerful validators. `url` fields are plain strings.

3. **Current CORS Config:**
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*", "http://localhost:3000"],
       # ...
   ```
   The wildcard `"*"` is hardcoded.

## Architectural Decisions
- Implement a global exception handler in `main.py` using `@app.exception_handler(Exception)` and custom exception classes (if necessary) to ensure a standardized JSON format: `{"error": "Internal Server Error", "detail": "...", "code": 500}`.
- Refactor the Pydantic models to use `Field(..., min_length=1)` and `HttpUrl` (or string with regex) for the URL fields so validation happens before handler execution.
- Update CORS middleware to read `ALLOWED_ORIGINS` from the `.env` via `os.getenv`, falling back to `["http://localhost:3000"]` and strictly avoid `*`.

## Target Files
- `backend/app/main.py`: Update models, exception handlers, remove manual `if not foo`, configure CORS.
- `backend/.env.example`: Document `ALLOWED_ORIGINS`.
