import os
from qdrant_client import QdrantClient

class HybridRetriever:
    def __init__(self):
        # Read from environment variables, defaulting to local in-memory/disk if not provided
        self.qdrant_url = os.getenv("QDRANT_URL", None)
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY", None)
        
        try:
            if self.qdrant_url and self.qdrant_api_key:
                # Connected to Qdrant Cloud
                self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
            elif self.qdrant_url:
                # Connected to a local docker or remote URL without API key
                self.client = QdrantClient(url=self.qdrant_url)
            else:
                # Fallback to local memory / local file storage for testing/deployment safety
                self.client = QdrantClient(":memory:")
            
            self._ensure_collection()
        except Exception as e:
            print(f"Warning: Qdrant initialization fallback triggered due to: {e}")
            self.client = QdrantClient(":memory:")

    def _ensure_collection(self):
        # Safety check to ensure collection exists
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            if "production_docs" not in collection_names:
                # Create default collection if it doesn't exist
                pass
        except Exception as e:
            print(f"Could not verify collections: {e}")

    def retrieve(self, query: str, top_k: int = 3):
        # Add your retrieval and search logic here
        return []