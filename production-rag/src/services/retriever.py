import math
import re
import threading
from collections import Counter
from typing import Any, Dict, List

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall(text.lower())


class HybridRetriever:
    """
    Lightweight in-memory retriever (BM25 keyword ranking).

    It is a process-wide singleton so that chunks ingested through /api/v1/ingest
    are visible to /api/v1/chat and /api/v1/retrieval-preview.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._chunks = []      # list of chunk dicts
                inst._tokens = []      # tokenised text per chunk
                inst._doc_names = []   # ordered unique document names
                cls._instance = inst
        return cls._instance

    # ---------- ingestion ----------
    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        with self._lock:
            for chunk in chunks:
                self._chunks.append(chunk)
                self._tokens.append(_tokenize(chunk["text"]))
                name = chunk["doc_name"]
                if name not in self._doc_names:
                    self._doc_names.append(name)

    def list_documents(self) -> List[str]:
        return list(self._doc_names)

    # ---------- retrieval ----------
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        q_terms = _tokenize(query)
        n_docs = len(self._chunks)
        if not q_terms or n_docs == 0:
            return []

        avg_len = sum(len(t) for t in self._tokens) / n_docs or 1.0
        df = Counter()
        for toks in self._tokens:
            for term in set(toks):
                df[term] += 1

        k1, b = 1.5, 0.75
        scored = []
        for chunk, toks in zip(self._chunks, self._tokens):
            tf = Counter(toks)
            score = 0.0
            for term in set(q_terms):
                if term not in tf:
                    continue
                idf = math.log(1 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
                freq = tf[term]
                score += idf * freq * (k1 + 1) / (freq + k1 * (1 - b + b * len(toks) / avg_len))
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [dict(c, score=round(s, 4)) for s, c in scored[:top_k]]