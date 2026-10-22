import os
from typing import List, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI

class LLMGenerator:
    """Handles prompt construction, citation grounding, and token streaming with history."""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY", "ollama")
        base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
        self.model_name = os.getenv("OPENAI_MODEL_NAME", "llama3.2")
        
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def build_prompt(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Constructs a grounded, zero-hallucination context injection block."""
        context_str = ""
        for idx, chunk in enumerate(retrieved_chunks, start=1):
            context_str += (
                f"--- DOCUMENT CHUNK {idx} ---\n"
                f"Source File: {chunk['doc_name']}\n"
                f"Page Number: {chunk['page_number']}\n"
                f"Content: {chunk['text']}\n\n"
            )

        system_instruction = (
            "You are an enterprise AI assistant answering questions based strictly on provided documents.\n"
            "Rules:\n"
            "1. Answer using ONLY facts from the provided context and ongoing conversation history.\n"
            "2. If the answer cannot be determined, state clearly: 'I don't know based on the provided documents.'\n"
            "3. Always cite sources inline using this format: [Document Name, Page X].\n"
            "4. Do not guess or extrapolate beyond what is explicitly stated."
        )

        user_prompt = f"Context Information:\n{context_str}\nCurrent Question: {query}"
        return system_instruction, user_prompt

    async def stream_answer(
        self, 
        query: str, 
        retrieved_chunks: List[Dict[str, Any]],
        history: List[Any] = []
    ) -> AsyncGenerator[str, None]:
        """Streams LLM tokens step-by-step incorporating past chat turns."""
        if not retrieved_chunks:
            yield "I don't know based on the provided documents. No relevant context was found."
            return

        system_instruction, user_prompt = self.build_prompt(query, retrieved_chunks)

        # Build message payload starting with system instruction
        messages = [{"role": "system", "content": system_instruction}]

        # Append previous conversation turns if any exist
        for h in history:
            messages.append({"role": h.role, "content": h.content})

        # Append current user prompt containing new context and query
        messages.append({"role": "user", "content": user_prompt})

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.0,
            max_tokens=512,
            stream=True,
            extra_body={
                "options": {
                    "num_ctx": 4096,
                    "num_predict": 512
                }
            }
        )

        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content