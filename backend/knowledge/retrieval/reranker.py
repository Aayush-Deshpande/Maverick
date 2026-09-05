"""
Local Cross-Encoder Semantic Reranking Service for Aerospace Manuals.
DRDO / iDEX Problem Statement ID: 26054

Uses FlashRank (local quantized ONNX TinyBERT) with zero cloud latency.
Provides deterministic lexical fallback if flashrank is not installed.
"""

from typing import List, Dict, Any
import time


_ranker = None


def _get_ranker():
    """Lazily loads FlashRank local cross-encoder."""
    global _ranker
    if _ranker is None:
        try:
            from flashrank import Ranker
            _ranker = Ranker()
        except Exception:
            _ranker = False
    return _ranker


def rerank_passages(query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Reranks documents against query semantically.

    Ranking strategy, best available first:
      1. Local sentence-transformer embedding cosine similarity (all-MiniLM-L6-v2, CPU).
      2. FlashRank local cross-encoder (if installed).
      3. Deterministic lexical keyword-overlap fallback.
    """
    if not documents:
        return []

    try:
        from backend.knowledge.retrieval.embedding_index import semantic_rank
        semantic_result = semantic_rank(query, documents, top_k=top_k)
        if semantic_result is not None:
            return semantic_result
    except Exception:
        pass

    ranker = _get_ranker()

    if ranker:
        try:
            from flashrank import RerankRequest
            passages = [
                {"id": i, "text": d.get("content", "")}
                for i, d in enumerate(documents)
            ]
            req = RerankRequest(query=query, passages=passages)
            results = ranker.rerank(req)
            
            reranked = []
            for r in results[:top_k]:
                doc_idx = r["id"]
                item = dict(documents[doc_idx])
                item["score"] = float(r["score"])
                item["ranker"] = "flashrank"
                reranked.append(item)
            return reranked
        except Exception:
            pass

    # Fast Deterministic Lexical Fallback
    query_terms = set(query.lower().split())
    scored = []
    for d in documents:
        content = d.get("content", "").lower()
        score = sum(1.0 for term in query_terms if term in content)
        # Normalize score
        norm_score = score / max(1, len(query_terms))
        item = dict(d)
        item["score"] = norm_score
        item["ranker"] = "lexical"
        scored.append(item)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
