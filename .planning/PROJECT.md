# TechNiche — Legal AI Assistant Backend

## What This Is

TechNiche is an advanced AI-powered legal assistant for Indian startups and SMEs. It uses a bespoke RAG pipeline with **Temporal Conflict Resolution** and **Deterministic Citation Bounding** to provide legal advice grounded exclusively in verified, timestamped Indian case law. The backend is Python/FastAPI and is the subject of a planned patent filing.

## Core Value

Every query must return a verifiable legal response — never a blank, never an ungrounded hallucination — backed by citations that are deterministically cross-checked against retrieved case chunks.

## Requirements

### Validated

<!-- Existing shipped capabilities inferred from codebase map -->

- ✓ FastAPI REST backend with 5 endpoints (`/`, `/api/crawl`, `/api/learn/url`, `/api/analyze`, `/api/query`, `/api/cases`) — existing
- ✓ RAG pipeline: scrape → embed (Pinecone inference) → store → retrieve → generate (OpenRouter) — existing
- ✓ Temporal Conflict Resolution: chronological overruling detection with precedent tracing — existing
- ✓ Citation Verification (`_verify_citations`): post-generation cross-referencing against retrieved chunks — existing
- ✓ Continuous Learning: ingest new cases via URL using `ingest_case_from_url` — existing
- ✓ Pydantic-validated structured metadata extraction during ingestion (case name, date, overruled cases, domain) via Gemini — existing
- ✓ Legal domain auto-detection for specialized prompting — existing
- ✓ OpenRouter multi-model fallback cascade — existing

### Active

<!-- Goals for this milestone: bulletproof backend for patent demonstration -->

- [ ] Health check endpoint (`/api/health`) returning Pinecone status, model availability, and index stats
- [ ] Knowledge base stats endpoint (`/api/stats`) with total vectors, domain breakdown, and case count
- [ ] Structured error responses with consistent JSON schema across all endpoints (no raw 500s)
- [ ] CORS hardening — environment-variable-driven allowed origins, not wildcard in production
- [ ] Retry logic with exponential backoff on Pinecone and OpenRouter calls
- [ ] Response caching for identical queries (in-memory TTL cache, 5-minute window)
- [ ] Comprehensive pytest test suite: unit tests for all core modules + integration tests for all endpoints
- [ ] Remove ChromaDB artifacts and dead scripts from `backend/` directory
- [ ] Restructure loose scripts into `backend/scripts/` directory
- [ ] Dependency pinning (`requirements.txt` with exact versions + `requirements-dev.txt` for test deps)
- [ ] Async endpoint handlers (`async def`) for I/O-bound routes to improve throughput

### Out of Scope

- Gemini LLM as a replacement for OpenRouter cascade — user explicitly excluded this; OpenRouter stays primary
- Frontend changes — this milestone is backend-only
- Authentication / API key gating — deferred; not needed for patent demo phase
- Database migration away from Pinecone — Pinecone is the production store

## Context

- **Prior work**: Backend was debugged and tested in a prior session (March 23 2026). Bugs were identified and fixed.
- **Codebase state**: `backend/app/core/` has `rag.py` (19 KB — main RAG + conflict resolution engine), `extraction.py` (Gemini structured extraction), `crawler.py`, `scraper.py`. `backend/app/utils/pinecone.py` handles vector DB client. `backend/app/ingest.py` is the ingestion orchestrator.
- **Tech debt identified**: ChromaDB leftovers (`chroma_db/`, `chroma_db_test/`), 7+ loose scripts at `backend/` root, wildcard CORS, no retry/backoff logic, no health endpoint, minimal test coverage.
- **Patent context**: The novel claims are (1) Timestamped Lexical Overruling, (2) Deterministic Citation Bounding, (3) Structured Pydantic Extraction Loop. All three must work reliably and be demonstrable.

## Constraints

- **Tech stack**: Python 3.10+, FastAPI, Pinecone Serverless, OpenRouter (multi-model cascade), Google GenAI (Gemini structured extraction only) — no changes to primary LLM provider
- **Deployment**: Render (via `render.yaml`) — keep Dockerfile and startup scripts compatible
- **Performance**: Responses must return within 30 seconds; ingestion within 60 seconds per URL
- **Test runner**: `pytest` — all tests in `backend/tests/` runnable via `python -m pytest tests/ -v`

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Gemini for extraction only (not primary LLM) | User explicitly wants OpenRouter cascade preserved; Gemini already integrated for structured extraction | — Pending |
| In-memory caching (not Redis) | Keep infrastructure simple for Render deployment; no persistent cache needed for demo | — Pending |
| Async endpoints | FastAPI supports async natively; Pinecone and HTTP calls are I/O-bound — parallelism wins | — Pending |
| Exact version pinning | Patent demo must be reproducible; floating versions cause drift | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-23 after initialization*
