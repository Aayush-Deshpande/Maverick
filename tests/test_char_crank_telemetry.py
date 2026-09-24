"""Characterization tests (B0.9): ml/crank_diagnostics, telemetry/{mavlink_efi,socketcan_bridge}."""
import random
import types

import pytest

from backend.ml.crank_diagnostics import (
    CrankDiagnostics, angular_resample, envelope_spectrum, order_features,
    order_spectrum,
)
from backend.physics.crank_dynamics import CrankDynamicsModel
from backend.telemetry.mavlink_efi import EFIFrame, MAVLinkEFISource, efi_to_anumaan
from backend.telemetry.socketcan_bridge import (
    PGN_EEC1, PGN_EGT, PGN_EFL1, PGN_ET1, PGN_TURBO, SocketCANBridge,
)


# ---- crank: shared, deterministic omega(theta) traces ---------------------

@pytest.fixture(scope="module")
def traces():
    m = CrankDynamicsModel()
    th, w_ok, _ = m.simulate_cycle(5200, 100, 1)
    m.set_misfire(2, 0.0)
    _, w_dead, _ = m.simulate_cycle(5200, 100, 1)
    m.clear_faults()
    m.set_misfire(2, 0.6)
    _, w_part, _ = m.simulate_cycle(5200, 100, 1)
    return th, w_ok, w_dead, w_part


def test_healthy_engine_is_nominal_and_uniform(traces):
    th, w_ok, _, _ = traces
    cd = CrankDiagnostics(4)
    for _ in range(30):
        contrib = cd.analyse_cycle(th, w_ok)
    assert [c.cylinder for c in contrib] == [1, 4, 2, 3]      # firing order 1-4-2-3
    r = cd.report()
    assert r.verdict == "NOMINAL" and r.cylinder is None
    assert all(v == pytest.approx(1.0, abs=1e-4) for v in r.contribution_ratio.values())
    assert r.severity_index < 1e-4
    assert r.misfire_rate == 0.0
    assert "within tolerance" in r.sentence()


def test_dead_cylinder_attributed_and_net_absorbing(traces):
    th, w_ok, w_dead, _ = traces
    cd = CrankDiagnostics(4)
    for _ in range(30):
        cd.analyse_cycle(th, w_dead)
    r = cd.report()
    assert r.verdict == "MISFIRING" and r.cylinder == 2
    assert r.misfire_rate == 1.0
    assert r.contribution_ratio[2] == pytest.approx(-2.93, abs=0.05)   # net drag, not clamped
    assert r.severity_index == pytest.approx(3.93, abs=0.05)
    for c in (1, 3, 4):
        assert r.contribution_ratio[c] == pytest.approx(1.0, abs=1e-3)
    assert "net absorbing" in r.sentence()
    d = r.as_dict()
    assert d["MISFIRE_CYLINDER"] == 2 and d["COMBUSTION_VERDICT"] == "MISFIRING"


def test_partial_misfire_reads_as_partial_but_still_flagged(traces):
    th, _, _, w_part = traces
    cd = CrankDiagnostics(4)
    for _ in range(30):
        cd.analyse_cycle(th, w_part)
    r = cd.report()
    assert r.cylinder == 2 and r.verdict == "MISFIRING"
    assert r.contribution_ratio[2] == pytest.approx(-2.81, abs=0.05)


@pytest.mark.parametrize("n_bad,rate,verdict", [(60, 0.060, "WEAK_CYLINDER"),
                                                (140, 0.140, "WEAK_CYLINDER"),
                                                (407, 0.407, "MISFIRING")])
def test_misfire_rate_recovered_exactly(traces, n_bad, rate, verdict):
    """Headline (B0.9): intermittent-misfire rate is recovered 6.0 / 14.0 / 40.7 %."""
    th, w_ok, w_dead, _ = traces
    n = 1000
    bad = set(random.Random(0).sample(range(n), n_bad))
    cd = CrankDiagnostics(4, history_cycles=n)
    for i in range(n):
        cd.analyse_cycle(th, w_dead if i in bad else w_ok)
    r = cd.report()
    assert r.cylinder == 2
    assert r.misfire_rate == pytest.approx(rate, abs=1e-9)
    assert r.verdict == verdict
    assert r.per_cylinder_rate[1] == r.per_cylinder_rate[3] == r.per_cylinder_rate[4] == 0.0


