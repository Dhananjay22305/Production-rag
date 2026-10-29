from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import root_router, router as api_router

BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Production RAG Engine",
    version="1.0.0",
    description="Enterprise RAG system with BM25 retrieval and Groq LLM generation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. API routes first so the static mount never swallows them.
app.include_router(api_router)
app.include_router(root_router)

# 2. Static frontend at the root (index.html, script.js, style.css).
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")