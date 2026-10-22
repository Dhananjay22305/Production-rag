import shutil
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from src.services.parser import DocumentParser
from src.services.retriever import HybridRetriever
from src.services.generator import LLMGenerator

router = APIRouter()

# Global Service Singletons
retriever = HybridRetriever()
generator = LLMGenerator()

class ChatMessage(BaseModel):
    role: str
    content: str

class QueryRequest(BaseModel):
    question: str
    top_k: int = 4
    history: Optional[List[ChatMessage]] = []

@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...), strategy: str = "sentence_aware"):
    """Ingests, cleans, chunks, and indexes uploaded PDF documents with size validation."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    temp_path = f"data/{file.filename}"
    os.makedirs("data", exist_ok=True)
    
    # Save file and check size (e.g., max 50MB limit for local prototype stability)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    file_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
    if file_size_mb > 50:  
        os.remove(temp_path)
        raise HTTPException(
            status_code=413, 
            detail=f"File size ({file_size_mb:.1f}MB) exceeds the 50MB local processing limit. Please upload a smaller document."
        )

    try:
        pages_data = DocumentParser.extract_text_from_pdf(temp_path)
        
        if strategy == "fixed":
            chunks = DocumentParser.chunk_fixed_size(pages_data, doc_name=file.filename)
        else:
            chunks = DocumentParser.chunk_sentence_aware(pages_data, doc_name=file.filename)

        # Index chunks in memory-safe batches
        retriever.index_chunks(chunks)

        return {
            "status": "Success",
            "filename": file.filename,
            "total_pages": len(pages_data),
            "total_chunks_created": len(chunks),
            "chunking_strategy": strategy
        }
    except Exception as e:
        import traceback
        traceback.print_exc()  # This will force the exact error line to print in your terminal
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@router.post("/chat")
async def chat_stream(request: QueryRequest):
    """Hybrid retrieves relevant context and streams grounded answers with conversation history."""
    retrieved_chunks = retriever.search(query=request.question, top_k=request.top_k)

    async def token_generator():
        async for token in generator.stream_answer(
            query=request.question, 
            retrieved_chunks=retrieved_chunks,
            history=request.history
        ):
            yield token

    return StreamingResponse(token_generator(), media_type="text/plain")

@router.get("/retrieval-preview")
async def preview_retrieval(question: str = Query(...), top_k: int = 4):
    """Returns top reranked chunks without triggering the LLM generation step."""
    retrieved_chunks = retriever.search(query=question, top_k=top_k)
    return {"query": question, "retrieved_chunks": retrieved_chunks}