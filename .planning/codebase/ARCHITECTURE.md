# Architecture Overview

The system follows a modern decoupled Client-Server architecture designed to support a Retrieval-Augmented Generation (RAG) AI application.

## Frontend (Next.js)
- Server-Side Rendering (SSR) and Client-Side Rendering (CSR) via Next.js App Router.
- Communicates with the backend exclusively through REST API calls.

## Backend (FastAPI)
- Exposes RESTful endpoints (`/api/crawl`, `/api/learn/url`, `/api/analyze`, `/api/query`, `/api/cases`).
- Validates all incoming payloads using Pydantic models.

## AI RAG Pipeline
1. **Ingestion**: The system crawls web pages (using `crawler.py` and BeautifulSoup), extracting legal case texts.
2. **Embedding**: Extracted text is chunked and embedded using an embedding model.
3. **Storage**: The vectors are inserted into a **Pinecone** index.
4. **Retrieval**: Upon receiving a query, it is embedded, and a similarity search is executed against Pinecone to find relevant cases.
5. **Resolution Engine**: Incorporates legal domain detection and Temporal Conflict Resolution to trace precedents and detect overruled citations.
6. **Generation**: An LLM (via OpenRouter) produces a final answer. A verification step (`_verify_citations`) checks groundedness against the retrieved context before returning the response to the user.
