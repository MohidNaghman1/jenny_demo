# Business Knowledge Assistant — Hybrid RAG Demo

A production-ready LangGraph agent that answers natural-language business questions
by routing across a **PDF contracts store** and a **SQLite payments database**, then
synthesising grounded answers with inline source citations.

Built with Groq (free tier) + HuggingFace local embeddings — **zero API cost beyond Groq**.

---

## Live Demo Architecture

```
User Question
      │
      ▼
┌──────────────────┐
│  Query Rewriter  │  LLM rewrites to keyword-rich search form
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│     Router       │  LLM decides: vector / sql / hybrid
└────────┬─────────┘
         │
   ┌─────┴──────────────────────┐
   │             │              │
   ▼             ▼              ▼
vector_node   sql_node    vector → sql
(FAISS/HF)  (LLM→SQLite)   (hybrid)
   │             │              │
   └─────────────┴──────────────┘
                 │
                 ▼
        ┌─────────────────┐
        │   Synthesizer   │  Grounded answer + citations
        └────────┬────────┘
                 │
     answer + route + reasoning + sources
```

**Data sources:**
- `data/contracts.pdf` — service agreements with clauses, penalties, suspension terms
- `data/payments.db` — SQLite table with customer names, amounts, due dates, status

---

## Quickstart (Local)

### 1. Get a free Groq API key

1. Visit [console.groq.com](https://console.groq.com)
2. Sign up → **API Keys** → **Create API Key**
3. Copy the key (starts with `gsk_...`)

### 2. Clone and configure

```bash
git clone <your-repo-url>
cd jenny_demo_v2

cp .env.example .env
# Open .env and paste your key:
# GROQ_API_KEY=gsk_...
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** HuggingFace embeddings (`BAAI/bge-small-en-v1.5`) download ~40 MB on
> first use. No API key needed — runs locally on CPU.

### 4. Build the FAISS index

```bash
python3 ingestion/ingest.py
```

This reads `data/contracts.pdf`, chunks it, embeds it, and saves the FAISS
vector index to `data/faiss_index/`. **Re-run this any time you change the PDF.**

### 5. Start the API

```bash
uvicorn api.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 6. Open the UI

No build step — open directly in any browser:

```bash
open ui/index.html       # macOS
xdg-open ui/index.html   # Linux
# Windows: double-click ui/index.html in Explorer
```

The UI calls `http://localhost:8000` by default.

---

## Deploy to Railway (Free Tier)

Railway gives **$5 free credit/month** — enough for a persistent demo.

### Steps

1. Push this repo to GitHub (keep `.env` out — it's in `.gitignore`)

2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**

3. Select your repo

4. Add environment variable in Railway dashboard:
   ```
   GROQ_API_KEY = gsk_...
   ```

5. Railway auto-detects `Procfile` and runs `bash start.sh`, which:
   - Builds the FAISS index on first deploy
   - Starts the FastAPI server on `$PORT`

6. Copy your Railway URL (e.g. `https://jenny-demo.up.railway.app`)

7. Host `ui/index.html` on **GitHub Pages**:
   - Repo Settings → Pages → Branch: `main`, Folder: `/ui`
   - Edit line 1 of the `<script>` in `index.html`:
     ```js
     window.API_BASE = "https://jenny-demo.up.railway.app";
     ```

8. Share the GitHub Pages URL with Jenny ✓

---

## Demo Queries

Use these four queries to demonstrate all routing paths:

| Query | Route | What it shows |
|---|---|---|
| `Which customers have overdue payments?` | `sql` | SQL-only: names, amounts, due dates |
| `What does the contract say about service suspension?` | `vector` | PDF-only: clause extraction with page citations |
| `Which customers have overdue payments and what does their contract say about suspension?` | `hybrid` | **Money shot** — single answer combining both sources |
| `What is the refund policy?` | `vector` | Policy lookup from PDF |
| `What are the late payment penalties?` | `vector` | Shows penalty clauses with page refs |

---

## API Reference

### `POST /ask`

```json
// Request
{
  "question": "Which customers have overdue payments?"
}

// Response
{
  "question":  "Which customers have overdue payments?",
  "answer":    "Acme Corp has an overdue payment of $5,000 due 2024-10-01 [Source: payments table]...",
  "route":     "sql",
  "reasoning": "The question asks about payment status which is stored in the database.",
  "sources":   ["payments table"]
}
```

### `GET /health`

Returns `{"status": "ok"}` — used by the UI header health indicator.

### `GET /docs`

Interactive Swagger UI for manual testing.

---

## Project Structure

```
jenny_demo_v2/
├── agent/
│   └── router.py             # LangGraph graph + all nodes
├── api/
│   └── main.py               # FastAPI app with CORS
├── data/
│   ├── contracts.pdf         # Source contracts document
│   ├── payments.db           # SQLite payments database
│   ├── create_mock_data.py   # Script to regenerate mock data
│   └── faiss_index/          # Generated by ingest.py — do not commit
├── ingestion/
│   └── ingest.py             # PDF → embeddings → FAISS index
├── prompts/
│   └── system_prompt.txt     # LLM instructions (grounding + citation rules)
├── tools/
│   ├── __init__.py
│   ├── vector_tool.py        # FAISS search (loaded once at startup)
│   └── sql_tool.py           # Text-to-SQL generation + execution
├── ui/
│   └── index.html            # Chat UI — open directly, no build needed
├── .env.example              # Copy to .env and add GROQ_API_KEY
├── .gitignore
├── Procfile                  # Railway: bash start.sh
├── railway.toml              # Railway config
├── runtime.txt               # Python 3.11
├── requirements.txt          # Pinned dependencies
├── start.sh                  # Auto-ingest + server startup script
└── README.md
```

---

## Replacing Mock Data with Real Data

1. **Contracts:** Replace `data/contracts.pdf` with your real contract PDF.
   Re-run: `python3 ingestion/ingest.py`

2. **Payments:** Replace `data/payments.db` with your database, or edit
   `data/create_mock_data.py` to match your schema and run it.
   Update `tools/sql_tool.py` if column names differ.

---

## Performance Notes

- **Startup:** ~3–5 seconds — HuggingFace model loads once into memory.
- **Per query:** ~1–2 seconds — Groq inference is fast; FAISS search is sub-100ms.
- **Scaling:** For production, swap FAISS for Pinecone/Weaviate and SQLite for Postgres.

---

## Tech Stack

| Component | Technology |
|---|---|
| LLM | Groq `llama-3.3-70b-versatile` (free tier) |
| Embeddings | HuggingFace `BAAI/bge-small-en-v1.5` (local, free) |
| Vector store | FAISS (in-process, no server needed) |
| Database | SQLite |
| Orchestration | LangGraph |
| API | FastAPI |
| UI | Vanilla HTML/CSS/JS (no build step) |
| Deployment | Railway |
