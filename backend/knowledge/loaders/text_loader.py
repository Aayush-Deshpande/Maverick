"""
Local Text / Markdown Loader for SOPs, Flight Manuals, and Directives.
DRDO / iDEX Problem Statement ID: 26054
"""

from pathlib import Path
from typing import Dict, Any, List


def load_text(file_path: Path) -> List[Dict[str, Any]]:
    """Loads plain text or Markdown files."""
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Text file not found: {file_path}")

    with open(path_obj, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read().strip()

    if content:
        return [{
            "content": content,
            "page_number": 1,
            "source": path_obj.name,
            "type": "text"
        }]
    return []
