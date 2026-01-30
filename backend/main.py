import os
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from dotenv import load_dotenv, find_dotenv
from sentence_transformers import SentenceTransformer

from .db import init_db, seed_demo_users
from .audit import init_audit, log_audit
from .auth import login, require_user
from .models import LoginRequest, LoginResponse, ChatRequest, ChatResponse, Citation, User
from .security import build_qdrant_security_filter
from .qdrant_store import get_qdrant, search
from .rag_llm import answer_from_context
from .ingest import ingest_document_for_user, extract_url, extract_pdf

from .rbac import require_admin
from .audit import list_audit_for_tenant

load_dotenv(find_dotenv(usecwd=True), override=True)

app = FastAPI(title="Enterprise RAG Platform")

_embedder = SentenceTransformer("all-MiniLM-L6-v2")

@app.get("/admin/audit")
def admin_audit(user: User = Depends(require_user), limit: int = 100):
    require_admin(user)
    return {"items": list_audit_for_tenant(user.tenant_id, limit=limit)}

@app.on_event("startup")
def _startup():
    init_db()
    init_audit()
    seed_demo_users()

@app.post("/auth/login", response_model=LoginResponse)
def auth_login(req: LoginRequest):
    token = login(req.username, req.password)
    return LoginResponse(access_token=token)

@app.post("/documents/upload_pdf")
async def upload_pdf(
    title: str = Form(...),
    roles_allowed: str = Form("member"),
    sensitive: bool = Form(False),
    file: UploadFile = File(...),
    user: User = Depends(require_user),  # Fixed: use Depends
):
    """Upload PDF → extract text → chunk → embed → store with security metadata"""
    
    max_mb = int(os.getenv("MAX_UPLOAD_MB", "15"))
    if not file.content_type or "pdf" not in file.content_type.lower():
        raise HTTPException(400, "Please upload a PDF file")
    
    data = await file.read()
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(413, "File too large (max 15MB)")
    
    # Extract text using PyPDF2 (real PDF parsing)
    raw_text = extract_pdf(data)
    
    roles = [r.strip() for r in roles_allowed.split(",") if r.strip()]
    max_chunks = int(os.getenv("MAX_CHUNKS_PER_DOC", "400"))

    doc_id, n_chunks = ingest_document_for_user(
        user=user,
        title=title,
        roles_allowed=roles,
        source_type="pdf",
        source_value=file.filename,
        raw_text=raw_text,
        sensitive_flag=sensitive,
        max_chunks=max_chunks,
    )
    
    return {
        "success": True,
        "doc_id": doc_id,
        "chunks_indexed": n_chunks,
        "message": f"Successfully indexed {n_chunks} chunks from {title}"
    }

@app.post("/documents/upload_url")
def upload_url(
    title: str,
    url: str,
    roles_allowed: str = "member",
    sensitive: bool = False,
    user: User = require_user,
):
    roles = [r.strip() for r in roles_allowed.split(",") if r.strip()]
    text = extract_url(url)
    max_chunks = int(os.getenv("MAX_CHUNKS_PER_DOC", "400"))

    doc_id, n = ingest_document_for_user(
        user=user,
        title=title,
        roles_allowed=roles,
        source_type="url",
        source_value=url,
        raw_text=text,
        sensitive_flag=sensitive,
        max_chunks=max_chunks,
    )
    return {"doc_id": doc_id, "chunks_indexed": n}

@app.post("/chat/query", response_model=ChatResponse)
def chat_query(req: ChatRequest, user: User = require_user):
    top_k = int(os.getenv("TOP_K", "6"))

    q_vec = _embedder.encode([req.question], normalize_embeddings=True)[0].tolist()
    q_filter = build_qdrant_security_filter(user)

    qc = get_qdrant()
    hits = search(qc, q_vec, q_filter, top_k=top_k)

    citations = []
    context_lines = []
    retrieved_for_audit = []

    for h in hits:
        p = h.payload
        snippet = (p["text"][:220] + "...") if len(p["text"]) > 220 else p["text"]
        citations.append(
            Citation(
                doc_id=int(p["doc_id"]),
                title=str(p["title"]),
                chunk_id=int(p["chunk_id"]),
                snippet=snippet,
            )
        )
        context_lines.append(
            f"[doc_id={p['doc_id']} title={p['title']} chunk_id={p['chunk_id']}]\n{p['text']}"
        )
        retrieved_for_audit.append({"doc_id": p["doc_id"], "chunk_id": p["chunk_id"]})

    context_pack = "\n\n---\n\n".join(context_lines) if context_lines else "NO_CONTEXT"
    answer = answer_from_context(req.question, context_pack)

    log_audit(user.tenant_id, user.user_id, req.question, json.dumps(retrieved_for_audit))

    return ChatResponse(
        answer=answer,
        citations=citations if citations else [
            Citation(doc_id=-1, title="none", chunk_id=-1, snippet="No relevant authorized context found.")
        ],
    )