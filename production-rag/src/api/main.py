from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Use absolute imports from src
from src.api.routes import router as api_router

app = FastAPI(
    title="Production RAG Engine",
    version="1.0.0",
    description="Local enterprise RAG system powered by Qdrant, BM25, and Ollama (nomic-embed-text + llama3)."
)

# Include your core API routes (ingest, chat, retrieval-preview, etc.)
app.include_router(api_router, prefix="/api/v1")

# Mount the static directory to serve your professional web UI at root (http://localhost:8000)
app.mount("/", StaticFiles(directory="static", html=True), name="static")