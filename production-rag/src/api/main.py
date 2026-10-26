from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router as api_router

app = FastAPI(
    title="Production RAG Engine",
    version="1.0.0",
    description="Enterprise RAG system powered by Qdrant, BM25, and LLMs."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router without a strict prefix so it works out-of-the-box, 
# while keeping api_router as is.
app.include_router(api_router)

@app.get("/")
async def root():
    return {
        "status": "Production RAG API is live and running!",
        "docs": "/docs",
        "endpoints": ["/query", "/upload"]
    }