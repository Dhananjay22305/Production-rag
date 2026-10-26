from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Use absolute imports from src
from src.api.routes import router as api_router

app = FastAPI(
    title="Production RAG Engine",
    version="1.0.0",
    description="Local enterprise RAG system powered by Qdrant, BM25, and LLMs."
)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Include API routes first so they take precedence
app.include_router(api_router, prefix="/api/v1")

# 2. Mount your static frontend folder at the root path
app.mount("/", StaticFiles(directory="static", html=True), name="static")