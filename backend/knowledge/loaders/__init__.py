"""
Document Loaders and Ingestion Engine for Rotax 912 iS & UAV Manuals.
DRDO / iDEX Problem Statement ID: 26054
"""

from pathlib import Path
from typing import Dict, Any, List

from backend.knowledge.loaders.pdf_loader import load_pdf
from backend.knowledge.loaders.office_loader import load_docx, load_pptx
from backend.knowledge.loaders.text_loader import load_text
from backend.knowledge.loaders.chunker import chunk_document


def load_and_chunk_file(file_path: Path, max_chunk_size: int = 1200) -> List[Dict[str, Any]]:
    """Loads any supported document and chunks it locally."""
    path_obj = Path(file_path)
    suffix = path_obj.suffix.lower()

    if suffix == ".pdf":
        raw_pages = load_pdf(path_obj)
    elif suffix in (".docx", ".doc"):
        raw_pages = load_docx(path_obj)
    elif suffix in (".pptx", ".ppt"):
        raw_pages = load_pptx(path_obj)
    elif suffix in (".txt", ".md", ".json", ".log"):
        raw_pages = load_text(path_obj)
    else:
        raw_pages = load_text(path_obj)

    all_chunks = []
    for p in raw_pages:
        all_chunks.extend(chunk_document(p, max_chunk_size=max_chunk_size))
    return all_chunks
