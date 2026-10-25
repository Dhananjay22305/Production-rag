import os
import uuid
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
import ollama

class HybridRetriever:
    """Handles vector search using Qdrant and Ollama dense embeddings with batched safety."""
    
    def __init__(self):
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        self.collection_name = os.getenv("QDRANT_COLLECTION_NAME", "hr_policies")
        
        # Initialize Qdrant client
        self.client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        
        # Initialize Local Embedding Model (nomic-embed-text via Ollama)
        self.embedding_model = os.getenv("EMBEDDING_MODEL_NAME", "nomic-embed-text")
        
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensures the Qdrant collection exists with correct vector dimensions."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            # nomic-embed-text outputs 768-dimensional vectors
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE)
            )

    def _get_embedding(self, text: str) -> List[float]:
        """Generates dense vector embeddings locally via Ollama."""
        response = ollama.embeddings(
            model=self.embedding_model,
            prompt=text
        )
        return response["embedding"]

    def index_chunks(self, chunks: List[Dict[str, Any]]):
        """Indexes document chunks into Qdrant in memory-safe batches of 50."""
        if not chunks:
            return

        batch_size = 50 
        total_chunks = len(chunks)
        
        for i in range(0, total_chunks, batch_size):
            batch = chunks[i:i + batch_size]
            points = []
            
            for chunk in batch:
                vector = self._get_embedding(chunk["text"])
                
                # Combine doc_name and chunk_id so different PDFs never collide and overwrite each other
                string_id = f"{chunk['doc_name']}_{chunk['chunk_id']}"
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, string_id))
                
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload={
                            "doc_name": chunk["doc_name"],
                            "page_number": chunk["page_number"],
                            "text": chunk["text"],
                            "original_chunk_id": chunk['chunk_id']
                        }
                    )
                )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Performs vector similarity search against Qdrant using modern client API."""
        query_vector = self._get_embedding(query)
        
        # Use query_points for modern qdrant-client versions
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k
        )
        
        retrieved_chunks = []
        for result in response.points:
            retrieved_chunks.append({
                "chunk_id": result.payload.get("original_chunk_id", str(result.id)),
                "score": result.score,
                "doc_name": result.payload.get("doc_name"),
                "page_number": result.payload.get("page_number"),
                "text": result.payload.get("text")
            })
            
        return retrieved_chunks