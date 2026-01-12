# Globals/Initialization
# - Load an embedding model: SentenceTransformer("all-MiniLM-L6-v2") [web:21

# Function: clean_text(s) -> cleaned_string
# - Replace all whitespace runs (spaces/newlines/tabs) with a single space
# - Trim leading/trailing spaces
# - Return cleaned string

# Function: chunk_text(text, chunk_size=900, overlap=150) -> list_of_chunks
# - chunks = empty list
# - i = 0
# - While i < length(text):
#   - chunk = substring(text, from=i, to=i + chunk_size)
#   - Append chunk to chunks
#   - i = i + (chunk_size - overlap)   # slide forward with overlap
# - Return chunks

# Function: heuristic_sensitive(text) -> boolean
# - keywords = ["password", "secret", "api key", "confidential", "ssn"]
# - t = lowercase(text)
# - If any keyword appears in t:
#   - Return True
# - Else:
#   - Return False

# Function: extract_pdf(file_bytes) -> text
# - Create PdfReader from an in-memory bytes buffer
# - pages_text = empty list
# - For each page in reader.pages:
#   - page_text = page.extract_text()
#   - If page_text is null, use empty string
#   - Append page_text to pages_text
# - Return pages_text joined with newline characters

# Function: extract_url(url) -> text
# - html = HTTP GET url (timeout=20 seconds).text
# - readable_doc = ReadabilityDocument(html)
# - main_html = readable_doc.summary(html_partial=True)
# - soup = BeautifulSoup(main_html, "html.parser")
# - text = soup.get_text(separator="\n")
# - Return text

# Function: ingest_document_for_user(
#     user, title, roles_allowed, source_type, source_value,
#     raw_text, sensitive_flag, max_chunks
# ) -> (doc_id, num_points)
# 1) Save document metadata in SQLite
# - doc_id = create_document(
#     tenant_id = user.tenant_id,
#     title = title,
#     created_by = user.user_id,
#     roles_allowed_json = JSON.stringify(roles_allowed),
#     source_type = source_type,
#     source_value = source_value
#   )

# 2) Clean and chunk text
# - text = clean_text(raw_text)
# - chunks = first max_chunks of chunk_text(text)

# 3) Embed chunks
# - vectors = embedder.encode(chunks, normalize_embeddings=True) converted to a plain list
# - vector_size = length(vectors[0])

# 4) Ensure Qdrant collection exists
# - qc = get_qdrant()
# - ensure_collection(qc, vector_size)

# 5) Build Qdrant points (vectors + payload metadata)
# - points = empty list
# - For each (idx, chunk, vec) in enumerate(zip(chunks, vectors)):
#   - point_id = integer created by concatenating doc_id and idx formatted with 4 digits
#   - sensitive_value = sensitive_flag OR heuristic_sensitive(chunk)
#   - payload = {
#       "tenant_id": user.tenant_id,
#       "doc_id": doc_id,
#       "title": title,
#       "chunk_id": idx,
#       "roles_allowed": roles_allowed,
#       "sensitive": sensitive_value,
#       "text": chunk,
#       "created_at": current UTC time in ISO format
#     }
#   - points.append(PointStruct(id=point_id, vector=vec, payload=payload))

# 6) Upsert into Qdrant and return
# - upsert_chunks(qc, points)
# - Return (doc_id, number of points)