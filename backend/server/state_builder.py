"""Build the versioned StateMessage (backend/server/state_schema.py) from one runtime tick (card M0-05).

Only measured or computed values are copied; anything the runtime does not produce yet stays null / empty (D7).
Status stays UNKNOWN until the status evaluator exists (card M2-01): the old always-"GO" logic is not carried over.
Highlights from diagnosis come in M3; until then active faults carry their resolved components for the training-mode
INJECTED outline only (D5).
"""
from __future__ import annotations

import datetime as _dt
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from backend.core.frame import Q_FROZEN, Q_INTERPOLATED, Q_LANE_DISAGREE, Q_OUT_OF_RANGE, Q_SHIELDED, Q_STALE
from backend.server.state_schema import ActiveFaultOut, EventOut, Highlight, Reading, StateMessage, Status

ROOT = Path(__file__).resolve().parents[2]

# Units of the canonical Frame channels (the Frame contract in backend/core/frame.py, not engine data).
FRAME_UNITS = {
    "rpm": "rpm", "prop_rpm": "rpm", "throttle": "%", "map_kpa": "kPa", "coolant_t": "C", "oil_p": "bar",
    "oil_t": "C", "fuel_flow": "kg/h", "fuel_t": "C", "rail_p": "bar", "bus_v": "V", "bus_i": "A", "batt_i": "A",
    "alt": "ft", "oat": "C", "tas": "kt", "cht": "C", "egt": "C",
}
SCALARS = ("rpm", "prop_rpm", "map_kpa", "coolant_t", "oil_p", "oil_t", "fuel_flow", "fuel_t", "rail_p",
           "bus_v", "bus_i", "batt_i")


def _quality(bits: Optional[int]) -> str:
    if not bits:
        return "OK"
    if bits & Q_SHIELDED:
        return "QUARANTINED"
    if bits & Q_INTERPOLATED:
        return "VIRTUAL"
    if bits & (Q_FROZEN | Q_OUT_OF_RANGE | Q_LANE_DISAGREE | Q_STALE):
        return "SUSPECT"
    return "OK"


@lru_cache(maxsize=16)
def component_nodes(engine_id: str) -> Dict[str, List[str]]:
    path = ROOT / "configs" / "components" / f"{engine_id}.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {c["component_id"]: c["nodes"] for c in data["components"]}


def resolve_fault_components(fault_raw: Dict[str, Any], engine_id: str, cylinder: Optional[int],
                             channel: Optional[str]) -> tuple[list[str], Optional[str]]:
    """Component ids for one active fault on one engine, plus the marker text when parts are missing."""
    entry = (fault_raw.get("components") or {}).get(engine_id)
    if not entry:
        return [], None
    if "by_channel" in entry:
        table = entry["by_channel"]
        cyl = None
        generic = channel
        if channel and channel.endswith("]") and "[" in channel:          # egt[3] -> egt[{cyl}], cyl 3
            base, _, idx = channel[:-1].partition("[")
            cyl, generic = idx, f"{base}[{{cyl}}]"
        comps = table.get(channel) or table.get(generic) or table.get("*") or []
        ids = [i.replace("{cyl}", cyl) if cyl else i for i in comps]
        return ids, entry.get("marker_for") if entry.get("marker") else None
    ids = [i.replace("{cyl}", str(cylinder)) for i in entry.get("now", [])] if cylinder else \
        [i for i in entry.get("now", []) if "{cyl}" not in i]
    marker = entry.get("marker_for")
    if marker and cylinder:
        marker = marker.replace("{cyl}", str(cylinder))
    return ids, marker if entry.get("marker") else None


def build_state(tick: Any, seq: int, *, registry: Any = None, active_faults: Iterable[Any] = (),
                fault_events: Iterable[Any] = (), rate_hz_actual: Optional[float] = None, time_scale: float = 1.0,
                levers: Optional[Dict[str, Optional[float]]] = None, training_mode: bool = False) -> StateMessage:
    f = tick.frame
    engine_id = tick.engine_id
    readings: Dict[str, Reading] = {}
    for name in SCALARS:
        v = getattr(f, name, None)
        if v is not None:
            readings[name] = Reading(value=float(v), unit=FRAME_UNITS[name], quality=_quality(f.quality.get(name)))
    for prefix, series in (("cht", f.cht), ("egt", f.egt)):
        for i, v in enumerate(series, start=1):
            key = f"{prefix}[{i}]"
            readings[key] = Reading(value=None if v is None else float(v), unit=FRAME_UNITS[prefix],
                                    quality=_quality(f.quality.get(f"{prefix}_{i}")))

    nodes = component_nodes(engine_id)
    faults_out: List[ActiveFaultOut] = []
    highlights: List[Highlight] = []
    for af in active_faults:
        raw = registry.get(af.fault_id).raw if registry is not None else {}
        comp_ids, marker = resolve_fault_components(raw, engine_id, af.cylinder, af.channel)
        faults_out.append(ActiveFaultOut(uuid=af.uuid, fault_id=af.fault_id, name=af.name, kind=af.kind,
                                         cylinder=af.cylinder, channel=af.channel, severity=af.severity,
                                         ramp_s=af.ramp_s, source=af.source, t0_s=af.t0_s, simulated=af.simulated,
                                         components=comp_ids, marker_for=marker))
        if training_mode:  # D5: the commanded fault is shown only in training mode, labelled INJECTED
            for cid in comp_ids:
                highlights.append(Highlight(component_id=cid, nodes=nodes.get(cid, []), level="INJECTED",
                                            reason=f"{af.fault_id} {af.name} (injected, training mode)",
                                            marker_for=marker))

    events = [EventOut(seq=e.seq, t_s=e.t_s, type=e.type, text=e.text, source=e.source) for e in fault_events]
    for e in getattr(tick, "events", []) or []:
        events.append(EventOut(seq=int(e.get("seq", 0)), t_s=float(e.get("t_sim", e.get("t", 0.0))),
                               type=str(e.get("kind", e.get("type", "EVENT"))), text=str(e.get("title", "")),
                               source="runtime"))

    det = tick.detection
    return StateMessage(
        engine_id=engine_id, seq=seq, sim_time_s=float(f.t),
        wall_time_iso=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="milliseconds"),
        rate_hz_actual=rate_hz_actual, time_scale=time_scale,
        source="REPLAY" if f.source == "REPLAY" else "CAN" if f.source == "CAN" else "MAVLINK" if f.source == "MAVLINK" else "SIM",
        levers=levers or {"throttle": f.throttle},
        environment={"altitude_ft": f.alt, "oat_c": f.oat, "tas_kt": f.tas},
        readings=readings,
        twin=tick.ukf, residuals={},
        detections=None if det is None else {"confirmed": bool(det.confirmed), "raw_alarm": bool(det.raw_alarm),
                                             "top_channels": [list(x) if isinstance(x, tuple) else x for x in det.top_channels],
                                             "scores": {k: float(v) for k, v in det.scores.items()},
                                             "ratios": {k: float(v) for k, v in det.ratios.items()},
                                             "candidate": tick.heavy},          # tier-1 readout scores (not probabilities)
        hypotheses=[],
        status=Status(level="UNKNOWN"),
        highlights=highlights,
        prognostics=tick.prognostics, reliability=tick.reliability,
        active_faults=faults_out, events_since=events,
        vibration_orders={k: float(v) for k, v in (f.vibration_orders or {}).items()},
        virtual_sensors={k: float(v) for k, v in (f.virtual_sensors or {}).items()},
    )
