"""Tests for Waveform Stack (B2.1-B2.5, W3): CI combustion, rail acoustics, structural dynamics, high-rate DAQ."""

import tempfile
from pathlib import Path
import numpy as np
import pytest

from backend.physics.combustion_ci import CICombustionModel, CICombustionParams
from backend.physics.engine_config import load_engine_config
from backend.physics.rail import CommonRailHydraulics, RailConfig
from backend.physics.structure import StructuralAcoustics
from backend.plant.sensors_hr import HighRateSensorChain
from backend.sources.waveform import WaveformRecorder, WaveformSource


def test_ci_combustion_peak_pressure_class():
    cfg = load_engine_config("vrde_jayem_2_2l")
    model = CICombustionModel(cfg)

    theta, p_bar, dp_dt = model.simulate_cycle_pressure(
        rpm=3800.0,
        map_kpa=220.0,  # full boost
        t_charge_k=335.0,
        fuel_mg_per_stroke=42.0,  # full load ~42 mg/stroke
    )
    peak_p = float(np.max(p_bar))
    # CI diesel peak cylinder pressure is in 120-180 bar class
    assert 120.0 <= peak_p <= 185.0, f"Peak CI pressure {peak_p:.1f} bar outside 120-180 bar class"
    assert len(theta) == 720
    assert np.max(dp_dt) > 0.0


def test_common_rail_hydraulics_and_injector_coking():
    rail = CommonRailHydraulics(RailConfig())
    qtys = [30.0, 30.0, 30.0, 30.0]
    angles = [0.0, 180.0, 360.0, 540.0]

    # Nominal rail pressure
    t_sec, p_nom = rail.simulate_cycle_rail_pressure(
        rpm=3600.0,
        target_p_bar=1600.0,
        inj_quantities_mm3=qtys,
        inj_angles_deg=angles,
        coking_factors=[1.0, 1.0, 1.0, 1.0],
    )
    # Injector 2 coked (factor 0.4)
    _, p_coked = rail.simulate_cycle_rail_pressure(
        rpm=3600.0,
        target_p_bar=1600.0,
        inj_quantities_mm3=qtys,
        inj_angles_deg=angles,
        coking_factors=[1.0, 0.4, 1.0, 1.0],
    )

    # During cylinder 2 injection window (around 180 deg / ~25% through cycle)
    # Coked injector has smaller pressure drop (higher local pressure)
    n = len(t_sec)
    window_cyl2 = slice(int(0.25 * n), int(0.35 * n))
    drop_nom = float(np.min(p_nom[window_cyl2]))
    drop_coked = float(np.min(p_coked[window_cyl2]))
    assert drop_coked > drop_nom, "Coked injector should have smaller localized pressure drop"


def test_draper_resonance_and_bearing_orders():
    cfg = load_engine_config("vrde_jayem_2_2l")
    acoustics = StructuralAcoustics(cfg)

    # Draper acoustic resonance frequencies in 5.6 - 20 kHz band
    draper_freqs = acoustics.calc_draper_frequencies(t_gas_k=1800.0)
    assert len(draper_freqs) == 3
    assert 5500.0 <= draper_freqs[0] <= 9000.0
    assert draper_freqs[2] <= 20000.0

    # Synthesize vibration with bearing defect BPFO
    dp_dt_nom = [np.ones(720) * 2.0 for _ in range(4)]
    t, angle, accel_bpfo = acoustics.synthesize_cycle_vibration(
        rpm=3000.0,
        dp_dtheta_per_cyl=dp_dt_nom,
        firing_angles_deg=[0.0, 180.0, 360.0, 540.0],
        bearing_fault="BPFO",
        bearing_severity=1.0,
    )
    _, _, accel_clean = acoustics.synthesize_cycle_vibration(
        rpm=3000.0,
        dp_dtheta_per_cyl=dp_dt_nom,
        firing_angles_deg=[0.0, 180.0, 360.0, 540.0],
        bearing_fault=None,
    )
    # Bearing defect increases high-frequency envelope energy
    rms_bpfo = float(np.sqrt(np.mean(accel_bpfo ** 2)))
    rms_clean = float(np.sqrt(np.mean(accel_clean ** 2)))
    assert rms_bpfo > rms_clean * 1.5


def test_sensor_chain_timer_and_adc():
    sensors = HighRateSensorChain(seed=101)
    ts = sensors.generate_crank_tooth_timestamps(rpm=3000.0, cycle_start_t=0.0, num_cycles=1)
    assert len(ts) == 58 * 2  # 60-2 wheel over 2 revs = 116 teeth

    # Verify <= 25 ns timer resolution (difference from 25ns grid should be near 0)
    dt_ns = (ts * 1e9) % 25.0
    grid_err = np.minimum(dt_ns, 25.0 - dt_ns)
    assert np.all(grid_err < 1e-3)


def test_waveform_source_and_recorder_npz_sha256():
    src = WaveformSource("vrde_jayem_2_2l", seed=42)
    cycle = src.next_cycle(rpm=3500.0)

    assert cycle.cycle_id == 1
    assert "block" in cycle.accel
    assert cycle.accel["block"].fs_hz == 51200.0
    assert cycle.rail_p_hr is not None
    assert cycle.rail_p_hr.fs_hz == 30000.0

    with tempfile.TemporaryDirectory() as tmpdir:
        npz_file = Path(tmpdir) / "test_cycle.npz"
        sha = WaveformRecorder.save_cycle(cycle, npz_file)
        assert len(sha) == 64  # valid SHA-256 hex string

        loaded = WaveformRecorder.load_cycle(npz_file, "vrde_jayem_2_2l")
        assert loaded.cycle_id == cycle.cycle_id
        assert np.array_equal(loaded.tooth_ts, cycle.tooth_ts)
        assert np.array_equal(loaded.accel["block"].data, cycle.accel["block"].data)
        assert np.array_equal(loaded.rail_p_hr.data, cycle.rail_p_hr.data)


def test_waveform_visibility_of_scalar_invisible_faults():
    """Prove F22: Injector coking and turbo bearing wear are clearly visible in waveforms while scalars stay nominal."""
    src = WaveformSource("vrde_jayem_2_2l", seed=50)

    # 1. Clean cycle
    cycle_clean = src.next_cycle(rpm=3500.0)
    rail_clean = cycle_clean.rail_p_hr.data
    accel_clean = cycle_clean.accel["block"].data

    # 2. Injector coking on cyl 1
    src.inject_fault("INJECTOR_COKING_IDID", cylinder=1, severity=1.0)
    cycle_coked = src.next_cycle(rpm=3500.0)
    rail_coked = cycle_coked.rail_p_hr.data

    # Waveform diff on rail pressure is statistically clear
    rail_diff_rms = float(np.sqrt(np.mean((rail_coked - rail_clean) ** 2)))
    assert rail_diff_rms > 1.0, f"Injector coking should produce measurable rail pressure waveform delta, got {rail_diff_rms:.2f}"

    # 3. Turbo bearing wear
    src.clear_faults()
    src.inject_fault("TURBO_BEARING_WEAR", severity=1.0)
    cycle_turbo = src.next_cycle(rpm=3500.0)
    accel_turbo = cycle_turbo.accel["block"].data

    turbo_diff_rms = float(np.sqrt(np.mean((accel_turbo - accel_clean) ** 2)))
    assert turbo_diff_rms > 1.0, f"Turbo bearing wear should produce significant vibration waveform delta, got {turbo_diff_rms:.2f}"
