"""M1-13 registry faults -> plant parameters (fast unit checks; T-FLT-2: faults change parameters only)."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.faults.registry import load_fault_registry
from backend.physics.engine_config import available_engines, load_engine_config
from backend.sim.faults import FaultParameters, effective_severity

REG = load_fault_registry()


def fault(fid, cyl=None, sev=1.0, ramp=10.0, t0=0.0, channel=None):
    return SimpleNamespace(fault_id=fid, cylinder=cyl, channel=channel, severity=sev, ramp_s=ramp, t0_s=t0)


def test_ramp_is_in_simulated_seconds():
    f = fault("F01", 2, sev=0.8, ramp=10.0, t0=100.0)
    assert effective_severity(f, 100.0) == 0.0
    assert effective_severity(f, 105.0) == pytest.approx(0.4)
    assert effective_severity(f, 500.0) == pytest.approx(0.8)


@pytest.mark.parametrize("engine_id", available_engines())
def test_every_applicable_fault_maps_to_model_inputs(engine_id):           # no registry parameter is ignored
    cfg = load_engine_config(engine_id)
    fp = FaultParameters(cfg, REG)
    healthy, _ = fp.health([], 1000.0)
    for spec in REG.applicable(cfg):
        cyl = 2 if spec.raw["scope"] == "CYLINDER" else None
        ch = "oil_p" if spec.raw["scope"] == "CHANNEL" else None
        h, sensors = fp.health([fault(spec.id, cyl, channel=ch)], 1000.0)
        assert h != healthy or sensors, f"{engine_id} {spec.id} changed nothing"


def test_per_cylinder_faults_touch_only_their_cylinder():
    cfg = load_engine_config(available_engines()[0])
    h, _ = FaultParameters(cfg, REG).health([fault("F01", 3)], 1000.0)
    assert h["quality"][2] == 0.0 and all(q == 1.0 for i, q in enumerate(h["quality"]) if i != 2)


def test_sensor_faults_leave_the_engine_healthy():
    cfg = load_engine_config(available_engines()[0])
    fp = FaultParameters(cfg, REG)
    h, sensors = fp.health([fault("S03", channel="cht[2]")], 1000.0)
    assert h == fp.health([], 1000.0)[0] and sensors[0]["channel"] == "cht[2]"


def test_t_flt_2_sim_faults_module_writes_no_outputs():
    src = Path(__file__).resolve().parents[2] / "backend" / "sim" / "faults.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for output in ("cht", "egt", "oil_bar", "bus_v", "rpm", "map_pa", "power_kw"):
        assert output not in names, f"faults.py touches the output {output}"
