import asyncio
import os
import threading

from groq import Groq


class LLMGenerator:
    def __init__(self):
        # Secure: pulls from environment variables only. Set GROQ_API_KEY in Render.
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set.")

        self.client = Groq(api_key=api_key)
        self.model_name = os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-20b")

    async def stream_answer(self, query: str, retrieved_chunks: list, history: list = None):
        context_str = "\n\n".join(chunk.get("text", "") for chunk in retrieved_chunks)

        messages = [
            {
                "role": "system",
                "content": "Answer concisely using only the provided context. "
                           "If the answer is not in the context, say so.\n\nContext:\n" + context_str,
            }
        ]
        for msg in (history or [])[-6:]:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": query})

        # The Groq SDK stream is synchronous; run it in a thread so the event loop isn't blocked.
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        DONE = object()

        def worker():
            try:
                stream = self.client.chat.completions.create(
                    model=self.model_name, messages=messages, temperature=0.1, stream=True
                )
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        loop.call_soon_threadsafe(queue.put_nowait, chunk.choices[0].delta.content)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, f"\n[Error from Groq: {e}]")
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, DONE)

        threading.Thread(target=worker, daemon=True).start()
        while True:
            item = await queue.get()
            if item is DONE:
                break
            yield item