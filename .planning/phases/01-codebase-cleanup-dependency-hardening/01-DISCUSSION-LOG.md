# Phase 1: Codebase Cleanup & Dependency Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 01-codebase-cleanup-dependency-hardening
**Areas discussed:** Dead script disposal, Informal test script classification, Dependency pinning strategy, E2E verification requirement

---

## Dead Scripts

| Option | Description | Selected |
|--------|-------------|----------|
| Delete outright | Permanently remove ChromaDB-dependent scripts (script.py, script2.py, script3.py, verify_conflict.py, test_rag_script.py) | ✓ |
| Move to scripts/ | Preserve for historical reference | |

**User's choice:** Delete outright
**Notes:** All 5 files import chromadb or are trivial throwaway scripts with no ongoing utility. Once chroma_db/ directories are removed, these files have no execution context.

---

## Informal Test Script Classification

| Option | Description | Selected |
|--------|-------------|----------|
| Move to backend/scripts/ | Treat as dev utilities / manual smoke tests | ✓ |
| Move to backend/tests/ | Treat as part of test suite | |
| Delete | Remove entirely | |

**User's choice:** Move to backend/scripts/ with renamed prefixes
**Notes:** Files are NOT pytest-compatible (no pytest fixtures, no `def test_*` structure). They require a live Pinecone connection and .env. Renaming from `test_*.py` to non-test-prefixed names prevents accidental pytest discovery. Full rename mapping captured in CONTEXT.md D-02.

---

## Dependency Pinning Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Pin current installed (pip freeze) | Use exact versions known to work today | ✓ |
| Research latest stable | Freshen to newer versions | |

**User's choice:** Pin current installed versions
**Notes:** Patent demo context — reproducibility is paramount. Exact versions: fastapi==0.128.0, uvicorn==0.40.0, pinecone==8.1.0, openai==2.9.0, pydantic==2.12.5, python-dotenv==1.2.1, requests==2.32.5, beautifulsoup4==4.14.2, google-generativeai==0.8.5, starlette==0.50.0, anyio==4.12.0, typing_extensions==4.15.0, httpx==0.28.1.

---

## E2E Verification Requirement

| Option | Description | Selected |
|--------|-------------|----------|
| E2E required before completion | Spin up server + browser test all endpoints | ✓ |
| Pytest-only verification | Run pytest tests, no live server check | |

**User's choice:** E2E browser testing required
**User's exact instruction:** "test the outputs before coming to a conclusion or marking the task complete. E2E testing is recommended on your browser."
**Notes:** Phase 1 is NOT complete until: (1) server starts cleanly, (2) all endpoints respond in browser/curl, (3) pytest passes, (4) fresh venv install succeeds.

---

## Agent's Discretion

- Commit order within phase (can split delete / move / pin into separate commits)
- Content and format of scripts/README.md
- Whether to add `__init__.py` to scripts/ (not needed)

## Deferred Ideas

- pytest-cov → Phase 5 (test suite phase)
- faker / test data libs → Phase 5
- Version bumps → post-patent-demo milestone
