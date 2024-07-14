from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from qdrant_client.models import PointStruct
import os

class VectorStoreActions:
    def __init__(self):
        self.client = QdrantClient(os.getenv('QDRANT_URL'))

    def create_collection(self, collection_name: str, size: int):
        try:
            collection = self.client.create_collection(collection_name, vectors_config=VectorParams(size=size, distance=Distance.COSINE))
            return collection
        except Exception as e:
            raise Exception(f"Error creating collection: {e}")
        
    def add_vectors(self, collection_name: str, points: list[PointStruct]):
        try:
            operation_info = self.client.upsert(
                collection_name=collection_name,
                wait=True,
                points=points
            )
            return operation_info
        except Exception as e:
            raise Exception(f"Error adding vectors: {e}")
        
    def run_vector_search_query(self, collection_name: str, query_vector: list[float], limit: int = 10):
        try:
            points = self.client.search(collection_name, query_vector, limit=limit)
            return points
        except Exception as e:
            raise Exception(f"Error running vector search query: {e}")



