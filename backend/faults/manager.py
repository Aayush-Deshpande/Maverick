"""Fault manager (card M0-04; DECISIONS D7, D9; audit R 19.4 edge cases).

The ONE entry point for injecting and clearing faults, whatever the surface (console, 3D, Blender app, voice,
mission schedule, API). It validates every request against configs/faults.json, keeps the active-fault list with
its origin, emits events, and drives the simulation through an adapter.

Until backend/sim exists (Phase 2), the adapter drives the current plant through each registry entry's
plant_mode_legacy. A valid fault that the current plant cannot simulate yet is still accepted, stored and announced
with simulated=False ("not yet simulated"); it is never silently dropped.

Inference code (detect, diagnose, status, prognose, twin) must never import this module (T-DYN-4).
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

from backend.faults.registry import FaultRegistry, FaultRejected
from backend.physics.engine_config import EngineConfig

SOURCES = {"console", "3d", "blender", "gcs", "voice", "api", "mission", "replay", "test", "legacy"}


class SimulationAdapter(Protocol):
    """What the manager needs from the engine simulation."""

    def now(self) -> float: ...
    def apply(self, fault: "ActiveFault") -> bool: ...   # True if the simulation models this fault
    def clear_all(self) -> None: ...


@dataclass
class ActiveFault:
    uuid: str
    fault_id: str
    name: str
    kind: str
    cylinder: Optional[int]
    channel: Optional[str]
    severity: float
    ramp_s: float
    source: str
    request_id: Optional[str]
    t0_s: float
    simulated: bool = False
    plant_mode: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FaultEvent:
    seq: int
    t_s: float
    type: str                      # FAULT_INJECTED | FAULT_UPDATED | FAULT_CLEARED | FAULT_REJECTED
    fault: Optional[Dict[str, Any]]
    source: str
    text: str


class FaultManager:
    def __init__(self, registry: FaultRegistry, cfg: EngineConfig, sim: SimulationAdapter,
                 on_event: Optional[Callable[[FaultEvent], None]] = None, history_limit: int = 500):
        self.registry = registry
        self.cfg = cfg
        self.sim = sim
        self._on_event = on_event
        self._active: Dict[str, ActiveFault] = {}
        self._by_request: Dict[str, str] = {}
        self._events: List[FaultEvent] = []
        self._history_limit = history_limit
        self._ids = itertools.count(1)
        self._seq = itertools.count(1)
        self._lock = threading.RLock()

    # -- queries ------------------------------------------------------------------------------------------------

    def active(self) -> List[ActiveFault]:
        with self._lock:
            return list(self._active.values())

    def history(self) -> List[FaultEvent]:
        with self._lock:
            return list(self._events)

    # -- commands -----------------------------------------------------------------------------------------------

    def inject(self, fault_id: str, cylinder: Optional[int] = None, channel: Optional[str] = None,
               severity: Optional[float] = None, ramp_s: Optional[float] = None, source: str = "api",
               request_id: Optional[str] = None) -> ActiveFault:
        if source not in SOURCES:
            raise FaultRejected(f"unknown source {source!r}; use one of {sorted(SOURCES)}")
        with self._lock:
            if request_id and request_id in self._by_request:          # repeated click / retry: same result
                existing = self._active.get(self._by_request[request_id])
                if existing is not None:
                    return existing
            try:
                spec = self.registry.validate_request(self.cfg, fault_id, cylinder=cylinder, channel=channel,
                                                      severity=severity, ramp_s=ramp_s)
            except FaultRejected as exc:
                self._emit("FAULT_REJECTED", None, source, str(exc))
                raise
            sev = float(spec.raw["default_severity"] if severity is None else severity)
            ramp = float(spec.raw["default_ramp_s"] if ramp_s is None else ramp_s)
            cyl = int(cylinder) if spec.scope == "CYLINDER" else None
            ch = channel if spec.scope == "CHANNEL" else None

            same = next((f for f in self._active.values()
                         if f.fault_id == spec.id and f.cylinder == cyl and f.channel == ch), None)
            if same is not None:                                         # same fault + place: update, not duplicate
                same.severity, same.ramp_s, same.source = sev, ramp, source
                if request_id:
                    self._by_request[request_id] = same.uuid
                self._reapply()
                self._emit("FAULT_UPDATED", same, source,
                           f"{spec.id} {spec.name} updated to severity {sev:.2f}, ramp {ramp:.0f} s")
                return same

            fault = ActiveFault(uuid=f"{self.cfg.engine_id}-{next(self._ids):05d}", fault_id=spec.id, name=spec.name,
                                kind=spec.kind, cylinder=cyl, channel=ch, severity=sev, ramp_s=ramp, source=source,
                                request_id=request_id, t0_s=self.sim.now(),
                                plant_mode=spec.raw.get("plant_mode_legacy"))
            fault.simulated = bool(self.sim.apply(fault))
            self._active[fault.uuid] = fault
            if request_id:
                self._by_request[request_id] = fault.uuid
            where = f" cylinder {cyl}" if cyl else (f" channel {ch}" if ch else "")
            sim_note = "" if fault.simulated else " (accepted; not yet simulated by the current plant - Phase 2)"
            self._emit("FAULT_INJECTED", fault, source, f"{spec.id} {spec.name}{where} injected{sim_note}")
            return fault

    def clear(self, uuid: Optional[str] = None, source: str = "api") -> List[ActiveFault]:
        """Clear one fault (by uuid) or all. Returns the cleared faults. Unknown uuid -> FaultRejected."""
        with self._lock:
            if uuid is None:
                cleared = list(self._active.values())
                self._active.clear()
            else:
                if uuid not in self._active:
                    raise FaultRejected(f"no active fault {uuid!r}")
                cleared = [self._active.pop(uuid)]
            self._by_request = {r: u for r, u in self._by_request.items() if u in self._active}
            self._reapply()
            for f in cleared:
                self._emit("FAULT_CLEARED", f, source, f"{f.fault_id} {f.name} cleared")
            return cleared

    # -- internals ----------------------------------------------------------------------------------------------

    def _reapply(self) -> None:
        """The legacy plant cannot change or remove a single fault, so rebuild its fault set from the active list.
        Ramps restart from now for the faults re-applied (documented limitation until backend/sim, Phase 2)."""
        self.sim.clear_all()
        for f in self._active.values():
            f.simulated = bool(self.sim.apply(f))

    def _emit(self, kind: str, fault: Optional[ActiveFault], source: str, text: str) -> None:
        ev = FaultEvent(seq=next(self._seq), t_s=self.sim.now(), type=kind,
                        fault=fault.to_dict() if fault else None, source=source, text=text)
        self._events.append(ev)
        if len(self._events) > self._history_limit:
            del self._events[: len(self._events) - self._history_limit]
        if self._on_event:
            self._on_event(ev)


def _sensor_channel_to_lever(channel: str) -> str:
    """Registry channel names (frame style, cht[2]) -> legacy sensor-lever names (cht_2)."""
    return channel.replace("[", "_").replace("]", "")


@dataclass
class LegacyRuntimeAdapter:
    """Drives an existing backend.runtime.engine_runtime.EngineRuntime (the current plant) - used until Phase 2.

    PHYSICAL faults with plant_mode_legacy go to the plant. S01/S03 on a CHT channel use the plant's own sensor
    modes; the other sensor faults use the runtime's sensor levers where a lever exists. Everything else returns
    False (not yet simulated)."""

    runtime: Any
    sensor_kinds: Dict[str, str] = field(default_factory=lambda: {
        "S01": "stuck", "S02": "bias", "S03": "drift", "S04": "noise", "S05": "dropout", "S06": "spoof"})

    def now(self) -> float:
        return float(self.runtime.source.plant._elapsed_sec)

    def apply(self, fault: ActiveFault) -> bool:
        if fault.kind == "PHYSICAL":
            if not fault.plant_mode:
                return False
            self.runtime.inject_fault(fault.plant_mode, cylinder=fault.cylinder, severity=fault.severity,
                                      ramp_sec=fault.ramp_s, origin="MANUAL")
            return True
        # sensor faults
        if fault.plant_mode and fault.channel and fault.channel.startswith("cht["):
            cyl = int(fault.channel[4:-1])
            self.runtime.inject_fault(fault.plant_mode, cylinder=cyl, severity=fault.severity,
                                      ramp_sec=fault.ramp_s, origin="MANUAL")
            return True
        kind = self.sensor_kinds.get(fault.fault_id)
        if kind is None or not fault.channel:
            return False
        # The legacy levers need magnitudes; until configs/sensors (Phase 2) defines them per channel, only the
        # kinds that need no magnitude are driven (stuck, dropout). The others are accepted but not simulated.
        if kind in ("stuck", "dropout"):
            self.runtime.set_sensor_fault(kind, _sensor_channel_to_lever(fault.channel))
            return True
        return False

    def clear_all(self) -> None:
        self.runtime.clear_faults()
