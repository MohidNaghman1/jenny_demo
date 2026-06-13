"""
FastAPI endpoint — Jenny Demo v2
Run: uvicorn api.main:app --reload --port 8000
"""
import sys
import os
import threading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI(
    title="Business Knowledge Assistant — Demo v2",
    description="Hybrid RAG: PDF contracts + SQLite payments | Groq LLM + HuggingFace embeddings",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Lazy loading — model loads in background, not blocking startup ─────────────

_ask_fn = None
_ready  = False
_error  = None

def _load():
    global _ask_fn, _ready, _error
    try:
        print("⏳ Loading agent (HuggingFace model + FAISS index)...")
        from agent.router import ask
        _ask_fn = ask
        _ready  = True
        print("✅ Agent ready.")
    except Exception as e:
        _error = str(e)
        print(f"❌ Agent load failed: {e}")

# Start loading immediately in background thread
threading.Thread(target=_load, daemon=True).start()

# ── Models ────────────────────────────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    question:  str
    answer:    str
    route:     str
    reasoning: str
    sources:   List[str]

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "status":      "ready" if _ready else "loading",
        "description": "Business Knowledge Assistant — Hybrid RAG Demo v2",
        "endpoints":   {"ask": "POST /ask", "health": "GET /health", "docs": "GET /docs"}
    }

@app.get("/health")
def health():
    if _error:
        raise HTTPException(status_code=500, detail=f"Agent failed to load: {_error}")
    return {
        "status": "ok" if _ready else "loading",
        "ready":  _ready,
    }

@app.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if _error:
        raise HTTPException(status_code=500, detail=f"Agent failed to load: {_error}")

    if not _ready:
        raise HTTPException(
            status_code=503,
            detail="Agent is still loading — please wait a few seconds and try again."
        )

    try:
        result = _ask_fn(request.question)
        return AnswerResponse(
            question  = request.question,
            answer    = result["answer"],
            route     = result["route"],
            reasoning = result["reasoning"],
            sources   = result.get("sources", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))