def test_misfire_rate_monotone_in_fault_frequency(traces):
    th, w_ok, w_dead, _ = traces
    rates = []
    for n_bad in (0, 20, 60, 120):
        cd = CrankDiagnostics(4)
        for i in range(200):
            cd.analyse_cycle(th, w_dead if i < n_bad else w_ok)
        rates.append(cd.report().per_cylinder_rate[2])
    assert rates == sorted(rates) and rates[0] == 0.0 and rates[-1] > 0.5


def test_crank_diagnostics_reset_and_validation(traces):
    th, w_ok, w_dead, _ = traces
    cd = CrankDiagnostics(4)
    for _ in range(20):
        cd.analyse_cycle(th, w_dead)
    cd.reset()
    r = cd.report()
    assert r.verdict == "NOMINAL" and r.per_cylinder_rate[2] == 0.0
    with pytest.raises(ValueError):
        cd.analyse_cycle([0.0, 1.0], [1.0])
    assert cd.cylinder_for_interval(5) == 4


def test_healthy_four_cylinder_order2_dominance(traces):
    th, w_ok, w_dead, _ = traces
    o, s = order_spectrum(w_ok, 360)                        # 2 revs of 360 samples
    f = order_features(o, s)
    assert f["ORDER_DOMINANT"] == pytest.approx(2.0, abs=0.06)
    assert f["ORDER_2_MAG"] > 2 * f["ORDER_4_MAG"] > 0
    assert f["ORDER_2_FRAC"] == pytest.approx(0.328, abs=0.02)
    assert f["ORDER_0.5_FRAC"] < 0.01 and f["ORDER_1_FRAC"] < 0.01
    # a dead cylinder moves the energy to the misfire line (order 0.5)
    fm = order_features(*order_spectrum(w_dead, 360))
    assert fm["ORDER_DOMINANT"] == pytest.approx(0.5, abs=0.06)
    assert fm["ORDER_0.5_FRAC"] > 10 * f["ORDER_0.5_FRAC"]
    assert fm["ORDER_2_FRAC"] < f["ORDER_2_FRAC"]


def test_order_helpers_edge_cases():
    assert order_spectrum([1.0, 2.0]) == ([], [])
    assert order_features([], []) == {}
    assert envelope_spectrum([0.0] * 4, 1000.0) == ([], [])
    assert angular_resample([0, 1], [0, 1], [0.0]) == ([], [])


def test_angular_resample_speed_invariant_order_bin():
    import math
    # 3 revs at constant speed, signal = 2 cycles per rev, 5 kHz sampling
    rev_t = 0.02
    t = [i / 5000.0 for i in range(int(4 * rev_t * 5000))]
    sig = [math.sin(2 * math.pi * 2 * ti / rev_t) for ti in t]
    tach = [k * rev_t for k in range(4)]
    th, x = angular_resample(t, sig, tach, samples_per_rev=128)
    o, s = order_spectrum(x, 128)
    f = order_features(o, s, targets=(2.0,))
    assert f["ORDER_DOMINANT"] == pytest.approx(2.0, abs=0.35)


def test_envelope_spectrum_finds_modulation_tone():
    import math
    fs, n = 10000.0, 8192
    sig = [(1 + 0.8 * math.cos(2 * math.pi * 87.0 * i / fs)) * math.sin(2 * math.pi * 1500.0 * i / fs)
           for i in range(n)]
    f, a = envelope_spectrum(sig, fs)
    peak = f[max(range(1, len(a)), key=lambda i: a[i])]
    assert peak == pytest.approx(87.0, abs=2.0)


# ---- mavlink EFI ----------------------------------------------------------

