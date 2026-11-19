"""T-DYN-1 static scan (card M0-12). Counts rule breaks per file; the baseline may only go down (like the ratchet)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCANNED = ["backend/runtime", "backend/server", "backend/faults", "frontend/src"]
SUFFIXES = {".py", ".ts", ".tsx"}
ENGINE_IDS = [p.stem for p in (ROOT / "configs" / "engines").glob("*.json")]
RULES = {
    # "x or 14.1" / "x ?? 3.5" / "x || 20" fallbacks for values (P Part 0 D7)
    "fallback": re.compile(r"(?:\bor\b|\?\?|\|\|)\s*-?\d+(?:\.\d+)?\b(?!\s*[:\]])"),
    # engine ids written in code (P Part 0 D5)
    "engine_id": re.compile("|".join(re.escape(e) for e in ENGINE_IDS)),
    # Math.random in product UI (P Part 0 D1)
    "random": re.compile(r"Math\.random\("),
}


def scan() -> dict:
    out = {}
    for folder in SCANNED:
        for path in sorted((ROOT / folder).rglob("*")):
            if path.suffix not in SUFFIXES or "node_modules" in path.parts or path.name.endswith(".d.ts"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            counts = {k: len(rx.findall(text)) for k, rx in RULES.items()}
            if any(counts.values()):
                out[path.relative_to(ROOT).as_posix()] = counts
    return out


if __name__ == "__main__":
    (Path(__file__).with_name("dyn_baseline.json")).write_text(json.dumps(scan(), indent=1, sort_keys=True) + "\n")
