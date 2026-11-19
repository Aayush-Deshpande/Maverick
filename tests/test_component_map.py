"""The component map is the contract between the simulation and the 3D twin.

It must never name a mesh that is not in the shipped GLB, must cover every fault the runtime will accept
for that engine, and must not claim the scalar detector sees a fault the registry marks waveform-only.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from backend.detect.calibration import SCALAR_CHANNELS
from backend.physics.engine_config import load_engine_config
from backend.runtime.registry import FAULT_REGISTRY, faults_for

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "frontend" / "public"
MAP = json.loads((PUBLIC / "twin" / "component_map.json").read_text(encoding="utf-8"))
ENGINES = sorted(MAP["engines"])
CHANNELS = {"cht", "egt", *SCALAR_CHANNELS}


def _glb_names(engine_id: str) -> list[str]:
    raw = (PUBLIC / "models" / f"{engine_id}.glb").read_bytes()
    (json_len,) = struct.unpack_from("<I", raw, 12)
    doc = json.loads(raw[20:20 + json_len])
    return [n.get("name", "") for n in doc.get("nodes", [])] + [m.get("name", "") for m in doc.get("meshes", [])]


def _expand(pattern: str, cylinders: int) -> list[str]:
    return [pattern.replace("{c}", str(c)) for c in range(1, cylinders + 1)] if "{c}" in pattern else [pattern]


def _patterns(entry: dict) -> list[str]:
    out = [p for stage in entry["pipeline"] for p in stage]
    return out


@pytest.mark.parametrize("engine_id", ENGINES)
def test_every_name_is_a_real_mesh(engine_id):
    eng = MAP["engines"][engine_id]
    names = _glb_names(engine_id)
    pats = [p for group in eng["subsystems"].values() for p in group]
    pats += [p for group in eng["sensors"].values() for p in group]
    for f in eng["faults"].values():
        pats += _patterns(f)
    missing = sorted({q for p in pats for q in _expand(p, eng["cylinders"]) if not any(n.startswith(q) for n in names)})
    assert not missing, f"{engine_id}: names not in the GLB: {missing}"


@pytest.mark.parametrize("engine_id", ENGINES)
def test_every_runtime_fault_is_mapped(engine_id):
    accepted = {s.mode for s in faults_for(load_engine_config(engine_id))}
    mapped = set(MAP["engines"][engine_id]["faults"])
    assert accepted <= mapped, f"{engine_id}: runtime faults with no component mapping: {sorted(accepted - mapped)}"
    assert mapped <= accepted, f"{engine_id}: mapped faults the runtime does not accept: {sorted(mapped - accepted)}"


@pytest.mark.parametrize("engine_id", ENGINES)
def test_evidence_matches_the_detector(engine_id):
    for mode, f in MAP["engines"][engine_id]["faults"].items():
        assert set(f["evidence"]) <= CHANNELS, f"{engine_id}/{mode}: unknown channel in {f['evidence']}"
        visible = FAULT_REGISTRY[mode].scalar_visible
        assert bool(f["evidence"]) == visible, (
            f"{engine_id}/{mode}: evidence {f['evidence']} contradicts registry scalar_visible={visible}")


def test_highlight_colours_match_the_blender_app():
    src = (ROOT / "apps" / "blender_twin" / "standalone_fault_diagnostic_app.py").read_text(encoding="utf-8")
    assert "(1.0, 0.28, 0.05, 1.0)" in src and MAP["highlight"]["fault_rgb"] == [1.0, 0.28, 0.05]
    assert "(0.06, 0.22, 0.38, 1.0)" in src and MAP["highlight"]["ghost_rgb"] == [0.06, 0.22, 0.38]
