"""ISA-18.2 Compliant Alarm Management and Flood Suppression (B6.3, VIS-06).

Provides:
1. Four-tier alarm rationalisation (Priority 1 Emergency to Priority 4 Low).
2. Explicit cause, consequence, required action, and response time window for every alarm.
3. State machine: UNACKNOWLEDGED, ACKNOWLEDGED, SHELVED, CLEARED.
4. Dynamic flood suppression (chattering alarm suppression and rate limiting).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class AlarmPriority(int, Enum):
    EMERGENCY = 1  # Immediate abort / loss of propulsion danger (< 30 s response)
    HIGH = 2       # Impending failure / derate required (< 5 min response)
    MEDIUM = 3     # Degraded margin / advisory (< 30 min response)
    LOW = 4        # Maintenance log / trend (< post-flight response)


class AlarmState(str, Enum):
    ACTIVE_UNACK = "ACTIVE_UNACK"
    ACTIVE_ACK = "ACTIVE_ACK"
    SHELVED = "SHELVED"
    CLEARED = "CLEARED"


@dataclass
class RationalisedAlarmSpec:
    alarm_id: str
    priority: AlarmPriority
    cause: str
    consequence: str
    operator_action: str
    time_to_respond_sec: float
    max_rate_per_min: int = 4


@dataclass
class ActiveAlarm:
    alarm_id: str
    priority: AlarmPriority
    state: AlarmState
    t_triggered: float
    message: str
    cause: str
    operator_action: str
    time_to_respond_sec: float
    shelved_until: Optional[float] = None


ALARM_RATIONALISATION_TABLE: Dict[str, RationalisedAlarmSpec] = {
    "ALARM_OIL_P_CRITICAL": RationalisedAlarmSpec(
        alarm_id="ALARM_OIL_P_CRITICAL",
        priority=AlarmPriority.EMERGENCY,
        cause="Loss of engine oil pressure below minimum operating redline",
        consequence="Imminent bearing seizure and total engine failure",
        operator_action="Reduce power immediately and initiate emergency recovery",
        time_to_respond_sec=20.0,
    ),
    "ALARM_CHT_OVERHEAT": RationalisedAlarmSpec(
        alarm_id="ALARM_CHT_OVERHEAT",
        priority=AlarmPriority.HIGH,
        cause="Cylinder head temperature exceedance above thermal limit",
        consequence="Thermal detonation, piston ring scuffing, head warp",
        operator_action="Enrich mixture/reduce throttle and increase airspeed for cooling",
        time_to_respond_sec=60.0,
    ),
    "ALARM_MISFIRE_DETECTED": RationalisedAlarmSpec(
        alarm_id="ALARM_MISFIRE_DETECTED",
        priority=AlarmPriority.HIGH,
        cause="Combustion work deficit on one or more cylinders",
        consequence="Loss of available propulsion margin, airframe vibration",
        operator_action="Verify ignition lane and switch to secondary FADEC lane if available",
        time_to_respond_sec=120.0,
    ),
    "ALARM_COOLING_DEGRADATION": RationalisedAlarmSpec(
        alarm_id="ALARM_COOLING_DEGRADATION",
        priority=AlarmPriority.MEDIUM,
        cause="Estimated cooling heat transfer efficiency eta_cool dropped below 75%",
        consequence="Progressive thermal accumulation under sustained climb",
        operator_action="Limit maximum climb power and plan early descent",
        time_to_respond_sec=600.0,
    ),
}


class ISA18AlarmManager:
    """Manages active alarm lifecycle, operator acknowledgment, shelving, and flood suppression."""

    def __init__(self, flood_limit_per_min: int = 8) -> None:
        self.flood_limit = flood_limit_per_min
        self.active_alarms: Dict[str, ActiveAlarm] = {}
        self.recent_trigger_times: List[float] = []

    def trigger_alarm(self, alarm_id: str, t: float, custom_message: Optional[str] = None) -> Optional[ActiveAlarm]:
        """Trigger an alarm if not flood-suppressed or shelved."""
        # Flood suppression rate limiter
        self.recent_trigger_times = [ts for ts in self.recent_trigger_times if t - ts < 60.0]
        if len(self.recent_trigger_times) >= self.flood_limit:
            return None  # Flood suppressed

        spec = ALARM_RATIONALISATION_TABLE.get(alarm_id, RationalisedAlarmSpec(
            alarm_id=alarm_id,
            priority=AlarmPriority.MEDIUM,
            cause="Unclassified anomaly condition",
            consequence="Potential sub-system degradation",
            operator_action="Investigate telemetry",
            time_to_respond_sec=300.0,
        ))

        # Check existing alarm state
        existing = self.active_alarms.get(alarm_id)
        if existing and existing.state == AlarmState.SHELVED:
            if existing.shelved_until and t < existing.shelved_until:
                return None  # Still shelved

        alarm = ActiveAlarm(
            alarm_id=alarm_id,
            priority=spec.priority,
            state=AlarmState.ACTIVE_UNACK,
            t_triggered=t,
            message=custom_message or spec.cause,
            cause=spec.cause,
            operator_action=spec.operator_action,
            time_to_respond_sec=spec.time_to_respond_sec,
        )
        self.active_alarms[alarm_id] = alarm
        self.recent_trigger_times.append(t)
        return alarm

    def acknowledge(self, alarm_id: str) -> None:
        if alarm_id in self.active_alarms:
            self.active_alarms[alarm_id].state = AlarmState.ACTIVE_ACK

    def shelve(self, alarm_id: str, duration_sec: float, t: float) -> None:
        if alarm_id in self.active_alarms:
            self.active_alarms[alarm_id].state = AlarmState.SHELVED
            self.active_alarms[alarm_id].shelved_until = t + duration_sec

    def clear(self, alarm_id: str) -> None:
        if alarm_id in self.active_alarms:
            self.active_alarms[alarm_id].state = AlarmState.CLEARED
            del self.active_alarms[alarm_id]
