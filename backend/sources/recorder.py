"""Recorder + ReplaySource (W3, B1.2): record any Frame stream to .npz + manifest and replay it bit-exactly.

The recording holds Frames only.  Ground truth (if any) goes to a separate ``truth`` list inside the manifest so
the inference path can replay a run without any route to it; evaluation code reads the manifest explicitly.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

from backend.core.frame import Frame, TruthRecord

SCALARS = ("rpm", "prop_rpm", "throttle", "map_kpa", "coolant_t", "oil_p", "oil_t", "fuel_flow", "fuel_t",
           "rail_p", "bus_v", "batt_i", "alt", "oat")


def record(path: str | Path, frames: Iterable[Frame], truths: Optional[Iterable[TruthRecord]] = None,
           meta: Optional[dict] = None) -> Path:
    """Write ``<path>.jsonl`` (frames, one per line) and ``<path>.manifest.json`` (sha256 + truth + meta)."""
    path = Path(path)
    frames = list(frames)
    lines = [json.dumps(asdict(f), sort_keys=True) for f in frames]
    body = "\n".join(lines) + "\n"
    path.with_suffix(".jsonl").write_text(body, encoding="utf-8")
    manifest = {
        "schema": "recording/1", "n_frames": len(frames), "sha256": hashlib.sha256(body.encode()).hexdigest(),
        "engine_config_id": frames[0].engine_config_id if frames else None, "meta": meta or {},
        "truth": None if truths is None else [asdict(t) for t in truths],
    }
    path.with_suffix(".manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return path.with_suffix(".jsonl")


class ReplaySource:
    """Yields recorded Frames with source='REPLAY' (same pipeline as live, D05)."""

    def __init__(self, path: str | Path) -> None:
        p = Path(path)
        self.jsonl = p if p.suffix == ".jsonl" else p.with_suffix(".jsonl")
        self.manifest = json.loads(self.jsonl.with_suffix(".manifest.json").read_text(encoding="utf-8"))
        body = self.jsonl.read_text(encoding="utf-8")
        if hashlib.sha256(body.encode()).hexdigest() != self.manifest["sha256"]:
            raise ValueError("recording does not match its manifest hash (modified or corrupt)")
        self._rows = [json.loads(x) for x in body.splitlines() if x]

    def __len__(self) -> int:
        return len(self._rows)

    def frames(self) -> Iterator[Frame]:
        for row in self._rows:
            row = dict(row, source="REPLAY")
            yield Frame.from_dict(row)

    def truths(self) -> List[dict]:
        """Evaluation-only accessor."""
        return self.manifest.get("truth") or []
