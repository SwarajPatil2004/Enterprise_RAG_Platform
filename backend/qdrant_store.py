# Globals/Configuration
# - COLLECTION = environment variable "QDRANT_COLLECTION" or default "enterprise_chunks"

# Function: get_qdrant() -> QdrantClient
# - Read QDRANT_URL from environment (must exist)
# - Read QDRANT_API_KEY from environment (must exist)
# - Create a QdrantClient using:
#   - url = QDRANT_URL
#   - api_key = QDRANT_API_KEY
# - Return the client [web:6]

# Function: ensure_collection(client, vector_size)
# - existing_collections = list of collection names from client.get_collections()
# - If COLLECTION is in existing_collections:
#   - Return (collection already exists) [web:6]
# - Otherwise:
#   - Create a new collection named COLLECTION with:
#     - vectors_config = VectorParams(size=vector_size, distance=COSINE) [web:1]
#   - Return (done)

# Function: upsert_chunks(client, points)
# - Upsert (insert or update) the given points into COLLECTION [web:6]

# Function: search(client, query_vector, q_filter, top_k) -> results
# - Run vector similarity search in COLLECTION using:
#   - query_vector = query_vector
#   - query_filter = q_filter
#   - limit = top_k
#   - with_payload = True (return metadata/payload along with matches) [web:6]
# - Return the search results