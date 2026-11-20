"""Re-analysis of a recorded sortie (card M5-05, T-MIS-3, T-DYN-4 in practice).

The tail is rebuilt from its recorded engine id, seed and warm-up length (calibration is deterministic), then every
recorded measured Frame goes through EngineRuntime.ingest - the same path a live frame takes, with NO truth record
(source REPLAY). The decision timeline (status, reasons, confirmed alarm, hypotheses) must equal the recorded one:
if it does, the recorded decisions came from the measurements alone.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from backend.core.frame import Frame
from backend.recording.recorder import read_frames, read_timeline, timeline_entry


def reanalyse(sortie_dir: Path, meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    from backend.runtime.engine_runtime import EngineRuntime   # lazy: the runtime imports the recorder
    rt = EngineRuntime(meta["engine_id"], seed=meta["seed"], warmup_ticks=meta["warmup_ticks"])
    rt.calibrate()
    if meta.get("mission_id"):                                 # the status rule uses the remaining mission time
        from backend.mission.executive import MissionExecutive, load_mission
        rt.mission = MissionExecutive(load_mission(meta["mission_id"]), t0=meta["mission_t0"])
    out = []
    for d in read_frames(sortie_dir):
        out.append(timeline_entry(rt.ingest(Frame.from_dict(d))))
    return out


def compare(sortie_dir: Path, meta: Dict[str, Any]) -> Dict[str, Any]:
    if meta.get("ticks_since_calibration"):
        return {"sortie_id": meta["sortie_id"], "identical": None,
                "reason": f"recording started {meta['ticks_since_calibration']} ticks after calibration: the "
                          "runtime state at its start cannot be rebuilt, so the timelines are not comparable"}
    recorded = read_timeline(sortie_dir)
    again = reanalyse(sortie_dir, meta)
    first_diff = next((i for i, (a, b) in enumerate(zip(recorded, again)) if a != b), None)
    return {"sortie_id": meta["sortie_id"], "ticks": len(recorded), "reanalysed": len(again),
            "identical": first_diff is None and len(recorded) == len(again), "first_difference_tick": first_diff}
