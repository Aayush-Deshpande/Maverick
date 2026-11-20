"""T-MIS-3 (M5-04/05): a recorded sortie (mission + an injected fault) re-analysed from its measured Frames alone - a
fresh runtime of the same tail, no truth, no fault list - reproduces the identical decision timeline (status, reasons,
confirmed alarm, hypotheses). Recorded state messages read back page by page. A recording started late is reported
as not comparable instead of a false 'identical'."""
import json

from backend.recording.recorder import list_recordings, read_states
from backend.recording.replay import compare
from backend.runtime.engine_runtime import EngineRuntime


def _rt():
    rt = EngineRuntime("rotax_912is", seed=31, warmup_ticks=400)
    rt.calibrate()
    return rt


def test_reanalysis_reproduces_the_decision_timeline(tmp_path):
    rt = _rt()
    rt.start_mission("hot_weather_thar")
    meta = rt.start_recording(root=tmp_path)
    for i in range(240):
        if i == 40:
            rt.inject_fault("F23", severity=1.0, ramp_sec=20)
        t = rt.tick()
        rt.recorder.add_state(json.dumps({"seq": i, "level": t.status["level"]}))
    rt.stop_recording()
    d = tmp_path / meta["sortie_id"]
    res = compare(d, {**meta, **list_recordings(tmp_path)[0]})
    assert res["identical"] is True and res["ticks"] == 240, res
    levels = [s["level"] for s in read_states(d, 0, 1000)]
    assert "GO" in levels and any(x != "GO" for x in levels)     # the fault really changed the decisions


def test_late_recording_is_not_claimed_comparable(tmp_path):
    rt = _rt()
    for _ in range(5):
        rt.tick()
    meta = rt.start_recording(root=tmp_path)
    rt.tick()
    rt.stop_recording()
    res = compare(tmp_path / meta["sortie_id"], list_recordings(tmp_path)[0])
    assert res["identical"] is None and "not comparable" in res["reason"]
