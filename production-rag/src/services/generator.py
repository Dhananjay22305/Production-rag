import os
from groq import Groq

class LLMGenerator:
    def __init__(self):
        # Secure: Pulls from environment variable only. No hardcoded key!
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set.")
            
        self.client = Groq(api_key=api_key)
        self.model_name = os.getenv("OPENAI_MODEL_NAME", "openai/gpt-oss-20b")

    async def stream_answer(self, query: str, retrieved_chunks: list, history: list = None):
        context_str = "\n\n".join([f"\n{chunk.get('text', '')}" for chunk in retrieved_chunks])
        
        messages = [
            {"role": "system", "content": f"Answer concisely using the provided context:\n{context_str}"},
            {"role": "user", "content": query}
        ]

        try:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
                stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            yield f"\n[Error connecting to Groq cloud: {str(e)}]"