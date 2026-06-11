"""
router.py — LangGraph orchestration for the Jenny Demo agent.

Graph:  query_rewriter → router → [vector | sql | hybrid] → synthesizer

Retrieval is fully delegated to:
  tools/vector_tool.py  —  FAISS search over contracts PDF
  tools/sql_tool.py     —  Text-to-SQL over payments SQLite database

All heavy objects (LLM, embeddings, FAISS index, DB schema) are loaded
once at import time and reused across every request.
"""

import os
import sys
from typing import List, Literal, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import vector_tool, sql_tool

load_dotenv()

# ── Constants ─────────────────────────────────────────────────────────────────

BASE        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_PATH = os.path.join(BASE, "prompts", "system_prompt.txt")

if not os.path.exists(PROMPT_PATH):
    raise FileNotFoundError(f"Prompt file missing: {PROMPT_PATH}")

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()
# ── LLM singleton ─────────────────────────────────────────────────────────────

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=os.getenv("GROQ_API_KEY"),
)

# ── Prompts ───────────────────────────────────────────────────────────────────

REWRITER_PROMPT = """\
You are a search query optimiser for a business knowledge system that contains:
- PDF contracts (clauses, penalties, suspension, reinstatement, refund policy)
- A payments database (customer names, amounts, due dates, overdue status)

Task: Rewrite the user's question into a concise, keyword-rich search query.
- Remove filler words and conversational phrasing.
- Preserve all domain terms: customer names, contract clauses, monetary terms, dates.
- If the question references both payments AND contracts, keep terms from both.
- Return ONLY the rewritten query — no explanation, no punctuation at the end."""

ROUTER_PROMPT = """\
You are a query router for a business assistant. Two data sources are available:

  vector — PDF contracts: service clauses, payment penalties, suspension terms,
           reinstatement conditions, refund policy, notice periods.

  sql    — Payments database: customer names, payment amounts, due dates,
           overdue/paid status.

Routing rules (apply in order):
  1. If the question is ONLY about contract terms/clauses → vector
  2. If the question is ONLY about payment records/amounts/status → sql
  3. If the question needs BOTH (e.g. "overdue customers AND their contract terms") → hybrid

Output format — exactly two lines, nothing else:
  Line 1: one word — vector, sql, or hybrid
  Line 2: one sentence explaining which data source(s) will answer this."""

ANSWER_INSTRUCTIONS = """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT FROM RETRIEVAL — USE ONLY THIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{context}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Reminder before answering:
- Report actual values from the records above (names, amounts, dates, terms).
- Cite every factual claim as [Source: contracts.pdf, Page X] or [Source: payments table].
- If the context does not contain the answer, respond:
  "This information is not available in the contracts or payments data."
"""

# ── State ─────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    question:        str
    rewritten_query: str
    route:           str
    vector_results:  List[str]
    sql_results:     List[str]
    answer:          str
    reasoning:       str
    sources:         List[str]

# ── Nodes ─────────────────────────────────────────────────────────────────────

def query_rewriter_node(state: AgentState) -> AgentState:
    response  = llm.invoke([
        SystemMessage(content=REWRITER_PROMPT),
        HumanMessage(content=state["question"]),
    ])
    rewritten = response.content.strip()
    print(f"\n✏️  REWRITER | original='{state['question']}' → rewritten='{rewritten}'")
    return {**state, "rewritten_query": rewritten}


def router_node(state: AgentState) -> AgentState:
    query    = state["rewritten_query"] or state["question"]
    response = llm.invoke([
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=query),
    ])

    lines  = response.content.strip().splitlines()
    route  = lines[0].strip().lower() if lines else "hybrid"
    reason = lines[1].strip() if len(lines) > 1 else ""

    if route not in ("vector", "sql", "hybrid"):
        route = "hybrid"

    print(f"🔀 ROUTER   | route={route.upper()} | reason={reason}")
    return {**state, "route": route, "reasoning": reason}


