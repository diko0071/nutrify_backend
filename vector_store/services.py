from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from qdrant_client.models import PointStruct
import os
from langchain_openai import OpenAIEmbeddings
import uuid 

class VectorStoreActions:
    def __init__(self):
        self.client = QdrantClient(os.getenv('QDRANT_URL'))

    def create_collection(self, collection_name: str):
        try:
            size = 1536
            collection = self.client.create_collection(collection_name, vectors_config=VectorParams(size=size, distance=Distance.COSINE))
            return collection
        except Exception as e:
            raise Exception(f"Error creating collection: {e}")
        
    def generate_vector(self, text: str):
        embeddings = OpenAIEmbeddings(model='text-embedding-3-small')
        vector = embeddings.embed_query(text)
        return vector
        
    def add_vector_to_collection(self, collection_name: str, vector: list[float], payload: dict):
        try:
            points = [PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload)]
            operation_info = self.client.upsert(
                collection_name=collection_name,
                wait=True,
                points=points
            )
            return operation_info
        except Exception as e:
            raise Exception(f"Error adding vectors: {e}")
        
    def run_vector_search_query_raw(self, collection_name: str, query_vector: list[float], limit: int = 10):
        try:
            points = self.client.search(collection_name, query_vector, limit=limit)
            return points
        except Exception as e:
            raise Exception(f"Error running vector search query: {e}")
        
    def run_search_query_with_text(self, collection_name: str, text: str, limit: int = 10):
        try:
            query_vector = self.generate_vector(text)
            search_results = self.run_vector_search_query_raw(collection_name, query_vector, limit)
            return search_results
        except Exception as e:
            raise Exception(f"Error running similarity search query: {e}")



