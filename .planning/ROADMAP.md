# TechNiche Backend — Roadmap

> **Milestone 1:** Backend Hardening & Patent Demonstration  
> **Goal:** Bulletproof backend — zero silent failures, comprehensive tests, clean codebase, new essential endpoints  
> **Granularity:** Standard (5-7 phases)

---

## Phase 1: Codebase Cleanup & Dependency Hardening
**Goal:** Clean foundation before adding features. Remove dead code, pin deps, restructure loose scripts.

### Plans
1. **Delete ChromaDB artifacts** — remove `backend/chroma_db/`, `backend/chroma_db_test/` directories; audit and remove any ChromaDB imports
2. **Reorganize scripts** — move all loose root scripts to `backend/scripts/` with a `README.md`
3. **Pin dependencies** — rewrite `requirements.txt` with exact pinned versions; create `requirements-dev.txt` with pytest, httpx, pytest-asyncio

### Verification
- `ls backend/` — no `chroma_db*` directories remain
- `ls backend/scripts/` — all loose scripts present
- `pip install -r backend/requirements.txt` — installs cleanly in a fresh venv
- `pip install -r backend/requirements-dev.txt` — test deps install cleanly

---

## Phase 2: Error Handling & Input Validation
**Goal:** No raw exceptions ever reach the client. All endpoints validate inputs strictly.

### Plans
1. **Structured error middleware** — global exception handler returning `{"error": ..., "detail": ..., "code": ...}`; replace all bare `raise HTTPException(status_code=500, detail=str(e))` with typed handlers
2. **Input validation hardening** — add field constraints to all Pydantic models (non-empty, max lengths, URL format validation for CrawlRequest/LearnRequest)
3. **CORS hardening** — `allow_origins` reads from `ALLOWED_ORIGINS` env var; document in `.env.example`

### Verification
- Send empty `{}` to `/api/query` → expect 422 with field errors
- Send malformed URL to `/api/learn/url` → expect 422
- Trigger a Pinecone error (disconnect test) → expect structured JSON error, not traceback
- `grep -r "allow_origins" backend/` — must not contain `["*"]` hardcoded

---

## Phase 3: New Endpoints (Health & Stats)
**Goal:** Observable backend — health and statistics endpoints for demo and monitoring.

### Plans
1. **`GET /api/health`** — checks Pinecone connectivity, returns connection status, index name, vector count, uptime; returns HTTP 200 when healthy, 503 when not
2. **`GET /api/stats`** — queries Pinecone `describe_index_stats()`, returns total vectors, unique cases (chunk_index=0 count), domain breakdown, index fullness

### Verification
- `curl http://localhost:8000/api/health` — returns `{"status": "healthy", "pinecone": {...}, ...}`
- `curl http://localhost:8000/api/stats` — returns `{"total_vectors": N, "unique_cases": M, ...}`
- With Pinecone key invalid → `/api/health` returns `{"status": "unhealthy"}`

---

## Phase 4: Retry Logic & Async Optimization
**Goal:** Transient failures auto-recover. I/O-bound endpoints use async properly.

### Plans
1. **Retry decorator** — implement `@retry_with_backoff(retries=3, base_delay=0.5)` utility; apply to Pinecone operations in `utils/pinecone.py` and OpenRouter LLM calls in `rag.py`
2. **Async endpoints** — convert all `def` endpoint handlers to `async def`; wrap sync Pinecone SDK calls in `asyncio.to_thread()`
3. **Response caching** — in-memory TTL cache (5 min) for `/api/query` and `/api/analyze`; cache invalidated on any new ingestion via `/api/learn/url` or `/api/crawl`

### Verification
- Run server, kill/restore network (or mock) — verify retry kicks in and request eventually succeeds
- Hit `/api/query` twice with same query — second response much faster (cache hit)
- Ingest a new URL → verify cache is cleared (next query re-fetches)
- Load test with 5 concurrent requests — no threading errors

---

## Phase 5: Comprehensive Test Suite
**Goal:** Every patent claim demonstrated by passing tests. Zero untested code paths in core modules.

### Plans
1. **Unit: Temporal Conflict Resolution** — `tests/test_temporal.py`: new case overrules old, old cannot overrule new, no-conflict scenario, malformed date handling
2. **Unit: Citation Verification** — `tests/test_citations.py`: citations that match retrieved chunks pass, citations not in context fail, partial match edge case
3. **Unit: Structured Extraction** — `tests/test_extraction.py`: happy path with valid legal text, missing fields handled, Pydantic validation catches bad output
4. **Integration: All API Endpoints** — `tests/test_api.py`: all 7 endpoints (including new health + stats) with `TestClient` and mocked external dependencies
5. **Integration: Error Paths** — `tests/test_error_paths.py`: empty inputs, invalid URLs, Pinecone down (mocked), all return correct codes and JSON shapes

### Verification
- `cd backend && python -m pytest tests/ -v` — all tests pass
- `cd backend && python -m pytest tests/ --tb=short -q` — pass summary shows 0 failures
- Minimum 80% line coverage on `core/rag.py`, `core/extraction.py` — `pytest --cov=app --cov-report=term-missing`

---

## Phase 6: Final Audit & Documentation
**Goal:** Patent-demo ready. Everything documented, startup validated, no loose ends.

### Plans
1. **Startup validation** — lifespan handler logs index stats, aborts startup clearly if Pinecone unreachable in production (`ENVIRONMENT=production` env check)
2. **Update README** — document all 7 endpoints, env variables, how to run tests, how to run scripts in `scripts/`; note patent claims with corresponding code references
3. **`.env.example` audit** — ensure all required env vars documented: `OPENROUTER_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `GOOGLE_API_KEY`, `ALLOWED_ORIGINS`, `ENVIRONMENT`

### Verification
- Remove `PINECONE_API_KEY` from env and start server → meaningful startup error logged
- `python -m pytest tests/ -v` — all tests pass (final check)
- Review README for completeness — all endpoints listed, all env vars documented

---

## Milestone Completion Criteria

- [ ] `python -m pytest tests/ -v` passes with 0 failures
- [ ] `curl /api/health` returns `{"status": "healthy"}`
- [ ] No `chroma_db` directories in `backend/`
- [ ] No wildcard `*` in CORS config (hardcoded)
- [ ] All 3 patent claim mechanisms testable via test suite
- [ ] README documents all endpoints and env vars
