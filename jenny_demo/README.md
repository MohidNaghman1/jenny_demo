# Business Knowledge Assistant — Hybrid RAG Demo

A production-structured LangGraph agent that answers business questions by
routing across a PDF contracts store and a SQLite payments database,
then synthesises grounded answers with source citations.

---

## Architecture

```
User Question
      │
      ▼
┌─────────────────────┐
│   Query Rewriter    │  Rewrites to keyword-rich search query
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│       Router        │  Classifies: vector / sql / hybrid
└──────────┬──────────┘
           │
     ┌─────┴──────────────────┐
     ▼                        ▼                      ▼
vector_node              sql_node            vector → sql
FAISS semantic      LLM-generated SQL         (hybrid)
search over PDF     over payments.db
     │                        │                      │
     └────────────────────────┴──────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │    Synthesizer      │  Cited, grounded answer
                    └─────────────────────┘
```

**Stack**

| Component     | Technology                                        |
|---------------|---------------------------------------------------|
| LLM           | Groq `llama-3.3-70b-versatile`                    |
| Embeddings    | HuggingFace Inference API `BAAI/bge-small-en-v1.5`|
| Vector store  | FAISS                                             |
| Orchestration | LangGraph                                         |
| API           | FastAPI                                           |
| Frontend      | Vanilla HTML/CSS/JS (no build step)               |
| Deployment    | Render (free tier)                                |

---

## Project Structure

```
├── agent/
│   └── router.py            # LangGraph graph — pure orchestration
├── api/
│   └── main.py              # FastAPI endpoints
├── data/
│   ├── contracts.pdf        # Source PDF document
│   ├── payments.db          # SQLite payments database
│   ├── faiss_index/         # Pre-built FAISS index (commit this)
│   └── create_mock_data.py
├── ingestion/
│   └── ingest.py            # PDF → chunks → HF API embeddings → FAISS
├── prompts/
│   └── system_prompt.txt    # LLM system prompt
├── tools/
│   ├── __init__.py
│   ├── vector_tool.py       # FAISS search (singleton)
│   └── sql_tool.py          # Schema cache + text-to-SQL
├── ui/
│   └── index.html           # Chat UI — open directly in browser
├── .env.example
├── .gitignore
├── render.yaml              # Render deployment config
├── requirements.txt
└── runtime.txt
```

---

## Local Setup

### 1 — Get API keys (both free)

**Groq API key**
1. Sign up at [console.groq.com](https://console.groq.com)
2. Navigate to **API Keys** → **Create API Key**
3. Copy the key (starts with `gsk_`)

**HuggingFace token**
1. Sign up at [huggingface.co](https://huggingface.co)
2. Go to **Settings** → **Access Tokens** → **New Token**
3. Select **Read** role, copy the token (starts with `hf_`)

### 2 — Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```
GROQ_API_KEY=gsk_your_key_here
HF_TOKEN=hf_your_token_here
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Build the FAISS index

```bash
python3 ingestion/ingest.py
```

Output:
```
📄 Loading PDF...
   Loaded 2 pages
   Split into 18 chunks
🔢 Embedding via HuggingFace Inference API (BAAI/bge-small-en-v1.5)...
✅ FAISS index saved to data/faiss_index
   Total vectors: 18
```

> ⚠️ Commit `data/faiss_index/` to your repo before deploying.
> Render does not run ingestion — it uses the pre-built index from the repo.

### 5 — Start the API

```bash
uvicorn api.main:app --reload --port 8000
```

- API: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

### 6 — Open the UI

```bash
open ui/index.html       # macOS
xdg-open ui/index.html   # Linux
```

No npm, no build tools. The UI calls `http://localhost:8000/ask`.

---

## Deploying to Render (Free Tier)

Render free tier is sufficient for a demo — no credit card required.

### Step 1 — Build FAISS index locally and commit it

```bash
python3 ingestion/ingest.py
git add data/faiss_index/
git commit -m "Add pre-built FAISS index"
git push
```

### Step 2 — Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/jenny-rag-demo.git
git push -u origin main
```

### Step 3 — Deploy on Render

1. Go to [render.com](https://render.com) → **New** → **Web Service**
2. Connect your GitHub repo
3. Render detects `render.yaml` automatically
4. Go to **Environment** and add:
   ```
   GROQ_API_KEY = gsk_your_key_here
   HF_TOKEN     = hf_your_token_here
   ```
5. Click **Deploy** — build takes ~2 minutes

Your API will be live at `https://your-app.onrender.com`

### Step 4 — Update the UI with your live URL

Edit one line in `ui/index.html`:

```javascript
// Change this:
const API = "http://localhost:8000";

// To your Render URL:
const API = "https://your-app.onrender.com";
```

### Step 5 — Host the UI on GitHub Pages

1. Push the updated `ui/index.html`
2. Go to repo **Settings** → **Pages**
3. Source: **main branch** → **/ui** folder
4. UI live at: `https://YOUR_USERNAME.github.io/jenny-rag-demo`

> ⚠️ Render free tier spins down after 15 minutes of inactivity.
> First request after idle takes ~30 seconds to wake up. This is normal for a demo.

---

## API Reference

### `POST /ask`

```json
// Request
{
  "question": "Which customers have overdue payments and what does their contract say about suspension?"
}

// Response
{
  "question":  "Which customers have overdue payments...",
  "answer":    "Acme Corp has two overdue payments totalling $10,000 [Source: payments table]. Their contract specifies suspension after 60 days of non-payment with a $200 reinstatement fee [Source: contracts.pdf, Page 1].",
  "route":     "hybrid",
  "reasoning": "The question requires payment data from the database and suspension terms from the contracts.",
  "sources":   ["payments table", "contracts.pdf p.1"]
}
```

### `GET /health`

```json
{ "status": "ok" }
```

---

## Demo Queries

| Query | Route | Tests |
|---|---|---|
| Which customers have overdue payments? | `sql` | SQL-only, amounts + dates |
| What does the contract say about service suspension? | `vector` | PDF-only, clause extraction |
| Which customers have overdue payments and what does their contract say about suspension? | `hybrid` | Cross-source synthesis |
| What is the refund policy? | `vector` | PDF-only, policy lookup |
| What is the weather today? | `vector` | Missing-info behaviour |

---

## Key Design Decisions

**HuggingFace Inference API for embeddings** — Eliminates the 40MB local model
download. Embeddings are generated via API call, keeping Render's free tier
memory usage well within limits.

**Pre-built FAISS index committed to repo** — Render's free tier has no
persistent disk. The index is built locally and committed so it's available
at runtime without any build-time ingestion step.

**Singletons at module load** — Embeddings client, FAISS index, DB schema,
and system prompt are all initialised once. Zero cold-start cost per query.

**Tools as separate modules** — `tools/vector_tool.py` and `tools/sql_tool.py`
own their data access logic. `router.py` is pure orchestration. Each tool
is independently testable and swappable.

**Query rewriting before routing** — Raw user question is rewritten into a
keyword-rich search query before hitting FAISS. Improves retrieval quality
significantly for conversational or vague phrasings.
