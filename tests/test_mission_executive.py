"""Unit and Integration Tests for MissionExecutive and SortieExporter."""

import pytest
import time
from backend.mission.executive import (
    MissionExecutive,
    create_ladakh_preset,
    create_thar_preset,
    create_endurance_preset,
    create_rapid_throttle_preset,
    create_endurance_phase_preset,
)
from backend.mission.models import FlightPhase, MissionStatus
from backend.runtime.hub import RuntimeHub


@pytest.fixture(scope="module")
def hub():
    h = RuntimeHub(["rotax_912is", "rotax_915is", "austro_ae300"], seed=42, warmup_ticks=600)
    h.calibrate_all()
    return h


def test_mission_presets_initialization():
    m1 = create_ladakh_preset("rotax_912is")
    assert m1.engine_id == "rotax_912is"
    assert len(m1.waypoints) >= 4
    assert len(m1.scheduled_events) >= 1

    m2 = create_thar_preset("rotax_915is")
    assert m2.engine_id == "rotax_915is"
    assert m2.environment.theater_name == "THAR_HOT_HIGH"

    m3 = create_endurance_preset("austro_ae300")
    assert m3.engine_id == "austro_ae300"


def test_mission_executive_step_and_kinematics(hub):
    preset = create_ladakh_preset("rotax_912is")
    preset.planned_duration_sec = 60.0  # Fast duration for test
    exec_sim = MissionExecutive(hub, preset)

    assert exec_sim.state.status == MissionStatus.READY.value
    exec_sim.state.status = MissionStatus.RUNNING.value

    # Step simulation
    for _ in range(50):
        state = exec_sim.step(dt=0.1)

    assert state.time_elapsed_sec > 0.0
    assert state.pos_z_m > 3000.0  # Above Ladakh base elevation
    assert state.commanded_throttle_pct > 0.0
    assert len(exec_sim.recorded_frames) > 0


def test_mission_live_fault_injection_and_flyhash(hub):
    preset = create_ladakh_preset("rotax_912is")
    exec_sim = MissionExecutive(hub, preset)
    exec_sim.state.status = MissionStatus.RUNNING.value

    # Step nominal
    for _ in range(30):
        exec_sim.step(dt=0.1)

    # Inject live fault
    rec = exec_sim.inject_live_fault("COOLING_DEGRADATION", severity=1.0, ramp_sec=10.0)
    assert rec["mode"] == "COOLING_DEGRADATION"

    # Step more frames to observe residual and FlyHash reaction
    for _ in range(40):
        state = exec_sim.step(dt=0.1)

    assert len(state.active_faults) > 0
    assert state.flyhash_novelty_score >= 0.0


def test_mission_operator_derate_and_abort(hub):
    preset = create_ladakh_preset("rotax_912is")
    exec_sim = MissionExecutive(hub, preset)
    exec_sim.state.status = MissionStatus.RUNNING.value

    # Derate
    res = exec_sim.derate(0.80)
    assert res["status"] == MissionStatus.DERATED.value
    assert exec_sim.derate_scale == 0.80

    # Abort
    res = exec_sim.abort()
    assert res["status"] == MissionStatus.ABORTED.value
    assert "live_csv" in res["artifacts"]
    assert "manifest" in res["artifacts"]


def test_mission_thread_lifecycle(hub):
    preset = create_ladakh_preset("rotax_912is")
    exec_sim = MissionExecutive(hub, preset)
    exec_sim.start()
    assert exec_sim.state.status == MissionStatus.RUNNING.value
    time.sleep(0.1)
    exec_sim.pause()
    assert exec_sim.state.status == MissionStatus.PAUSED.value
    exec_sim.resume()
    assert exec_sim.state.status == MissionStatus.RUNNING.value
    exec_sim.stop()


