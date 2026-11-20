"""M3-03 sensor validation / FDI: sensor faults visible on one channel are caught and typed, nominal flights stay
(almost) clean, latency is measured (idea text I-02 says ~40 ms), and a quarantined sensor is replaced by the
observer's estimate marked VIRTUAL."""
import pytest

from backend.detect.sensor_fdi import SensorFDI
from backend.physics.engine_config import available_engines
from backend.sources import PlantSource

STRAY_BUDGET = 3          # stray verdicts allowed per 30 min nominal flight (each one is a short ADVISORY)


@pytest.mark.parametrize("engine_id", available_engines())
def test_nominal_flight_is_clean_and_fast(engine_id):
    src, fdi = PlantSource(engine_id, seed=4), SensorFDI(engine_id)
    verdicts, worst_ms = [], 0.0
    for i in range(1800):
        thr = 60 if (i // 300) % 2 == 0 else 90                     # throttle steps and climbs: a real flight
        f, _ = src.step(1.0, throttle_pct=thr, altitude_ft=5000 + (i // 600) * 4000, oat_c=10)
        r = fdi.validate(f)
        verdicts += r.verdicts
        worst_ms = max(worst_ms, r.latency_ms)
    assert len(verdicts) <= STRAY_BUDGET, [(v.channel, v.fault) for v in verdicts]
    assert worst_ms < 40.0                                          # I-02 claim; measured value ~0.3 ms


@pytest.mark.parametrize("sensor_fault,channel,expected,within_s", [
    ("S01", "cht[2]", "FROZEN", 12), ("S04", "oil_t", None, 5), ("S05", "oil_p", "DROPOUT", 1),
    ("S06", "egt[1]", "OUT_OF_RANGE", 1), ("S07", "map_kpa", "LANE_DISAGREE", 3)])
def test_sensor_faults_are_caught_and_typed(sensor_fault, channel, expected, within_s):
    engine = "rotax_914"
    src, fdi = PlantSource(engine, seed=4), SensorFDI(engine)
    name = channel.replace("[", "_").replace("]", "")
    caught = None
    for i in range(120):
        if i == 50:
            src.inject_fault(sensor_fault, channel=channel, severity=1.0, ramp_sec=1)
        f, _ = src.step(1.0, 70, 5000, 10)
        r = fdi.validate(f)
        if i >= 50 and caught is None and name in r.quarantined:
            caught = (i - 50, [v.fault for v in r.verdicts if v.channel == name])
    assert caught is not None and caught[0] <= within_s, caught
    if expected:
        assert expected in caught[1]
    for _ in range(3):                                              # the other sensors stay trusted
        f, _ = src.step(1.0, 70, 5000, 10)
        assert fdi.validate(f).quarantined == [name]


def test_quarantined_cht_is_published_virtual_from_the_observer():
    from backend.runtime.engine_runtime import EngineRuntime
    from backend.server.state_builder import build_state
    rt = EngineRuntime("rotax_912is", seed=2, warmup_ticks=400)
    rt.calibrate()
    for _ in range(30):
        rt.tick()
    rt.inject_fault("S06", cylinder=2, severity=1.0, ramp_sec=1)   # CHT 2 sender reads an impossible value
    for _ in range(12):
        t = rt.tick()
    msg = build_state(t, seq=1)
    r = msg.readings["cht[2]"]
    true_cht = rt.source.last.cht[1]
    assert r.quality == "VIRTUAL" and abs(r.value - true_cht) < 10.0
