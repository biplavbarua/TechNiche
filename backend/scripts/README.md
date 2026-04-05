# Backend Scripts

This directory contains utility functions, informal checks, and ad-hoc scripts used for development.

- **smoke_conflict_resolution.py**: Quick test to ensure conflict resolution endpoints behave.
- **debug_rag.py**: Standalone script to query OpenRouter + Pinecone directly.
- **check_pinecone.py**: Informal check for Pinecone connectivity/index stats.
- **smoke_rag.py**: Ad-hoc checks of RAG core extraction function outside API Context.
- **train_bot.py**: Helper to upload specific texts/URLs into Pinecone.
- **list_models.py**: Quick check to verify OpenRouter models via their API.
- **verify_api.py / verify_key.py**: Basic checks to validate environment keys.

Please keep this directory clean of formal tests which belong in `tests/`.
