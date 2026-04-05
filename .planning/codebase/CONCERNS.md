# Technical Concerns & Debt

## Database Transitions
- **ChromaDB Artifacts**: The `backend/` directory contains remnants of a previous vector database integration (`chroma_db/`, `chroma_db_test/`). These files should be safely archived or deleted as the application has migrated to using Pinecone to avoid confusion.

## Code Organization
- **Standalone Scripts**: Several root-level Python scripts exist in `backend/` (`script.py`, `train_bot.py`, `rag2.py`, etc.). These appear to be experimental or utility scripts. They should be evaluated, documented, and moved to an appropriate `scripts/` or `tools/` directory to declutter the main application scope.

## Security Practices
- **CORS Permissiveness**: The backend FastAPI configuration in `main.py` permits requests from any origin (`allow_origins=["*"]`). In a production setting, this should be tightened to specific deployment URLs.

## Testing Coverage
- **Frontend Unit Tests**: The frontend relies entirely on a single Playwright script for E2E testing. There is a notable absence of isolated component-level tests (e.g., Jest or React Testing Library), making granular component regressions harder to detect.
