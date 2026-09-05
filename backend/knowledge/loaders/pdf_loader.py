"""
Local PDF Document Loader for Aerospace & Engine Manuals.
DRDO / iDEX Problem Statement ID: 26054

Extracts raw and structured text from PDF maintenance manuals using pypdf/pdfplumber on-device.
Zero cloud dependencies.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional


def load_pdf(file_path: Path) -> List[Dict[str, Any]]:
    """
    Parses a PDF document locally page-by-page.
    """
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    pages = []
    
    # Try pypdf first
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path_obj))
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({
                    "content": text.strip(),
                    "page_number": idx + 1,
                    "source": path_obj.name,
                    "type": "pdf"
                })
        if pages:
            return pages
    except ImportError:
        pass

    # Fallback to pdfplumber if installed
    try:
        import pdfplumber
        with pdfplumber.open(str(path_obj)) as pdf:
            for idx, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({
                        "content": text.strip(),
                        "page_number": idx + 1,
                        "source": path_obj.name,
                        "type": "pdf"
                    })
    except ImportError:
        pass

    return pages
