"""
sql_tool.py — Text-to-SQL execution over payments.db.
Schema is fetched once at import time and cached.
"""
import os
import re
import sqlite3
from typing import List, Tuple
from langchain_core.messages import HumanMessage, SystemMessage


BASE    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "payments.db")


def _build_schema() -> str:
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    parts  = []
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [f"{r[1]} {r[2]}" for r in cursor.fetchall()]
        parts.append(f"{table}(\n  " + ",\n  ".join(cols) + "\n)")
    conn.close()
    return "\n".join(parts)


# Cached at import — no DB round-trip per query
SCHEMA = _build_schema()

SQL_SYSTEM_PROMPT = f"""\
You are a SQLite expert. Database schema:

{SCHEMA}

Rules:
1. Write a single SELECT query to answer the question.
2. Always SELECT * — never list individual columns.
3. Return ONLY the raw SQL — no markdown, no backticks, no explanation.
"""


def run(llm, question: str) -> Tuple[List[str], List[str]]:
    """
    Generate and execute a SQL query for the given question.

    Args:
        llm      — ChatGroq (or any LangChain chat model)
        question — user question or rewritten query

    Returns:
        results — list of formatted context strings with source tags
        sources — list of source labels e.g. ["payments table"]
    """

    response  = llm.invoke([
        SystemMessage(content=SQL_SYSTEM_PROMPT),
        HumanMessage(content=question),
    ])

    raw       = response.content.strip()
    match     = re.search(r"```(?:sql)?\s*(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    sql_query = match.group(1).strip() if match else raw.strip()
    print(f"   🗄️  SQL: {sql_query}")

    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(sql_query)
        rows    = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
        conn.close()

        if not rows:
            return ["[Source: payments database]\nNo matching records found."], []

        formatted = "\n".join(str(dict(zip(columns, row))) for row in rows)
        print(f"   Returned {len(rows)} rows")
        return [f"[Source: payments table]\n{formatted}"], ["payments table"]

    except Exception as e:
        conn.close()
        print(f"   SQL error: {e}")
        return [f"[Source: payments database]\nQuery error: {e}"], []
