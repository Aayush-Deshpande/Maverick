"""Engine status evaluator (card M2-01, P Part 4 Step 2.1-2.2, DECISIONS D4).

Levels: ENGINE_OFF, GO, ADVISORY, CAUTION, NO-GO. Inputs are observable only: the measured Frame (readings with
quality), the engine's banded limits (configs/engines/<id>.json 'limits'), the ECU engine_state, quarantined sensors,
diagnosis hypotheses and time-to-limit predictions. It never reads injected faults or plant truth (T-DYN-4).

Rules (P Step 2.2):
  warning band (reading with quality OK)      -> NO-GO
  caution band (outside normal, inside warning; or above a time-limited value too long) -> CAUTION
  hypothesis posterior >= threshold           -> that fault's status_at_full_severity (registry)
  time-to-limit < mission remaining           -> CAUTION "will exceed <limit> in <t>"
  one quarantined sensor                       -> ADVISORY;  two on one subsystem -> CAUTION
  engine_state FAILED                          -> NO-GO;     OFF -> ENGINE_OFF
Hysteresis: enter immediately; exit only after the value is back inside the band by a margin (share of the band span)
for a hold time. NO-GO latches until it is acknowledged AND its cause has cleared. Every non-GO level carries reasons.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
ORDER = {"ENGINE_OFF": 0, "GO": 1, "ADVISORY": 2, "CAUTION": 3, "NO-GO": 4}


def load_status_config() -> Dict[str, Any]:
    return json.loads((ROOT / "configs" / "status.json").read_text(encoding="utf-8"))


@dataclass
class Reason:
    code: str
    level: str
    text: str
    channel: Optional[str] = None
    fault_id: Optional[str] = None
    value: Optional[float] = None
    limit: Optional[float] = None


@dataclass
class StatusResult:
    level: str
    reasons: List[Reason] = field(default_factory=list)
    latched: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"level": self.level, "latched": self.latched, "reasons": [asdict(r) for r in self.reasons]}


@dataclass
class _Active:
    reason: Reason
    lo: Optional[float]          # band the value must return inside (with margin) to clear
    hi: Optional[float]
    clear_since: Optional[float] = None
    band: Optional[tuple] = None  # the rule in force when it was raised (rpm rules switch bands)


LEGACY_CHANNELS = {"oil_press": "oil_p", "oil_temp": "oil_t", "map": "map_kpa", "bus_voltage": "bus_v",
                   "fuel_flow": "fuel_flow", "vib_gearbox_rms": "vibration"}


def canonical_channel(name: str) -> str:
    """'CHT_<k>' / 'cht_<k>' -> 'cht[<k>]'; legacy validator names -> Frame names."""
    low = name.lower()
    if low in LEGACY_CHANNELS:
        return LEGACY_CHANNELS[low]
    for prefix in ("cht", "egt"):
        if low.startswith(prefix + "_") and low[len(prefix) + 1:].isdigit():
            return f"{prefix}[{low[len(prefix) + 1:]}]"
    return low


def frame_readings(frame: Any) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    for name in ("rpm", "prop_rpm", "map_kpa", "coolant_t", "oil_p", "oil_t", "fuel_flow", "fuel_p", "fuel_t",
                 "rail_p", "gearbox_t", "bus_v"):
        out[name] = getattr(frame, name, None)
    for prefix in ("cht", "egt"):
        for i, v in enumerate(getattr(frame, prefix, []) or [], start=1):
            out[f"{prefix}[{i}]"] = v
    return out


class StatusEvaluator:
    def __init__(self, cfg: Any, status_cfg: Optional[Dict[str, Any]] = None) -> None:
        sc = status_cfg or load_status_config()
        self.limits: Dict[str, Dict[str, Any]] = cfg.limits or {}
        self.idle_rpm, self.mc_rpm = float(cfg.idle_rpm), float(cfg.max_continuous_rpm)
        self.margin = float(sc["exit_margin_fraction_of_band"]["value"])
        self.hold_s = float(sc["exit_hold_s"]["value"])
        self.posterior_min = float(sc["hypothesis_posterior_min"]["value"])
        self.subsystem = sc["subsystems"]["map"]
        self._active: Dict[str, _Active] = {}
        self._band: Dict[str, tuple] = {}
        self._over_since: Dict[str, float] = {}
        self._latched: Optional[Reason] = None
        self._acknowledged = False

    # -- operator -------------------------------------------------------------------------------------------
    def acknowledge(self) -> None:
        """Acknowledge a latched NO-GO; it clears once its cause has also cleared."""
        self._acknowledged = True

    # -- evaluation -----------------------------------------------------------------------------------------
    def evaluate(self, t: float, frame: Any, engine_state: Optional[str] = None,
                 quarantined: Iterable[str] = (), hypotheses: Iterable[Dict[str, Any]] = (),
                 time_to_limit: Iterable[Dict[str, Any]] = ()) -> StatusResult:
        if engine_state == "OFF":
            self._active.clear()
            return StatusResult("ENGINE_OFF")
        found: List[Tuple[Reason, Optional[float], Optional[float]]] = []
        if engine_state == "FAILED":
            found.append((Reason("ENGINE_FAILED", "NO-GO", "Engine has stopped running (ECU state FAILED)"), None, None))
        q = {canonical_channel(c) for c in quarantined}
        found += self._limit_reasons(t, frame_readings(frame), q)
        found += self._sensor_reasons(q)
        for h in hypotheses:
            if h.get("posterior", 0.0) >= self.posterior_min and h.get("status_at_full_severity"):
                found.append((Reason("HYPOTHESIS", h["status_at_full_severity"],
                                     f"{h['fault_id']} {h.get('name', '')} suspected (posterior {h['posterior']:.2f})",
                                     fault_id=h["fault_id"], value=h["posterior"]), None, None))
        for p in time_to_limit:
            if p.get("time_to_limit_s") is not None and p.get("mission_remaining_s") is not None \
                    and p["time_to_limit_s"] < p["mission_remaining_s"]:
                found.append((Reason("TIME_TO_LIMIT", "CAUTION",
                                     f"will exceed {p['channel']} limit {p['limit']} in {p['time_to_limit_s'] / 60:.0f} min",
                                     channel=p["channel"], limit=p["limit"]), None, None))
        return self._apply_hysteresis(t, found, frame_readings(frame))

    def _limit_reasons(self, t: float, r: Dict[str, Optional[float]], quarantined: set):
        out = []
        rpm = r.get("rpm")
        for ch, lim in self.limits.items():
            names = [k for k in r if k.startswith(ch + "[")] if lim.get("per_cylinder") else [ch]
            for name in names:
                v = r.get(name)
                if v is None or name in quarantined:
                    continue                                   # no data / not trusted: the sensor reason covers it
                out += self._check(t, name, v, lim, rpm)
        return out

    def _check(self, t: float, name: str, v: float, lim: Dict[str, Any], rpm: Optional[float]):
        unit = lim.get("unit", "")
        wl, wh = lim.get("warning_low"), lim.get("warning_high")
        normal = lim.get("normal")
        rule = lim.get("rpm_rule")
        if rule and rpm is not None and "above_rpm" in rule:   # band applies above an rpm, a minimum below it
            if rpm > rule["above_rpm"]:
                normal = rule.get("normal", normal)
            else:
                normal, wl = None, rule.get("below_min", wl)
        elif rule and rpm is not None and "at_idle_min" in rule:  # minimum rises from idle to max continuous
            x = min(1.0, max(0.0, (rpm - self.idle_rpm) / max(self.mc_rpm - self.idle_rpm, 1.0)))
            wl = rule["at_idle_min"] + x * (rule["at_max_continuous_min"] - rule["at_idle_min"])
        tl = lim.get("time_limited")
        self._band[name] = (wl, wh, tuple(normal) if normal else None)
        if wh is not None and v > wh:
            return [(Reason("LIMIT_WARNING_HIGH", "NO-GO", f"{name} {v:.1f} {unit} above warning {wh} {unit}",
                           channel=name, value=v, limit=wh), None, wh)]
        if wl is not None and v < wl:
            return [(Reason("LIMIT_WARNING_LOW", "NO-GO", f"{name} {v:.1f} {unit} below warning {wl} {unit}",
                           channel=name, value=v, limit=wl), wl, None)]
        if tl is not None:
            base = (normal[1] if normal else None) or lim.get("normal_max")
            if base is not None and v > base:
                start = self._over_since.setdefault(name, t)
                if v > tl["max"]:
                    return [(Reason("LIMIT_WARNING_HIGH", "NO-GO", f"{name} {v:.1f} {unit} above {tl['max']} {unit}",
                                   channel=name, value=v, limit=tl["max"]), None, tl["max"])]
                if t - start > tl["max_s"]:
                    return [(Reason("TIME_LIMIT", "CAUTION",
                                   f"{name} above {base} {unit} for {t - start:.0f} s (max {tl['max_s']} s)",
                                   channel=name, value=v, limit=base), None, base)]
                return []                                     # inside the allowed time window
            self._over_since.pop(name, None)
        nm = lim.get("normal_max")
        if nm is not None and v > nm and tl is None:
            return [(Reason("LIMIT_CAUTION_HIGH", "CAUTION", f"{name} {v:.1f} {unit} above normal {nm} {unit}",
                           channel=name, value=v, limit=nm), None, nm)]
        if normal:
            lo, hi = normal
            if v > hi:
                return [(Reason("LIMIT_CAUTION_HIGH", "CAUTION", f"{name} {v:.1f} {unit} above normal {hi} {unit}",
                               channel=name, value=v, limit=hi), lo, hi)]
            if v < lo:
                return [(Reason("LIMIT_CAUTION_LOW", "CAUTION", f"{name} {v:.1f} {unit} below normal {lo} {unit}",
                               channel=name, value=v, limit=lo), lo, hi)]
        return []

    def _sensor_reasons(self, quarantined: set):
        out, per_sub = [], {}
        for ch in sorted(quarantined):
            per_sub.setdefault(self.subsystem.get(ch.split("[")[0], "other"), []).append(ch)
        for sub, chans in per_sub.items():
            if len(chans) >= 2:
                out.append((Reason("SENSORS_QUARANTINED", "CAUTION",
                                   f"{len(chans)} {sub} sensors quarantined ({', '.join(chans)})"), None, None))
            else:
                out.append((Reason("SENSOR_QUARANTINED", "ADVISORY", f"{chans[0]} sensor quarantined (reading not used)",
                                   channel=chans[0]), None, None))
        return out

    def _apply_hysteresis(self, t: float, found, r: Dict[str, Optional[float]]) -> StatusResult:
        now = {}
        for reason, lo, hi in found:
            key = f"{reason.code}:{reason.channel or reason.fault_id or reason.text}"
            now[key] = _Active(reason, lo, hi, band=self._band.get(reason.channel))
        for key, act in list(self._active.items()):            # exits need margin + hold time
            if key in now:
                continue
            v = r.get(act.reason.channel) if act.reason.channel else None
            if act.band is not None and self._band.get(act.reason.channel) != act.band:
                inside = True               # that band no longer applies (e.g. below the rpm of an rpm rule)
            elif act.reason.channel and v is not None and (act.lo is not None or act.hi is not None):
                span = (act.hi - act.lo) if (act.lo is not None and act.hi is not None) else abs(act.hi or act.lo)
                m = self.margin * span
                inside = (act.hi is None or v <= act.hi - m) and (act.lo is None or v >= act.lo + m)
            else:
                inside = True
            if not inside:
                act.clear_since = None
                now[key] = act
                continue
            act.clear_since = t if act.clear_since is None else act.clear_since
            if t - act.clear_since < self.hold_s:
                now[key] = act
        self._active = now
        reasons = [a.reason for a in now.values()]
        nogo = [x for x in reasons if x.level == "NO-GO"]
        if nogo:
            self._latched, self._acknowledged = nogo[0], False
        elif self._latched is not None and self._acknowledged:
            self._latched = None
        latched = False
        if self._latched is not None and not nogo:
            latched = True
            reasons = [Reason("LATCHED", "NO-GO", f"NO-GO latched until acknowledged: {self._latched.text}",
                              channel=self._latched.channel, value=self._latched.value,
                              limit=self._latched.limit)] + reasons
        level = max((x.level for x in reasons), key=lambda lv: ORDER[lv], default="GO")
        return StatusResult(level, reasons, latched)
