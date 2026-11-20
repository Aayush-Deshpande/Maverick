"""M7-01/02/04: engine telemetry over a python-can bus (T-CAN-1, T-CAN-2)."""
import copy

import pytest

can = pytest.importorskip("can")
pytest.importorskip("cantools")

from backend.core.frame import Frame                                   # noqa: E402
from backend.sources.can_link import CanLink                           # noqa: E402

FRAME = Frame(t=12.0, source="PLANT", engine_config_id="rotax_912is", rpm=5432.1, prop_rpm=2235.4, map_kpa=84.37,
              throttle=72.0, cht=[101.23, 99.87, 103.4, 98.76], egt=[742.33, 751.2, 739.94, 760.01], coolant_t=88.4,
              oil_p=3.456, oil_t=96.78, fuel_flow=17.42, fuel_p=3.01, rail_p=None, bus_v=14.21, bus_i=21.5, batt_i=-1.5,
              gearbox_t=None, vibration_orders={"0.5X": 0.412, "1X": 0.233, "2X": 1.87})


@pytest.fixture
def link():
    lk = CanLink(channel="anumaan-test-link")
    yield lk
    lk.close()


def test_every_channel_crosses_the_bus_within_one_resolution_step(link):
    out = link.roundtrip(copy.deepcopy(FRAME))
    for s in link.sigs:
        sent = s.path.partition(".")
        before = getattr(FRAME, sent[0]) if not sent[2] else (FRAME.vibration_orders.get(sent[2]) if sent[0] == "vibration_orders" else getattr(FRAME, sent[0])[int(sent[2])])
        after = getattr(out, sent[0]) if not sent[2] else (out.vibration_orders.get(sent[2]) if sent[0] == "vibration_orders" else getattr(out, sent[0])[int(sent[2])])
        if before is None:
            assert after is None, s.path                       # NOT AVAILABLE arrives as null, never a number
        else:
            assert after == pytest.approx(before, abs=s.signal.scale / 2 + 1e-9), s.path
    assert link.alerts == [] and link.bytes_sent == 6 * 8


def test_intrusion_detector_flags_spoofed_and_broken_traffic(link):
    link.roundtrip(copy.deepcopy(FRAME))                       # one clean message set (counters 0)
    ids = link.ids
    msg = link.db.get_message_by_name("ANU_FLUID")
    kinds = {a.kind for a in ids.inspect_frame(0x18FF10FF, 8, bytes(8), 13.0)}
    assert "UNKNOWN_ID" in kinds
    skipped = msg.encode({"OilPressure": 300, "OilTemperature": 1300, "CoolantTemperature": 1280, "FuelFlow": 1742,
                          "Counter": 5}, scaling=False)          # counter jumps 0 -> 5
    assert "SEQUENCE_GAP" in {a.kind for a in ids.inspect_frame(msg.frame_id, 8, skipped, 13.0)}
    impossible = msg.encode({"OilPressure": 300, "OilTemperature": 1300, "CoolantTemperature": 4000, "FuelFlow": 1742,
                             "Counter": 6}, scaling=False, strict=False)   # coolant 360 C: outside the DBC's physical range
    assert "OUT_OF_RANGE" in {a.kind for a in ids.inspect_frame(msg.frame_id, 8, impossible, 14.0)}


@pytest.mark.slow
def test_t_can_1_diagnosis_over_can_matches_direct():
    """The same engine, seed and fault, once DIRECT and once over the CAN bus: same status and top hypothesis."""
    from backend.runtime.engine_runtime import EngineRuntime
    results = []
    for source in ("DIRECT", "CAN"):
        rt = EngineRuntime("rotax_912is", seed=3, data_source=source)
        rt.calibrate()
        rt.inject_fault("F23", severity=1.0, ramp_sec=20)
        tick = None
        for _ in range(120):
            tick = rt.tick()
        status = (getattr(tick, "status", None) or {}).get("level")
        hyps = [h.get("fault_id") for h in getattr(tick, "hypotheses", None) or [] if h.get("fault_id")]
        results.append((status, hyps[:1]))
        if rt.can_link is not None:
            assert rt.can_link.alerts == []                      # clean bus: no intrusion alerts
            rt.can_link.close()
    assert results[0] == results[1]
    assert results[1][1] == ["F23"]
