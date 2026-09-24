"""Tests for SensorLevers (R7) and bit-exact live-vs-replay (D05)."""

import numpy as np
import pytest
from backend.core.frame import Frame, TruthRecord
from backend.runtime.engine_runtime import EngineRuntime
from backend.runtime.sensor_levers import SensorLevers


def test_sensor_levers_operations():
    sl = SensorLevers(seed=42)
    f = Frame(
        t=10.0,
        source="PLANT",
        engine_config_id="rotax_914",
        rpm=4000.0,
        map_kpa=100.0,
        oil_p=3.5,
        cht=[110.0, 110.0, 110.0, 110.0],
        egt=[700.0, 700.0, 700.0, 700.0],
    )

    # Bias on map_kpa
    sl.inject_bias("map_kpa", 15.0)
    f_bias = sl.apply(f, dt=1.0)
    assert f_bias.map_kpa == 115.0

    # Drift on oil_p
    sl.inject_drift("oil_p", rate_per_sec=0.5)
    f_drift1 = sl.apply(f, dt=1.0)
    assert f_drift1.oil_p == 4.0
    f_drift2 = sl.apply(f, dt=2.0)
    assert f_drift2.oil_p == 5.0  # accumulated 0.5*1 + 0.5*2 = 1.5

    # Stuck on cht_2
    sl.inject_stuck("cht_2", frozen_value=125.0)
    f_stuck = sl.apply(f, dt=1.0)
    assert f_stuck.cht[1] == 125.0

    # Dropout on egt_3
    sl.inject_dropout("egt_3")
    f_drop = sl.apply(f, dt=1.0)
    assert f_drop.egt[2] == 0.0

    # Clear
    sl.clear()
    assert sl.has_active_faults is False
    f_clean = sl.apply(f, dt=1.0)
    assert f_clean.map_kpa == 100.0
    assert f_clean.oil_p == 3.5


def test_runtime_sensor_fault_kpi_exclusion():
    rt = EngineRuntime("rotax_914", seed=1, warmup_ticks=400)
    rt.calibrate()

    # Normal tick -> SCRIPTED, kpi_eligible=True
    t1 = rt.tick()
    assert t1.truth.origin == "SCRIPTED"
    assert t1.truth.kpi_eligible is True

    # Inject sensor fault -> MANUAL, kpi_eligible=False
    rt.set_sensor_fault("bias", "map_kpa", offset=20.0)
    t2 = rt.tick()
    assert t2.truth.origin == "MANUAL"
    assert t2.truth.kpi_eligible is False
    assert any("SENSOR_BIAS" in af.mode for af in t2.truth.active_faults)

    # Clear sensor fault -> restores (after resetting manual_origin)
    rt.clear_faults()
    rt.manual_origin = False
    t3 = rt.tick()
    assert t3.truth.origin == "SCRIPTED"
    assert t3.truth.kpi_eligible is True


def test_bit_exact_live_vs_replay():
    """Prove that live ticking and ingesting recorded Frames produce identical detector outputs (D05)."""
    rt_live = EngineRuntime("rotax_914", seed=7, warmup_ticks=400)
    rt_live.calibrate()

    # Run 50 ticks, collect Frames
    recorded_frames = []
    live_ticks = []
    for _ in range(50):
        t = rt_live.tick()
        recorded_frames.append(t.frame)
        live_ticks.append(t)

    # Create a fresh replay runtime calibrated on the EXACT same calibration frames
    rt_replay = EngineRuntime("rotax_914", seed=7, warmup_ticks=400)
    rt_replay.detector = rt_live.detector  # share identical calibration state

    # Ingest recorded frames
    replay_ticks = []
    for f in recorded_frames:
        t = rt_replay.ingest(f)
        replay_ticks.append(t)

    assert len(live_ticks) == len(replay_ticks)
    for lt, rt in zip(live_ticks, replay_ticks):
        assert lt.detection.scores == rt.detection.scores
        assert lt.detection.ratios == rt.detection.ratios
        assert lt.detection.raw_alarm == rt.detection.raw_alarm
        assert lt.detection.confirmed == rt.detection.confirmed
        assert lt.detection.top_channels == rt.detection.top_channels
