# TechNiche Backend — Requirements

> **Milestone:** Backend Hardening & Patent Demonstration  
> **Generated:** 2026-03-23  
> **Status:** Active

---

## 1. Reliability & Error Handling

### 1.1 — Structured Error Responses
**Priority:** P0 (Critical)  
**Rationale:** Raw Python exceptions leaking as 500 errors break the demo and look unprofessional in a patent context.

All endpoints must return JSON error responses conforming to:
```json
{ "error": "string", "detail": "string", "code": "string" }
```
No raw `str(e)` leaks. Internal stack traces logged to log file, not sent to client.

### 1.2 — Retry Logic with Exponential Backoff
**Priority:** P0 (Critical)  
**Rationale:** OpenRouter and Pinecone calls can transiently fail. Without retry, one bad call fails the whole demo.

- Pinecone operations: 3 retries, backoff starting at 0.5s
- OpenRouter LLM calls: 3 retries, backoff starting at 1s
- Retry only on network/timeout errors, not on 4xx validation errors

### 1.3 — Input Validation Hardening
**Priority:** P1**  
All request fields validated: non-empty, maximum length enforced (query ≤ 2000 chars, URL format-validated). Return 422 with field-level detail on invalid input.

---

## 2. New Endpoints

### 2.1 — Health Check (`GET /api/health`)
**Priority:** P0 (Critical for demo)  
Returns:
```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "pinecone": { "connected": bool, "index_name": "string", "vector_count": int },
  "models": { "embed_model": "string", "llm_provider": "openrouter" },
  "uptime_seconds": float
}
```

### 2.2 — Stats Endpoint (`GET /api/stats`)
**Priority:** P1  
Returns index-level statistics:
```json
{
  "total_vectors": int,
  "unique_cases": int,
  "domain_breakdown": { "domain_name": int, ... },
  "index_fullness": float
}
```

---

## 3. Performance

### 3.1 — Response Caching
**Priority:** P1  
In-memory TTL cache (TTL = 300 seconds) on `/api/query` and `/api/analyze` keyed by normalized query string. Cache must be invalidated when new cases are ingested.

### 3.2 — Async Endpoint Handlers
**Priority:** P1  
Convert all endpoint handler functions to `async def`. Pinecone and HTTP calls use `asyncio.to_thread()` where sync SDKs are used.

### 3.3 — Startup Validation
**Priority:** P0**  
On server startup, verify Pinecone connection and abort with clear error if failing. Log startup diagnostics.

---

## 4. Cleanup & Tech Debt

### 4.1 — Remove ChromaDB Artifacts
**Priority:** P1  
Delete `backend/chroma_db/` and `backend/chroma_db_test/` directories. Remove any ChromaDB imports from codebase.

### 4.2 — Reorganize Loose Scripts
**Priority:** P2  
Move `script.py`, `script2.py`, `script3.py`, `train_bot.py`, `list_models.py`, `verify_api.py`, `verify_conflict.py`, `verify_key.py` to `backend/scripts/`. Add `README` in `scripts/`.

### 4.3 — Dependency Pinning
**Priority:** P1  
`requirements.txt` — exact pinned versions for all production deps.  
`requirements-dev.txt` — test/dev deps (`pytest`, `httpx`, `pytest-asyncio`).

### 4.4 — CORS Hardening
**Priority:** P1  
CORS `allow_origins` must read from `ALLOWED_ORIGINS` environment variable. Default to `http://localhost:3000` in development. Wildcard `*` must not be set in production.

---

## 5. Testing

### 5.1 — Unit Tests: Core Modules
**Priority:** P0 (Required for patent demonstration)  
- `test_rag.py` — query_legal_assistant happy path, empty context path, citation verification logic
- `test_extraction.py` — Pydantic extraction, field validation, overruled case detection  
- `test_temporal.py` — Temporal conflict resolution: new overrules old, old cannot overrule new, no conflict scenario
- `test_crawler.py` — crawler returns structured case list, handles bad URLs gracefully

### 5.2 — Integration Tests: API Endpoints
**Priority:** P0  
Using `httpx`/`TestClient` with mocked Pinecone and OpenRouter:
- `test_api_health.py` — `/api/health` returns correct schema
- `test_api_query.py` — `/api/query` returns response + citations, handles empty query
- `test_api_analyze.py` — `/api/analyze` returns analysis, handles empty idea
- `test_api_learn.py` — `/api/learn/url` returns success, handles bad URL
- `test_api_cases.py` — `/api/cases` returns case list
- `test_api_stats.py` — `/api/stats` returns correct schema

### 5.3 — Error Path Tests
**Priority:** P1  
- Pinecone connection failure → `/api/health` returns `degraded`
- OpenRouter model failure → fallback to next model in cascade
- Invalid URL → 422 with field error detail
- Empty vector store → `/api/query` returns graceful "no results" response, not 500

---

## 6. Out of Scope

- Gemini as primary LLM — OpenRouter cascade remains the primary provider
- Redis or distributed caching — in-memory is sufficient for demo
- Frontend changes
- Authentication / API key gating
- Persistent query logging / analytics
