"""
vector_tool.py — FAISS retrieval over contracts PDF.
Loaded once at import time; reused across all queries.
"""
import os
from typing import List, Tuple

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(BASE, "data", "faiss_index")

embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

faiss_db = FAISS.load_local(
    INDEX_PATH,
    embeddings,
    allow_dangerous_deserialization=True,
)


def search(query: str, k: int = 4) -> Tuple[List[str], List[str]]:
    """
    Search the FAISS index.

    Returns:
        results — list of formatted context strings with source tags
        sources — list of deduplicated source labels e.g. "contracts.pdf p.2"
    """
    hits    = faiss_db.similarity_search_with_relevance_scores(query, k=k)
    results = []
    sources = []

    for doc, score in hits:
        page  = doc.metadata.get("page", "?")
        src   = doc.metadata.get("source", "contracts.pdf")
        chunk = doc.page_content.strip()
        label = f"{src} p.{page}"

        results.append(f"[Source: {src}, Page {page}] (score={score:.2f})\n{chunk}")
        if label not in sources:
            sources.append(label)

        print(f"   📄 p.{page} score={score:.2f}: {chunk[:70]}...")

    return results, sources
