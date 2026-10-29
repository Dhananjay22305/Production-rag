import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.services.generator import LLMGenerator
from src.services.parser import DocumentParser
from src.services.retriever import HybridRetriever

# The frontend (static/script.js) calls everything under /api/v1.
router = APIRouter(prefix="/api/v1")
# Kept so Render's health check / old links on /health still work.
root_router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    top_k: int = 3
    history: Optional[List[Dict[str, Any]]] = None


@router.get("/health")
@root_router.get("/health")
async def health_check():
    retriever = HybridRetriever()
    return {"status": "healthy", "documents": len(retriever.list_documents())}


@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...), strategy: str = "sentence_aware"):
    filename = os.path.basename(file.filename or "document.pdf")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        pages = DocumentParser.extract_text_from_pdf(tmp_path)
        if not pages:
            raise HTTPException(
                status_code=422,
                detail="No extractable text found (scanned/image-only PDF?).",
            )

        if strategy == "fixed":
            chunks = DocumentParser.chunk_fixed_size(pages, doc_name=filename)
        else:
            chunks = DocumentParser.chunk_sentence_aware(pages, doc_name=filename)

        retriever = HybridRetriever()
        retriever.add_chunks(chunks)
        docs = retriever.list_documents()

        return {
            "filename": filename,
            "status": "indexed",
            "chunks_count": len(chunks),
            "total_documents_count": len(docs),
            "active_documents": docs,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.get("/retrieval-preview")
async def retrieval_preview(question: str = Query(...), top_k: int = 3):
    chunks = HybridRetriever().retrieve(question, top_k=top_k)
    return {"question": question, "retrieved_chunks": chunks}


@router.post("/chat")
async def chat(req: ChatRequest):
    chunks = HybridRetriever().retrieve(req.question, top_k=req.top_k)

    async def token_stream():
        if not chunks:
            yield "I couldn't find anything relevant in the ingested documents. Upload a PDF in the Document Ingestion tab first, or try rephrasing."
            return
        try:
            generator = LLMGenerator()
        except Exception as e:
            yield f"[Backend is running, but the LLM is not configured: {e}]"
            return
        async for token in generator.stream_answer(req.question, chunks, req.history):
            yield token

    return StreamingResponse(token_stream(), media_type="text/plain; charset=utf-8")