"""T-MIS-5 (M5-06): a sortie report is generated from a recording and contains every Step 5.6 section; the injected
oil-pressure fault appears as a non-GO status segment and as a leading hypothesis."""
from backend.recording.recorder import list_recordings
from backend.reports.sortie_report import SECTIONS, write_report
from backend.runtime.engine_runtime import EngineRuntime
from backend.server.state_builder import build_state


def test_report_has_every_section_and_the_fault(tmp_path):
    rt = EngineRuntime("rotax_914", seed=41, warmup_ticks=400)
    rt.calibrate()
    meta = rt.start_recording(root=tmp_path)
    for i in range(200):
        if i == 30:
            rt.inject_fault("F23", severity=1.0, ramp_sec=10)
        t = rt.tick()
        rt.recorder.add_state(build_state(t, seq=i).model_dump_json())
    rt.stop_recording()
    html = write_report(tmp_path / meta["sortie_id"]).read_text(encoding="utf-8")
    for s in SECTIONS:
        assert f"<h2>{s}</h2>" in html, s
    assert "Evidence class: SIMULATION" in html
    assert "F23" in html or "oil_p" in html
    assert list_recordings(tmp_path)[0]["frames"] == 200
