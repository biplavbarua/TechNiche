# Coding Conventions & Standards

## Backend (Python/FastAPI)
- **Type Hinting**: All functions should use Python type hints to improve readability and allow Pydantic to properly validate data.
- **Payload Validation**: Always define and use Pydantic `BaseModel` classes for incoming HTTP request bodies.
- **Separation of Concerns**: Keep route handlers (`main.py`) thin. Delegate heavy lifting to modules within the `core/` or `utils/` directories.
- **Environment Variables**: Load secrets from `.env` instead of hardcoding. Access them via `os.getenv()`.
- **API Responses**: Wrap standard JSON responses in `JSONResponse` or return dicts that FastAPI can automatically serialize. Handle exceptions securely without leaking internal traceback details to clients.

## Frontend (Next.js/React)
- **Component Architecture**: Use functional components with hooks.
- **Rendering Directives**: Clearly demarcate client vs. server components (use `"use client"` at the top of components that run in the browser, e.g., `Dashboard.tsx`).
- **Styling**: Use Tailwind CSS utility classes. Avoid writing custom CSS unless absolutely necessary (which should go in `globals.css`).
- **Animations**: Standardize on Framer Motion for UI animations to maintain a consistent feel.
