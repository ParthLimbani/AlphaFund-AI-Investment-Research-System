"""
Procedural memory using ChromaDB + sentence-transformers.
Stores past analysis snapshots with timeliness-decay scoring (from FINCON).
Half-life ~14 days: decay = similarity * exp(-λ * days_since_stored).
"""
import math
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import os

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL, PROCEDURAL_DECAY_LAMBDA


_client: Optional[chromadb.PersistentClient] = None
_collection = None
_embedder: Optional[SentenceTransformer] = None


def _get_collection():
    global _client, _collection, _embedder
    if _collection is None:
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _collection = _client.get_or_create_collection(
            name="procedural_memory",
            metadata={"hnsw:space": "cosine"},
        )
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _collection, _embedder


def store_analysis(ticker: str, analysis_type: str, content: dict) -> str:
    """
    Persists a structured analysis result.
    analysis_type: 'fundamental' | 'technical' | 'sentiment' | 'decision'
    Returns the stored document ID.
    """
    collection, embedder = _get_collection()
    doc_id = str(uuid.uuid4())
    text = f"{ticker} {analysis_type}: {json.dumps(content, default=str)}"
    embedding = embedder.encode(text).tolist()

    collection.add(
        documents=[text],
        embeddings=[embedding],
        metadatas=[{
            "ticker": ticker,
            "analysis_type": analysis_type,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "content_json": json.dumps(content, default=str),
        }],
        ids=[doc_id],
    )
    return doc_id


def retrieve_similar(ticker: str, query: str, top_k: int = 5) -> list[dict]:
    """
    Retrieves top-k similar past analyses, ranked by timeliness-decayed similarity.
    Returns list of dicts with content + decay_score.
    """
    collection, embedder = _get_collection()
    query_text = f"{ticker} {query}"
    embedding = embedder.encode(query_text).tolist()

    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(top_k * 3, max(1, collection.count())),
        where={"ticker": ticker},
        include=["documents", "metadatas", "distances"],
    )

    now = datetime.now(timezone.utc)
    scored = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        similarity = 1 - dist  # cosine distance → similarity
        stored_at_str = meta.get("stored_at", "")
        try:
            stored_at = datetime.fromisoformat(stored_at_str)
            days_old = (now - stored_at).total_seconds() / 86400
        except Exception:
            days_old = 0

        decay_score = similarity * math.exp(-PROCEDURAL_DECAY_LAMBDA * days_old)

        try:
            content = json.loads(meta.get("content_json", "{}"))
        except Exception:
            content = {}

        scored.append({
            "ticker": meta.get("ticker"),
            "analysis_type": meta.get("analysis_type"),
            "stored_at": stored_at_str,
            "days_old": round(days_old, 1),
            "similarity": round(similarity, 4),
            "decay_score": round(decay_score, 4),
            "content": content,
        })

    scored.sort(key=lambda x: x["decay_score"], reverse=True)
    return scored[:top_k]


def retrieve_past_decisions(ticker: str, top_k: int = 5) -> list[dict]:
    """Convenience wrapper: retrieves past decision records for a ticker."""
    return retrieve_similar(ticker, "investment decision BUY SELL HOLD", top_k=top_k)
