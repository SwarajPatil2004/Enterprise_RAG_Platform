import os
import json
import io
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.concurrency import run_in_threadpool
from sentence_transformers import SentenceTransformer
import uvicorn

# Load .env from project root FIRST
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH, override=True)

app = FastAPI(title="Enterprise RAG Platform")

# Import after app is created to avoid circular imports
from backend.db import init_db, seed_demo_users
from backend.audit import init_audit, log_audit
from backend.auth import login, require_user
from backend.models import LoginRequest, LoginResponse, ChatRequest, ChatResponse, Citation, User
from backend.security import build_qdrant_security_filter
from backend.qdrant_store import get_qdrant, search
from backend.rag_llm import answer_from_context
from backend.ingest import ingest_document_for_user, extract_pdf, extract_url

_embedder = SentenceTransformer("all-MiniLM-L6-v2")

@app.on_event("startup")
def _startup():
    """Initialize database and demo users."""
    init_db()
    init_audit()
    seed_demo_users()
    print("✅ Database initialized with demo users")

@app.post("/auth/login", response_model=LoginResponse)
def auth_login(req: LoginRequest):
    """Login and return JWT token."""
    token = login(req.username, req.password)
    return LoginResponse(access_token=token)

@app.post("/documents/upload_pdf")
async def upload_pdf(
    title: str = Form(...),
    roles_allowed: str = Form("member"),
    allowed_users: str = Form(""),
    allowed_groups: str = Form(""),
    sensitive: bool = Form(False),
    file: UploadFile = File(...),
    user: User = Depends(require_user),
):
    """Upload PDF → extract text → chunk → embed → store with ACL."""
    
    max_mb = int(os.getenv("MAX_UPLOAD_MB", "15"))
    if not file.content_type or "pdf" not in file.content_type.lower():
        raise HTTPException(400, "Please upload a PDF file")
    
    data = await file.read()
    if len(data) > max_mb * 1024 * 1024:
        raise HTTPException(413, "File too large (max 15MB)")
    
    try:
        print(f"DEBUG: Starting upload_pdf for {file.filename}")
        # Extract text using PyPDF2 (real PDF parsing) - run in threadpool to avoid blocking loop
        print("DEBUG: Calling extract_pdf in threadpool")
        raw_text = await run_in_threadpool(extract_pdf, data)
        print(f"DEBUG: Extracted {len(raw_text)} chars")
        
        if not raw_text.strip():
            raise HTTPException(400, "No text extracted from PDF")
        
        roles = [r.strip() for r in roles_allowed.split(",") if r.strip()]
        users = [int(u.strip()) for u in allowed_users.split(",") if u.strip()]
        groups = [g.strip() for g in allowed_groups.split(",") if g.strip()]
        max_chunks = int(os.getenv("MAX_CHUNKS_PER_DOC", "400"))

        print("DEBUG: Calling ingest_document_for_user in threadpool")
        doc_id, n_chunks = await run_in_threadpool(
            ingest_document_for_user,
            user=user,
            title=title,
            roles_allowed=roles,
            allowed_users=users,
            allowed_groups=groups,
            source_type="pdf",
            source_value=file.filename,
            raw_text=raw_text,
            sensitive_flag=sensitive,
            max_chunks=max_chunks,
        )
        print("DEBUG: Ingest complete")
        
        return {
            "success": True,
            "doc_id": doc_id,
            "chunks_indexed": n_chunks,
            "message": f"Successfully indexed {n_chunks} chunks from {title}"
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Internal Server Error: {str(e)}")

@app.post("/documents/upload_url")
async def upload_url(
    title: str = Form(...),
    url: str = Form(...),
    roles_allowed: str = Form("member"),
    allowed_users: str = Form(""),
    allowed_groups: str = Form(""),
    sensitive: bool = Form(False),
    user: User = Depends(require_user),
):
    """Ingest URL → extract text → chunk → embed → store with ACL."""
    roles = [r.strip() for r in roles_allowed.split(",") if r.strip()]
    users = [int(u.strip()) for u in allowed_users.split(",") if u.strip()]
    groups = [g.strip() for g in allowed_groups.split(",") if g.strip()]
    
    text = extract_url(url)
    if not text.strip():
        raise HTTPException(400, "No text extracted from URL")
    
    max_chunks = int(os.getenv("MAX_CHUNKS_PER_DOC", "400"))

    doc_id, n_chunks = ingest_document_for_user(
        user=user,
        title=title,
        roles_allowed=roles,
        allowed_users=users,
        allowed_groups=groups,
        source_type="url",
        source_value=url,
        raw_text=text,
        sensitive_flag=sensitive,
        max_chunks=max_chunks,
    )
    
    return {
        "success": True,
        "doc_id": doc_id,
        "chunks_indexed": n_chunks
    }

@app.post("/chat/query", response_model=ChatResponse)
async def chat_query(req: ChatRequest, user: User = Depends(require_user)):
    """RAG query with security trimming."""
    try:
        top_k = int(os.getenv("TOP_K", "6"))

        print(f"DEBUG: Processing Query: {req.question}")
        
        # 1. Embedding (CPU bound)
        def encode_query(q):
            # Force CPU to avoid CUDA crashes/conflicts
            return _embedder.encode([q], normalize_embeddings=True, device="cpu")[0].tolist()
            
        q_vec = await run_in_threadpool(encode_query, req.question)
        
        q_filter = build_qdrant_security_filter(user)

        try:
            qc = get_qdrant()
            hits = search(qc, q_vec, q_filter, top_k=top_k)
        except Exception as e:
            print(f"Qdrant error: {e}")
            return ChatResponse(
                answer="Qdrant unavailable. Please check your QDRANT_URL/API_KEY.",
                citations=[Citation(doc_id=-1, title="error", chunk_id=-1, snippet="Vector DB connection failed")]
            )

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
        
        # 2. LLM Inference (CPU/GPU bound, heavily blocking)
        print("DEBUG: Calling LLM...")
        answer = await run_in_threadpool(answer_from_context, req.question, context_pack)
        print("DEBUG: LLM complete")

        log_audit(user.tenant_id, user.user_id, req.question, json.dumps(retrieved_for_audit))

        return ChatResponse(
            answer=answer,
            citations=citations if citations else [
                Citation(doc_id=-1, title="none", chunk_id=-1, snippet="No relevant authorized context found.")
            ],
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return ChatResponse(
            answer=f"**System Error**: {str(e)}\n\nCheck server logs for traceback.",
            citations=[]
        )

@app.get("/admin/audit")
async def admin_audit(user: User = Depends(require_user), limit: int = 100):
    """Admin audit log viewer."""
    from backend.audit import list_audit_for_tenant
    from backend.rbac import require_admin
    require_admin(user)
    return {"items": list_audit_for_tenant(user.tenant_id, limit=limit)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)