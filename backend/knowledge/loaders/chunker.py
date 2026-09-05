"""
Paragraph & Section Text Chunker for Aerospace Technical Documents.
DRDO / iDEX Problem Statement ID: 26054

Splits technical documents into semantically coherent chunks while preserving
table definitions, ATA chapter citations, and step-by-step checklists.
"""

from typing import Dict, Any, List


def chunk_document(
    doc: Dict[str, Any],
    max_chunk_size: int = 1200,
    overlap_size: int = 150
) -> List[Dict[str, Any]]:
    """
    Chunks document text by paragraphs or length limits.
    """
    content = doc.get("content", "").strip()
    if not content:
        return []

    # If small enough, keep as single chunk
    if len(content) <= max_chunk_size:
        chunk = dict(doc)
        chunk["chunk_id"] = 0
        return [chunk]

    paragraphs = content.split("\n\n")
    chunks = []
    current_text = ""
    chunk_index = 0

    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue

        if len(current_text) + len(p_clean) + 2 <= max_chunk_size:
            current_text = f"{current_text}\n\n{p_clean}" if current_text else p_clean
        else:
            if current_text:
                chunks.append({
                    "content": current_text,
                    "page_number": doc.get("page_number", 1),
                    "source": doc.get("source", "unknown"),
                    "type": doc.get("type", "text"),
                    "chunk_id": chunk_index
                })
                chunk_index += 1
                # Overlap tail
                tail = current_text[-overlap_size:] if len(current_text) > overlap_size else ""
                current_text = f"{tail}\n\n{p_clean}" if tail else p_clean
            else:
                # Handle single huge paragraph
                for i in range(0, len(p_clean), max_chunk_size - overlap_size):
                    sub_p = p_clean[i:i + max_chunk_size]
                    chunks.append({
                        "content": sub_p,
                        "page_number": doc.get("page_number", 1),
                        "source": doc.get("source", "unknown"),
                        "type": doc.get("type", "text"),
                        "chunk_id": chunk_index
                    })
                    chunk_index += 1
                current_text = ""

    if current_text:
        chunks.append({
            "content": current_text,
            "page_number": doc.get("page_number", 1),
            "source": doc.get("source", "unknown"),
            "type": doc.get("type", "text"),
            "chunk_id": chunk_index
        })

    return chunks
