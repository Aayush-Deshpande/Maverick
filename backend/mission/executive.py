"""Mission executive (cards M5-01/M5-02, P Part 4 Steps 5.1-5.2, T-MIS-1).

A mission is DATA (configs/missions/<id>.json): ordered phases with a duration in simulated seconds, a throttle
target, an altitude target and either an OAT or an ISA deviation, plus optional scheduled faults. The executive runs
on the engine's own sim clock and drives the SAME lever path the operator uses (EngineRuntime.set_levers); scheduled
faults go through the same fault path with origin "mission". It never touches the plant directly, so missions,
manual control, replay and every client see one engine.

OAT for an ISA-deviation phase is recomputed each tick from the CURRENT altitude (the aircraft climbs through the
lapse rate), not from the phase's target altitude.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.mission.reliability import MissionPhase as ReliabilityPhase, MissionProfile as ReliabilityProfile

ROOT = Path(__file__).resolve().parents[2]
MISSIONS = ROOT / "configs" / "missions"
ISA_SL_C = 15.0                                  # ISA sea-level temperature
ISA_LAPSE_C_PER_FT = 0.0019812                   # ISA troposphere lapse, 1.98 C per 1000 ft
S_PER_H = 3600.0


def list_missions() -> List[Dict[str, Any]]:
    out = []
    for p in sorted(MISSIONS.glob("*.json")):
        m = json.loads(p.read_text(encoding="utf-8"))
        out.append({"id": m["id"], "title": m["title"], "ps_item": m.get("ps_item"), "engines": m["engines"],
                    "duration_s": sum(ph["duration_s"] for ph in m["phases"]), "provenance": m.get("provenance")})
    return out


def load_mission(mission_id: str) -> Dict[str, Any]:
    path = MISSIONS / f"{mission_id}.json"
    if not path.exists():
        raise KeyError(mission_id)
    return json.loads(path.read_text(encoding="utf-8"))


def applies(mission: Dict[str, Any], engine_id: str) -> bool:
    return mission["engines"] == "ALL" or engine_id in mission["engines"]


@dataclass
class MissionExecutive:
    mission: Dict[str, Any]
    t0: float
    state: str = "RUNNING"                        # RUNNING | COMPLETE | ABORTED
    phase_index: int = 0
    fired: set = field(default_factory=set)       # scheduled faults already injected
    throttle_cycles: int = 0
    _last_throttle: Optional[float] = None

    @property
    def phases(self) -> List[Dict[str, Any]]:
        return self.mission["phases"]

    @property
    def total_s(self) -> float:
        return float(sum(p["duration_s"] for p in self.phases))

    def _locate(self, elapsed: float) -> tuple:
        start = 0.0
        for i, p in enumerate(self.phases):
            if elapsed < start + p["duration_s"]:
                return i, elapsed - start
            start += p["duration_s"]
        return len(self.phases), 0.0

    def step(self, t: float, runtime: Any) -> None:
        """Apply this tick's lever targets and due scheduled faults to the runtime (before its plant step)."""
        if self.state != "RUNNING":
            return
        elapsed = t - self.t0
        i, t_in = self._locate(elapsed)
        if i >= len(self.phases):
            self.state = "COMPLETE"
            return
        self.phase_index = i
        p = self.phases[i]
        oat = p.get("oat_c")
        if oat is None:
            oat = ISA_SL_C - ISA_LAPSE_C_PER_FT * runtime.levers.altitude_ft + p.get("isa_dev_c", 0.0)
        runtime.set_levers(throttle_pct=p["throttle_pct"], altitude_ft=p["altitude_ft"], oat_c=oat)
        if self._last_throttle is not None and p["throttle_pct"] != self._last_throttle:
            self.throttle_cycles += 1                 # a commanded throttle transition (phase boundary)
        self._last_throttle = p["throttle_pct"]
        for k, f in enumerate(p.get("faults", [])):
            key = (i, k)
            if key not in self.fired and t_in >= f.get("at_s", 0.0):
                runtime.inject_fault(f["fault_id"], cylinder=f.get("cylinder"), severity=f.get("severity", 1.0),
                                     ramp_sec=f.get("ramp_s", 60.0), origin="SCRIPTED")
                self.fired.add(key)

    def abort(self) -> None:
        self.state = "ABORTED"

    def remaining_s(self, t: float) -> float:
        return max(0.0, self.total_s - (t - self.t0)) if self.state == "RUNNING" else 0.0

    def remaining_profile(self, t: float) -> Optional[ReliabilityProfile]:
        """The rest of the mission as a reliability profile (power fraction ~ throttle), for M4-04."""
        if self.state != "RUNNING":
            return None
        i, t_in = self._locate(t - self.t0)
        phases = []
        for k, p in enumerate(self.phases[i:], start=i):
            dur = p["duration_s"] - (t_in if k == i else 0.0)
            oat = p.get("oat_c")
            if oat is None:
                oat = ISA_SL_C - ISA_LAPSE_C_PER_FT * p["altitude_ft"] + p.get("isa_dev_c", 0.0)
            phases.append(ReliabilityPhase(p["name"], dur / S_PER_H, p["altitude_ft"], p["throttle_pct"] / 100.0, oat))
        return ReliabilityProfile(self.mission["id"], phases) if phases else None

    def progress(self, t: float) -> Dict[str, Any]:
        i = min(self.phase_index, len(self.phases) - 1)
        return {"mission_id": self.mission["id"], "title": self.mission["title"], "state": self.state,
                "phase": self.phases[i]["name"], "phase_index": i, "phases": len(self.phases),
                "elapsed_s": round(t - self.t0, 1), "total_s": self.total_s,
                "remaining_s": round(self.remaining_s(t), 1), "throttle_changes": self.throttle_cycles}
