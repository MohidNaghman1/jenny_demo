"""
FastAPI endpoint — Jenny Demo v2
Run: uvicorn api.main:app --reload --port 8000
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from agent.router import ask

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

class QuestionRequest(BaseModel):
    question: str

class AnswerResponse(BaseModel):
    question:  str
    answer:    str
    route:     str
    reasoning: str
    sources:   List[str]   # NEW

@app.get("/")
def root():
    return {
        "status": "running",
        "description": "Business Knowledge Assistant — Hybrid RAG Demo v2",
        "endpoints": {"ask": "POST /ask", "health": "GET /health", "docs": "GET /docs"}
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask", response_model=AnswerResponse)
def ask_question(request: QuestionRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    try:
        result = ask(request.question)
        return AnswerResponse(
            question  = request.question,
            answer    = result["answer"],
            route     = result["route"],
            reasoning = result["reasoning"],
            sources   = result.get("sources", []),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