def vector_node(state: AgentState) -> AgentState:
    query            = state["rewritten_query"] or state["question"]
    results, sources = vector_tool.search(query)
    merged           = _merge(state.get("sources", []), sources)
    return {**state, "vector_results": results, "sources": merged}


def sql_node(state: AgentState) -> AgentState:
    question         = state["rewritten_query"] or state["question"]
    results, sources = sql_tool.run(llm, question)
    merged           = _merge(state.get("sources", []), sources)
    return {**state, "sql_results": results, "sources": merged}


def synthesizer_node(state: AgentState) -> AgentState:
    context_parts = []
    if state.get("vector_results"):
        context_parts.append("=== CONTRACT DOCUMENTS ===")
        context_parts.extend(state["vector_results"])
    if state.get("sql_results"):
        context_parts.append("=== DATABASE RECORDS ===")
        context_parts.extend(state["sql_results"])

    if not context_parts:
        return {**state, "answer": "This information is not available in the contracts or payments data."}

    context  = "\n\n".join(context_parts)
    prompt   = SYSTEM_PROMPT + ANSWER_INSTRUCTIONS.format(context=context)

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=f"Question: {state['question']}\n\nAnswer:"),
    ])

    answer = response.content.strip()
    print(f"✅ ANSWER   | {len(answer)} chars")
    return {**state, "answer": answer}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _merge(existing: List[str], new: List[str]) -> List[str]:
    out = list(existing)
    for s in new:
        if s not in out:
            out.append(s)
    return out

# ── Graph ─────────────────────────────────────────────────────────────────────

def _route_decision(state: AgentState) -> Literal["vector_node", "sql_node", "both"]:
    r = state.get("route", "hybrid")
    if r == "vector": return "vector_node"
    if r == "sql":    return "sql_node"
    return "both"


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("query_rewriter_node", query_rewriter_node)
    g.add_node("router_node",         router_node)
    g.add_node("vector_node",         vector_node)
    g.add_node("sql_node",            sql_node)
    g.add_node("vector_then_sql",     vector_node)
    g.add_node("sql_after_vector",    sql_node)
    g.add_node("synthesizer_node",    synthesizer_node)

    g.set_entry_point("query_rewriter_node")
    g.add_edge("query_rewriter_node", "router_node")

    g.add_conditional_edges("router_node", _route_decision, {
        "vector_node": "vector_node",
        "sql_node":    "sql_node",
        "both":        "vector_then_sql",
    })

    g.add_edge("vector_node",     "synthesizer_node")
    g.add_edge("sql_node",        "synthesizer_node")
    g.add_edge("vector_then_sql", "sql_after_vector")
    g.add_edge("sql_after_vector","synthesizer_node")
    g.add_edge("synthesizer_node", END)

    return g.compile()


graph = build_graph()

# ── Public API ────────────────────────────────────────────────────────────────

def ask(question: str) -> dict:
    """
    Run the full agent pipeline for a given question.

    Returns:
        answer    — grounded natural language answer with citations
        route     — 'vector', 'sql', or 'hybrid'
        reasoning — one-sentence explanation of the routing decision
        sources   — deduplicated list of source labels
    """
    state = graph.invoke({
        "question":        question,
        "rewritten_query": "",
        "route":           "",
        "vector_results":  [],
        "sql_results":     [],
        "answer":          "",
        "reasoning":       "",
        "sources":         [],
    })
    return {
        "answer":    state["answer"],
        "route":     state["route"],
        "reasoning": state["reasoning"],
        "sources":   state.get("sources", []),
    }


if __name__ == "__main__":
    queries = [
        "Which customers have overdue payments?",
        "What does the contract say about service suspension?",
        "Which customers have overdue payments and what does their contract say about suspension?",
        "What is the refund policy?",
        "What are the late payment penalties?",
    ]
    for q in queries:
        print(f"\n{'='*60}\n❓ {q}")
        r = ask(q)
        print(f"ROUTE:  {r['route']}")
        print(f"ANSWER: {r['answer']}")
        print(f"SOURCES: {r['sources']}")