def test_efi_to_anumaan_dict_mapping_and_units():
    msg = {"rpm": 5200, "cylinder_head_temperature": 118.5, "exhaust_gas_temperature": 760,
           "intake_manifold_pressure": 101.3, "fuel_flow": 240.0, "health": 1, "ecu_index": 0,
           "ignition_voltage": 14.1, "throttle_position": 62.0}
    fr = efi_to_anumaan(msg, t_sec=12.5)
    assert isinstance(fr, EFIFrame) and fr.healthy is True and fr.t_sec == 12.5
    c = fr.channels
    assert c["ENGINE_RPM"] == 5200 and c["CHT_1"] == 118.5 and c["EGT_1"] == 760
    assert c["MAP"] == 101.3 and c["BUS_VOLTAGE"] == 14.1 and c["TPS"] == 62.0
    assert c["FUEL_FLOW_G_MIN"] == 240.0
    assert c["FUEL_FLOW"] == pytest.approx(240.0 * 60 / 720.0)     # 20 L/h of avgas
    assert "ECU_HEALTH" not in c and "ECU_INDEX" not in c
    d = fr.as_dict()
    assert d["T_SEC"] == 12.5 and d["ECU_HEALTH_OK"] is True
    jet = efi_to_anumaan(msg, fuel_density_g_per_l=804.0)
    assert jet.channels["FUEL_FLOW"] < c["FUEL_FLOW"]


def test_efi_object_input_missing_and_bad_fields():
    obj = types.SimpleNamespace(rpm=3000, health=0, ecu_index=2, exhaust_gas_temperature="bad")
    fr = efi_to_anumaan(obj)
    assert fr.channels == {"ENGINE_RPM": 3000.0}
    assert fr.healthy is False and fr.ecu_index == 2
    assert efi_to_anumaan({}).healthy is True            # health defaults to OK


def test_mavlink_source_health_without_connection():
    src = MAVLinkEFISource("udpin:127.0.0.1:1")
    h = src.health()
    assert h["connected"] is False and h["frames_seen"] == 0 and src.frames_seen == 0


# ---- socketcan bridge -----------------------------------------------------

def test_socketcan_disconnected_is_inert():
    b = SocketCANBridge()
    assert b.is_connected is False
    assert b.send_telemetry({"rpm": 1}) == 0
    assert b.read_telemetry() == {}
    st = b.stats()
    assert st["connected"] is False and st["frames_tx"] == 0


def test_socketcan_pack_decode_roundtrip():
    pytest.importorskip("can")
    b = SocketCANBridge()
    telem = {"ENGINE_RPM": 5200.0, "CHT_1": 135.0, "EGT_1": 750.0, "OIL_PRESSURE": 4.8,
             "OIL_TEMP": 95.0, "MAP": 102.0}
    frames = b.pack_frames(telem)
    assert [f.arbitration_id for f in frames] == [PGN_EEC1, PGN_ET1, PGN_EFL1, PGN_EGT, PGN_TURBO]
    assert all(len(f.data) == 8 and f.is_extended_id for f in frames)
    got = {}
    for f in frames:
        k, v = b.decode_frame(f)
        got[k] = v
    assert got["ENGINE_RPM"] == pytest.approx(5200.0, abs=0.125)
    assert got["CHT_1"] == pytest.approx(135.0, abs=1.0)
    assert got["EGT_1"] == pytest.approx(750.0, abs=0.05)
    assert got["OIL_PRESSURE"] == pytest.approx(4.8, abs=0.04)
    assert got["MAP"] == pytest.approx(102.0, abs=2.0)
    assert b._last_rx_telemetry["OIL_TEMP"] == pytest.approx(95.0, abs=1.0)


def test_socketcan_saturation_and_unknown_frame():
    pytest.importorskip("can")
    b = SocketCANBridge()
    f = b.pack_frames({"ENGINE_RPM": 1e9, "CHT_1": 1e4, "EGT_1": 1e9, "MAP": 1e6})
    assert b.decode_frame(f[0])[1] == pytest.approx(65535 * 0.125, abs=0.1)
    assert b.decode_frame(f[1])[1] == 215.0                # 8-bit, offset -40 => ceiling
    assert b.decode_frame(types.SimpleNamespace(arbitration_id=0x123, data=b"\0" * 8)) is None
    d = b.pack_frames({})                                  # defaults
    assert b.decode_frame(d[0])[1] == pytest.approx(5200.0, abs=0.2)
