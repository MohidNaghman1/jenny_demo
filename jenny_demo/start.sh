#!/bin/bash
# start.sh — used by Railway to start the app
# Builds FAISS index on first deploy if not already present.
set -e

INDEX_DIR="data/faiss_index"

if [ ! -d "$INDEX_DIR" ]; then
  echo "📄 FAISS index not found — running ingest.py..."
  python3 ingestion/ingest.py
  echo "✅ Ingestion complete."
else
  echo "✅ FAISS index already exists — skipping ingest."
fi

echo "🚀 Starting FastAPI server..."
uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
