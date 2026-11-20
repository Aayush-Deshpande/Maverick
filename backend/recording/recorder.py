"""Sortie recorder and replay store (cards M5-04/M5-05, P Part 4 Steps 5.4-5.5, T-MIS-3).

One folder per sortie under var/recordings/<sortie_id>/:
  meta.json        engine, tail, seed, warm-up ticks, mission, configuration hash, start/stop times
  frames.jsonl.gz  every MEASURED Frame exactly as the runtime received it (before any inference touched it)
  timeline.jsonl   per tick: sim time, status level + reason codes, confirmed alarm, leading hypotheses
  states.jsonl.gz  every published state message (what the operator saw) - replayed as-is with a REPLAY flag
Recording starts at a calibrated runtime, so re-analysis (backend/recording/replay.py) can rebuild the same tail
from its seed and push the recorded Frames through the identical ingest path. Writes only measured data and the
system's own outputs; plant truth is never recorded.
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import gzip
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

ROOT = Path(__file__).resolve().parents[2]


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def recordings_dir() -> Path:
    from backend.runtime.paths import var_path          # lazy: backend.runtime imports this package
    return var_path("recordings")


def config_hash(engine_id: str) -> str:
    h = hashlib.sha256()
    for p in [ROOT / "configs" / "engines" / f"{engine_id}.json", ROOT / "configs" / "faults.json",
              ROOT / "configs" / "detect.json", ROOT / "configs" / "physics" / "defaults.json"]:
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def timeline_entry(tick: Any) -> Dict[str, Any]:
    """The decision record of one tick (compared by re-analysis)."""
    st = tick.status or {}
    return {"t": round(float(tick.frame.t), 3), "level": st.get("level"),
            "reasons": sorted(r.get("code", "") + ":" + str(r.get("channel") or r.get("fault_id") or "")
                              for r in st.get("reasons", [])),
            "confirmed": bool(tick.detection and tick.detection.confirmed),
            "hypotheses": [[h["fault_id"], h.get("cylinder"), h.get("channel"), round(h["posterior"], 3)]
                           for h in (tick.hypotheses or [])[:3]]}


class SortieRecorder:
    def __init__(self, engine_id: str, tail_id: str, seed: int, warmup_ticks: int, start_t: float,
                 mission_id: Optional[str] = None, root: Optional[Path] = None) -> None:
        self.sortie_id = f"{engine_id}-{_dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"
        self.dir = (root or recordings_dir()) / self.sortie_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.meta = {"schema": "sortie/1", "sortie_id": self.sortie_id, "engine_id": engine_id, "tail_id": tail_id,
                     "seed": seed, "warmup_ticks": warmup_ticks, "mission_id": mission_id,
                     "config_hash": config_hash(engine_id), "start_sim_t": start_t, "start_wall": _now(),
                     "stop_sim_t": None, "stop_wall": None, "frames": 0, "evidence_class": "SIMULATION"}
        self._frames = gzip.open(self.dir / "frames.jsonl.gz", "at", encoding="utf-8")
        self._states = gzip.open(self.dir / "states.jsonl.gz", "at", encoding="utf-8")
        self._timeline = (self.dir / "timeline.jsonl").open("a", encoding="utf-8")
        self._write_meta()

    def _write_meta(self) -> None:
        (self.dir / "meta.json").write_text(json.dumps(self.meta, indent=1), encoding="utf-8")

    def add_frame(self, frame: Any) -> None:
        self._frames.write(json.dumps(dataclasses.asdict(frame)) + "\n")
        self.meta["frames"] += 1

    def add_tick(self, tick: Any) -> None:
        self._timeline.write(json.dumps(timeline_entry(tick)) + "\n")

    def add_state(self, message_json: str) -> None:
        self._states.write(message_json + "\n")

    def stop(self, t: float) -> Dict[str, Any]:
        for f in (self._frames, self._states, self._timeline):
            f.close()
        self.meta.update(stop_sim_t=t, stop_wall=_now())
        self._write_meta()
        return self.meta


def list_recordings(root: Optional[Path] = None) -> List[Dict[str, Any]]:
    out = []
    for m in sorted((root or recordings_dir()).glob("*/meta.json")):
        try:
            out.append(json.loads(m.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as e:      # a damaged recording is listed, never hidden
            out.append({"sortie_id": m.parent.name, "error": f"unreadable meta.json: {e}"})
    return out


def _lines(path: Path) -> Iterator[str]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield line


def read_frames(sortie_dir: Path) -> Iterator[Dict[str, Any]]:
    for line in _lines(sortie_dir / "frames.jsonl.gz"):
        yield json.loads(line)


def read_timeline(sortie_dir: Path) -> List[Dict[str, Any]]:
    return [json.loads(x) for x in _lines(sortie_dir / "timeline.jsonl")]


def read_states(sortie_dir: Path, offset: int = 0, limit: int = 200) -> List[Dict[str, Any]]:
    out = []
    for i, line in enumerate(_lines(sortie_dir / "states.jsonl.gz")):
        if i < offset:
            continue
        if len(out) >= limit:
            break
        out.append(json.loads(line))
    return out
