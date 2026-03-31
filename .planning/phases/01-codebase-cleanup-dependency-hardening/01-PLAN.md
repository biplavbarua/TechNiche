---
wave: 1
depends_on: []
files_modified: [
  "backend/script.py", 
  "backend/script2.py", 
  "backend/script3.py", 
  "backend/verify_conflict.py", 
  "backend/test_rag_script.py",
  "backend/test_conflict_resolution.py",
  "backend/test_debug_rag.py",
  "backend/test_pinecone.py",
  "backend/test_rag.py",
  "backend/train_bot.py",
  "backend/list_models.py",
  "backend/verify_api.py",
  "backend/verify_key.py",
  "backend/requirements.txt",
  "backend/requirements-dev.txt",
  "backend/scripts/README.md"
]
autonomous: true
requirements: []
---

# Phase 1: Codebase Cleanup & Dependency Hardening - Plan

<objective>
To clean up the backend directory by deleting ChromaDB artifacts and dead scripts, reorganizing development/test utilities into a `scripts` folder, and pinning all dependencies for reproduciblity.
</objective>

<tasks>
<task id="1-01">
<title>Delete ChromaDB Artifacts and Dead Scripts</title>
<read_first>backend/script.py</read_first>
<action>
Execute bash commands to delete dead artifacts and scripts entirely from the repository:
```bash
rm -rf backend/chroma_db/ backend/chroma_db_test/
rm backend/script.py backend/script2.py backend/script3.py backend/verify_conflict.py backend/test_rag_script.py
```
</action>
<acceptance_criteria>
`ls -la backend/` MUST NOT contain `chroma_db`, `chroma_db_test`, `script.py`, `script2.py`, `script3.py`, `verify_conflict.py`, or `test_rag_script.py`.
</acceptance_criteria>
</task>

<task id="1-02">
<title>Reorganize Informal Test Scripts to scripts directory</title>
<read_first>backend/test_conflict_resolution.py</read_first>
<action>
1. `mkdir -p backend/scripts`
2. Run standard `mv` commands to reposition informal utilities to new names under the `backend/scripts/` directory:
```bash
mv backend/test_conflict_resolution.py backend/scripts/smoke_conflict_resolution.py
mv backend/test_debug_rag.py backend/scripts/debug_rag.py
mv backend/test_pinecone.py backend/scripts/check_pinecone.py
mv backend/test_rag.py backend/scripts/smoke_rag.py
mv backend/train_bot.py backend/scripts/train_bot.py
mv backend/list_models.py backend/scripts/list_models.py
mv backend/verify_api.py backend/scripts/verify_api.py
mv backend/verify_key.py backend/scripts/verify_key.py
```
3. Create `backend/scripts/README.md` with instructions noting these scripts require `.env`.
</action>
<acceptance_criteria>
`ls backend/scripts/` MUST list `smoke_conflict_resolution.py`, `debug_rag.py`, `check_pinecone.py`, `smoke_rag.py`, `train_bot.py`, `list_models.py`, `verify_api.py`, `verify_key.py`, and `README.md`.
</acceptance_criteria>
</task>

<task id="1-03">
<title>Pin Dependencies</title>
<read_first>backend/requirements.txt</read_first>
<action>
Overwrite `backend/requirements.txt` with precise versions:
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
Create `backend/requirements-dev.txt` with:
```
pytest==8.4.2
httpx==0.28.1
pytest-asyncio==1.3.0
```
</action>
<acceptance_criteria>
`cat backend/requirements.txt` matches exact list above. `cat backend/requirements-dev.txt` contains `pytest==8.4.2`.
</acceptance_criteria>
</task>

<task id="1-04">
<title>Verify Server and E2E Environment</title>
<read_first>backend/app/main.py</read_first>
<action>
- Create a fresh pip mock or python venv to run `pip install -r backend/requirements.txt` ensuring clean installs.
- Run `cd backend && python -m pytest tests/` and verify existing test behavior still passes.
- Start `uvicorn app.main:app --port 8000` locally in background, perform GET requests using curl logic, verifying HTTP 200 outputs.
- Start and test with Browser agent if required.
</action>
<acceptance_criteria>
Tests complete with exit code 0. Endpoint `http://localhost:8000` curl outputs properly without error.
</acceptance_criteria>
</task>
</tasks>
