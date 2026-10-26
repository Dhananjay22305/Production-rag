from fastapi import APIRouter, HTTPException, UploadFile, File
from src.services.retriever import HybridRetriever
from src.services.generator import LLMGenerator
from src.services.parser import parse_pdf
import os

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.post("/query")
async def query_rag(query: str):
    try:
        retriever = HybridRetriever()
        generator = LLMGenerator()
        retrieved_chunks = retriever.retrieve(query)
        return {"query": query, "results": retrieved_chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        parsed_data = parse_pdf(file_path)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return {"filename": file.filename, "status": "Successfully parsed", "chunks_count": len(parsed_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")