"""Physics constants for one engine: configs/physics/defaults.json overridden by the engine's own "physics" block
(configs/engines/<id>.json). Values are plain floats; provenance stays queryable for the UI (P Part 6 U6)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def physics_blocks(engine_id: str) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """{section: {name: {"value", "status", "ref"}}} with the engine's overrides applied."""
    defaults = _load(ROOT / "configs" / "physics" / "defaults.json")
    engine = _load(ROOT / "configs" / "engines" / f"{engine_id}.json").get("physics", {})
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for section, entries in defaults.items():
        if isinstance(entries, dict):
            out[section] = {**entries, **engine.get(section, {})}
    for section, entries in engine.items():
        out.setdefault(section, dict(entries))
    return out


def physics_values(engine_id: str, section: str) -> Dict[str, float]:
    block = physics_blocks(engine_id).get(section)
    if block is None:
        raise KeyError(f"no physics section {section!r} for {engine_id} (configs/physics/defaults.json)")
    return {k: float(v["value"]) for k, v in block.items()}
