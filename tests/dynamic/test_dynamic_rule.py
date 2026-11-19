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


@pytest.mark.xfail(strict=True, reason="T-DYN-2 frozen channels: needs the M1 physics (card M1-14)")
def test_t_dyn_2_no_frozen_channels():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason="T-DYN-3 perturbation signs: needs configs/sensors sensitivity (card M1-14)")
def test_t_dyn_3_perturbation_signs():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason="T-DYN-5 add-an-engine: needs M1 calibration from config alone (card M1-14)")
def test_t_dyn_5_add_an_engine():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason="T-DYN-6 add-a-fault: needs registry-driven parameter effects (card M1-13)")
def test_t_dyn_6_add_a_fault():
    raise NotImplementedError


@pytest.mark.xfail(strict=True, reason="T-DYN-8 dropout -> NO DATA: needs S05 in the sensor layer (card M1-13)")
def test_t_dyn_8_no_silent_fallback():
    raise NotImplementedError
