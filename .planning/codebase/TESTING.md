# Testing Strategy

## Backend Testing
- **Framework**: `pytest`
- **Location**: `backend/tests/`
- **Focus**: Unit tests covering RAG logic, citation verification (`test_rag.py`), and integration endpoints.
- **Execution**: Run tests from the `backend/` directory using:
  ```bash
  python -m pytest tests/ -v
  ```

## Frontend Testing
- **Framework**: Playwright
- **Location**: `frontend/playwright-test.js`
- **Focus**: End-to-End (E2E) testing simulating user flow—navigating to the page, filling forms, waiting for dynamic RAG analysis content, and taking screenshots.
- **Execution**: Run the E2E script with Node.js while the local frontend and backend servers are active:
  ```bash
  node playwright-test.js
  ```
- **Note**: Frontend is currently lacking component-level unit tests (e.g., Jest/Vitest).

## Continuous Integration
- Currently, tests are executed manually. Integrating these into a CI/CD pipeline (e.g., GitHub Actions) is a recommended future step.