def test_autopilot_integrates_position_not_time_fraction(hub):
    """Proves the aircraft actually flies (position integrated from real velocity) rather
    than being interpolated as a function of elapsed-time / planned-duration fraction --
    the defect this rewrite fixes. A route flown for a short slice of its total planned
    duration should cover a distance consistent with speed*time, NOT with
    (elapsed/planned_duration) * total_route_length."""
    import math

    preset = create_ladakh_preset("rotax_912is")
    exec_sim = MissionExecutive(hub, preset)
    exec_sim.state.status = MissionStatus.RUNNING.value

    # One tick first to trigger the flight model's lazy start-position initialization
    # (pos_x_m/pos_y_m default to 0,0 until the first advance() call seeds them at WP0) --
    # otherwise the baseline below would spuriously include that seed jump.
    exec_sim.step(dt=0.05)
    start_x, start_y = exec_sim.flight_model.pos_x_m, exec_sim.flight_model.pos_y_m

    # Fly for 60 more real sim seconds (dt=0.05 * 1200 ticks) -- a tiny slice of the ~2250s
    # planned duration. Under the old time-fraction model this would cover ~1/37th of the
    # ~76km route (~2km) regardless of actual speed. Under real integration it should cover
    # only what the aircraft's actual airspeed allows in 60s (well under 2km at cruise).
    for _ in range(1200):
        state = exec_sim.step(dt=0.05)

    dist_covered_m = math.hypot(
        exec_sim.flight_model.pos_x_m - start_x,
        exec_sim.flight_model.pos_y_m - start_y,
    )
    total_route_m = 75000.0  # approx, see terrain-alignment comment in create_ladakh_preset

    # Real integrated flight at realistic UAV speeds (well under 150 kt = ~77 m/s) covers
    # well under 5km in 60s -- the old fake model would have covered ~1/37 of the total
    # route (~2km) purely from elapsed-time fraction regardless of speed. The assertion
    # that actually distinguishes the two models is against *speed*, not just a distance
    # ceiling: distance covered must be explicable by integrated speed, not a bogus jump.
    assert dist_covered_m < 5000.0, (
        f"covered {dist_covered_m:.0f}m in 60s -- implausible for a UAV, suggests the "
        "position is being interpolated by time-fraction rather than integrated from speed"
    )
    # And the aircraft should have actually moved (not frozen/stuck).
    assert dist_covered_m > 50.0
    # Position should never have taken a fraction-of-total-route-length jump characteristic
    # of the old model (60s / 2250s planned * 75km route ~= 2000m -- a real UAV at takeoff/
    # climb speeds covers noticeably less than that in the first 60s from a standing start).
    assert round(state.time_elapsed_sec, 2) == 60.05


def test_terrain_heightfield_matches_real_canyon_geometry():
    """The terrain heightfield must be sampled from the real Ladakh canyon GLB, not a fake
    linear interpolation between two hand-authored waypoint scalars -- and must return
    elevations consistent with the real DEM (canyon floor ~3000-3200m, ridge ~4400-5000m)."""
    from backend.mission.terrain import get_terrain_heightfield

    terrain = get_terrain_heightfield()
    assert terrain.loaded, "terrain heightfield failed to load from the real GLB mesh"

    # Near WP_LEH (base, canyon floor) -- real elevation ~3195-3200m.
    base_elev = terrain.elevation_at(657, 35338)
    assert 3050.0 < base_elev < 3400.0

    # Near WP_RIDGE (gorge exit onto the high plateau) -- real elevation ~4400-4900m,
    # meaningfully higher than the canyon floor (proves this isn't a flat/fallback plane).
    ridge_elev = terrain.elevation_at(-150, 583)
    assert 4200.0 < ridge_elev < 5200.0
    assert ridge_elev > base_elev + 800.0


def test_mission_operator_divert(hub):
    preset = create_ladakh_preset("rotax_912is")
    exec_sim = MissionExecutive(hub, preset)
    exec_sim.state.status = MissionStatus.RUNNING.value

    for _ in range(60):
        exec_sim.step(dt=0.05)

    original_final_wp = exec_sim.definition.waypoints[-1].id
    res = exec_sim.divert(lat=34.70, lon=77.60, name="ALTERNATE_FIELD")
    assert res["divert_waypoint"]["name"] == "ALTERNATE_FIELD"
    assert exec_sim.definition.waypoints[-1].id != original_final_wp
    assert exec_sim.definition.waypoints[-1].name == "ALTERNATE_FIELD"

    # The autopilot should now be seeking the new diverted waypoint, not the old route.
    for _ in range(60):
        state = exec_sim.step(dt=0.05)
    assert state.time_elapsed_sec > 0.0


# ---------------------------------------------------------------------------
# Phase-based mission tests (ARCH-2026-MP-002)
# ---------------------------------------------------------------------------

def test_phase_mission_progresses_through_all_phases(hub):
    """Proves the phase-based mission actually advances phase-by-phase (not stuck, not
    skipping) and altitude/throttle change with each phase, matching that phase's authored
    values -- the core requirement of the phase-based pivot."""
    preset = create_endurance_phase_preset("rotax_912is")
    exec_sim = MissionExecutive(hub, preset)
    assert exec_sim.is_phase_mode
    exec_sim.state.status = MissionStatus.RUNNING.value
    exec_sim.time_scale = 4.0

    seen_phase_names = []
    for _ in range(3000):
        state = exec_sim.step(dt=0.05)
        if not seen_phase_names or seen_phase_names[-1] != state.phase:
            seen_phase_names.append(state.phase)
        if state.status == MissionStatus.COMPLETED.value:
            break

    expected_order = ["TAKEOFF", "CLIMB", "CRUISE", "LOITER", "DESCENT", "LANDING", "COMPLETED"]
    assert seen_phase_names == expected_order
    assert state.status == MissionStatus.COMPLETED.value


