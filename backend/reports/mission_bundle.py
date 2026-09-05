"""
Mission Knowledge Graph -> Report Dump adapter — DRDO / iDEX PS-26054

Turns a completed sortie (its MissionKnowledgeGraph rows plus the final AnalyticsState
snapshot) into the seven PS-26054 report categories, then hands them to
ReportDumpWriter. Keeping this translation here rather than inside EngineStateService
means the 20 Hz service only has to call one function at debrief time, and the
standalone simulators can reuse the exact same report schema.

Stdlib only.
"""

import os
import time
from typing import Any, Dict, List, Optional

from backend.reports.report_dump_writer import (
    ReportDumpWriter,
    format_elapsed,
    summarise_telemetry_csv,
    worst_severity,
)

# Sensor trigger + ML signature text for the 8 canonical PS-26054 fault scenarios
# (doc01 §4). Mirrors the published fault matrix so a fault node in the viewer shows
# the same evidence a reviewer would find in the problem statement.
FAULT_EVIDENCE: Dict[int, Dict[str, str]] = {
    1: {"trigger": "CHT > 135 °C on Cylinder #2",
        "signature": "ΔCHT₂ > +25 °C thermal runaway slope; Cyl #1/#3/#4 nominal"},
    2: {"trigger": "Fuel flow drop with EGT divergence",
        "signature": "-20% fuel flow; EGT₁ lean-combustion divergence on Cyl #1"},
    3: {"trigger": "RPM jitter with cyclic EGT drop",
        "signature": "RPM flutter ±180 RPM; cyclic EGT drop on the affected runner"},
    4: {"trigger": "Oil pressure < 2.0 bar",
        "signature": "Continuous linear oil-pressure decay with gradual oil-temp rise"},
    5: {"trigger": "Vibration RMS > 1.8 mm/s",
        "signature": "Spectral energy peak at 3rd harmonic of the prop reduction shaft"},
    6: {"trigger": "EGT delta > 65 °C across runners",
        "signature": "Runner #3 divergence from uneven air-fuel ratio distribution"},
    7: {"trigger": "DC bus voltage < 12.8 V",
        "signature": "Bus sag under ISR avionics load; battery discharge current rising"},
    8: {"trigger": "MAP Lane A/B delta > 8 kPa",
        "signature": "Cross-channel disparity between Lane A and Lane B MAP transducers"},
}

THEATER_NAMES = {
    "LADAKH": "Northern Sector (Ladakh)",
    "THAR_DESERT": "Western Sector (Thar Desert)",
}

MISSION_PROFILES = {
    "LADAKH": "High-Altitude ISR Loiter",
    "THAR_DESERT": "Extreme-Heat Desert Border Patrol",
}


def build_and_write_mission_bundle(
    graph,
    sortie_id: str,
    analytics: Optional[Dict[str, Any]] = None,
    summary_markdown_path: Optional[str] = None,
    generated_by: str = "engine_service",
    root: Optional[str] = None,
) -> Optional[str]:
    """
    Export one completed sortie into report_dump/mission_NNN/.

    Returns the mission folder path, or None if the sortie is unknown to the graph.
    `analytics` is an AnalyticsState dump (model_dump()); when absent, the
    prediction/health categories fall back to whatever the graph itself recorded.
    """
    sortie = graph.sorties.get(sortie_id)
    if sortie is None:
        return None

    analytics = analytics or {}
    start = float(sortie.start_timestamp)
    end = float(sortie.end_timestamp or time.time())

    anomaly_ids = graph.sortie_anomalies.get(sortie_id, [])
    anomalies = [graph.anomalies[a] for a in anomaly_ids if a in graph.anomalies]
    anomalies.sort(key=lambda a: a.timestamp_epoch)
    action_ids = graph.sortie_actions.get(sortie_id, [])
    actions = [graph.maintenance_actions[a] for a in action_ids if a in graph.maintenance_actions]

    region = sortie.region
    severity = worst_severity([a.severity for a in anomalies])

    manifest = {
        "sortie_id": sortie.sortie_id,
        "name": MISSION_PROFILES.get(region, "Standard ISR Sortie"),
        "uav_tail_number": sortie.uav_tail_number,
        "region": region,
        "theater": THEATER_NAMES.get(region, "Unclassified Sector"),
        "status": sortie.status,
        "severity": severity,
        "start_time": _iso(start),
        "end_time": _iso(end),
        "start_epoch": round(start, 3),
        "end_epoch": round(end, 3),
        "duration_hours": round(sortie.flight_hours, 3),
        "health_index_start": round(sortie.start_health_index, 3),
        "health_index_end": round(sortie.final_health_index, 3),
        "fault_count": len(anomalies),
        "open_actions": sum(1 for a in actions if a.status == "OPEN"),
        "generated_by": generated_by,
    }
    if sortie.min_oat_c is not None:
        manifest["oat_range_c"] = [round(sortie.min_oat_c, 1), round(sortie.max_oat_c, 1)]
    if sortie.min_altitude_ft is not None:
        manifest["altitude_range_ft"] = [int(sortie.min_altitude_ft), int(sortie.max_altitude_ft)]

    summary_md = None
    if summary_markdown_path and os.path.exists(summary_markdown_path):
        try:
            with open(summary_markdown_path, "r", encoding="utf-8") as f:
                summary_md = f.read()
        except OSError:
            summary_md = None

    writer = ReportDumpWriter(root=root)
    return writer.write_mission(
        manifest=manifest,
        readings=summarise_telemetry_csv(sortie.telemetry_log_path),
        telemetry_csv_source=sortie.telemetry_log_path,
        health=_build_health(graph, sortie, analytics),
        faults=_build_faults(graph, anomalies, start),
        timeline=_build_timeline(sortie, anomalies, actions, start, end),
        predictions=_build_predictions(analytics),
        actions=_build_actions(analytics, actions),
        summary_markdown=summary_md,
    )


