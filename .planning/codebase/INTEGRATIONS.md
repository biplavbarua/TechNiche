# Integrations

## AI & Machine Learning
- **OpenRouter**: Used via its API to route requests to various LLMs (e.g., Anthropic Claude, OpenAI, Google) for legal analysis and summary generation. Required environment variable: `OPENROUTER_API_KEY`.
- **Google GenAI**: Potentially used as a fallback or specific model endpoint. Required environment variable: `GOOGLE_API_KEY`.

## Databases
- **Pinecone**: Cloud-based Vector Database used to store and search text embeddings representing crawled legal documents and case law. Required environment variables: `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `PINECONE_HOST`.

## Future / Deprecated
- **ChromaDB**: Codebase contains remnant directories (`chroma_db`, `chroma_db_test`), indicating it was used during prototyping but has been superseded by Pinecone.
