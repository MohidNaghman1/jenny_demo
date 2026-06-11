#!/bin/bash
# start.sh — used by Railway to start the app
# Builds FAISS index on first deploy if not already present.
set -e


echo "🚀 Starting FastAPI server..."
uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
