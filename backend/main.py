# Setup
# - Load environment variables (.env)
# - app = FastAPI("Enterprise RAG Platform")
# - embedder = SentenceTransformer("all-MiniLM-L6-v2")

# On startup
# - init_db()
# - init_audit()
# - seed_demo_users()

# POST /auth/login
# - Read username/password from request
# - token = login(username, password)
# - Return { access_token: token }

# POST /documents/upload_pdf
# - Read form fields: title, roles_allowed (comma-separated), sensitive, file
# - max_mb = env MAX_UPLOAD_MB (default 15)
# - data = await file.read()
# - If data size > max_mb:
#   - Raise HTTP 413 "File too large"
# - raw_text = decode bytes as UTF-8 (ignore errors)
# - roles = split roles_allowed by "," and trim
# - max_chunks = env MAX_CHUNKS_PER_DOC (default 400)
# - (doc_id, n) = ingest_document_for_user(user, title, roles, "pdf", file.filename, raw_text, sensitive, max_chunks)
# - Return { doc_id, chunks_indexed: n }

# POST /documents/upload_url
# - Read inputs: title, url, roles_allowed, sensitive
# - roles = split roles_allowed by "," and trim
# - text = extract_url(url)
# - max_chunks = env MAX_CHUNKS_PER_DOC (default 400)
# - (doc_id, n) = ingest_document_for_user(user, title, roles, "url", url, text, sensitive, max_chunks)
# - Return { doc_id, chunks_indexed: n }

# POST /chat/query
# - top_k = env TOP_K (default 6)
# - q_vec = embedder.encode([question], normalize_embeddings=True)[0] as list
# - q_filter = build_qdrant_security_filter(user)
# - hits = Qdrant.search(query_vector=q_vec, filter=q_filter, limit=top_k)
# - For each hit:
#   - Build a Citation(doc_id, title, chunk_id, short snippet)
#   - Append full chunk text to context_lines (with doc/chunk identifiers)
#   - Append {doc_id, chunk_id} to retrieved_for_audit
# - context_pack = join context_lines with separators; if none, use "NO_CONTEXT"
# - answer = answer_from_context(question, context_pack)
# - log_audit(tenant_id, user_id, question, JSON(retrieved_for_audit))
# - Return { answer, citations } (or a single "none" citation if no authorized hits)