# ----------------------------------------------------------------------
# Category builders
# ----------------------------------------------------------------------

def _build_health(graph, sortie, analytics: Dict[str, Any]) -> Dict[str, Any]:
    """Engine + per-subsystem health, with the physics residuals that produced it."""
    subsystems = []
    for sub in graph.subsystems.values():
        anomaly_count = len(graph.subsystem_anomalies.get(sub.subsystem_id, []))
        subsystems.append({
            "subsystem_id": sub.subsystem_id,
            "name": sub.name,
            "ata_chapter": sub.ata_chapter,
            "target_mesh": sub.target_mesh,
            "current_health": round(sub.current_health, 3),
            "cumulative_stress_hours": round(sub.cumulative_stress_hours, 2),
            "lifetime_anomalies": anomaly_count,
            "action_required": sub.current_health < 0.75 or anomaly_count > 0,
        })
    subsystems.sort(key=lambda s: s["current_health"])

    start_h = sortie.start_health_index
    end_h = sortie.final_health_index
    payload: Dict[str, Any] = {
        "engine_health_index_start": round(start_h, 3),
        "engine_health_index_end": round(end_h, 3),
        "health_degradation": round(start_h - end_h, 3),
        "final_anomaly_score": round(float(analytics.get("anomaly_score", 0.0)), 4),
        "fleet_subsystems": subsystems,
    }
    live_health = analytics.get("subsystem_health") or {}
    if live_health:
        payload["sortie_subsystem_health"] = {k: round(float(v), 3) for k, v in live_health.items()}
    residuals = analytics.get("residuals") or {}
    if residuals:
        payload["physics_residuals"] = {k: round(float(v), 4) for k, v in residuals.items()}
    sanity = analytics.get("sensor_sanity") or {}
    if sanity:
        payload["sensor_sanity"] = sanity
    return payload


def _build_faults(graph, anomalies: List[Any], start: float) -> Optional[Dict[str, Any]]:
    """One entry per ML-confirmed fault detection, with its PS-26054 evidence."""
    if not anomalies:
        return None
    detections = []
    for a in anomalies:
        sub = graph.subsystems.get(a.subsystem_id)
        evidence = FAULT_EVIDENCE.get(a.fault_id, {})
        entry = {
            "event_id": a.event_id,
            "detected_at": format_elapsed(a.timestamp_epoch, start),
            "detected_at_epoch": round(a.timestamp_epoch, 3),
            "fault_id": a.fault_id,
            "fault_name": a.fault_name,
            "severity": a.severity,
            "anomaly_score": round(a.anomaly_score, 4),
            "ata_chapter": a.ata_chapter,
            "subsystem": sub.name if sub else a.subsystem_id,
            "target_mesh": sub.target_mesh if sub else None,
            "sensor_trigger": evidence.get("trigger", "—"),
            "ml_signature": evidence.get("signature", "—"),
            "recommended_action": a.recommended_action,
        }
        if a.trend_note:
            entry["precursor_trend"] = a.trend_note
        detections.append(entry)

    by_severity: Dict[str, int] = {}
    for d in detections:
        by_severity[d["severity"]] = by_severity.get(d["severity"], 0) + 1

    return {
        "total_detections": len(detections),
        "counts_by_severity": by_severity,
        "detections": detections,
    }


