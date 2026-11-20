"""Search over the REAL manuals and certificates (card AI-03; D34/D44: no generated text is ever indexed).

The corpus is configs/knowledge/manuals.json. Each PDF page is split into chunks that keep their document, edition and
page number, so every hit can be cited. Ranking is TF-IDF with word 1-2 grams (scikit-learn): manual questions turn
on exact technical terms ("oil pressure", "take-off", "EGT"), it is deterministic and needs no model download. The
index is cached in var/rag/ and rebuilt when any document's hash changes. Documents that are not on this machine
(docs/reference/oem/ is local-only for copyright) are skipped and reported, never replaced by anything else.
"""
from __future__ import annotations

import hashlib
import json
import pickle
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.runtime.paths import var_path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "knowledge" / "manuals.json"
INDEX_VERSION = 2
TOC_DOT_SHARE = 0.15            # chunks with more dot leaders than this share are contents pages: never an answer


def _config() -> Dict[str, Any]:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _pages(path: Path) -> List[str]:
    from pypdf import PdfReader
    return [(p.extract_text() or "") for p in PdfReader(str(path)).pages]


def _chunks(text: str, size: int) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    out, start = [], 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):                                    # end on a sentence or word boundary
            cut = max(text.rfind(". ", start, end), text.rfind(" ", start, end))
            end = cut + 1 if cut > start + size // 2 else end
        out.append(text[start:end].strip())
        start = end
    return [c for c in out if len(c) > 40 and c.count(". .") * 3 < len(c) * TOC_DOT_SHARE]


class ManualIndex:
    def __init__(self) -> None:
        self.cfg = _config()
        self.docs: List[Dict[str, Any]] = []        # documents actually indexed
        self.missing: List[str] = []
        self.chunks: List[Dict[str, Any]] = []
        self._vec = self._mat = None

    @classmethod
    def load(cls) -> "ManualIndex":
        idx = cls()
        present = [d for d in idx.cfg["documents"] if (ROOT / d["path"]).exists()]
        idx.missing = [d["id"] for d in idx.cfg["documents"] if d not in present]
        key = {"v": INDEX_VERSION, "chunk": idx.cfg["chunk_chars"],
               "docs": {d["id"]: _hash(ROOT / d["path"]) for d in present}}
        cache = var_path("rag") / "manual_index.pkl"           # var_path creates the directory
        if cache.exists():
            try:
                data = pickle.loads(cache.read_bytes())
                if data["key"] == key:
                    idx.docs, idx.chunks, idx._vec, idx._mat = data["docs"], data["chunks"], data["vec"], data["mat"]
                    return idx
            except Exception:                                  # stale or unreadable cache: rebuild below
                pass
        idx._build(present)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps({"key": key, "docs": idx.docs, "chunks": idx.chunks,
                                        "vec": idx._vec, "mat": idx._mat}))
        return idx

    def _build(self, present: List[Dict[str, Any]]) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        for d in present:
            for page_no, text in enumerate(_pages(ROOT / d["path"]), start=1):
                for c in _chunks(text, self.cfg["chunk_chars"]):
                    self.chunks.append({"doc": d["id"], "page": page_no, "text": c})
            self.docs.append(d)
        if self.chunks:
            self._vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english", min_df=1)
            self._mat = self._vec.fit_transform([c["text"] for c in self.chunks])

    def search(self, query: str, engine_id: Optional[str] = None, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        if not self.chunks or not query.strip():
            return []
        allowed = {d["id"] for d in self.docs if engine_id is None or d["engines"] == "ALL" or engine_id in d["engines"]}
        scores = (self._mat @ self._vec.transform([query]).T).toarray().ravel()
        meta = {d["id"]: d for d in self.docs}
        hits = []
        for i in scores.argsort()[::-1]:
            if scores[i] <= 0 or len(hits) >= (top_k or self.cfg["top_k"]):
                break
            c = self.chunks[i]
            if c["doc"] not in allowed:
                continue
            d = meta[c["doc"]]
            hits.append({"document": d["title"], "edition": d["edition"], "page": c["page"],
                         "score": round(float(scores[i]), 3), "text": c["text"]})
        return hits


_index: Optional[ManualIndex] = None


def manual_index() -> ManualIndex:
    global _index
    if _index is None:
        _index = ManualIndex.load()
    return _index
