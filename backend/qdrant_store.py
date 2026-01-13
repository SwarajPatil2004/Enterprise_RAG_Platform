import os
from datetime import datetime
from qdrant_client import QdrantClient, models

COLLECTION = os.getenv("QDRANT_COLLECTION", "enterprise_chunks")

def get_qdrant() -> QdrantClient:
    return QdrantClient(
        url=os.environ["QDRANT_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
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