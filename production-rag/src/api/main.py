from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router as api_router

class SPAStaticFiles(StaticFiles):
    """Custom static file handler that bypasses API routes so they never get swallowed."""
    async def get_response(self, path: str, scope: Request):
        if path.startswith("api/") or path == "upload" or path == "query" or path == "health":
            raise 404
        return await super().get_response(path, scope)

app = FastAPI(
    title="Production RAG Engine",
    version="1.0.0",
    description="Local enterprise RAG system powered by Qdrant, BM25, and LLMs."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Register API routes first
app.include_router(api_router)

# 2. Mount static files using the custom handler at the root
app.mount("/", SPAStaticFiles(directory="static", html=True), name="static")