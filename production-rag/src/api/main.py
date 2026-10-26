from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

# Use absolute imports from src
from src.api.routes import router as api_router

app = FastAPI(
    title="Production RAG Engine",
    version="1.0.0",
    description="Local enterprise RAG system powered by Qdrant, BM25, and Ollama/Groq."
)

# Enable CORS so external frontends or browsers can talk to your API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this to your frontend domain in strict production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your core API routes FIRST (so /api/v1/... is never blocked)
app.include_router(api_router, prefix="/api/v1")

# Optional: Only mount static files if the 'static' directory actually exists
if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
else:
    @app.get("/")
    async def root_fallback():
        return {
            "message": "Production RAG API is running!",
            "docs": "/docs",
            "api_prefix": "/api/v1"
        }