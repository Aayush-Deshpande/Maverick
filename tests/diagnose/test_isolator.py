"""M3-05 Bayesian isolation: the closed-form severity marginal is right, a quiet residual stays NOMINAL, a one-channel
offset is a SENSOR hypothesis while a coupled pattern is the PROCESS fault (with its cylinder), and on the plant the
injected fault leads the posterior (calibrated signatures from seeds 11/12, test tail seed 1001: disjoint, D17)."""
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.integrate import quad

from backend.diagnose.directive import directive
from backend.diagnose.isolator import BayesianIsolator, _log_marginal
from backend.evaluation.tail import calibrated

ENGINE = "rotax_912is"


def test_severity_marginal_matches_numerical_integration():
    rng = np.random.default_rng(0)
    z, m, var = rng.normal(size=6), rng.normal(size=6), 0.7
    ll, s_hat = _log_marginal(z, m, var, 0.0, 1.5)
    # same constants dropped as in the closed form: exp(-0.5 |z - s m|^2 / var), uniform prior on [0, 1.5]
    num, _ = quad(lambda s: np.exp(-0.5 * np.sum((z - s * m) ** 2) / var) / 1.5, 0.0, 1.5)
    assert ll == pytest.approx(np.log(num), rel=1e-6)
    assert 0.0 <= s_hat <= 1.5


def _isolator():
    names = [f"cht_{i}" for i in range(1, 5)] + [f"egt_{i}" for i in range(1, 5)] + ["oil_p", "oil_t", "fuel_flow", "map_kpa", "rpm"]
    return BayesianIsolator(ENGINE, names), names


def test_quiet_residual_is_nominal_and_offsets_are_typed():
    iso, names = _isolator()
    iso.update(np.random.default_rng(1).normal(0.0, 0.3, len(names)))
    assert iso.posterior()[0].kind == "NOMINAL"
    iso.reset()
    z = np.zeros(len(names))
    z[names.index("cht_3")] = 6.0                       # one sender reads high, nothing coupled moves
    for _ in range(30):
        iso.update(z)
    top = iso.posterior()[0]
    assert top.kind == "SENSOR" and top.channel == "cht_3"


def test_process_signature_with_location_is_recovered():
    iso, names = _isolator()
    fid, kind, cyl, ch, m, _p = next(h for h in iso.hyp if h[0] == "F01" and h[2] == 3)
    for _ in range(30):
        iso.update(0.4 * m)                              # misfire on cylinder 3 at 40 % of the calibrated size
    top = iso.posterior()[0]
    assert (top.fault_id, top.cylinder, top.kind) == ("F01", 3, "PROCESS")
    assert top.severity == pytest.approx(0.4, abs=0.05)
    d = directive([h.to_dict() for h in iso.posterior()])
    assert d["fault_id"] == "F01" and "3" in d["maintenance_action"]["text"] and d["ata_chapter"]


@pytest.mark.parametrize("fault_id,cylinder,channel,expect", [
    ("F01", 3, None, ("F01", 3, None)),
    ("S02", None, "cht[2]", ("S02", None, "cht_2")),
    ("F13", None, None, ("F13", None, None)),
])
def test_injected_fault_leads_on_the_plant(fault_id, cylinder, channel, expect):
    src, det = calibrated(ENGINE, 1001)
    iso = BayesianIsolator(ENGINE, det.cal.channel_names())
    op = (70.0, 7000.0, 15.0)
    for _ in range(200):
        f, _ = src.step(1.0, throttle_pct=op[0], altitude_ft=op[1], oat_c=op[2])
        iso.update(det.score(f).z_raw)
    src.apply(SimpleNamespace(fault_id=fault_id, cylinder=cylinder, channel=channel, severity=0.8, ramp_s=60.0,
                              t0_s=src.now()))
    for _ in range(300):
        f, _ = src.step(1.0, throttle_pct=op[0], altitude_ft=op[1], oat_c=op[2])
        iso.update(det.score(f).z_raw)
    top = iso.posterior(det.cal.sensor_coupling(f))[0]
    assert (top.fault_id, top.cylinder, top.channel) == expect, top
    assert top.posterior > 0.5
