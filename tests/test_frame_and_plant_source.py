"""
B1.1 / B1.2(part 1): the canonical Frame contract and PlantSource.

The point of these tests is the *structural* separation of inference input from
ground truth (decision D04), not just that the dataclasses construct.
"""

from __future__ import annotations

import dataclasses

import pytest

from backend.core.frame import (
    FORBIDDEN_FRAME_FIELDS,
    Frame,
    TruthRecord,
)
from backend.sources import PlantSource


def test_frame_has_no_truth_or_twin_output_fields():
    names = {f.name for f in dataclasses.fields(Frame)}
    assert names.isdisjoint(FORBIDDEN_FRAME_FIELDS)
    assert names.isdisjoint({n.lower() for n in FORBIDDEN_FRAME_FIELDS})
    for leaky in ("fault_id", "active_faults", "health_index", "rul_hours", "failed"):
        assert leaky not in names


def test_frame_from_dict_refuses_forbidden_fields():
    with pytest.raises(ValueError, match="FAULT_ID"):
        Frame.from_dict({"t": 0.0, "source": "PLANT", "engine_config_id": "rotax_914", "FAULT_ID": 3})


def test_frame_validates_source_and_cylinder_counts():
    with pytest.raises(ValueError):
        Frame(t=0.0, source="MAGIC", engine_config_id="rotax_914")
    with pytest.raises(ValueError):
        Frame(t=0.0, source="PLANT", engine_config_id="rotax_914", cht=[1.0, 2.0], egt=[1.0])


def test_unmeasured_channels_are_none_not_zero():
    f = Frame(t=0.0, source="REPLAY", engine_config_id="rotax_914", rpm=3000.0)
    assert f.oil_p is None and f.cht == []
    assert f.channels() == {"rpm": 3000.0}


def test_plant_source_emits_frame_and_separate_truth():
    src = PlantSource("rotax_914", seed=7)
    frame, truth = src.step(1.0)
    assert isinstance(frame, Frame) and isinstance(truth, TruthRecord)
    assert frame.source == "PLANT"
    assert frame.n_cylinders == 4 and len(frame.cht) == len(frame.egt) == 4
    assert frame.rpm is not None and frame.map_kpa is not None
    assert truth.is_nominal and not truth.failed


def test_injected_fault_appears_in_truth_only_never_in_frame():
    src = PlantSource("rotax_914", seed=3)
    src.inject_fault("MISFIRE", cylinder=3, severity=0.8, ramp_sec=1.0)
    frame, truth = src.step(5.0)
    assert [f.mode for f in truth.active_faults] == ["MISFIRE"]
    assert truth.active_faults[0].location == 3
    blob = repr(dataclasses.asdict(frame)).lower()
    assert "misfire" not in blob
    assert "active_faults" not in blob


def test_same_seed_reproduces_and_different_builds_differ():
    a = [f.cht[0] for f, _ in PlantSource("rotax_914", seed=11).run(20)]
    b = [f.cht[0] for f, _ in PlantSource("rotax_914", seed=11).run(20)]
    c = [f.cht[0] for f, _ in PlantSource("rotax_914", seed=12).run(20)]
    assert a == b
    assert a != c


def test_engine_class_is_configuration():
    for cfg in ("rotax_914", "rotax_915is", "vrde_jayem_2_2l"):
        frame, _ = PlantSource(cfg, seed=1).step(1.0)
        assert frame.engine_config_id == cfg
        assert frame.n_cylinders == 4


def test_a_cooling_fault_moves_plant_readings_without_leaking_the_label():
    healthy = PlantSource("rotax_914", seed=5)
    faulty = PlantSource("rotax_914", seed=5)
    faulty.inject_fault("COOLING_DEGRADATION", severity=0.95, ramp_sec=10.0)
    h = [f.cht[0] for f, _ in healthy.run(120, dt_sec=5.0)][-1]
    x = [f.cht[0] for f, _ in faulty.run(120, dt_sec=5.0)][-1]
    assert x > h + 5.0, f"cooling degradation should raise CHT (healthy {h:.1f}, faulty {x:.1f})"
