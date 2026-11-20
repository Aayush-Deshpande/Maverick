"""T-FLT-1 ratchet (card M1-13; R 22.2 item 2 "no fault is ever ignored"). Every (engine, applicable physical fault)
pair that passed every expected_signature channel in tests/sim/t_flt_1_baseline.json must still pass; the set may
only grow (update the baseline when a model or registry fix adds pairs). Slow: run with python -m pytest -m slow.
The full table with deltas is docs/physics/t_flt_1_report.csv (scripts/sim/run_t_flt_1.py)."""
import json
from pathlib import Path

import pytest

from backend.faults.registry import load_fault_registry
from backend.physics.engine_config import load_engine_config
from backend.sim.signature import run_pair

BASELINE = json.loads((Path(__file__).with_name("t_flt_1_baseline.json")).read_text(encoding="utf-8"))
REG = load_fault_registry()


@pytest.mark.slow
@pytest.mark.parametrize("pair", BASELINE["passing"], ids=lambda p: f"{p[0]}-{p[1]}")
def test_baseline_pairs_still_move_their_full_signature(pair):
    engine_id, fault_id = pair
    bad = [r for r in run_pair(load_engine_config(engine_id), REG, fault_id) if not r.ok]
    assert not bad, [(r.channel, r.delta, r.min_delta) for r in bad]
