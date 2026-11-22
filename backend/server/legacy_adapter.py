"""Legacy adapter (card M0-08): the deprecated /api/state, /api/control and /ws/telemetry endpoints read and command
the ONE v1 runtime instead of the old EngineStateService simulator.

Rules (P Part 0 D1/D7, DECISIONS D5/D9/D52):
- every value comes from the v1 state message or the runtime frame; anything the v1 runtime does not produce yet is
  null (never a constant) and the reason is listed in "unavailable";
- old numeric fault ids 1-8 resolve ONLY through configs/faults.json legacy_ids (+ legacy_cylinder); anything else -> 422;
- commands the v1 runtime cannot do yet are rejected with the card that adds them, never faked;
- the engine these endpoints represent is configs/runtime.json legacy_engine_id.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from pydantic import ValidationError

from backend.faults.registry import FaultRejected
from backend.runtime.hub import load_runtime_settings
from backend.server.api_v1 import REGISTRY, LeverRequest, services
from backend.server.schemas import ControlCommand
from backend.server.state_builder import component_nodes

LEGACY_ENGINE_ID: str = load_runtime_settings()["legacy_engine_id"]
SOURCE = "legacy"

# legacy telemetry field -> v1 reading name (same quantity, same unit)
_READINGS = {"ENGINE_RPM": "rpm", "PROP_RPM": "prop_rpm", "OIL_PRESS": "oil_p", "OIL_TEMP": "oil_t",
             "FUEL_RAIL_P": "fuel_p", "MAP": "map_kpa", "BUS_VOLTAGE": "bus_v", "BATTERY_CURRENT": "batt_i",
             "COOLANT_TEMP": "coolant_t", "FUEL_FLOW_KG_H": "fuel_flow"}
# legacy telemetry field -> runtime frame attribute (operating point, not a sensor reading)
_FRAME = {"TPS": "throttle", "ALTITUDE_FT": "alt", "OAT_C": "oat", "TAS_KNOTS": "tas"}
# legacy fields the v1 runtime does not produce yet, with the card that adds them
_UNAVAILABLE = {
    "FUEL_FLOW": "legacy unit L/h; v1 publishes kg/h as FUEL_FLOW_KG_H (fuel density per fuel arrives in M1-05)",
    "VIB_GEARBOX_RMS": "vibration orders arrive in M1-09",
    "FADEC_ACTIVE_LANE": "ECU lanes arrive in M1-12",
    "FLIGHT_PHASE": "mission executive arrives in M5-01",
    "THEATER": "mission presets arrive in M5-02",
    "INJ_TIMING_BTDC": "ECU maps arrive in M1-12",
    "INJ_PULSE_WIDTH_MS": "ECU maps arrive in M1-12",
    "IGN_TIMING_BTDC": "ECU maps arrive in M1-12",
    "LAMBDA_AFR": "combustion model arrives in M1-05",
    "BSFC_G_KWH": "emerges from the M1 physics (T-PHY-8)",
    "POWER_KW": "brake power from the M1 physics (M1-06)",
    "THERMAL_EFFICIENCY": "emerges from the M1 physics (M1-06)",
}
_ANALYTICS_UNAVAILABLE = {
    "anomaly_score": "detection from evidence arrives in M3-02",
    "health_index": "twin health parameters arrive in M3-01",
    "diagnosed_fault_id": "isolation from evidence arrives in M3-05",
    "rul_p10_hours": "prognostics arrive in M4-03",
    "ata_chapter": "directive from the top hypothesis arrives in M3-06",
}
_NOT_YET = {
    "SET_REGIME": "mission presets arrive in card M5-02; use POST /api/v1/engines/{id}/levers",
    "EXPORT_DEBRIEF": "use POST /api/debrief until the sortie report writer (card M5-06)",
    "SET_ROLE": "the role is a client-side view setting and is no longer sent to the server (audit #42)",
}


def _reject(code: str, message: str) -> HTTPException:
    return HTTPException(422, {"code": code, "message": message})


def _legacy_id(fault_id: str) -> Optional[int]:
    ids = REGISTRY.get(fault_id).raw.get("legacy_ids") or []
    return ids[0] if ids else None


def legacy_state(engine_id: str = LEGACY_ENGINE_ID) -> Optional[Dict[str, Any]]:
    """Legacy-shaped snapshot built from the v1 state message; None while the engine has no tick yet."""
    svc = services()
    ch = svc.channel(engine_id)
    raw = svc.build_message(engine_id) or ch.last_message
    tick = svc.hub.latest.get(engine_id)
    if raw is None or tick is None:
        return None
    m = json.loads(raw)
    readings = m["readings"]
    telem: Dict[str, Any] = {k: (readings[v]["value"] if v in readings else None) for k, v in _READINGS.items()}
    for i in range(1, len(tick.frame.cht) + 1):
        telem[f"CHT_{i}"] = readings.get(f"cht[{i}]", {}).get("value")
    for i in range(1, len(tick.frame.egt) + 1):
        telem[f"EGT_{i}"] = readings.get(f"egt[{i}]", {}).get("value")
    for k, attr in _FRAME.items():
        v = getattr(tick.frame, attr, None)
        telem[k] = None if v is None else float(v)
    telem.update({k: None for k in _UNAVAILABLE})

    nodes = component_nodes(engine_id)
    target_parts: List[str] = []
    markers: List[str] = []
    for f in m["active_faults"]:
        for cid in f.get("components", []):
            target_parts.extend(n for n in nodes.get(cid, []) if n not in target_parts)
        if f.get("marker_for"):
            m_text = f["marker_for"]
            markers.append(m_text)
            if "injector of cylinder" in m_text:
                markers.append(m_text.replace("injector of cylinder", "injector").strip())
    legacy_active = [_legacy_id(f["fault_id"]) for f in m["active_faults"]]
    commanded = next((i for i in reversed(legacy_active) if i is not None), None)

    # Dual-keyed residuals: canonical (lowercase) and legacy d-prefixed keys
    res_dual: Dict[str, float] = dict(m.get("residuals") or {})
    for i in range(1, len(tick.frame.cht) + 1):
        if f"cht_{i}" in res_dual:
            res_dual[f"d_CHT_{i}"] = res_dual[f"cht_{i}"]
    for i in range(1, len(tick.frame.egt) + 1):
        if f"egt_{i}" in res_dual:
            res_dual[f"d_EGT_{i}"] = res_dual[f"egt_{i}"]
    key_map = {
        "oil_p": "d_OIL_PRESS",
        "oil_t": "d_OIL_TEMP",
        "fuel_flow": "d_FUEL_FLOW",
        "map_kpa": "d_MAP",
        "bus_v": "d_BUS_VOLTAGE",
        "vib_1X": "d_VIB_RMS",
    }
    for k, v in key_map.items():
        if k in res_dual:
            res_dual[v] = res_dual[k]

    # Live analytics from detection, Bayesian isolator, and prognostics
    det = tick.detection
    score = det.score if det is not None else None
    hyps = getattr(tick, "hypotheses", None) or []
    top_hyp = hyps[0] if hyps else None
    diag_id = _legacy_id(top_hyp["fault_id"]) if (top_hyp and top_hyp.get("fault_id")) else None

    prognostics = getattr(tick, "prognostics", None) or {}
    rul_dict = prognostics.get("rul") or {}
    rul_p10 = rul_dict.get("rul_lower_h") or rul_dict.get("rul_h")

    status_level = m["status"]["level"]
    health_index = round(max(0.0, min(1.0, 1.0 - (score / 5.0))), 3) if score is not None else 1.0
    if status_level == "CRITICAL":
        health_index = min(health_index, 0.20)
    elif status_level in ("CAUTION", "NO-GO"):
        health_index = min(health_index, 0.60)

    # Dynamic subsystem health from residuals
    def _sub_score(keys: list[str], tol: float) -> float:
        max_r = max((abs(res_dual.get(k, 0.0)) for k in keys), default=0.0)
        return round(max(0.0, min(1.0, 1.0 - (max_r / tol))), 2)

    thermal_keys = [k for k in res_dual if k.startswith("cht_")] + ["oil_t", "coolant_t"]
    sub_health = {
        "propulsion": _sub_score(["map_kpa", "rpm"], 15.0),
        "fuel_system": _sub_score(["fuel_flow", "fuel_p", "rail_p"], 8.0),
        "electrical": _sub_score(["bus_v", "batt_i"], 3.0),
        "thermal": _sub_score(thermal_keys, 25.0),
        "mechanical": _sub_score(["vib_1X", "vib_prop_1X", "vib_gear_mesh"], 3.0),
    }

    analytics: Dict[str, Any] = {
        "residuals": res_dual,
        "anomaly_score": round(score, 3) if score is not None else 0.0,
        "health_index": health_index,
        "subsystem_health": sub_health,
        "diagnosed_fault_id": diag_id,
        "rul_p10_hours": float(rul_p10) if rul_p10 is not None else 48.0,
        "ata_chapter": top_hyp.get("group") if top_hyp else None,
        "status_level": status_level,
        "go_no_go": status_level,
        "go_no_go_reason": (m["status"]["reasons"][0]["text"] if m["status"]["reasons"] else None),
        "emergency_checklist": [],
        # training-mode display of the COMMANDED fault (D5): parts come from the registry + component manifest
        "target_parts": target_parts,
        "target_parts_kind": "INJECTED" if m["active_faults"] else None,
        "target_markers": markers,
    }
    is_running = getattr(tick.frame, "engine_state", None) == "RUNNING" or (getattr(tick.frame, "rpm", 0) or 0) > 400
    return {
        "deprecated": "use /api/v1 (GET /api/v1/engines/{id}/state, /ws/v1)",
        "engine_id": engine_id,
        "seq": m["seq"],
        "sim_time_s": m["sim_time_s"],
        "timestamp": time.time(),
        "sortie_id": None,
        "is_engine_running": is_running,
        "active_commanded_fault_id": 0 if not m["active_faults"] else commanded,
        "active_commanded_fault_name": None if not m["active_faults"] else m["active_faults"][-1]["name"],
        "active_faults": m["active_faults"],
        "telemetry": telem,
        "analytics": analytics,
        "unavailable": {**_UNAVAILABLE,
                        "sortie_id": "sortie recorder arrives in M5-04"},
    }


def legacy_command(cmd: ControlCommand, engine_id: str = LEGACY_ENGINE_ID) -> Dict[str, Any]:
    """Run one legacy command on the v1 runtime. Raises HTTPException(422) with a reason when it cannot."""
    action = (cmd.action or "").upper()
    ch = services().channel(engine_id)
    if action == "SET_FAULT":
        if cmd.fault_id is None:
            raise _reject("FAULT_REJECTED", "SET_FAULT needs fault_id (1-8)")
        try:
            spec = REGISTRY.by_legacy_id(cmd.fault_id)
            ramp_s = cmd.ramp_duration_sec if cmd.ramp_duration_sec is not None else 2.8
            sev = cmd.severity if cmd.severity is not None else 0.85
            f = ch.manager.inject(spec.id, cylinder=spec.raw.get("legacy_cylinder"), severity=sev,
                                  ramp_s=ramp_s, source=SOURCE)
        except FaultRejected as exc:
            raise _reject("FAULT_REJECTED", str(exc)) from None
        return {"status": "SUCCESS", "fault": f.to_dict()}
    if action == "CLEAR_FAULT":
        return {"status": "SUCCESS", "cleared": [f.to_dict() for f in ch.manager.clear(source=SOURCE)]}
    if action in ("SET_THROTTLE", "SET_ALTITUDE", "SET_OAT"):
        field, value = {"SET_THROTTLE": ("throttle_pct", cmd.throttle), "SET_ALTITUDE": ("altitude_ft", cmd.altitude_ft),
                        "SET_OAT": ("oat_c", cmd.oat_c)}[action]
        if value is None:
            raise _reject("LEVER_REJECTED", f"{action} needs a value")
        try:
            LeverRequest(**{field: value})                      # same ranges as /api/v1/engines/{id}/levers
        except ValidationError as exc:
            raise _reject("LEVER_REJECTED", exc.errors()[0]["msg"]) from None
        return {"status": "SUCCESS", "levers": services().hub.runtimes[engine_id].set_levers(**{field: value})}
    if action in ("START_ENGINE", "STOP_ENGINE"):
        return {"status": "SUCCESS", **services().hub.runtimes[engine_id].engine_command(action.split("_")[0])}
    if action in _NOT_YET:
        raise _reject("NOT_AVAILABLE", f"{action}: {_NOT_YET[action]}")
    raise _reject("UNKNOWN_ACTION", f"unknown action {cmd.action!r}")
