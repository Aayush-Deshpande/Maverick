"""E24: 12-Tail 3-Base Discrete Event Simulation (DES) Fleet Reliability & Economics (B10.1, B10.2, V7, R9, R10, R11).

Evaluates:
1. 180-day operational deployment across 3 bases (Suratgarh, Bhatinda, Leh high-altitude).
2. Comparison of 3 maintenance policies:
   - REACTIVE (run-to-failure, in-flight shutdowns, high AOG).
   - PERIODIC_100HR (fixed 100-hr intervals, premature component scrap).
   - ANUMAAN_CBM (predictive RUL, opportunistic bundling, zero secondary damage).
3. Availability, reliability, mission success rate, and life-cycle cost savings.
"""

from __future__ import annotations

import json
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from backend.physics.engine_config import load_engine_config
from backend.performance.maps import PerformanceMaps
from backend.mission.profiles import (
    create_standard_male_surveillance_mission,
    create_high_altitude_leh_mission,
)
from backend.maintenance.work_package import WorkPackageGenerator
from backend.diagnose.bn import Hypothesis
from backend.prognose.rul import RULEstimate
from backend.economics.impact import FleetEconomicsModel, CostModelParameters
from backend.twin.history import OperationalHistoryTracker


@dataclass
class SimulatedTail:
    tail_id: str
    base_id: str
    engine_profile: str
    tracker: OperationalHistoryTracker
    is_grounded: bool = False
    grounded_remaining_hours: float = 0.0
    # Component health state (0.0 = nominal, 1.0 = failed)
    wear_injector: float = 0.0
    wear_cooling: float = 0.0
    wear_oil: float = 0.0
    wear_turbo: float = 0.0


