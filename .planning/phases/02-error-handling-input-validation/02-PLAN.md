# Phase 02: Error Handling & Input Validation - Plan

## Goal
No raw exceptions ever reach the client. All endpoints validate inputs strictly, and CORS is hardened against wildcard vulnerabilities.

## Phase Plans

### 2-01: Implement Structured Global Error Handling
**File:** `backend/app/main.py`
- Import `Request` and `JSONResponse` from `fastapi`.
- Add a global exception handler `@app.exception_handler(Exception)` that catches all unhandled exceptions.
- The handler should return a JSON format like `{"error": "Internal Server Error", "detail": str(e), "code": 500}`.
- Refactor all existing `except Exception as e:` blocks within the endpoint functions (`/api/crawl`, `/api/learn/url`, `/api/analyze`, `/api/query`, `/api/cases`). Remove the overly broad generic exception raising in favor of either relying on the global handler (which catches everything) or raising targeted `HTTPException` codes without exposing internal tracebacks in normal responses where a standard formatted error is desired. We want to ensure an intentional error payload returns `{"error": ...}` instead of exposing raw Pydantic errors or exception stacktraces. Note that since we're using FastAPI's default `HTTPException`, a global handler for `Exception` won't catch `HTTPException`. So also add a custom exception handler for `HTTPException` returning our standard format.

### 2-02: Input Validation Hardening
**File:** `backend/app/main.py`
- Update the Pydantic models to use `Field` and properly typed fields:
  ```python
  from pydantic import BaseModel, Field, HttpUrl
  
  class AnalysisRequest(BaseModel):
      idea: str = Field(..., min_length=5, description="The abstract idea to analyze")

  class QueryRequest(BaseModel):
      query: str = Field(..., min_length=2, description="The user query")

  class CrawlRequest(BaseModel):
      url: HttpUrl = Field(..., description="The URL to crawl for related cases")

  class LearnRequest(BaseModel):
      url: HttpUrl = Field(..., description="The Wikipedia URL to learn from")
  ```
- With these Pydantic validations in place, remove the manual empty checks in the endpoints like `if not request.idea: raise HTTPException...`.

### 2-03: CORS Hardening and Documentation
**File:** `backend/app/main.py`
- Modify the `CORSMiddleware` configuration. Parse the comma-separated `ALLOWED_ORIGINS` environment variable.
  ```python
  allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")
  origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]
  ```
- Apply these `origins` to `allow_origins`. Explicitly do not include `*` unless the environment mandates it for some external integration (and even then, strictly parse the env).

**File:** `backend/.env.example`
- Add `ALLOWED_ORIGINS=http://localhost:3000` to the example file.

## Verification
- Send empty `{}` to `/api/query` → expect 422 with structured field errors.
- Send malformed URL (e.g., `not_a_url`) to `/api/learn/url` → expect 422.
- Intentionally cause a Pinecone error (e.g. by passing an invalid value temporarily) and ensure a clean structured JSON format is returned instead of an unstructured traceback string.
