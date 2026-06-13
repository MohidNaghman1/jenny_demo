"""
Run once: python3 ingestion/ingest.py
Chunks contracts.pdf, embeds with HuggingFace (local, free), saves FAISS index.
Uses BAAI/bge-small-en-v1.5 — no API key required.
"""
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
from langchain_community.vectorstores import FAISS

BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH   = os.path.join(BASE, "data", "contracts.pdf")
INDEX_PATH = os.path.join(BASE, "data", "faiss_index")

def ingest():
    print("📄 Loading PDF...")
    loader = PyPDFLoader(PDF_PATH)
    pages  = loader.load()
    print(f"   Loaded {len(pages)} pages")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", " "]
    )
    chunks = splitter.split_documents(pages)

    for chunk in chunks:
        chunk.metadata["source"] = "contracts.pdf"
        chunk.metadata["page"]   = chunk.metadata.get("page", 0) + 1

    print(f"   Split into {len(chunks)} chunks")

    if os.getenv("USE_HF_API", "false").lower() == "true":
            print("🔢 Embedding via HuggingFace Inference API...")
            embeddings = HuggingFaceInferenceAPIEmbeddings(
                api_key=os.getenv("HF_TOKEN", ""),
                model_name="BAAI/bge-small-en-v1.5",
            )
    else:
            print("🔢 Embedding via local model...")
            embeddings = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-en-v1.5",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )

    db = FAISS.from_documents(chunks, embeddings)
    db.save_local(INDEX_PATH)

    print(f"✅ FAISS index saved to {INDEX_PATH}")
    print(f"   Total vectors: {db.index.ntotal}")

if __name__ == "__main__":
    ingest()
