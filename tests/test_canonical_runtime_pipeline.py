"""
End-to-End Acceptance Test for the Canonical Digital Twin Pipeline.
DRDO / iDEX Problem Statement ID: 26054.

Verifies the complete unbroken live pipeline:
- Sensor Sanity & Shielding
- High-Rate Vibration Order DSP
- Thermofluid UKF State Observer & Unsensored Virtual Sensors
- Statistical Residual Detection
- Digital Twin Validity & 3-Way Fault Attribution
- ASTM E1049 Rainflow Fatigue Damage & Finite Conformal RUL Intervals
- Weibull-Markov Mission Reliability & UAV Glide Polar Reachability
- EngineService & REST/WebSocket Telemetry Serialization
"""

import math
import pytest
import numpy as np

from backend.core.frame import Frame, Q_SHIELDED
from backend.physics.engine_config import load_engine_config
from backend.runtime.engine_runtime import EngineRuntime
from backend.server.engine_service import EngineStateService


def test_canonical_runtime_pipeline_end_to_end():
    """Verify that every single stage in EngineRuntime executes and outputs valid contracts."""
    runtime = EngineRuntime("rotax_912is", seed=42, warmup_ticks=400)
    runtime.calibrate()

    # Step runtime for 25 ticks
    ticks = []
    for _ in range(25):
        t = runtime.tick()
        ticks.append(t)

    assert len(ticks) == 25
    last_tick = ticks[-1]
    f = last_tick.frame

    # 1. Vibration Order DSP
    assert f.vibration_orders is not None
    assert "1X" in f.vibration_orders
    assert "2X" in f.vibration_orders
    assert "3X_prop" in f.vibration_orders
    assert "sub_whirl" in f.vibration_orders
    assert "gear_mesh" in f.vibration_orders
    assert "bpfo" in f.vibration_orders
    assert f.vibration_orders["1X"] > 0.0

    # 2. Synthesized Virtual Sensors
    assert f.virtual_sensors is not None
    assert "P_max_bar" in f.virtual_sensors
    assert "TIT_degC" in f.virtual_sensors
    assert "h_min_um" in f.virtual_sensors
    assert "P_ind_kw" in f.virtual_sensors
    assert f.virtual_sensors["P_max_bar"] > 20.0
    assert f.virtual_sensors["TIT_degC"] > 500.0

    # 3. Thermofluid UKF State Observer
    assert last_tick.ukf is not None
    assert "nis" in last_tick.ukf
    assert "params" in last_tick.ukf
    assert len(last_tick.ukf["params"]) > 0

    # 4. Twin Validity Monitor & 3-Way Attribution
    assert last_tick.validity is not None
    assert "verdict" in last_tick.validity
    assert "attribution" in last_tick.validity
    assert last_tick.validity["attribution"] in ["NOMINAL", "MODEL_DRIFT", "ENGINE_FAULT", "SENSOR_FAULT"]

    # 5. Damage Accumulation & Conformal RUL Intervals
    assert last_tick.prognostics is not None
    dmg = last_tick.prognostics["damage"]
    assert "damage_total" in dmg
    assert "damage_thermal_lcf" in dmg

    rul = last_tick.prognostics["rul"]
    assert "rul_point" in rul
    assert "rul_p_lower" in rul and "rul_p_upper" in rul
    low, high = rul["rul_p_lower"], rul["rul_p_upper"]
    assert math.isfinite(low) and math.isfinite(high)
    assert low <= high

    # 6. Mission Reliability & Glide Polar Reachability
    assert last_tick.reliability is not None
    assert "mission_reliability" in last_tick.reliability
    assert 0.0 <= last_tick.reliability["mission_reliability"] <= 1.0

    assert last_tick.glide is not None
    assert "glide_ratio" in last_tick.glide
    assert "still_air_range_km" in last_tick.glide
    assert "reachable_airfields" in last_tick.glide
    assert len(last_tick.glide["reachable_airfields"]) >= 5


def test_sensor_fault_shielding_and_attribution():
    """Verify that sensor faults trigger shielding and 3-way attribution."""
    runtime = EngineRuntime("rotax_912is", seed=42, warmup_ticks=400)
    runtime.calibrate()

    # Establish baseline tick before injection
    runtime.tick()

    # Inject sensor bias on CHT_1
    runtime.set_sensor_fault("bias", "cht_1", offset=45.0)

    # First tick right after unphysical jump: rate spike detected
    t_spike = runtime.tick()
    assert (t_spike.frame.quality.get("cht_1", 0) & Q_SHIELDED != 0) or ("CHT_1" in t_spike.sanity.get("failed_channels", []))

    for _ in range(15):
        t = runtime.tick()

    # Twin validity attribution should recognize anomaly
    assert t.validity["attribution"] in ["SENSOR_FAULT", "MODEL_DRIFT", "ENGINE_FAULT"]


def test_engine_service_unified_state_serialization():
    """Verify that EngineService serves all digital twin telemetry contracts."""
    service = EngineStateService.get_instance()
    state = service.get_latest_state()

    assert state.is_engine_running is True
    assert state.telemetry.ENGINE_RPM > 0

    # Ensure digital twin contracts are populated in EngineTelemetry
    assert state.telemetry.vibration_orders is not None
    assert "1X" in state.telemetry.vibration_orders
    assert "3X_prop" in state.telemetry.vibration_orders

    assert state.telemetry.virtual_sensors is not None
    assert "P_max_bar" in state.telemetry.virtual_sensors
    assert "TIT_degC" in state.telemetry.virtual_sensors

    # Ensure analytics contracts are populated in AnalyticsState
    assert state.analytics.twin_validity is not None
    assert state.analytics.twin_validity["verdict"] in ["VALID", "DEGRADED", "INVALID"]

    assert state.analytics.glide_assessment is not None
    assert state.analytics.glide_assessment["glide_ratio"] > 10.0
    assert len(state.analytics.glide_assessment["reachable_airfields"]) > 0

    assert state.analytics.mission_reliability is not None
    assert state.analytics.mission_reliability["mission_reliability"] > 0.0


def test_multi_engine_agnostic_pipeline():
    """Verify canonical pipeline operates across diverse multi-engine architectures."""
    engines = ["rotax_914", "rotax_915is", "austro_ae300", "vrde_jayem_2_2l"]
    for eng_id in engines:
        rt = EngineRuntime(eng_id, seed=10, warmup_ticks=400)
        rt.calibrate()
        tick = rt.tick()
        assert tick.frame.vibration_orders is not None
        assert tick.frame.virtual_sensors is not None
        assert tick.validity is not None
        assert tick.glide is not None
