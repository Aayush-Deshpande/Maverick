"""Fleet Economics, Mission Reliability, and Financial Impact Model (V7, INN-06).

Evaluates life-cycle cost savings and fleet availability metrics comparing:
1. Reactive Maintenance (fix-on-failure, high in-flight aborts & catastrophic teardowns).
2. Fixed-Interval Periodic Maintenance (fixed 100-hr inspections and premature TBO scrap).
3. ANUMAAN CBM Digital Twin (predictive RUL, opportunistic bundling, zero secondary damage).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class CostModelParameters:
    labor_rate_usd_per_hour: float = 85.0
    aog_flight_abort_penalty_usd: float = 12500.0   # Unscheduled sortie cancellation & recovery cost
    catastrophic_secondary_damage_usd: float = 38000.0  # Seized piston / destroyed turbo casing
    fuel_cost_usd_per_kg: float = 1.65             # Jet-A1 / Avgas average cost
    scheduled_inspection_cost_usd: float = 1200.0  # Base hangar fee + consumables per check


@dataclass
class FleetEconomicMetrics:
    maintenance_strategy: str
    fleet_flight_hours: float
    fleet_availability_pct: float
    total_maintenance_cost_usd: float
    cost_per_flight_hour_usd: float
    in_flight_shutdown_count: int
    unscheduled_groundings_count: int
    wasted_component_life_pct: float
    cost_savings_vs_reactive_pct: float


class FleetEconomicsModel:
    """Calculates fleet lifecycle economics and mission reliability impact."""

    def __init__(self, params: CostModelParameters | None = None) -> None:
        self.params = params or CostModelParameters()

    def evaluate_fleet_scenario(
        self,
        strategy: str,
        fleet_size: int,
        days: int,
        daily_flight_hours_per_tail: float,
        failures_in_flight: int,
        unscheduled_groundings: int,
        scheduled_inspections: int,
        total_maintenance_labor_hours: float,
        spares_consumed_cost_usd: float,
        excess_fuel_consumed_kg: float = 0.0,
        wasted_component_life_pct: float = 0.0,
    ) -> FleetEconomicMetrics:
        total_efh = fleet_size * days * daily_flight_hours_per_tail

        # Labor costs
        labor_cost = total_maintenance_labor_hours * self.params.labor_rate_usd_per_hour

        # Hangar / inspection base fees
        inspection_cost = scheduled_inspections * self.params.scheduled_inspection_cost_usd

        # Secondary damage & AOG penalties
        damage_cost = failures_in_flight * self.params.catastrophic_secondary_damage_usd
        aog_penalty = unscheduled_groundings * self.params.aog_flight_abort_penalty_usd

        # Fuel degradation penalty
        fuel_cost = excess_fuel_consumed_kg * self.params.fuel_cost_usd_per_kg

        total_cost = (
            labor_cost
            + inspection_cost
            + spares_consumed_cost_usd
            + damage_cost
            + aog_penalty
            + fuel_cost
        )

        cost_per_efh = total_cost / max(1.0, total_efh)

        # Availability estimate
        down_hours = total_maintenance_labor_hours + (unscheduled_groundings * 48.0) + (failures_in_flight * 120.0)
        total_possible_fleet_hours = fleet_size * days * 24.0
        availability = max(0.0, min(100.0, (1.0 - down_hours / total_possible_fleet_hours) * 100.0))

        return FleetEconomicMetrics(
            maintenance_strategy=strategy,
            fleet_flight_hours=total_efh,
            fleet_availability_pct=round(availability, 2),
            total_maintenance_cost_usd=round(total_cost, 2),
            cost_per_flight_hour_usd=round(cost_per_efh, 2),
            in_flight_shutdown_count=failures_in_flight,
            unscheduled_groundings_count=unscheduled_groundings,
            wasted_component_life_pct=round(wasted_component_life_pct, 2),
            cost_savings_vs_reactive_pct=0.0,  # Computed in comparative sweep
        )
