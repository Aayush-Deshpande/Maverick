"""Operational History and Severity Accumulator per Tail (R11, B4.6).

Tracks:
1. Cumulative Engine Flight Hours (EFH).
2. Thermal cycle counting (cold starts to operating temp).
3. Overtemp and overspeed exposure durations.
4. Maintenance and component replacement history.
5. Tail severity factor calculation feeding Empirical Bayes priors.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MaintenanceRecord:
    event_id: str
    flight_hours: float
    timestamp_utc: str
    action_type: str        # INSPECTION | COMPONENT_REPLACED | OVERHAUL
    affected_subsystem: str  # CYLINDER | TURBO | OIL | FUEL
    description: str


@dataclass
class TailHistoryState:
    tail_id: str
    engine_profile: str
    cumulative_efh: float = 0.0
    thermal_cycles: int = 0
    total_fuel_consumed_kg: float = 0.0
    overtemp_seconds: float = 0.0
    overspeed_seconds: float = 0.0
    component_flight_hours: Dict[str, float] = field(default_factory=lambda: {
        "cylinders": 0.0,
        "injectors": 0.0,
        "oil_system": 0.0,
        "turbocharger": 0.0,
    })
    maintenance_log: List[MaintenanceRecord] = field(default_factory=list)

    @property
    def operational_severity_index(self) -> float:
        """Severity factor (1.0 = nominal, >1.0 = harsh operating environment like Leh dust/altitude)."""
        if self.cumulative_efh < 1.0:
            return 1.0
        # Overtemp penalty + cycle frequency penalty
        cycles_per_100h = (self.thermal_cycles / self.cumulative_efh) * 100.0
        cycle_factor = max(1.0, cycles_per_100h / 50.0)
        overtemp_factor = 1.0 + (self.overtemp_seconds / (self.cumulative_efh * 3600.0)) * 50.0
        return float(min(2.5, cycle_factor * overtemp_factor))


class OperationalHistoryTracker:
    """Maintains persistent operational history per UAV tail."""

    def __init__(self, tail_id: str, engine_profile: str) -> None:
        self.state = TailHistoryState(tail_id=tail_id, engine_profile=engine_profile)

    def log_sortie(
        self,
        duration_hours: float,
        fuel_used_kg: float,
        overtemp_sec: float = 0.0,
        overspeed_sec: float = 0.0,
        is_cold_start: bool = True,
    ) -> None:
        """Log completed flight sortie."""
        self.state.cumulative_efh += duration_hours
        self.state.total_fuel_consumed_kg += fuel_used_kg
        self.state.overtemp_seconds += overtemp_sec
        self.state.overspeed_seconds += overspeed_sec
        if is_cold_start:
            self.state.thermal_cycles += 1

        for comp in self.state.component_flight_hours:
            self.state.component_flight_hours[comp] += duration_hours

    def log_maintenance_event(
        self,
        event_id: str,
        action_type: str,
        affected_subsystem: str,
        description: str,
        timestamp_utc: str = "",
    ) -> None:
        """Log a maintenance action and reset subsystem running hours if replaced/overhauled."""
        rec = MaintenanceRecord(
            event_id=event_id,
            flight_hours=self.state.cumulative_efh,
            timestamp_utc=timestamp_utc,
            action_type=action_type,
            affected_subsystem=affected_subsystem,
            description=description,
        )
        self.state.maintenance_log.append(rec)

        if action_type in ("COMPONENT_REPLACED", "OVERHAUL"):
            subsys_lower = affected_subsystem.lower()
            if subsys_lower in self.state.component_flight_hours:
                self.state.component_flight_hours[subsys_lower] = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self.state)
