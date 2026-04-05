# Folder Structure

```
TechNiche/
├── .planning/                  # Project planning and GSD artifacts
│   └── codebase/               # Codebase documentation guides
├── backend/                    # Python FastAPI application
│   ├── app/                    # Main application code
│   │   ├── core/               # Business logic (rag.py, crawler.py)
│   │   ├── utils/              # Helper modules (pinecone.py)
│   │   ├── main.py             # FastAPI entry point & routers
│   │   └── ingest.py           # Data ingestion scripts
│   ├── tests/                  # Pytest test suite
│   ├── requirements.txt        # Python dependencies
│   └── (Standalone Scripts)    # e.g., script.py, train_bot.py, rag2.py
├── frontend/                   # Next.js application
│   ├── app/                    # Next.js App Router Next configuration
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/             # React components (Dashboard, TechBackground)
│   ├── lib/                    # Frontend utilities
│   ├── public/                 # Static assets
│   ├── package.json            # Node dependencies
│   └── playwright-test.js      # E2E test script
└── README.md                   # Project overview
```
