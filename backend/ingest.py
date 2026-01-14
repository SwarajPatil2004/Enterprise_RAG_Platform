import io
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
    """Remove extra spaces and newlines, like cleaning up messy handwriting."""
    s = re.sub(r"\s+", " ", s)  # Replace all whitespace with single spaces
    return s.strip()

def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    """Split long text into smaller pieces, like cutting a big sandwich into bites."""
    chunks = []
    i = 0
    while i < len(text):
        end = min(i + chunk_size, len(text))
        chunks.append(text[i:end])
        i += (chunk_size - overlap)
        if i >= len(text):
            break
    return chunks

def heuristic_sensitive(text: str) -> bool:
    """Check if text looks secret by looking for special words."""
    keywords = ["password", "secret", "api key", "confidential", "ssn", "credit card"]
    t = text.lower()
    return any(k in t for k in keywords)

def extract_pdf(file_bytes: bytes) -> str:
    """Read text from PDF file, like opening a book and copying the words."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages.append(f"[Page {page_num+1}]\n{text}")
        return "\n\n".join(pages)
    except Exception:
        return ""

def extract_url(url: str) -> str:
    """Get readable text from webpage, like copying the main article."""
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        html = response.text
        
        # readability-lxml extracts the main content, ignoring ads/menus
        readable_doc = Readable(html)
        summary_html = readable_doc.summary(html_partial=True)
        
        # BeautifulSoup cleans up the HTML into plain text
        soup = BeautifulSoup(summary_html, "html.parser")
        text = soup.get_text("\n\n")
        
        return text.strip()
    except Exception:
        return ""

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
    """Main factory: document → chunks → vectors → Qdrant + SQLite"""
    
    # STEP 1: Save document info in SQLite (like writing in a notebook)
    doc_id = create_document(
        tenant_id=user.tenant_id,
        title=title,
        created_by=user.user_id,
        roles_allowed_json=json.dumps(roles_allowed),
        source_type=source_type,
        source_value=source_value,
    )

    # STEP 2: Clean up messy text
    text = clean_text(raw_text)
    if not text:
        raise ValueError("No text extracted from document")

    # STEP 3: Split into chunks (max limit for safety/cost)
    chunks = chunk_text(text)[:max_chunks]
    print(f"Created {len(chunks)} chunks from {title}")

    # STEP 4: Convert text to numbers (embeddings) using sentence-transformers
    vectors = _embedder.encode(chunks, normalize_embeddings=True).tolist()
    vector_size = len(vectors[0])  # Usually 384 for MiniLM

    # STEP 5: Connect to Qdrant and setup collection
    qc = get_qdrant()
    ensure_collection(qc, vector_size)

    # STEP 6: Create Qdrant points (vector + security metadata)
    points = []
    for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
        # Each chunk gets a unique ID like "doc123_chunk0001"
        point_id = int(f"{doc_id * 10000 + idx}")
        
        # Security metadata (this enables tenant isolation + RBAC)
        payload = {
            "tenant_id": user.tenant_id,
            "doc_id": doc_id,
            "title": title,
            "chunk_id": idx,
            "roles_allowed": roles_allowed,
            "sensitive": bool(sensitive_flag or heuristic_sensitive(chunk)),
            "text": chunk,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        points.append(models.PointStruct(
            id=point_id,
            vector=vec,
            payload=payload
        ))

    # STEP 7: Save to Qdrant
    upsert_chunks(qc, points)
    return doc_id, len(points)