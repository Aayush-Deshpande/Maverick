"""Card M0-03 (ANUMAAN_COMPONENTS_ADDENDUM.txt section 8, tests 1-4): component manifests match the canonical web
models exactly, and every applicable fault on every engine resolves to real parts or an explicit location marker."""
import json
import sys
from pathlib import Path

import pytest

from backend.faults.registry import load_fault_registry
from backend.physics.engine_config import available_engines, load_engine_config

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "assets"))
from glb_nodes import node_names  # noqa: E402

ENGINES = available_engines()


def manifest(engine_id):
    return json.loads((ROOT / "configs" / "components" / f"{engine_id}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("engine_id", ENGINES)
def test_manifest_nodes_exist_in_glb_and_are_unique(engine_id):  # A section 8 test 1
    m = manifest(engine_id)
    glb_nodes = set(node_names(str(ROOT / m["glb"]), mesh_only=True))
    seen = {}
    for comp in m["components"]:
        assert comp["nodes"], f"{engine_id}.{comp['component_id']} has no nodes"
        for n in comp["nodes"]:
            assert n in glb_nodes, f"{engine_id}: node {n!r} of {comp['component_id']} is not in {m['glb']}"
            assert n not in seen, f"{engine_id}: node {n!r} in {seen[n]} and {comp['component_id']}"
            seen[n] = comp["component_id"]
    assert m["unassigned_nodes"] == [], f"{engine_id}: unassigned nodes {m['unassigned_nodes'][:10]}"
    assert len(seen) == len(glb_nodes)


def _resolve(ids, cyl):
    return [i.replace("{cyl}", str(cyl)) for i in ids]


@pytest.mark.parametrize("engine_id", ENGINES)
def test_every_applicable_fault_resolves_to_parts_or_a_marker(engine_id):  # A section 8 test 2
    cfg = load_engine_config(engine_id)
    comp_ids = {c["component_id"] for c in manifest(engine_id)["components"]}
    reg = load_fault_registry()
    for spec in reg.applicable(cfg):
        entry = spec.raw["components"].get(engine_id)
        assert entry is not None, f"{spec.id} applies to {engine_id} but has no components entry"
        if spec.kind == "SENSOR":
            continue
        for cyl in (range(1, cfg.cylinder_count + 1) if spec.scope == "CYLINDER" else [None]):
            ids = _resolve(entry["now"], cyl)
            missing = [i for i in ids if i not in comp_ids]
            assert not missing, f"{spec.id} on {engine_id}: unknown component ids {missing}"
            assert ids or entry["marker"], f"{spec.id} on {engine_id}: no parts and no marker"


def test_forbidden_mappings():  # A section 8 test 3 (the parts that are known to be wrong)
    reg = load_fault_registry()
    for spec in reg.all():
        for engine_id, entry in spec.raw["components"].items():
            now = entry.get("now", [])
            assert "wastegate_MISSEGMENTED" not in now, f"{spec.id} maps to the missegmented 914 wastegate"
            if spec.name == "AIR_FILTER_BLOCKAGE":
                assert "air_baffles" not in now, "air filter fault must not light the 915 cooling baffles"


@pytest.mark.parametrize("engine_id", ["austro_ae300", "vrde_jayem_2_2l"])
def test_per_cylinder_faults_light_different_parts_per_cylinder(engine_id):  # A section 8 test 4
    reg = load_fault_registry()
    cfg = load_engine_config(engine_id)
    nodes_by_comp = {c["component_id"]: set(c["nodes"]) for c in manifest(engine_id)["components"]}
    for fid in ("F06", "F08"):
        entry = reg.get(fid).raw["components"][engine_id]
        node_sets = []
        for cyl in range(1, cfg.cylinder_count + 1):
            nodes = set()
            for cid in _resolve(entry["now"], cyl):
                nodes |= nodes_by_comp[cid]
            node_sets.append(frozenset(nodes))
        assert len(set(node_sets)) == cfg.cylinder_count, f"{fid} on {engine_id}: cylinders share the same parts"