def run_e24_fleet_simulation() -> dict:
    random.seed(42)
    np.random.seed(42)

    bases = {
        "BASE_SURATGARH": {"elev_m": 150.0, "severity_mult": 1.0, "tails": ["UAV-S01", "UAV-S02", "UAV-S03", "UAV-S04"]},
        "BASE_BHATINDA": {"elev_m": 200.0, "severity_mult": 1.05, "tails": ["UAV-B01", "UAV-B02", "UAV-B03", "UAV-B04"]},
        "BASE_LEH": {"elev_m": 3300.0, "severity_mult": 1.45, "tails": ["UAV-L01", "UAV-L02", "UAV-L03", "UAV-L04"]},
    }

    strategies = ["REACTIVE", "PERIODIC_100HR", "ANUMAAN_CBM"]
    strategy_results = {}
    econ_model = FleetEconomicsModel()

    sim_days = 180
    daily_sorties_per_tail = 1
    sortie_duration_hours = 4.5

    for strat in strategies:
        # Initialize 12 tails
        tails: Dict[str, SimulatedTail] = {}
        for base_name, base_info in bases.items():
            for tid in base_info["tails"]:
                profile_name = "austro_ae300" if "LEH" in base_name else "rotax_915is"
                tracker = OperationalHistoryTracker(tid, profile_name)
                tails[tid] = SimulatedTail(
                    tail_id=tid,
                    base_id=base_name,
                    engine_profile=profile_name,
                    tracker=tracker,
                )

        in_flight_shutdowns = 0
        unscheduled_groundings = 0
        scheduled_inspections = 0
        total_labor_hours = 0.0
        spares_cost_usd = 0.0
        wasted_life_accum = []

        wp_gen = WorkPackageGenerator()

        for day in range(sim_days):
            for tid, tail in tails.items():
                base_info = bases[tail.base_id]
                sev = base_info["severity_mult"]

                # If grounded, tick down repair time
                if tail.is_grounded:
                    tail.grounded_remaining_hours -= 24.0
                    if tail.grounded_remaining_hours <= 0.0:
                        tail.is_grounded = False
                    continue

                # Run daily sortie
                tail.tracker.log_sortie(
                    duration_hours=sortie_duration_hours,
                    fuel_used_kg=sortie_duration_hours * 18.0,
                    overtemp_sec=5.0 * sev,
                    is_cold_start=True,
                )

                # Stochastic degradation accumulation per hour
                # Nominal lifespan ~800-1200 flight hours
                tail.wear_injector += (sortie_duration_hours / 900.0) * sev * random.uniform(0.7, 1.4)
                tail.wear_cooling += (sortie_duration_hours / 1100.0) * sev * random.uniform(0.7, 1.3)
                tail.wear_oil += (sortie_duration_hours / 1000.0) * sev * random.uniform(0.8, 1.2)
                tail.wear_turbo += (sortie_duration_hours / 850.0) * sev * random.uniform(0.8, 1.5)

                # --- Policy 1: REACTIVE ---
                if strat == "REACTIVE":
                    if any(w >= 1.0 for w in [tail.wear_injector, tail.wear_cooling, tail.wear_oil, tail.wear_turbo]):
                        # In-flight shutdown
                        in_flight_shutdowns += 1
                        unscheduled_groundings += 1
                        tail.is_grounded = True
                        tail.grounded_remaining_hours = 72.0  # 3 days AOG repair
                        total_labor_hours += 16.0
                        spares_cost_usd += 3200.0
                        # Reset wear
                        tail.wear_injector = 0.0
                        tail.wear_cooling = 0.0
                        tail.wear_oil = 0.0
                        tail.wear_turbo = 0.0

                # --- Policy 2: PERIODIC 100-HR ---
                elif strat == "PERIODIC_100HR":
                    # Check 100-hr boundary
                    if tail.tracker.state.cumulative_efh % 100.0 < sortie_duration_hours:
                        scheduled_inspections += 1
                        total_labor_hours += 8.0
                        spares_cost_usd += 450.0
                        tail.is_grounded = True
                        tail.grounded_remaining_hours = 24.0

                        # Routine replacement of components at 500h even if still healthy (wasted life)
                        if tail.tracker.state.cumulative_efh % 500.0 < sortie_duration_hours:
                            wasted_life_accum.append(max(0.0, 1.0 - max(tail.wear_injector, tail.wear_turbo)))
                            total_labor_hours += 12.0
                            spares_cost_usd += 1850.0
                            tail.wear_injector = 0.0
                            tail.wear_turbo = 0.0

                    # Unscheduled failure if wear reached 1.0 between 100h checks
                    if any(w >= 1.0 for w in [tail.wear_injector, tail.wear_cooling, tail.wear_oil, tail.wear_turbo]):
                        in_flight_shutdowns += 1
                        unscheduled_groundings += 1
                        tail.is_grounded = True
                        tail.grounded_remaining_hours = 48.0
                        total_labor_hours += 14.0
                        spares_cost_usd += 2800.0
                        tail.wear_injector = 0.0
                        tail.wear_cooling = 0.0
                        tail.wear_oil = 0.0
                        tail.wear_turbo = 0.0

                # --- Policy 3: ANUMAAN CBM DIGITAL TWIN ---
                elif strat == "ANUMAAN_CBM":
                    # Estimate RUL from degradation state
                    min_rul_hrs = min(
                        (1.0 - tail.wear_injector) * 900.0 / sev,
                        (1.0 - tail.wear_cooling) * 1100.0 / sev,
                        (1.0 - tail.wear_oil) * 1000.0 / sev,
                        (1.0 - tail.wear_turbo) * 850.0 / sev,
                    )
                    ruls = {
                        "injector": RULEstimate("injector", "cyl_1", max(1.0, (1.0 - tail.wear_injector) * 900.0 / sev), 0, 0),
                        "cooling": RULEstimate("cooling", "sys", max(1.0, (1.0 - tail.wear_cooling) * 1100.0 / sev), 0, 0),
                        "oil": RULEstimate("oil", "sys", max(1.0, (1.0 - tail.wear_oil) * 1000.0 / sev), 0, 0),
                        "turbo": RULEstimate("turbo", "chra", max(1.0, (1.0 - tail.wear_turbo) * 850.0 / sev), 0, 0),
                    }

                    # Trigger predictive work package when RUL < 20 hours
                    if min_rul_hrs <= 20.0:
                        hyps = [Hypothesis("INJECTOR_COKING", "cyl_1", 0.85, "AG_INJ")] if tail.wear_injector > 0.90 else []
                        wp = wp_gen.generate_work_package(
                            tail_id=tid,
                            engine_profile=tail.engine_profile,
                            flight_hours=tail.tracker.state.cumulative_efh,
                            hypotheses=hyps,
                            ruls=ruls,
                            horizon_hours=25.0,
                        )
                        scheduled_inspections += 1
                        total_labor_hours += wp.total_labor_hours
                        spares_cost_usd += wp.total_spares_cost_usd
                        tail.is_grounded = True
                        tail.grounded_remaining_hours = 12.0  # Swift planned ground turnaround (no AOG emergency delay)

                        # Reset components serviced
                        tail.wear_injector = 0.0 if tail.wear_injector > 0.80 else tail.wear_injector
                        tail.wear_turbo = 0.0 if tail.wear_turbo > 0.80 else tail.wear_turbo
                        tail.wear_cooling = 0.0 if tail.wear_cooling > 0.80 else tail.wear_cooling
                        tail.wear_oil = 0.0 if tail.wear_oil > 0.80 else tail.wear_oil

        wasted_pct = float(np.mean(wasted_life_accum) * 100.0) if wasted_life_accum else 0.0
        metrics = econ_model.evaluate_fleet_scenario(
            strategy=strat,
            fleet_size=12,
            days=sim_days,
            daily_flight_hours_per_tail=sortie_duration_hours,
            failures_in_flight=in_flight_shutdowns,
            unscheduled_groundings=unscheduled_groundings,
            scheduled_inspections=scheduled_inspections,
            total_maintenance_labor_hours=total_labor_hours,
            spares_consumed_cost_usd=spares_cost_usd,
            wasted_component_life_pct=wasted_pct,
        )
        strategy_results[strat] = metrics

    # Compute comparative cost savings vs reactive baseline
    base_cost = strategy_results["REACTIVE"].total_maintenance_cost_usd
    for strat, res in strategy_results.items():
        savings = ((base_cost - res.total_maintenance_cost_usd) / base_cost) * 100.0
        res.cost_savings_vs_reactive_pct = round(max(0.0, savings), 2)

    output = {
        "metadata": {
            "experiment": "E24_fleet_des",
            "evidence_class": "SIMULATION",
            "seed": 42,
            "fleet_size": 12,
            "bases": list(bases.keys()),
            "simulation_days": sim_days,
            "total_fleet_flight_hours": sim_days * 12 * sortie_duration_hours,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "results": {
            strat: {
                "fleet_availability_pct": res.fleet_availability_pct,
                "in_flight_shutdowns": res.in_flight_shutdown_count,
                "unscheduled_groundings": res.unscheduled_groundings_count,
                "total_maintenance_cost_usd": res.total_maintenance_cost_usd,
                "cost_per_flight_hour_usd": res.cost_per_flight_hour_usd,
                "wasted_component_life_pct": res.wasted_component_life_pct,
                "cost_savings_vs_reactive_pct": res.cost_savings_vs_reactive_pct,
            }
            for strat, res in strategy_results.items()
        },
    }

    out_path = Path("docs/evaluation/E24_fleet_des.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"E24 evaluation complete -> {out_path}")
    for strat, data in output["results"].items():
        print(f"[{strat}] Avail: {data['fleet_availability_pct']}%, IFSD: {data['in_flight_shutdowns']}, Cost/EFH: ${data['cost_per_flight_hour_usd']}, Savings: {data['cost_savings_vs_reactive_pct']}%")

    return output


if __name__ == "__main__":
    run_e24_fleet_simulation()
