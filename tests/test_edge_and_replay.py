"""W3/W4: recorder/replay bit-exactness and the edge node's gated downlink accounting."""
import numpy as np
import pytest

from backend.detect import ResidualDetector
from backend.edge.node import EdgeNode, HOST, PI5_EMULATED
from backend.sources import PlantSource
from backend.sources.recorder import ReplaySource, record

OPS = [(45, 2000, 25), (60, 9000, 10), (75, 12000, 0), (90, 18000, -15)]


def flight(src, n, seed, fault=None):
    rng = np.random.default_rng(seed)
    if fault:
        src.inject_fault(fault, severity=1.0, ramp_sec=60.0)
    op, out = OPS[0], []
    for i in range(n):
        if i % 30 == 0:
            op = OPS[int(rng.integers(len(OPS)))]
        out.append(src.step(1.0, throttle_pct=op[0], altitude_ft=op[1], oat_c=op[2]))
    return out


@pytest.fixture(scope="module")
def tail():
    src = PlantSource("rotax_914", seed=4)
    nominal = [f for f, _ in flight(src, 900, 1)][24:]
    return src, ResidualDetector.calibrate(nominal, alpha=0.01)


def test_record_replay_is_bit_exact(tmp_path):
    src = PlantSource("rotax_914", seed=1)
    pairs = flight(src, 60, 2, "COOLING_DEGRADATION")
    p = record(tmp_path / "run", [f for f, _ in pairs], [t for _, t in pairs], {"origin": "test"})
    rs = ReplaySource(p)
    back = list(rs.frames())
    assert len(back) == 60 and all(b.source == "REPLAY" for b in back)
    assert back[10].cht == pairs[10][0].cht and back[10].rpm == pairs[10][0].rpm
    assert rs.truths()[-1]["active_faults"], "truth kept out-of-band for evaluation"


def test_replay_detects_tampering(tmp_path):
    src = PlantSource("rotax_914", seed=1)
    p = record(tmp_path / "r", [f for f, _ in flight(src, 30, 2)])
    p.write_text(p.read_text().replace("rotax_914", "rotax_915is", 1), encoding="utf-8")
    with pytest.raises(ValueError):
        ReplaySource(p)


def test_edge_gates_downlink_and_accounts(tail):
    src, det = tail
    node = EdgeNode(det, PI5_EMULATED)
    for f, _ in flight(src, 300, 5):
        node.process(f)
    quiet = node.report()
    assert quiet["reduction_vs_waveform"] > 1000 and quiet["evidence"] == "EMULATED"
    for f, _ in flight(src, 150, 6, "COOLING_DEGRADATION"):
        node.process(f)
    loud = node.report()
    assert loud["bytes_sent"] > quiet["bytes_sent"]          # alarms cost bytes, quiet flight almost none
    assert loud["latency_ms_p99"] < 50.0                      # inside the 20 Hz frame budget even with 4x slowdown


def test_host_profile_is_labelled_measured(tail):
    assert EdgeNode(tail[1], HOST).report()["evidence"] == "MEASURED"
