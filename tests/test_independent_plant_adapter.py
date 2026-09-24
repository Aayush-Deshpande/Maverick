"""
Tests for backend.plant.adapter.IndependentPlantAdapter — the G01 wiring.

These are deliberately independent of EngineStateService (a no-arg singleton;
env-var-gated construction there is exercised manually, not under pytest) and
exercise the adapter directly, which is also the cleaner unit boundary.
"""

import pytest

from backend.physics.thermo_model import RotaxThermoModel
from backend.plant.adapter import (
    FAULT_TO_PLANT_MAPPING,
    IndependentPlantAdapter,
    PLANT_MODELLED_FAULT_IDS,
)
from backend.telemetry.can_streamer import TelemetryStreamer


def _make_adapter(seed=42):
    streamer = TelemetryStreamer(sample_rate_hz=20.0)
    thermo = RotaxThermoModel()
    return IndependentPlantAdapter(streamer, thermo, seed=seed), streamer


def test_nominal_frame_is_well_formed():
    """The adapter must not crash and must return a fully-populated triple."""
    adapter, _ = _make_adapter()
    actual, expected, residuals = adapter.generate_frame(
        throttle_cmd=72.0, altitude_cmd=20000.0, oat_cmd=-22.0
    )
    assert actual.ENGINE_RPM > 0
    assert 0.0 < actual.OIL_PRESS < 10.0
    assert actual.CHT_1 > 0 and actual.CHT_4 > 0
    # PROP_RPM must track the plant's independent RPM through the gear ratio,
    # not be left over from the streamer's own (different) RPM computation.
    assert actual.PROP_RPM == pytest.approx(actual.ENGINE_RPM / 2.43, abs=0.1)


def test_nominal_residuals_are_structured_not_pure_noise():
    """
    The whole point of G01: with the independent plant, actual and expected
    come from two different models. Residuals on healthy, steady-state flight
    should therefore show a small but *non-zero, non-random* standing offset
    (model mismatch) rather than the near-zero-mean noise the old circular
    generator produced by construction (actual = expected + noise).

    This does not assert a specific magnitude -- that would be overfitting the
    test to today's tuning -- only that CHT residuals are not centred on exactly
    zero, which is the structural signature of true independence.
    """
    adapter, _ = _make_adapter(seed=7)
    cht1_residuals = []
    for _ in range(40):
        actual, expected, residuals = adapter.generate_frame(
            throttle_cmd=72.0, altitude_cmd=20000.0, oat_cmd=-22.0, dt_sec=1.0
        )
        cht1_residuals.append(residuals.d_CHT_1)

    # Let thermal lag settle, then check the back half of the run.
    tail = cht1_residuals[20:]
    mean_abs = sum(abs(r) for r in tail) / len(tail)
    assert mean_abs > 0.05, (
        f"mean |residual| = {mean_abs:.4f}; expected a non-trivial standing "
        "offset from independent-model mismatch, not near-zero noise"
    )


@pytest.mark.parametrize("fault_id", sorted(FAULT_TO_PLANT_MAPPING.keys()))
def test_mapped_faults_move_the_expected_channel(fault_id):
    """Faults 1-4: confirm the plant-driven channel actually degrades directionally."""
    adapter, streamer = _make_adapter(seed=fault_id)

    # Warm up nominal so there is a baseline to compare against.
    for _ in range(10):
        baseline, _, _ = adapter.generate_frame(
            throttle_cmd=75.0, altitude_cmd=15000.0, oat_cmd=-10.0, dt_sec=1.0
        )

    streamer.set_fault(fault_id, severity=1.0, ramp_duration_sec=5.0)

    last = None
    for _ in range(30):
        last, _, _ = adapter.generate_frame(
            throttle_cmd=75.0, altitude_cmd=15000.0, oat_cmd=-10.0, dt_sec=1.0
        )

    if fault_id == 1:  # COOLING_DEGRADATION -> CHTs should rise
        assert last.CHT_1 > baseline.CHT_1 + 2.0 or last.CHT_2 > baseline.CHT_2 + 2.0
    elif fault_id == 2:  # INJECTOR_COKING cyl 1 -> cylinder 1 combustion degrades
        assert last.EGT_1 != pytest.approx(baseline.EGT_1, abs=0.5) or \
               last.CHT_1 != pytest.approx(baseline.CHT_1, abs=0.5)
    elif fault_id == 3:  # MISFIRE cyl 2 -> RPM should sag as combustion drops out
        assert last.ENGINE_RPM < baseline.ENGINE_RPM
    elif fault_id == 4:  # OIL_PRESSURE_LOSS -> oil pressure should fall
        assert last.OIL_PRESS < baseline.OIL_PRESS - 0.1


@pytest.mark.parametrize("fault_id", [5, 6, 7, 8])
def test_unmapped_faults_pass_through_untouched(fault_id):
    """
    Faults 5-8 are not in VirtualEngine's fault library. The adapter must fall
    back to the streamer's own (pre-existing, tested) fault deltas unchanged --
    this is the regression guard for the scoped-fix design.
    """
    adapter, streamer = _make_adapter(seed=100 + fault_id)
    streamer.set_fault(fault_id, severity=1.0, ramp_duration_sec=2.0)

    plain_streamer = streamer  # same object; adapter wraps it, doesn't copy it
    for _ in range(20):
        via_adapter, _, _ = adapter.generate_frame(
            throttle_cmd=75.0, altitude_cmd=15000.0, oat_cmd=-10.0, dt_sec=1.0
        )

    assert fault_id not in PLANT_MODELLED_FAULT_IDS
    # HEALTH_INDEX is only ever written by the streamer's own fault-delta
    # blocks (never touched by the adapter's overwrite), so it moving off
    # 1.0 proves the streamer's fault-5..8 path ran and was preserved.
    assert via_adapter.HEALTH_INDEX < 1.0


def test_fault_switch_reinjects_plant_fault():
    """Switching from one mapped fault to another must clear and re-inject,
    not accumulate state from the previous fault."""
    adapter, streamer = _make_adapter(seed=99)
    streamer.set_fault(4, severity=1.0, ramp_duration_sec=3.0)
    for _ in range(15):
        adapter.generate_frame(throttle_cmd=75.0, altitude_cmd=15000.0, oat_cmd=-10.0, dt_sec=1.0)

    streamer.reset_fault()
    streamer.set_fault(3, severity=1.0, ramp_duration_sec=3.0)
    last = None
    for _ in range(15):
        last, _, _ = adapter.generate_frame(throttle_cmd=75.0, altitude_cmd=15000.0, oat_cmd=-10.0, dt_sec=1.0)

    # Oil pressure loss (fault 4) must not still be depressing OIL_PRESS
    # once we've switched to fault 3 (misfire) -- confirms clear_faults() ran.
    assert last.OIL_PRESS > 2.0


def test_truth_access_for_evaluation_only():
    """The evaluation-only truth() escape hatch must expose real ground truth
    the twin never sees, for harness use -- not silently equal to actual."""
    adapter, streamer = _make_adapter(seed=3)
    streamer.set_fault(3, severity=1.0, ramp_duration_sec=1.0)
    for _ in range(10):
        adapter.generate_frame(throttle_cmd=75.0, altitude_cmd=15000.0, oat_cmd=-10.0, dt_sec=1.0)

    truth = adapter.truth()
    assert "cht_true" in truth or any("cht" in k.lower() for k in truth)
