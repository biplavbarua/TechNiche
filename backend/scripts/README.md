# Backend Scripts

This directory contains various utility and testing scripts for the TechNiche backend.
Most of these scripts interact with external APIs (OpenRouter, Pinecone) or local database instances.

## Prerequisites

Before running any script here, ensure that you have your environment variables set up properly.
You can use `python-dotenv` and place a `.env` file in the `backend/` directory holding your API keys.

**Important:** These scripts must be run with the `backend/` directory in your PYTHONPATH or run from within the `backend/` directory itself, e.g.:
```bash
cd backend
python scripts/check_pinecone.py
```
