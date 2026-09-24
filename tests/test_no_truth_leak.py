"""
Guards against ground-truth leaking into the live inference path (B0.1).

``EnginePhysicalState.FAULT_ID`` / ``HEALTH_INDEX`` / ``RUL_HOURS`` are fields the
*synthetic plant* stamps onto its own output for the evaluator's benefit (see
``docs/build/INTERFACES.md`` Sec 1-2: the planned ``Frame``/``TruthRecord`` split).
Real telemetry -- CAN, MAVLink, replayed flight data -- never carries a fault-ID
field, so any detector that reads one is cheating: it will look correct against
the synthetic generator and fall over on anything real.

This is a static source scan (AST-based, not an execution trace) over the
live-inference packages. It deliberately does NOT scan backend/evaluation/,
backend/plant/, or tests/, because those are exactly the places truth is
*supposed* to flow: the evaluator, and the plant that stamps it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Packages that sit on the live inference path -- must never read truth fields.
SCANNED_PACKAGES = [
    REPO_ROOT / "backend" / "ml",
    REPO_ROOT / "backend" / "twin",
    REPO_ROOT / "backend" / "detect",  # future home of the detector suite (B5.1)
    REPO_ROOT / "backend" / "sources",  # source adapters must emit Frames, never read truth fields
]

FORBIDDEN_ATTRS = {"FAULT_ID", "HEALTH_INDEX", "RUL_HOURS"}

# RUL_HOURS is a *write* target for the (soon-to-be-retired) rul_estimator.py --
# writing a prognostic's own output field is not a truth leak. Everything else
# in this allowlist is a historical/known exception, reviewed individually.
ALLOWED_ASSIGNMENT_TARGETS = {
    REPO_ROOT / "backend" / "ml" / "rul_estimator.py",
}


def _find_forbidden_attribute_reads(path: Path) -> list[tuple[int, str]]:
    """Return (line, attr_name) for every *read* of a forbidden attribute name
    in the given file. Assignment targets (``x.RUL_HOURS = ...``) are excluded
    for files in ALLOWED_ASSIGNMENT_TARGETS; everywhere else even a write is
    flagged, because a live detector has no business touching these names at all.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[tuple[int, str]] = []

    # Map each Attribute node to whether it's a plain Store (assignment target).
    store_ids = set()
    if path in ALLOWED_ASSIGNMENT_TARGETS:
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
                store_ids.add(id(node))

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRS:
            if id(node) in store_ids:
                continue
            hits.append((node.lineno, node.attr))
    return hits


def _iter_python_files():
    for pkg in SCANNED_PACKAGES:
        if not pkg.exists():
            continue
        yield from sorted(pkg.rglob("*.py"))


def test_no_ground_truth_attribute_reads_in_live_inference_path():
    violations: list[str] = []
    for path in _iter_python_files():
        if "__pycache__" in path.parts:
            continue
        for lineno, attr in _find_forbidden_attribute_reads(path):
            violations.append(f"{path.relative_to(REPO_ROOT)}:{lineno} reads .{attr}")

    assert not violations, (
        "Ground-truth field(s) read on the live inference path -- these fields "
        "exist only on the synthetic plant's output for the evaluator's benefit "
        "and are never present on real telemetry (see docs/build/INTERFACES.md "
        "Sec 1-2):\n  " + "\n  ".join(violations)
    )


def test_flyhash_novelty_calibration_does_not_reference_fault_id():
    """Regression pin for the specific B0.1 bug: Stage 2c of the detection
    pipeline used to gate FlyHash calibration on ``actual.FAULT_ID == 0``. It
    must now gate on the pipeline's own frame counter (a startup window), which
    is derivable from real telemetry alone."""
    src = (REPO_ROOT / "backend" / "ml" / "detection_pipeline.py").read_text(encoding="utf-8")
    assert "FAULT_ID" not in src, (
        "detection_pipeline.py must not reference FAULT_ID anywhere -- "
        "calibration must use frame-count-based windowing instead (B0.1)"
    )
    assert "_frame_count <= self._novelty.calibration_frames" in src, (
        "expected the frame-count-windowed calibration gate introduced in B0.1"
    )


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
