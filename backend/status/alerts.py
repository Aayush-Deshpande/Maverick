"""Alert management (card M2-03, P Step 2.4, P Part 6 U3 - ISA-18.2 / EEMUA 191).

Alerts come from the status evaluator's reasons: one alert per cause (code + channel/fault), with first/last time,
activation count, acknowledge, shelve with automatic un-shelve, and a root-cause group (the fault of a hypothesis, else
the channel's subsystem) so one problem shows as one group with its details inside. Every alert names an operator
action (configs/status.json alert_actions) - a reason with no action is an event, not an alert.
Master WARNING / CAUTION: an active, unacknowledged, unshelved NO-GO / CAUTION alert.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from backend.status.evaluator import ORDER, StatusResult, load_status_config


@dataclass
class Alert:
    id: str
    level: str
    code: str
    text: str
    action: str
    group: str
    channel: Optional[str]
    fault_id: Optional[str]
    first_s: float
    last_s: float
    count: int
    active: bool = True
    acknowledged: bool = False
    shelved_until: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AlertManager:
    def __init__(self, status_cfg: Optional[Dict[str, Any]] = None) -> None:
        sc = status_cfg or load_status_config()
        self.actions: Dict[str, str] = {k: v for k, v in sc["alert_actions"].items() if k not in ("ref",)}
        self.max_shelve_s = float(sc["max_shelve_s"]["value"])
        self.subsystem = sc["subsystems"]["map"]
        self.alerts: Dict[str, Alert] = {}

    def _group(self, channel: Optional[str], fault_id: Optional[str]) -> str:
        if fault_id:
            return fault_id
        if channel:
            return self.subsystem.get(channel.split("[")[0], channel)
        return "engine"

    def update(self, t: float, status: StatusResult) -> List[Alert]:
        seen = set()
        for r in status.reasons:
            if r.code not in self.actions:
                continue                                          # no operator action: event log, not an alert
            key = f"{r.code}:{r.channel or r.fault_id or ''}"
            seen.add(key)
            a = self.alerts.get(key)
            if a is None:
                self.alerts[key] = Alert(id=key, level=r.level, code=r.code, text=r.text, action=self.actions[r.code],
                                         group=self._group(r.channel, r.fault_id), channel=r.channel,
                                         fault_id=r.fault_id, first_s=t, last_s=t, count=1)
                continue
            if not a.active:                                      # re-raised: a new activation
                a.count += 1
                a.acknowledged = False
            a.active, a.level, a.text, a.last_s = True, r.level, r.text, t
        for key, a in self.alerts.items():
            if key not in seen:
                a.active = False
            if a.shelved_until is not None and t >= a.shelved_until:
                a.shelved_until = None                            # automatic un-shelve
        for key in [k for k, a in self.alerts.items() if not a.active and a.acknowledged]:
            del self.alerts[key]                                  # cleared and acknowledged: done
        return self.list()

    def list(self) -> List[Alert]:
        return sorted(self.alerts.values(), key=lambda a: (-ORDER[a.level], a.first_s))

    def acknowledge(self, alert_id: Optional[str] = None) -> List[str]:
        ids = [alert_id] if alert_id else list(self.alerts)
        for i in ids:
            if i not in self.alerts:
                raise KeyError(alert_id)
            self.alerts[i].acknowledged = True
        return ids

    def shelve(self, alert_id: str, t: float, duration_s: float) -> Alert:
        a = self.alerts[alert_id]
        if a.level == "NO-GO":
            raise ValueError("a NO-GO (warning) alert cannot be shelved")
        a.shelved_until = t + min(max(duration_s, 0.0), self.max_shelve_s)
        return a

    def master(self) -> Dict[str, bool]:
        live = [a for a in self.alerts.values() if a.active and not a.acknowledged and a.shelved_until is None]
        return {"warning": any(a.level == "NO-GO" for a in live), "caution": any(a.level == "CAUTION" for a in live)}
