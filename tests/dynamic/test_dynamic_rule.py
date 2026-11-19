"""Card M0-12: the "completely dynamic" rule tests (P Part 0.3). Off items are strict xfails naming their card."""
import ast
import hashlib
import json
from pathlib import Path

import pytest

from backend.runtime.engine_runtime import EngineRuntime
from tests.dynamic.scan import ROOT, scan

BASELINE = json.loads((Path(__file__).with_name("dyn_baseline.json")).read_text(encoding="utf-8"))
INFERENCE = ["backend/detect", "backend/diagnose", "backend/prognose", "backend/twin", "backend/status"]
TRUTH = ("backend.faults.manager", "backend.sim.faults")


def test_t_dyn_1_static_scan_never_increases():
    regressions = []
    for rel, counts in scan().items():
        allowed = BASELINE.get(rel, {})
        for rule, n in counts.items():
            if n > allowed.get(rule, 0):
                regressions.append(f"{rel}: {rule} {allowed.get(rule, 0)} -> {n}")
    assert not regressions, "dynamic-rule breaks increased (P Part 0):\n" + "\n".join(regressions)


def test_t_dyn_4_inference_never_imports_fault_truth():
    hits = []
    for pkg in INFERENCE:
        for path in (ROOT / pkg).rglob("*.py") if (ROOT / pkg).exists() else []:
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                mods = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                       [node.module or ""] if isinstance(node, ast.ImportFrom) else []
                hits += [f"{path.relative_to(ROOT)}: {m}" for m in mods if m.startswith(TRUTH)]
    assert not hits, hits


def _run(seed):
    rt = EngineRuntime(BASELINE_ENGINE, seed=seed, warmup_ticks=400)
    rt.calibrate()
    h = hashlib.sha256()
    for _ in range(30):
        f = rt.tick().frame
        h.update(repr((f.t, f.rpm, f.oil_p, tuple(f.cht), tuple(f.egt))).encode())
    return h.hexdigest()


BASELINE_ENGINE = sorted(p.stem for p in (ROOT / "configs" / "engines").glob("*.json"))[0]


def test_t_dyn_7_determinism_same_seed_same_frames():
    assert _run(7) == _run(7)
    assert _run(7) != _run(8)


SIM_DT = 0.05
ENGINES = sorted(p.stem for p in (ROOT / "configs" / "engines").glob("*.json"))


def _sensors_cfg(engine_id):
    return json.loads((ROOT / "configs" / "sensors" / f"{engine_id}.json").read_text(encoding="utf-8"))


def _channel(frame, name):
    if name.endswith("[*]"):
        series = getattr(frame, name[:-3])
        return None if any(v is None for v in series) else sum(series) / len(series)
    return getattr(frame, name)


@pytest.mark.parametrize("engine_id", ENGINES)
def test_t_dyn_2_no_frozen_channels(engine_id):
    """120 s of simulated time, throttle 30->100->30 %, altitude 0->15,000 ft: every load-dependent channel moves by
    more than 5 sensor-noise sigmas (configs/sensors load_dependent, noise from configs/physics sensors)."""
    from backend.sim.source import SimSource
    src = SimSource(engine_id, seed=0)
    channels = _sensors_cfg(engine_id)["load_dependent"]["channels"]
    seen = {c: [] for c in channels}
    n = int(120 / SIM_DT)
    for i in range(n):
        x = i / n
        frame, _ = src.step(SIM_DT, throttle_pct=30 + 70 * (1 - abs(2 * x - 1)), altitude_ft=15000 * x)
        for c in channels:
            v = _channel(frame, c)
            if v is not None:
                seen[c].append(v)
    frozen = []
    for c, vals in seen.items():
        sigma = src.sensors.sigma(c.replace("[*]", "[1]"), sum(vals) / len(vals))
        if not vals or max(vals) - min(vals) <= 5 * sigma:
            frozen.append(f"{c}: range {max(vals) - min(vals) if vals else None} <= 5 sigma ({5 * sigma:.3g})")
    assert not frozen, frozen


def _outputs(o):
    return {"power_kw": o.power_kw, "map_kpa": o.map_kpa, "fuel_flow": o.fuel_kg_h, "oil_t": o.oil_c,
            "coolant_t": o.coolant_c, "cht_mean": sum(o.cht) / len(o.cht), "egt_mean": sum(o.egt) / len(o.egt)}


