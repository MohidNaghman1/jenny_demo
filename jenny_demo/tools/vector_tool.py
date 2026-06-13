"""
vector_tool.py — FAISS retrieval over contracts PDF.
Lazy-loaded on first query to avoid startup crash.
"""
import os
from typing import List, Tuple
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_community.vectorstores import FAISS

BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(BASE, "data", "faiss_index")

_embeddings = None
_faiss_db   = None

def _get_db():
    global _embeddings, _faiss_db
    if _faiss_db is None:

        _embeddings = HuggingFaceInferenceAPIEmbeddings(
            api_key=os.getenv("HF_TOKEN", ""),
            model_name="BAAI/bge-small-en-v1.5",
        )
        _faiss_db = FAISS.load_local(
            INDEX_PATH,
            _embeddings,
            allow_dangerous_deserialization=True,
        )
    return _faiss_db


def search(query: str, k: int = 4) -> Tuple[List[str], List[str]]:
    hits    = _get_db().similarity_search_with_relevance_scores(query, k=k)
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