from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import os

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = os.getenv("QDRANT_PORT", 6333)

def init_db():
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    collections = ["level1_usagers", "level2_direction"]
    
    for collection_name in collections:
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE), # Assuming e5-base/large
            )
            print(f"Collection {collection_name} created.")
        else:
            print(f"Collection {collection_name} exists.")

if __name__ == "__main__":
    init_db()
