import os
from datetime import datetime
from qdrant_client import QdrantClient, models

COLLECTION = os.getenv("QDRANT_COLLECTION", "enterprise_chunks")

# Global singleton for memory client
_memory_client = None

def get_qdrant() -> QdrantClient:
    global _memory_client
    
    url = os.environ.get("QDRANT_URL")
    api_key = os.environ.get("QDRANT_API_KEY")

    if url == ":memory:" or url == "memory":
        if _memory_client is None:
            print("initializing global Qdrant :memory: client")
            _memory_client = QdrantClient(location=":memory:")
        return _memory_client
    
    return QdrantClient(
        url=url,
        api_key=api_key,
    )

def ensure_collection(client: QdrantClient, vector_size: int):
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION in existing:
        return

    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )

def upsert_chunks(client: QdrantClient, points: list[models.PointStruct]):
    client.upsert(collection_name=COLLECTION, points=points)

def search(client: QdrantClient, query_vector: list[float], q_filter: models.Filter, top_k: int):
    return client.search(
        collection_name=COLLECTION,
        query_vector=query_vector,
        query_filter=q_filter,
        limit=top_k,
        with_payload=True,
    )