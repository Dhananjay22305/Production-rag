import os
from qdrant_client import QdrantClient

class HybridRetriever:
    def __init__(self):
        self.qdrant_url = os.getenv("QDRANT_URL", None)
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY", None)
        
        try:
            if self.qdrant_url and self.qdrant_api_key:
                self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
            elif self.qdrant_url:
                self.client = QdrantClient(url=self.qdrant_url)
            else:
                self.client = QdrantClient(":memory:")
            
            self._ensure_collection()
        except Exception as e:
            print(f"Warning: Qdrant fallback triggered: {e}")
            self.client = QdrantClient(":memory:")

    def _ensure_collection(self):
        try:
            self.client.get_collections()
        except Exception as e:
            print(f"Collection check skipped: {e}")

    def retrieve(self, query: str, top_k: int = 3):
        return []