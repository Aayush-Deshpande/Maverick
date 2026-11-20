"""D62: the ECU reports its own lane state (Rotax OM-912 i p.4-5 warning indicator); diagnosis takes a reported lane
loss as direct evidence. Engines without ECU lanes (914 dual CDI) report nothing and use the signature instead."""
from backend.physics.engine_config import load_engine_config
from backend.runtime.engine_runtime import EngineRuntime
from backend.sim.source import registry


def test_lost_ecu_lane_is_reported_and_diagnosed_without_a_residual_alarm():
    rt = EngineRuntime("rotax_912is", seed=2)
    rt.calibrate()
    assert rt.tick().frame.ecu_lanes_ok == load_engine_config("rotax_912is").ecu_lanes
    rt.inject_fault("F36", severity=1.0, ramp_sec=5)
    for _ in range(15):
        tick = rt.tick()
    assert tick.frame.ecu_lanes_ok == 1
    top = tick.hypotheses[0]
    assert top["fault_id"] == "F36" and top["group"] == "ECU self-test report" and top["posterior"] >= 0.9
    assert (tick.status or {}).get("level") == "CAUTION"            # continue, no dispatch; not an emergency


def test_lane_faults_split_by_who_can_report_them():
    reg = registry()
    assert reg.get("F04").applicability(load_engine_config("rotax_914"))[0]           # dual CDI, nothing reports it
    assert not reg.get("F04").applicability(load_engine_config("rotax_912is"))[0]     # ECU lanes: that is F36
    assert reg.get("F36").applicability(load_engine_config("rotax_912is"))[0]
