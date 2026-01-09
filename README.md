# Enterprise RAG Platform

A multi-tenant RAG (Retrieval-Augmented Generation) demo: different “companies” (tenants) upload PDFs/URLs, and users can ask questions and get answers **only from documents they’re allowed to see**, with **citations** for every answer.

**Core idea:** “security trimming” — the backend filters retrieval by `tenant_id` + `roles_allowed` so unauthorized text is never sent to the model. Qdrant supports metadata (payload) filtering for vector search, which makes this possible.
---

## Features

- Multi-tenant isolation (Tenant A cannot access Tenant B data).
- RBAC/ACL on every chunk (`roles_allowed` + optional `sensitive` flag).- Citations returned for each answer (doc + chunk id + snippet).
- Local embeddings (Sentence Transformers) and **local LLM** (llama.cpp) → no paid APIs.
- Optional RAG evaluation gate (golden dataset + metrics) before merging.

---

## Tech Stack (Free)

- Backend: FastAPI + Uvicorn
- Frontend: Streamlit
- Vector DB: Qdrant Cloud **free tier** (1GB)
- Embeddings: `sentence-transformers` (local)
- LLM: `llama-cpp-python` (local llama.cpp, GGUF model); can also run an OpenAI-compatible local server.
- Metadata DB: SQLite (local file)

---

## Architecture (High Level)

1. **Upload** PDF/URL → extract text → chunk → embed → store in Qdrant with payload metadata.
2. **Chat query** → embed question → Qdrant vector search with filter:
   - `tenant_id == user.tenant_id`
   - `roles_allowed contains user.role`
   - if non-admin: block `sensitive==true`
3. Build context from retrieved chunks → send to local LLM → return answer + citations.

Qdrant filtering is the enforcement layer that makes multi-tenant + RBAC retrieval safe.
---

## Repository Layout

```text
enterprise-rag-platform/
  backend/
    main.py
    auth.py
    db.py
    ingest.py
    qdrant_store.py
    rag_llm.py
    security.py
    models.py
    audit.py
  frontend/
    app.py
  eval/
    golden.json
    run_eval.py
  requirements.txt
  .env.example
  README.md
```

---

## Prerequisites

- Python 3.10+
- A Qdrant Cloud free cluster URL + API key
- A local GGUF model file for llama.cpp (download separately)

---

## Setup (Local, $0)

### 1) Clone and create venv

```bash
git clone <YOUR_REPO_URL>
cd enterprise-rag-platform

python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment variables

Copy `.env.example` to `.env` and fill:

- `QDRANT_URL` and `QDRANT_API_KEY` from your Qdrant Cloud free cluster]
- `JWT_SECRET` any random string
- `LLAMA_MODEL_PATH` path to your local `.gguf` model

Example:

```bash
QDRANT_URL="https://xxx.cloud.qdrant.io"
QDRANT_API_KEY="..."
JWT_SECRET="change-me"
QDRANT_COLLECTION="chunks"
SQLITE_PATH="backend/app.db"

LLM_MODE="local_llamacpp"
LLAMA_MODEL_PATH="./models/model.gguf"
LLAMA_N_CTX="4096"
LLAMA_N_THREADS="8"
LLAMA_N_GPU_LAYERS="0"
```

If your machine is weak, you can set `LLM_MODE="extractive"` (no LLM; returns top chunk text + citations).

---

## Run the App

### 1) Start backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Backend runs at:
- http://127.0.0.1:8000

### 2) Start frontend (Streamlit)

```bash
streamlit run frontend/app.py
```

Frontend runs at:
- http://localhost:8501

---

## Demo Users (Example)

This project seeds demo users on startup (edit in `backend/db.py`):

- Tenant `t1`: `alice / test` (admin)
- Tenant `t1`: `bob / test` (member)
- Tenant `t2`: `eve / test` (admin)

Use tenant + username/password on the Streamlit login page.

---

## API (Quick Reference)

### `POST /auth/login`
Input:
```json
{"tenant_id":"t1","username":"alice","password":"test"}
```

Output:
```json
{"access_token":"...","token_type":"bearer"}
```

### `POST /documents/upload`
Upload either:
- a PDF file, **or**
- a URL

Also pass `roles_allowed` like `["admin","member"]`.

### `POST /chat/query`
Input:
```json
{"question":"What is our refund policy?","top_k":5}
```

Output:
```json
{
  "answer":"...",
  "citations":[
    {"doc_id":"doc_x","title":"Refund Policy","chunk_id":"...","text":"..."}
  ]
}
```

---

## Security Notes (Important)

- The UI is **not** security. The backend enforces access control by applying Qdrant filters (tenant + role + sensitive rules).
- Context is treated as untrusted text. The system prompt instructs the LLM to ignore any “instructions” embedded inside documents (basic prompt-injection defense).

---

## Evaluation (Optional)

Run a small golden test set:

```bash
python eval/run_eval.py
```

This should call `/chat/query` and compute metrics; fail fast if quality drops.

---

## Troubleshooting

- **No results**: ensure you uploaded documents under the same tenant you are logged into.
- **LLM too slow**: use a smaller GGUF model or set `LLM_MODE=extractive`.
- **Qdrant auth errors**: re-check `QDRANT_URL` and `QDRANT_API_KEY` from your Qdrant Cloud cluster.