def _build_timeline(sortie, anomalies: List[Any], actions: List[Any],
                    start: float, end: float) -> Dict[str, Any]:
    """Chronological mission record: launch, every detection, every order, recovery."""
    events: List[Dict[str, Any]] = [{
        "at": "T+00:00:00",
        "epoch": round(start, 3),
        "event_type": "MISSION_START",
        "severity": "NOMINAL",
        "title": f"Sortie {sortie.sortie_id} launched",
        "detail": f"{MISSION_PROFILES.get(sortie.region, 'ISR sortie')} — "
                  f"{THEATER_NAMES.get(sortie.region, sortie.region)}. "
                  f"Propulsion health index {sortie.start_health_index:.2f}.",
    }]

    actions_by_subsystem: Dict[str, List[Any]] = {}
    for act in actions:
        actions_by_subsystem.setdefault(act.subsystem_id, []).append(act)

    for a in anomalies:
        rel = format_elapsed(a.timestamp_epoch, start)
        if a.trend_note:
            events.append({
                "at": rel,
                "epoch": round(a.timestamp_epoch, 3),
                "event_type": "DEGRADATION_TREND",
                "severity": "ADVISORY",
                "title": "Sub-threshold drift detected",
                "detail": a.trend_note,
            })
        events.append({
            "at": rel,
            "epoch": round(a.timestamp_epoch, 3),
            "event_type": "FAULT_CONFIRMED",
            "severity": a.severity,
            "title": f"Fault {a.fault_id:02d} — {a.fault_name}",
            "detail": f"Classifier confirmed on {a.subsystem_id} "
                      f"(score {a.anomaly_score:.2f}, {a.ata_chapter}).",
        })
        events.append({
            "at": rel,
            "epoch": round(a.timestamp_epoch, 3),
            "event_type": "ACTION_ISSUED",
            "severity": a.severity,
            "title": "Prescriptive directive issued",
            "detail": a.recommended_action,
        })
        for act in actions_by_subsystem.get(a.subsystem_id, []):
            rul = ""
            if act.rul_p10_hours is not None:
                rul = f" RUL at order — P10 {act.rul_p10_hours:.1f} h / P50 {act.rul_p50_hours:.1f} h."
            events.append({
                "at": rel,
                "epoch": round(a.timestamp_epoch, 3),
                "event_type": "MAINTENANCE_ORDER",
                "severity": "ADVISORY",
                "title": f"Work order {act.action_id} raised",
                "detail": f"{act.description}{rul}",
            })

    events.append({
        "at": format_elapsed(end, start),
        "epoch": round(end, 3),
        "event_type": "MISSION_END",
        "severity": "NOMINAL",
        "title": f"Sortie complete — {sortie.status}",
        "detail": f"{sortie.flight_hours:.2f} flight hours logged. "
                  f"Final propulsion health {sortie.final_health_index * 100:.1f}%.",
    })

    events.sort(key=lambda e: e["epoch"])
    return {
        "mission_start": _iso(start),
        "mission_end": _iso(end),
        "duration_hours": round(sortie.flight_hours, 3),
        "event_count": len(events),
        "events": events,
    }


def _build_predictions(analytics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """RUL prognostics + the pre-flight Go/No-Go advisory (doc01 §3 Pillars 1 & 2)."""
    rul = analytics.get("rul_by_component") or {}
    trend = analytics.get("early_warning_trend")
    if not rul and not trend and not analytics.get("go_no_go"):
        return None

    components = []
    for name, bands in rul.items():
        if not isinstance(bands, dict):
            continue
        components.append({
            "component": name,
            "rul_p10_hours": round(float(bands.get("p10", 0.0)), 2),
            "rul_p50_hours": round(float(bands.get("p50", 0.0)), 2),
            "rul_p90_hours": round(float(bands.get("p90", 0.0)), 2),
        })
    components.sort(key=lambda c: c["rul_p10_hours"])

    payload: Dict[str, Any] = {
        "go_no_go": analytics.get("go_no_go", "GO"),
        "go_no_go_reason": analytics.get("go_no_go_reason", ""),
        "planned_sortie_hours": analytics.get("planned_sortie_hours", 18.0),
        "limiting_component": analytics.get("limiting_component"),
        "rul_by_component": components,
    }
    if trend:
        payload["early_warning_trend"] = trend
    causal = analytics.get("causal_chain") or []
    if causal:
        payload["causal_chain"] = causal
    return payload


def _build_actions(analytics: Dict[str, Any], actions: List[Any]) -> Optional[Dict[str, Any]]:
    """Prescriptive in-flight directives plus the CBM work orders left for ground crew."""
    orders = [{
        "action_id": act.action_id,
        "subsystem_id": act.subsystem_id,
        "ata_chapter": act.ata_chapter,
        "description": act.description,
        "status": act.status,
        "rul_p10_hours": round(act.rul_p10_hours, 2) if act.rul_p10_hours is not None else None,
        "rul_p50_hours": round(act.rul_p50_hours, 2) if act.rul_p50_hours is not None else None,
        "limiting_component": act.limiting_component,
    } for act in actions]

    directive = analytics.get("prescriptive_action")
    checklist = analytics.get("emergency_checklist") or []
    maintenance_order = analytics.get("maintenance_order")

    if not orders and not checklist and not directive:
        return None

    payload: Dict[str, Any] = {
        "open_orders": sum(1 for o in orders if o["status"] == "OPEN"),
        "total_orders": len(orders),
        "maintenance_orders": orders,
    }
    if directive:
        payload["final_pilot_directive"] = directive
    if analytics.get("root_cause"):
        payload["root_cause"] = analytics["root_cause"]
    if checklist:
        payload["emergency_checklist"] = checklist
    if maintenance_order and maintenance_order != "No maintenance required.":
        payload["closing_maintenance_order"] = maintenance_order
    return payload


def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))
