# Backend Developer Scripts

This directory contains informal test scripts and developer utilities to smoke test specific features or integrations quickly (e.g. Pinecone, OpenRouter, basic RAG).

These are not part of the standard `pytest` automated test suite and are designed to be run manually on-demand.

## Prerequisites

All scripts depend on your live project environment variables. Ensure you run these scripts with a filled `.env` file present in the `backend/` directory or your OS environment. 

## Utilities

- `check_pinecone.py`: Smoke test Pinecone server connection and indexing.
- `debug_rag.py`: Interactive debugging of Retrieval Augmented Generation pipelines.
- `list_models.py`: List deployed models available on OpenRouter/Gemini.
- `smoke_conflict_resolution.py`: Smoke test the case conflict resolution logic directly via LLMs.
- `smoke_rag.py`: Simple smoke test for RAG search.
- `train_bot.py`: Ad-hoc training or instruction tuning utility script.
- `verify_api.py` / `verify_key.py`: Ad-hoc credential or endpoint verifications.
