"""
Local Semantic Embedding Index for Aerospace Manuals.
DRDO / iDEX Problem Statement ID: 26054

Uses a small local sentence-transformer (all-MiniLM-L6-v2, CPU) to rank document
chunks by cosine similarity to a query. Runs entirely offline/on-device. This is
the primary ranking strategy for the RAG pipeline; reranker.py falls back to
FlashRank or keyword overlap if sentence-transformers is unavailable.
"""

from typing import List, Dict, Any, Optional
import hashlib
import threading

from backend.ml_runtime_lock import TRANSFORMERS_FIRST_IMPORT_LOCK

_model = None
_model_load_attempted = False
# Guards the one-time SentenceTransformer/transformers import+load below (in addition to the
# process-wide TRANSFORMERS_FIRST_IMPORT_LOCK acquired inside — see backend/ml_runtime_lock.py
# for why both are needed: this one dedupes repeat callers into this module specifically, the
# shared one prevents this module's first load from racing Qwen's or Kokoro's).
_load_lock = threading.Lock()

# Cache of the last-embedded corpus so repeated queries against the same
# (static, loaded-once-at-startup) chunk set don't re-embed on every call.
_cache_key: Optional[str] = None
_cache_embeddings = None
_cache_lock = threading.Lock()


def _get_model():
    """Lazily loads the local embedding model on CPU. Returns False permanently on failure."""
    global _model, _model_load_attempted
    if _model_load_attempted and _model is not None:
        return _model
    with _load_lock:
        if _model_load_attempted and _model is not None:
            return _model
        try:
            # Needed on some Windows machines running TLS-inspecting endpoint-security software
            # whose CA isn't in certifi's bundle — verifies against the OS trust store instead.
            try:
                import truststore
                truststore.inject_into_ssl()
            except ImportError:
                pass

            with TRANSFORMERS_FIRST_IMPORT_LOCK:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        except Exception:
            _model = False
        finally:
            _model_load_attempted = True
    return _model


def _corpus_fingerprint(documents: List[Dict[str, Any]]) -> str:
    h = hashlib.sha1()
    for d in documents:
        h.update(d.get("content", "").encode("utf-8", errors="ignore"))
        h.update(b"\x00")
    return h.hexdigest()


def semantic_rank(query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> Optional[List[Dict[str, Any]]]:
    """
    Ranks documents by cosine similarity to the query using a local embedding model.
    Returns None (rather than an empty list) if the embedding model isn't available,
    so callers can distinguish "no semantic ranker" from "no matches".
    """
    model = _get_model()
    if not model or not documents:
        return None

    import numpy as np

    global _cache_key, _cache_embeddings
    key = _corpus_fingerprint(documents)
    with _cache_lock:
        if key != _cache_key or _cache_embeddings is None or len(_cache_embeddings) != len(documents):
            contents = [d.get("content", "") for d in documents]
            _cache_embeddings = model.encode(contents, normalize_embeddings=True, show_progress_bar=False)
            _cache_key = key
        local_cache = _cache_embeddings

    query_emb = model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
    scores = local_cache @ query_emb

    order = np.argsort(-scores)[:top_k]
    results = []
    for idx in order:
        if int(idx) < len(documents):
            item = dict(documents[int(idx)])
            item["score"] = float(scores[int(idx)])
            item["ranker"] = "semantic"
            results.append(item)
    return results