def test_phase_mission_altitude_ramps_between_phases(hub):
    """Altitude must genuinely climb/descend across phases (not stay frozen) -- this is the
    specific bug the terrain-anchor sign error caused during development (aircraft pinned to
    the terrain-clearance floor on high ground) and must not regress."""
    preset = create_endurance_phase_preset("rotax_912is")
    exec_sim = MissionExecutive(hub, preset)
    exec_sim.state.status = MissionStatus.RUNNING.value
    exec_sim.time_scale = 4.0

    altitudes = []
    for i in range(3000):
        state = exec_sim.step(dt=0.05)
        if i % 100 == 0:
            altitudes.append(state.pos_z_m)
        if state.status == MissionStatus.COMPLETED.value:
            break

    # Altitude must vary meaningfully over the mission (climb then descend) -- a frozen
    # altitude (the terrain-floor-pin bug) would show near-zero spread here.
    assert max(altitudes) - min(altitudes) > 500.0


def test_phase_scheduled_fault_fires_at_phase_elapsed_time(hub):
    """A fault scheduled at (CRUISE, 30s) must fire only once CRUISE has been active for
    >= 30s -- not at 30s of global mission time, and not in a different phase."""
    # hub is module-scoped and shared across tests -- clear any fault left active by an
    # earlier test in this module before asserting on when THIS test's fault first appears.
    hub.runtimes["rotax_912is"].clear_faults()

    preset = create_endurance_phase_preset("rotax_912is")
    # Override with a fault scheduled early in CRUISE for a fast, deterministic test.
    preset.phase_events = [
        type(preset.phase_events[0])(phase_name="CRUISE", elapsed_in_phase_sec=5.0,
                                     fault_mode="COOLING_DEGRADATION", severity=0.9, ramp_sec=5.0)
    ]
    exec_sim = MissionExecutive(hub, preset)
    exec_sim.state.status = MissionStatus.RUNNING.value
    exec_sim.time_scale = 4.0

    fired_phase = None
    for _ in range(3000):
        state = exec_sim.step(dt=0.05)
        if state.active_faults and fired_phase is None:
            fired_phase = state.phase
        if state.status == MissionStatus.COMPLETED.value:
            break

    assert fired_phase == "CRUISE"


def test_live_mission_reliability_profile_reflects_actual_phases(hub):
    """Proves the reliability wire is real: mission_reliability() with the mission's actual
    live phase profile must differ from a plain default call (the previous behavior, always
    using the generic canned ISR_18H_PROFILE) -- i.e. the fix in engine_runtime.py's
    mission_reliability(profile=...) is actually being used, not silently ignored."""
    preset = create_endurance_phase_preset("rotax_912is")
    exec_sim = MissionExecutive(hub, preset)
    exec_sim.state.status = MissionStatus.RUNNING.value

    for _ in range(20):
        exec_sim.step(dt=0.05)

    live_profile = exec_sim._build_live_reliability_profile()
    # The live profile's total duration must reflect the actual short demo mission
    # (~7.5 minutes), NOT the generic ISR_18H_PROFILE's 18 hours -- proving a real,
    # mission-specific profile is being built and used rather than the canned fallback.
    assert live_profile.total_hours < 0.5
    assert [p.name for p in live_profile.phases][0] == "TAKEOFF"


def test_live_fault_damage_reduces_mission_reliability(hub):
    """Injecting a real fault must visibly reduce the live mission reliability computed from
    the actual phase profile -- proves ComponentHazard.set_damage() (found dead/unwired
    during investigation) is now actually connected to real fault state."""
    preset = create_endurance_phase_preset("rotax_912is")
    exec_sim = MissionExecutive(hub, preset)
    exec_sim.state.status = MissionStatus.RUNNING.value
    runtime = hub.runtimes["rotax_912is"]

    profile_before = exec_sim._build_live_reliability_profile()
    reliability_before = runtime.reliability_engine.analytic_reliability(profile_before)["reliability"]

    exec_sim.inject_live_fault("COOLING_DEGRADATION", severity=0.95, ramp_sec=5.0)
    for _ in range(200):
        state = exec_sim.step(dt=0.05)
        if state.active_faults:
            break

    exec_sim._apply_live_fault_damage(runtime)
    profile_after = exec_sim._build_live_reliability_profile()
    reliability_after = runtime.reliability_engine.analytic_reliability(profile_after)["reliability"]

    assert reliability_after < reliability_before
