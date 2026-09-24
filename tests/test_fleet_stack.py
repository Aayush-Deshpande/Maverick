"""Tests for FLEET Stack (B10.1, B10.2, V7, R9, R10, R11).

Verifies:
1. Performance maps and atmospheric altitude scaling across engine profiles.
2. Multi-phase mission profile timeline sampling.
3. Automated ATA maintenance work package generation and opportunistic bundling.
4. Fleet economics and life-cycle cost model.
5. Tail operational history, severity index, and maintenance logging.
"""

from __future__ import annotations

import pytest

from backend.physics.engine_config import load_engine_config
from backend.performance.maps import PerformanceMaps
from backend.mission.profiles import (
    MissionPhase,
    create_standard_male_surveillance_mission,
    create_high_altitude_leh_mission,
)
from backend.maintenance.work_package import WorkPackageGenerator
from backend.diagnose.bn import Hypothesis
from backend.prognose.rul import RULEstimate
from backend.economics.impact import FleetEconomicsModel, CostModelParameters
from backend.twin.history import OperationalHistoryTracker


def test_performance_maps_and_atmosphere():
    cfg_rotax = load_engine_config("rotax_915is")
    perf = PerformanceMaps(cfg_rotax)

    # 1. ISA Atmosphere
    atm_sl = perf.get_isa_atmosphere(0.0)
    assert pytest.approx(atm_sl.p_amb_bar, rel=1e-3) == 1.01325
    assert pytest.approx(atm_sl.density_kg_m3, rel=1e-2) == 1.225

    atm_8k = perf.get_isa_atmosphere(8000.0)
    assert atm_8k.p_amb_bar < 0.40
    assert atm_8k.t_amb_k < 240.0

    # 2. BSFC
    bsfc_mid = perf.calculate_bsfc(rpm=5500.0, power_kw=85.0)
    assert 240.0 < bsfc_mid < 380.0

    # 3. Turbo state at altitude
    t_state = perf.calculate_turbo_state(engine_power_kw=85.0, altitude_m=5000.0)
    assert t_state["compressor_pr"] > 1.2
    assert t_state["is_choked"] is False

    # 4. Max power lapse
    p_sl = perf.max_available_power_kw(altitude_m=0.0)
    p_high = perf.max_available_power_kw(altitude_m=10000.0)
    assert p_high < p_sl


def test_mission_profiles():
    mission = create_standard_male_surveillance_mission(loiter_hours=6.0)
    assert mission.total_duration_sec > 6.0 * 3600.0

    # Sample at takeoff (t = 320s)
    phase, alt, throttle, tas, _ = mission.sample_at(320.0)
    assert phase == MissionPhase.TAKEOFF
    assert throttle == 100.0

    # Sample in loiter
    phase_l, alt_l, throttle_l, _, _ = mission.sample_at(10000.0)
    assert phase_l == MissionPhase.LOITER_RECON
    assert alt_l == 6000.0

    # Leh profile base altitude
    leh_mission = create_high_altitude_leh_mission()
    assert leh_mission.base_elevation_m == 3300.0


def test_work_package_generator():
    gen = WorkPackageGenerator()

    # Diagnostic hypothesis: INJECTOR_COKING (P=0.82)
    hyps = [
        Hypothesis(mode_id="INJECTOR_COKING", location="cyl_1", probability=0.82, ambiguity_group_id="AG_INJ"),
        Hypothesis(mode_id="NOMINAL", location=None, probability=0.18, ambiguity_group_id="AG_NOM"),
    ]
    # RUL prediction: turbo bearing at 18.0 hrs
    ruls = {
        "turbocharger": RULEstimate(
            component="turbocharger",
            location="turbo_1",
            rul_hours_median=18.0,
            rul_hours_lower=12.0,
            rul_hours_upper=24.0,
            nominal_coverage=0.90,
            physics_rul_hours=17.5,
            data_rul_hours=18.5,
        ),
    }

    # At 92.0 flight hours (due for 100hr inspection soon -> triggers opportunistic bundle)
    wp = gen.generate_work_package(
        tail_id="UAV-01",
        engine_profile="rotax_915is",
        flight_hours=92.0,
        hypotheses=hyps,
        ruls=ruls,
        horizon_hours=25.0,
    )

    assert wp.criticality == "AOG_CRITICAL"
    assert len(wp.tasks) >= 3  # Injector cleaning + Turbo inspection + 100hr opportunistic bundle
    assert any("73-10" in t.ata_chapter for t in wp.tasks)
    assert any("81-10" in t.ata_chapter for t in wp.tasks)
    assert any(t.criticality == "OPPORTUNISTIC" for t in wp.tasks)
    assert wp.total_labor_hours > 5.0
    assert wp.total_spares_cost_usd > 100.0


def test_fleet_economics_model():
    econ = FleetEconomicsModel()

    # Reactive scenario (5 in-flight aborts, 12 unscheduled groundings)
    res_reactive = econ.evaluate_fleet_scenario(
        strategy="REACTIVE",
        fleet_size=12,
        days=180,
        daily_flight_hours_per_tail=4.0,
        failures_in_flight=5,
        unscheduled_groundings=12,
        scheduled_inspections=0,
        total_maintenance_labor_hours=1200.0,
        spares_consumed_cost_usd=85000.0,
    )

    # ANUMAAN CBM (0 in-flight aborts, 2 unscheduled groundings, 40 scheduled/predictive visits)
    res_cbm = econ.evaluate_fleet_scenario(
        strategy="ANUMAAN_CBM",
        fleet_size=12,
        days=180,
        daily_flight_hours_per_tail=4.0,
        failures_in_flight=0,
        unscheduled_groundings=2,
        scheduled_inspections=40,
        total_maintenance_labor_hours=750.0,
        spares_consumed_cost_usd=42000.0,
    )

    assert res_cbm.total_maintenance_cost_usd < res_reactive.total_maintenance_cost_usd
    assert res_cbm.fleet_availability_pct > res_reactive.fleet_availability_pct
    assert res_cbm.in_flight_shutdown_count == 0


def test_operational_history_tracker():
    tracker = OperationalHistoryTracker("UAV-04", "austro_ae300")

    tracker.log_sortie(duration_hours=6.5, fuel_used_kg=78.0, overtemp_sec=120.0, is_cold_start=True)
    tracker.log_sortie(duration_hours=5.0, fuel_used_kg=60.0, overtemp_sec=0.0, is_cold_start=True)

    assert tracker.state.cumulative_efh == 11.5
    assert tracker.state.thermal_cycles == 2
    assert tracker.state.component_flight_hours["turbocharger"] == 11.5
    assert tracker.state.operational_severity_index >= 1.0

    # Overhaul turbocharger
    tracker.log_maintenance_event(
        event_id="EVT-001",
        action_type="COMPONENT_REPLACED",
        affected_subsystem="TURBOCHARGER",
        description="Replaced CHRA cartridge due to wear",
    )
    assert tracker.state.component_flight_hours["turbocharger"] == 0.0
    assert tracker.state.component_flight_hours["cylinders"] == 11.5
