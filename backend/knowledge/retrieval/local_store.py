"""
Local Technical Manual Knowledge Store.
DRDO / iDEX Problem Statement ID: 26054

Indexes PDF, Word, and text documents placed in data/documents/ and provides
sub-second semantic search & retrieval for the Diagnostic Agent and LLM Copilot.
100% Air-Gapped and Offline.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import logging
import os

from backend.knowledge.loaders import load_and_chunk_file
from backend.knowledge.retrieval.reranker import rerank_passages

logger = logging.getLogger("LocalKnowledgeStore")


# Calibrated on real 24-chunk Rotax/DRDO corpus with all-MiniLM-L6-v2 cosine similarity:
#   On-topic (CHT limits, torque, low oil pressure SOP, etc.): 0.334 – 0.525
#   Vague status ("what is the issue in the system", "is anything wrong"): 0.106 – 0.204
#   Off-topic ("capital of France", "sourdough", "football"): 0.071 – 0.143
# 0.28 cleanly bisects the empty band (0.204 – 0.334), filtering vague status and off-topic
# queries while admitting every genuine technical inquiry.
_SEMANTIC_MIN_SCORE = 0.28


class LocalKnowledgeStore:
    """Local, offline document index for aerospace engineering manuals."""

    def __init__(self, docs_dir: Optional[Path] = None):
        if docs_dir is None:
            self.docs_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "documents"
        else:
            self.docs_dir = Path(docs_dir)

        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.chunks: List[Dict[str, Any]] = []
        self._load_all_documents()

    # Preference order when the same manual exists in multiple formats (e.g. an exported
    # "Manual.md" alongside the original "Manual.docx"/"Manual.pdf") — lowest index wins.
    # Loading every format of the same document (which the old suffix-only glob filter did)
    # silently duplicates every passage 2-3x in the corpus: retrieval then burns most of its
    # top_k budget returning near-identical chunks of the SAME manual instead of drawing from
    # the other five, which is exactly what was observed live (a 4-chunk retrieval collapsing
    # to 2 distinct source citations). Preferring plain-text formats first is also what keeps
    # the RAG corpus fully populated on a machine missing the optional pypdf/pdfplumber/
    # python-docx/python-pptx parsers (only used as a fallback here, not a hard dependency).
    _FORMAT_PRIORITY = {".md": 0, ".txt": 1, ".json": 2, ".docx": 3, ".doc": 3, ".pptx": 4, ".pdf": 5}

    def _load_all_documents(self):
        """Scans data/documents/ and loads one copy of each available manual, preferring
        the plain-text format when the same manual exists in more than one."""
        self.chunks.clear()
        if not self.docs_dir.exists():
            return

        candidates: Dict[str, Path] = {}
        for p in self.docs_dir.glob("*.*"):
            suffix = p.suffix.lower()
            if suffix not in self._FORMAT_PRIORITY:
                continue
            existing = candidates.get(p.stem)
            if existing is None or self._FORMAT_PRIORITY[suffix] < self._FORMAT_PRIORITY[existing.suffix.lower()]:
                candidates[p.stem] = p

        for p in candidates.values():
            try:
                file_chunks = load_and_chunk_file(p)
                self.chunks.extend(file_chunks)
            except Exception as e:
                    # logger.warning (not print/bare stdout) deliberately: on a Windows console
                    # without UTF-8 mode enabled, a bare print() of a manual filename/parser
                    # error containing a non-ASCII character (curly quote, em dash, etc.) raises
                    # an uncaught UnicodeEncodeError here, which propagates out of __init__() and
                    # crashes the whole FastAPI startup (LocalKnowledgeStore -> MissionCopilot ->
                    # EngineStateService are all constructed synchronously during server startup)
                    # over a single failed-to-parse document. logging survives the same encoding
                    # failure by falling back to escaping the character instead of raising.
                    logger.warning(f"Failed to load {p.name}: {e}")

    def reload(self):
        """Reloads all documents from the folder."""
        self._load_all_documents()

    def query(self, query_text: str, top_k: int = 5, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """Queries the indexed documents with semantic reranking. Applies min_score cutoff
        specifically to semantic ranker results to reject vague or off-topic queries."""
        if not self.chunks:
            return []

        if min_score is None:
            min_score = _SEMANTIC_MIN_SCORE

        results = rerank_passages(query_text, self.chunks, top_k=top_k)
        filtered = []
        for r in results:
            ranker = r.get("ranker")
            score = float(r.get("score", 0.0))
            if ranker == "semantic":
                if score >= min_score:
                    filtered.append(r)
            elif ranker == "flashrank":
                # FlashRank outputs cross-encoder sigmoid probabilities (0.0 to 1.0).
                # Off-topic queries score < 1e-3, genuine technical matches score > 0.1.
                if score >= 0.05:
                    filtered.append(r)
            elif ranker == "lexical":
                # Keyword matches must have at least one term match
                if score > 0.0:
                    filtered.append(r)
            else:
                filtered.append(r)
        return filtered[:top_k]

    @property
    def total_chunks(self) -> int:
        return len(self.chunks)
