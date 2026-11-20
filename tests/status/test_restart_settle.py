"""A restart is not a fault: after RESET + START the start-up transient is not diagnosed (configs/runtime.json
restart_settle_s), and diagnosis then starts from a clean, healthy state."""
from backend.runtime.engine_runtime import EngineRuntime


def test_no_fault_is_diagnosed_after_resetting_a_seized_engine():
    rt = EngineRuntime("rotax_912is", seed=4)
    rt.calibrate()
    rt.inject_fault("F23", severity=1.0, ramp_sec=5)
    for _ in range(400):
        tick = rt.tick()
    assert tick.frame.engine_state == "FAILED"                    # the oil chain seized it
    rt.clear_faults()
    rt.engine_command("RESET")
    rt.engine_command("START")
    confident = []
    for _ in range(150):
        tick = rt.tick()
        confident += [h["fault_id"] for h in tick.hypotheses or [] if h.get("fault_id") and h["posterior"] >= 0.7]
    assert tick.frame.engine_state == "RUNNING" and confident == []
