"""Deterministic maintenance directive from the fault registry (cards M3-06/M3-07, idea text I-07).

The leading isolation hypothesis (backend/diagnose/isolator.py) is turned into a directive using only the
registry text (configs/faults.json): root cause, physics explanation, in-flight mitigation, maintenance action,
ATA chapter and the status the registry assigns at full severity. Nothing is generated; every text carries its
source. Alternatives that cannot be told apart (same ambiguity group) or are close in posterior are listed, so
the operator sees the uncertainty instead of a false single answer.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.diagnose.isolator import NOMINAL
from backend.sim.source import registry          # cached registry: the schema check runs once

ALTERNATIVE_RATIO = 0.25            # list alternatives with at least this share of the leading posterior


def _fill(text: Optional[str], cylinder: Optional[int], channel: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    return text.replace("{cyl}", str(cylinder) if cylinder else "(all)").replace("{channel}", channel or "(channel)")


def directive(hypotheses: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """hypotheses: IsolationHypothesis.to_dict() list, ranked. None when NOMINAL leads or there is nothing."""
    if not hypotheses or hypotheses[0]["kind"] == "NOMINAL":
        return None
    top = hypotheses[0]
    raw = registry().get(top["fault_id"]).raw
    cyl, ch = top.get("cylinder"), top.get("channel")
    alternatives = [{"fault_id": h["fault_id"], "name": h["name"], "cylinder": h.get("cylinder"),
                     "channel": h.get("channel"), "posterior": h["posterior"],
                     "same_group": h.get("group") is not None and h.get("group") == top.get("group")}
                    for h in hypotheses[1:]
                    if h["posterior"] >= ALTERNATIVE_RATIO * top["posterior"] or
                    (h.get("group") is not None and h.get("group") == top.get("group"))]
    return {
        "fault_id": top["fault_id"], "fault_name": raw.get("name"), "description": raw.get("description"),
        "kind": top["kind"], "cylinder": cyl, "channel": ch, "posterior": top["posterior"],
        "severity_estimate": top.get("severity"),
        "ata_chapter": raw.get("ata_chapter"),
        "status_at_full_severity": raw.get("status_at_full_severity"),
        "root_cause": _fill(raw.get("physics_explanation"), cyl, ch),
        "mitigation_inflight": {**(raw.get("mitigation_inflight") or {}),
                                "text": _fill((raw.get("mitigation_inflight") or {}).get("text"), cyl, ch)},
        "maintenance_action": {**(raw.get("maintenance_action") or {}),
                               "text": _fill((raw.get("maintenance_action") or {}).get("text"), cyl, ch)},
        "supporting": top.get("supporting", []), "contradicting": top.get("contradicting", []),
        "alternatives": alternatives,
        "source": "configs/faults.json (registry text) + backend/diagnose/isolator.py (posterior)",
    }


SENSOR_STATUS = "ADVISORY"          # one sender offset: the engine is not implicated (T-STS-4)


def status_hypotheses(hypotheses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Hypotheses with the level the status evaluator applies: the registry's status_at_full_severity for an
    engine (PROCESS) fault, ADVISORY for a sensor offset; NOMINAL is dropped."""
    reg = registry()
    out = []
    for h in hypotheses:
        if h["kind"] == "NOMINAL":
            continue
        raw = {} if h["kind"] == "SENSOR" else reg.get(h["fault_id"]).raw
        level = SENSOR_STATUS if h["kind"] == "SENSOR" else raw.get("status_at_full_severity")
        out.append({**h, "status_at_full_severity": level, "immediate_no_go": bool(raw.get("immediate_no_go"))})
    return out


__all__ = ["directive", "status_hypotheses", "NOMINAL"]
