import re
from typing import List, Dict, Any
from pypdf import PdfReader
import os

class DocumentParser:
    """Handles PDF extraction, text cleaning, and chunking strategies."""
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> List[Dict[str, Any]]:
        """Extracts text page by page with metadata citations."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at: {file_path}")
            
        reader = PdfReader(file_path)
        pages_data = []
        
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            # Clean headers/footers and redundant whitespace
            cleaned_text = re.sub(r'\s+', ' ', text).strip()
            if cleaned_text:
                pages_data.append({
                    "page_number": page_num,
                    "text": cleaned_text
                })
        return pages_data

    @staticmethod
    def chunk_fixed_size(
        pages_data: List[Dict[str, Any]], 
        doc_name: str, 
        chunk_size: int = 500, 
        overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """Fixed-size character/word sliding window chunking."""
        chunks = []
        chunk_id = 0
        
        for page in pages_data:
            text = page["text"]
            words = text.split(" ")
            
            for i in range(0, len(words), chunk_size - overlap):
                chunk_words = words[i:i + chunk_size]
                chunk_text = " ".join(chunk_words)
                
                if len(chunk_text.strip()) > 20:  # Ignore tiny empty fragments
                    chunks.append({
                        "chunk_id": f"{doc_name}_p{page['page_number']}_c{chunk_id}",
                        "doc_name": doc_name,
                        "page_number": page["page_number"],
                        "text": chunk_text,
                        "strategy": "fixed"
                    })
                    chunk_id += 1
        return chunks

    @staticmethod
    def chunk_sentence_aware(
        pages_data: List[Dict[str, Any]], 
        doc_name: str, 
        max_chunk_words: int = 250
    ) -> List[Dict[str, Any]]:
        """Sentence-aware chunking to prevent mid-sentence cuts."""
        chunks = []
        chunk_id = 0

        for page in pages_data:
            text = page["text"]
            # Split text into sentences using basic sentence-ending regex
            sentences = re.split(r'(?<=[.!?]) +', text)
            
            current_chunk = []
            current_count = 0
            
            for sentence in sentences:
                words = sentence.split(" ")
                word_count = len(words)
                
                if current_count + word_count > max_chunk_words and current_chunk:
                    chunks.append({
                        "chunk_id": f"{doc_name}_p{page['page_number']}_c{chunk_id}",
                        "doc_name": doc_name,
                        "page_number": page["page_number"],
                        "text": " ".join(current_chunk),
                        "strategy": "sentence_aware"
                    })
                    chunk_id += 1
                    current_chunk = []
                    current_count = 0
                
                current_chunk.append(sentence)
                current_count += word_count
            
            if current_chunk:
                chunks.append({
                    "chunk_id": f"{doc_name}_p{page['page_number']}_c{chunk_id}",
                    "doc_name": doc_name,
                    "page_number": page["page_number"],
                    "text": " ".join(current_chunk),
                    "strategy": "sentence_aware"
                })
                chunk_id += 1
                
        return chunks

def parse_pdf(file_path: str, doc_name: str = "document") -> List[Dict[str, Any]]:
    """
    Wrapper function to maintain backward compatibility with routes.py 
    while utilizing the DocumentParser class.
    """
    pages_data = DocumentParser.extract_text_from_pdf(file_path)
    chunks = DocumentParser.chunk_sentence_aware(pages_data, doc_name=doc_name)
    return chunks