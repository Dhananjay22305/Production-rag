from fastapi import APIRouter, HTTPException, UploadFile, File
from src.services.retriever import HybridRetriever
from src.services.generator import LLMGenerator
from src.services.parser import parse_pdf
import os

router = APIRouter()

@router.get("/")
async def root():
    return {"status": "Production RAG API is running successfully!"}

@router.post("/query")
async def query_rag(query: str):
    try:
        # Lazy load retriever and generator inside the endpoint
        retriever = HybridRetriever()
        generator = LLMGenerator()
        
        # Retrieve chunks
        retrieved_chunks = retriever.retrieve(query)
        
        # Generate answer stream or response
        return {"query": query, "results": retrieved_chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
            
        # Parse PDF using pypdf
        parsed_data = parse_pdf(file_path)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return {"filename": file.filename, "status": "Successfully parsed", "data": parsed_data[:2]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")