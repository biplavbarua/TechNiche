# Phase 1: Codebase Cleanup & Dependency Hardening - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove all ChromaDB artifacts (directories + imports), delete dead/ChromaDB-dependent scripts,
reorganize remaining loose backend scripts into `backend/scripts/`, pin all dependencies to
exact known-good versions, and create `requirements-dev.txt`. This is a pure cleanup phase —
no new functionality, no app behavior changes.

**Delivery test:** After cleanup, `python -m uvicorn app.main:app` must start cleanly, all 5
existing endpoints must respond, and `pip install -r requirements.txt` must install cleanly
in a fresh virtualenv.

</domain>

<decisions>
## Implementation Decisions

### D-01: Dead Script Disposal — DELETE outright
The following files are ChromaDB-dependent and have zero value once `chroma_db/` is removed.
They must be **deleted entirely** — do NOT move to `scripts/`:

- `backend/script.py` — queries `chroma_db` collection (import chromadb)
- `backend/script2.py` — queries `chroma_db` collection (import chromadb)
- `backend/script3.py` — queries `chroma_db` collection (import chromadb)
- `backend/verify_conflict.py` — imports chromadb directly
- `backend/test_rag_script.py` — 2-line throwaway (one-liner call to query_legal_assistant)

### D-02: Informal Test Scripts — move to `backend/scripts/`
These are manual smoke tests / dev utilities that require a live `.env` + Pinecone connection.
They are NOT pytest-compatible. Move them to `backend/scripts/` (rename to drop the ambiguous
`test_` prefix):

| Current path | New path | Rename reason |
|---|---|---|
| `backend/test_conflict_resolution.py` | `backend/scripts/smoke_conflict_resolution.py` | Avoids confusion with pytest; it's a live-API smoke test |
| `backend/test_debug_rag.py` | `backend/scripts/debug_rag.py` | It's a debug runner, not a test |
| `backend/test_pinecone.py` | `backend/scripts/check_pinecone.py` | Connectivity + embedding sanity check |
| `backend/test_rag.py` | `backend/scripts/smoke_rag.py` | Manual RAG query runner |

Also move the remaining dev utilities:
- `backend/train_bot.py` → `backend/scripts/train_bot.py`
- `backend/list_models.py` → `backend/scripts/list_models.py`
- `backend/verify_api.py` → `backend/scripts/verify_api.py`
- `backend/verify_key.py` → `backend/scripts/verify_key.py`

Create `backend/scripts/README.md` documenting that these are manual scripts requiring a live `.env`.

### D-03: Dependency Pinning — use current installed (pip freeze) versions
Pin to exactly what is installed and known-good. Do NOT bump versions.

**`backend/requirements.txt`** (production deps, exact pins):
```
fastapi==0.128.0
uvicorn==0.40.0
pinecone==8.1.0
openai==2.9.0
pydantic==2.12.5
python-dotenv==1.2.1
requests==2.32.5
beautifulsoup4==4.14.2
google-generativeai==0.8.5
starlette==0.50.0
anyio==4.12.0
typing_extensions==4.15.0
httpx==0.28.1
```

**`backend/requirements-dev.txt`** (test/dev deps, exact pins):
```
pytest==8.4.2
httpx==0.28.1
pytest-asyncio==1.3.0
```

### D-04: ChromaDB audit — no app/code imports found
Confirmed: `grep -r "chromadb" backend/app/` returns no results.
Only the dead scripts (deleted in D-01) and `verify_conflict.py` (deleted in D-01) import chromadb.
No `requirements.txt` cleanup needed for chromadb (it's not listed there).

### D-05: Verification requirement — E2E test before marking complete
After all cleanup changes, the executor MUST:
1. Start the server: `cd backend && uvicorn app.main:app --reload`
2. Verify all endpoints respond via browser or curl
3. Run `python -m pytest tests/ -v` from `backend/` — all existing tests pass
4. Run `pip install -r requirements.txt` in a fresh venv to verify clean install
The phase is NOT complete until all 4 verification steps pass.

### Agent's Discretion
- Order of git commits within the plan (delete vs. move vs. pin can be separate commits)
- Whether `scripts/README.md` uses a table or prose to document each script
- Whether to create `backend/scripts/__init__.py` (not needed; these are standalone runners)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Planning
- `.planning/ROADMAP.md` — Phase 1 plans and verification criteria (§ Phase 1)
- `.planning/REQUIREMENTS.md` — §4 Cleanup & Tech Debt (4.1, 4.2, 4.3 are in scope for Phase 1)
- `.planning/STATE.md` — Current phase status and notes

### Existing Code (read before modifying)
- `backend/requirements.txt` — current unpinned file (rewrite in place)
- `backend/app/main.py` — entry point; verify imports still work after script removal
- `backend/tests/` — existing pytest suite must still pass after cleanup

### No external specs — requirements fully captured in decisions above

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/tests/test_conflict_resolution.py` — proper pytest suite (keep, do NOT touch)
- `backend/tests/test_extraction.py` — proper pytest suite (keep)
- `backend/tests/test_rag.py` — proper pytest suite (keep)
- `backend/tests/__init__.py` — keep

### Established Patterns
- No `backend/scripts/` directory exists yet — create it fresh
- `backend/app/` uses `from app.xxx import ...` style — not affected by script cleanup
- `backend/Dockerfile` and `start_render.sh` reference `requirements.txt` — pin in-place (same filename)

### Integration Points
- Scripts being deleted/moved have NO imports from `backend/app/` code except `train_bot.py`,
  `test_conflict_resolution.py`, `test_debug_rag.py`, `test_rag.py`, `test_rag_script.py`
  (which call `app.core.rag` etc.) — moving these to `scripts/` does not break anything in `app/`
- `requirements.txt` is referenced by `Dockerfile` and Render deploy — filename stays the same

</code_context>

<specifics>
## Specific Ideas

- Rename loose `test_*.py` scripts with non-`test_` prefixes when moving to `scripts/` — prevents
  pytest from accidentally picking them up during `pytest tests/` runs
- `scripts/README.md` should include one-line description per script and note that `.env` must be
  configured before running any of them
- The `chroma_db/` and `chroma_db_test/` directories at `backend/` root should be deleted with
  `rm -rf`, not gitignored

</specifics>

<deferred>
## Deferred Ideas

- Adding `pytest-cov` to requirements-dev.txt — deferred to Phase 5 (test suite phase)
- Adding `faker` or test data generation libs — deferred to Phase 5
- Bumping deps to latest stable versions — deferred; current known-good versions preserved for
  patent demo reproducibility

### Reviewed Todos (not folded)
None — no pending todos were found for Phase 1.

</deferred>

---

*Phase: 01-codebase-cleanup-dependency-hardening*
*Context gathered: 2026-03-31*
