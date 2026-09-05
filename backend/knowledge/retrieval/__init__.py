"""
Retrieval and Reranking Service for Rotax 912 iS & DRDO UAV Manuals.
DRDO / iDEX Problem Statement ID: 26054
"""

from backend.knowledge.retrieval.reranker import rerank_passages
from backend.knowledge.retrieval.local_store import LocalKnowledgeStore
