import json
import re
import requests
from bs4 import BeautifulSoup
from readability import Document as Readable
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from qdrant_client import models
from datetime import datetime

from .db import create_document
from .qdrant_store import get_qdrant, ensure_collection, upsert_chunks
from .models import User

_embedder = SentenceTransformer("all-MiniLM-L6-v2")

def clean_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+chunk_size])
        i += (chunk_size - overlap)
    return chunks

def heuristic_sensitive(text: str) -> bool:
    keywords = ["password", "secret", "api key", "confidential", "ssn"]
    t = text.lower()
    return any(k in t for k in keywords)

def extract_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for p in reader.pages:
        pages.append(p.extract_text() or "")
    return "\n".join(pages)

def extract_url(url: str) -> str:
    html = requests.get(url, timeout=20).text
    doc = Readable(html)
    soup = BeautifulSoup(doc.summary(html_partial=True), "html.parser")
    return soup.get_text("\n")

def ingest_document_for_user(
    user: User,
    title: str,
    roles_allowed: list[str],
    source_type: str,
    source_value: str,
    raw_text: str,
    sensitive_flag: bool,
    max_chunks: int,
):
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