@pytest.mark.parametrize("engine_id", ENGINES)
def test_t_dyn_3_perturbation_signs(engine_id):
    """From a trimmed cruise point (600 s), change one input at a time and run 300 s: every output named in the
    configs/sensors sensitivity table moves in its declared sign. Plant truth (no sensor noise)."""
    import copy
    from backend.sim.source import SimSource
    cfg = _sensors_cfg(engine_id)
    trim = {k: v for k, v in cfg["cruise_trim"].items() if k not in ("status", "ref")}
    src = SimSource(engine_id, seed=0)

    def apply(s, c):
        lv = s.plant.levers
        lv.throttle_pct, lv.altitude_ft, lv.isa_dev_c, lv.humidity_pct = (
            c["throttle_pct"], c["altitude_ft"], c["isa_dev_c"], c["humidity_pct"])
        lv.tas_kt = c["tas_kt"]

    def run(s, seconds):
        o = None
        for _ in range(int(seconds / SIM_DT)):
            o = s.advance(SIM_DT)
        return o

    apply(src, trim)
    run(src, 600)
    wrong = []
    base = _outputs(run(copy.deepcopy(src), 300))
    for lever, spec in cfg["sensitivity"].items():
        if lever in ("status", "ref"):
            continue
        s = copy.deepcopy(src)
        c = dict(trim)
        current = s.plant.core.design_tas_kt if (lever == "tas_kt" and c[lever] is None) else c[lever]
        c[lever] = current + spec["delta"]
        apply(s, c)
        o = s.plant
        out = _outputs(run(s, 300))
        assert o.state == "RUNNING", f"{lever}: engine left RUNNING ({o.failure})"
        for name, sign in spec["expect"].items():
            d = out[name] - base[name]
            if d * sign <= 0:
                wrong.append(f"{lever} +{spec['delta']}: {name} moved {d:+.4g}, expected sign {sign:+d}")
    assert not wrong, wrong


@pytest.mark.xfail(strict=True, reason="T-DYN-5 add-an-engine: the plant calibrates from config alone (M1); still needs a placeholder GLB + manifest and the UI menus checked with Playwright (M8)")
def test_t_dyn_5_add_an_engine():
    raise NotImplementedError


def test_t_dyn_6_add_a_fault(tmp_path):
    """A new registry entry (config only, no code) is accepted, applied through its parameter_effects, and moves
    its expected signature in a paired run."""
    from backend.faults.registry import load_fault_registry
    from backend.physics.engine_config import load_engine_config
    from backend.sim.signature import run_pair
    data = json.loads((ROOT / "configs" / "faults.json").read_text(encoding="utf-8"))
    base = next(f for f in data["faults"] if f["kind"] == "PHYSICAL" and f["scope"] == "ENGINE"
                and any(e["parameter"] == "pump_health" for e in f["parameter_effects"]))
    new = json.loads(json.dumps(base))
    new.update(id="F99", name="TEST_ADDED_OIL_PUMP_WEAR", legacy_ids=[], plant_mode_legacy=None)
    new["parameter_effects"] = [{"component": "thermal", "parameter": "pump_health", "op": "scale",
                                 "at_full_severity": 0.4}]
    new["expected_signature"] = [{"channel": "oil_p", "direction": -1, "min_delta": 0.3, "unit": "bar"}]
    data["faults"].append(new)
    path = tmp_path / "faults.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    reg = load_fault_registry(path)
    cfg = load_engine_config(ENGINES[0])
    assert reg.get("F99") in reg.applicable(cfg)
    res = run_pair(cfg, reg, "F99")
    assert res and all(r.ok for r in res), [(r.channel, r.delta) for r in res]


def test_t_dyn_8_no_silent_fallback():
    """S05 dropout on a channel: the runtime keeps running and the published state has NO value for it (the UI shows
    NO DATA), never a substituted number."""
    from backend.faults.manager import FaultManager, RuntimeAdapter
    from backend.faults.registry import load_fault_registry
    from backend.server.state_builder import build_state
    rt = EngineRuntime(BASELINE_ENGINE, seed=3, warmup_ticks=400)
    rt.calibrate()
    mgr = FaultManager(load_fault_registry(), rt.cfg, RuntimeAdapter(rt))
    mgr.inject("S05", channel="oil_p", severity=1.0, ramp_s=1, source="test")
    for _ in range(3):
        tick = rt.tick()
    assert tick.frame.oil_p is None
    msg = build_state(tick, seq=1, registry=mgr.registry, active_faults=mgr.active())
    assert "oil_p" not in msg.readings or msg.readings["oil_p"].value is None
