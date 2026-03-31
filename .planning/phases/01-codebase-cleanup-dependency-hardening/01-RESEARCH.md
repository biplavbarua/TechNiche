# Phase 1: Codebase Cleanup & Dependency Hardening - Research

## Context Validated
1. **ChromaDB Artifacts**: `backend/chroma_db/` and `backend/chroma_db_test/` are directories containing SQLite artifacts. There are no ChromaDB imports remaining in `backend/app/`.
2. **Dead Scripts**: The 5 scripts listed in CONTEXT.md (`script.py`, etc.) are safe to `rm`.
3. **Move Scripts**: The 8 remaining scripts (`test_conflict_resolution.py`, etc.) should be moved to `backend/scripts/` with `mv`. Renames apply as specified in CONTEXT.md.
4. **Dependencies**: The `requirements.txt` file and `requirements-dev.txt` file have exact specifications from CONTEXT.md.
5. **E2E Verification**: Needs `uvicorn` background execution, `pytest` suite testing, and browser E2E checks after the cleanup are completed successfully.

## Validation Architecture
- **Methodology**: Local execution + browser-based testing as enforced by the `E2E Verification` decision.
- **Tools**: Bash commands for file manipulation, Python pip for installation, Pytest for suite testing, Uvicorn for server.

## RESEARCH COMPLETE
