"""Characterization tests (B0.9): backend/twin/{validity,integrity}.py"""
import random

import pytest

from backend.twin.integrity import (
    TelemetryIntegrityMonitor, _expected_map, default_constraints,
)
from backend.twin.validity import TwinValidityMonitor, chi2_bounds


# ---- validity -------------------------------------------------------------

def test_chi2_bounds_shape():
    lo, hi = chi2_bounds(4)
    assert 0 < lo < 4 < hi
    lo2, hi2 = chi2_bounds(50)
    assert lo2 < 50 < hi2                             # bounds are on the SUM (chi2 with dof), mean = dof
    assert chi2_bounds(4) == (lo, hi)


def _feed(mon, n, rng, sigma=1.0, bias=None):
    for _ in range(n):
        r = {c: rng.gauss(0, sigma) for c in mon.channels}
        for c, b in (bias or {}).items():
            r[c] += b
        mon.update(r)


def test_validity_nominal_is_trustworthy():
    rng = random.Random(0)
    mon = TwinValidityMonitor(["a", "b", "c"], window=400)
    _feed(mon, 400, rng)
    v = mon.assess()
    assert v.trustworthy is True
    assert v.attribution == "NOMINAL"
    assert v.confidence == pytest.approx(1.0)
    assert v.nis == pytest.approx(3.0, abs=0.6)   # NIS is the per-frame sum over channels (mean = dof)
    assert v.reasons == ["all consistency checks passed"]
    assert "consistent" in v.sentence()
    d = v.as_dict()
    assert d["TWIN_TRUSTWORTHY"] is True and d["TWIN_ATTRIBUTION"] == "NOMINAL"


def test_validity_drift_and_fault_attribution():
    rng = random.Random(1)
    mon = TwinValidityMonitor(["a", "b", "c"], window=400)
    _feed(mon, 400, rng, sigma=3.0)                   # residuals 3x larger than expected
    v = mon.assess(fault_suspected=False)
    assert v.nis_in_bounds is False
    assert v.attribution == "MODEL_DRIFT" and v.trustworthy is False   # conf 0.65 but attribution blocks trust
    assert v.confidence == pytest.approx(0.65)
    assert "MODEL_DRIFT" in v.sentence()
    # same statistics, but the detector flagged a fault independently
    assert mon.assess(fault_suspected=True).attribution == "ENGINE_FAULT"


def test_validity_bias_and_sensor_fault():
    rng = random.Random(2)
    mon = TwinValidityMonitor(["a", "b"], window=400)
    _feed(mon, 400, rng, bias={"a": 1.5})
    v = mon.assess()
    assert "a" in v.bias_channels
    assert v.attribution == "MODEL_DRIFT"
    assert mon.assess(sensor_quarantined=["a"]).attribution == "SENSOR_FAULT"


def test_validity_envelope_and_reset():
    mon = TwinValidityMonitor(["a"], envelope={"alt": (0.0, 100.0)})
    rng = random.Random(3)
    for _ in range(50):
        mon.update({"a": rng.gauss(0, 1)}, operating_point={"alt": 500.0})
    v = mon.assess()
    assert v.attribution == "OUT_OF_ENVELOPE" and v.out_of_envelope
    mon.reset()
    assert mon.assess().nis == 0.0 or mon.assess().attribution in ("NOMINAL", "OUT_OF_ENVELOPE")


def test_validity_deterministic_for_same_input():
    def run():
        rng = random.Random(9)
        m = TwinValidityMonitor(["a", "b"])
        _feed(m, 200, rng)
        return m.assess().as_dict()
    assert run() == run()


# ---- integrity ------------------------------------------------------------

def _frame(rng, noise=0.0):
    tps, alt, rpm = 70.0, 10000.0, 5000.0
    mp = _expected_map(tps, alt)
    power = (rpm / 5800.0) * (mp / 100.0) * 84.0
    fuel = power * 0.30 + 1.5
    oat = -5.0
    ratio = 1.6
    g = lambda s: rng.gauss(0, s) * noise
    return {
        "MAP": mp + g(2.0), "TPS": tps, "ALTITUDE_FT": alt,
        "FUEL_FLOW": fuel + g(0.5), "POWER_KW": power + g(1.0),
        "ENGINE_RPM": rpm, "EGT_1": 420.0 + 16.0 * fuel + g(10.0),
        "CHARGE_TEMP_C": (oat + 273.15) * ratio ** 0.2857 - 273.15 + g(3.0),
        "TURBO_PRESSURE_RATIO": ratio, "OAT_C": oat,
        "BUS_VOLTAGE": 14.2 - 0.08 * 5.0 + g(0.1), "BATTERY_CURRENT": 5.0,
        "OIL_PRESS": 0.6 + 0.00058 * rpm + g(0.1),
    }


def test_default_constraints_zero_residual_on_ideal_frame():
    frame = _frame(random.Random(0))
    cons = default_constraints()
    assert len(cons) == 7
    for c in cons:
        r = c.evaluate(frame)
        assert r is not None and abs(r) < 1e-6, c.name
    assert cons[0].evaluate({"MAP": 1.0}) is None       # missing inputs -> None


def test_integrity_calibrated_accepts_nominal_and_flags_spoof():
    rng = random.Random(4)
    mon = TelemetryIntegrityMonitor(freeze_samples=10**6).calibrate([_frame(rng, 1.0) for _ in range(500)])
    th = mon.thresholds
    assert len(th) == 7 and all(v > 0 for v in th.values())
    # false-alarm rate is bounded by construction (alpha=0.01 per constraint, 7 constraints)
    alarms = sum(not mon.check(_frame(rng, 1.0)).consistent for _ in range(300))
    assert alarms / 300 < 0.15
    mon.reset()
    bad = _frame(rng)
    bad["MAP"] += 60.0
    bad["OIL_PRESS"] += 6.0
    v = mon.check(bad)
    assert v.consistent is False
    assert len(v.violated_constraints) >= 2
    assert v.classification == "SUSPECTED_SPOOF"
    assert v.as_dict()["TELEM_CONSISTENT"] is False


def test_integrity_single_violation_is_sensor_fault():
    rng = random.Random(5)
    mon = TelemetryIntegrityMonitor()          # uncalibrated: 3-unit default limit
    f = _frame(rng)
    f["BUS_VOLTAGE"] += 5.0
    v = mon.check(f)
    assert v.violated_constraints == ["electrical_balance"]
    assert v.classification == "SENSOR_FAULT"
    assert mon.check(_frame(rng)).classification in ("NOMINAL", "SENSOR_FAULT")


def test_integrity_frozen_stale_and_lane_checks():
    mon = TelemetryIntegrityMonitor(freeze_samples=10)
    rng = random.Random(6)
    last = None
    for i in range(12):
        f = _frame(rng)
        f["VIB"] = 1.0                      # never changes
        f["CHT_2"] = float(i)
        last = mon.check(f, t_sec=float(i) * 0.1)
    assert "VIB" in last.frozen_channels and "CHT_2" not in last.frozen_channels
    assert last.classification == "SENSOR_FAULT"

    mon2 = TelemetryIntegrityMonitor()
    mon2.check({"X": 1.0}, t_sec=0.0)
    v = mon2.check({"Y": 1.0}, t_sec=10.0)
    assert v.stale_channels == ["X"] and v.classification == "STALE_LINK"

    v = TelemetryIntegrityMonitor(constraints=[]).check(
        {"MAP_LANE_A": 100.0, "MAP_LANE_B": 120.0})
    assert v.lane_disagreements and v.classification == "SENSOR_FAULT"
