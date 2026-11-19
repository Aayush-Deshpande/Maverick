"""Card M0-04: fault manager. Edge cases from ANUMAAN_AUDIT_REPORT.txt section 19.4 that apply at this layer."""
import pytest

from backend.faults.manager import FaultManager, LegacyRuntimeAdapter
from backend.faults.registry import FaultRejected, load_fault_registry
from backend.physics.engine_config import load_engine_config


class FakeSim:
    def __init__(self, supported=("MISFIRE", "OIL_PRESSURE_LOSS", "COOLING_DEGRADATION")):
        self.t = 0.0
        self.applied = []
        self.clears = 0
        self.supported = set(supported)

    def now(self):
        return self.t

    def apply(self, fault):
        self.applied.append((fault.fault_id, fault.cylinder, fault.severity))
        return fault.plant_mode in self.supported

    def clear_all(self):
        self.clears += 1
        self.applied.clear()


@pytest.fixture
def mgr():
    events = []
    m = FaultManager(load_fault_registry(), load_engine_config("rotax_912is"), FakeSim(), on_event=events.append)
    m.events = events
    return m


def test_inject_records_source_and_event(mgr):
    f = mgr.inject("F01", cylinder=2, severity=0.7, ramp_s=5, source="3d")
    assert f.fault_id == "F01" and f.cylinder == 2 and f.source == "3d" and f.simulated
    assert mgr.events[-1].type == "FAULT_INJECTED" and "cylinder 2" in mgr.events[-1].text


def test_defaults_from_registry(mgr):
    f = mgr.inject("F23")
    assert f.severity == 0.8 and f.ramp_s == 60.0 and f.cylinder is None


def test_inapplicable_fault_rejected_and_logged(mgr):
    with pytest.raises(FaultRejected, match="fuel_system"):
        mgr.inject("F12")                                     # carburettor icing on the injected 912
    assert mgr.events[-1].type == "FAULT_REJECTED"
    assert mgr.active() == []


@pytest.mark.parametrize("kwargs,match", [
    (dict(fault_id="F01"), "cylinder"),                       # per-cylinder fault without a cylinder
    (dict(fault_id="F01", cylinder=0), "cylinder"),
    (dict(fault_id="F01", cylinder=5), "cylinder"),
    (dict(fault_id="F23", severity=1.5), "severity"),
    (dict(fault_id="F23", ramp_s=-1), "ramp"),
    (dict(fault_id="F23", source="hacker"), "source"),
    (dict(fault_id="NOPE"), "unknown"),
])
def test_invalid_requests_rejected(mgr, kwargs, match):
    with pytest.raises(FaultRejected, match=match):
        mgr.inject(**kwargs)


def test_repeated_request_id_is_idempotent(mgr):
    a = mgr.inject("F23", request_id="click-1")
    b = mgr.inject("F23", request_id="click-1")
    assert a.uuid == b.uuid and len(mgr.active()) == 1


def test_same_fault_same_place_updates_instead_of_duplicating(mgr):
    a = mgr.inject("F01", cylinder=2, severity=0.4)
    b = mgr.inject("F01", cylinder=2, severity=0.9)
    assert a.uuid == b.uuid and b.severity == 0.9 and len(mgr.active()) == 1
    assert mgr.events[-1].type == "FAULT_UPDATED"
    c = mgr.inject("F01", cylinder=3)
    assert c.uuid != a.uuid and len(mgr.active()) == 2       # other cylinder = second fault


def test_two_faults_coexist_and_clear_one_keeps_the_other(mgr):
    a = mgr.inject("F23")
    b = mgr.inject("F19", cylinder=1)
    mgr.clear(a.uuid)
    assert [f.uuid for f in mgr.active()] == [b.uuid]
    assert mgr.sim.applied == [("F19", 1, b.severity)]      # remaining fault re-applied to the simulation


def test_clear_all_and_unknown_uuid(mgr):
    mgr.inject("F23")
    mgr.inject("F19", cylinder=1)
    cleared = mgr.clear()
    assert len(cleared) == 2 and mgr.active() == []
    with pytest.raises(FaultRejected):
        mgr.clear("does-not-exist")


def test_fault_without_plant_support_is_accepted_not_dropped(mgr):
    f = mgr.inject("F32")                                     # alternator: no legacy plant mode yet
    assert not f.simulated and f in mgr.active()
    assert "not yet simulated" in mgr.events[-1].text


def test_sensor_fault_needs_a_channel(mgr):
    with pytest.raises(FaultRejected, match="channel"):
        mgr.inject("S03")
    f = mgr.inject("S03", channel="cht[2]")
    assert f.channel == "cht[2]" and f.cylinder is None


def test_legacy_runtime_adapter_drives_the_real_plant():
    from backend.runtime.engine_runtime import EngineRuntime
    rt = EngineRuntime("rotax_912is", seed=3)
    m = FaultManager(load_fault_registry(), rt.cfg, LegacyRuntimeAdapter(rt))
    f = m.inject("F01", cylinder=2, severity=0.9, ramp_s=1, source="test")
    assert f.simulated
    assert [(i["mode"], i["cylinder"]) for i in rt.injected] == [("MISFIRE", 2)]
    m.clear()
    assert rt.injected == []
