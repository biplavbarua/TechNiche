#!/bin/bash
# Run the application
# Use working directory 'backend' to match local setup
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 10000
