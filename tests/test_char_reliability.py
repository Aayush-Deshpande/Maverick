"""Characterization tests (B0.9): backend/reliability/{fmeca,isolability}.py"""
import json

import pytest

from backend.reliability.fmeca import FailureMode, SeverityClass, build_default_fmeca
from backend.reliability.isolability import (
    SignatureMatrix, canonical_signature, from_fmeca,
)


@pytest.fixture(scope="module")
def fmeca():
    return build_default_fmeca()


def test_failure_mode_scores():
    m = FailureMode("FM-X", "item", "mode", "cause", "local", "mission",
                    SeverityClass.CATASTROPHIC, ["a"], ["CH"], "method",
                    occurrence=4, detection_difficulty=5)
    assert m.severity_rank == 10
    assert m.rpn == 200
    assert m.criticality == pytest.approx(4.0)
    assert m.is_detectability_gap is False
    gap = FailureMode("FM-Y", "i", "m", "c", "l", "m", SeverityClass.MINOR)
    assert gap.is_detectability_gap is True
    assert gap.rpn == 2 * 3 * 5


def test_default_fmeca_headline_numbers(fmeca):
    s = fmeca.summary()
    assert s["total_modes"] == 20
    assert s["by_severity"] == {"I_CATASTROPHIC": 8, "II_CRITICAL": 9, "III_MARGINAL": 3}
    assert s["detectability_gaps"] == 0
    assert s["highest_rpn"][0] == ("FM-19", 252)
    assert [i for i, _ in s["highest_rpn"]] == ["FM-19", "FM-20", "FM-02", "FM-07", "FM-16"]
    assert len(fmeca.for_engine_class("SI")) == 16
    assert len(fmeca.for_engine_class("CI")) == 19
    assert len(fmeca.for_engine_class("ci")) == 19


def test_ranked_by_rpn_is_sorted_and_deterministic(fmeca):
    r = [m.rpn for m in fmeca.ranked_by_rpn()]
    assert r == sorted(r, reverse=True)
    assert [m.mode_id for m in fmeca.ranked_by_rpn(3)] == ["FM-19", "FM-20", "FM-02"]
    assert len(fmeca.traceability_matrix()) == 20
    assert "FM-01" in fmeca.channel_coverage()["CRANK_OMEGA"]


def test_fmeca_markdown_and_json(fmeca, tmp_path):
    md = fmeca.to_markdown()
    assert "FM-19" in md and "20 modes" in md
    p = fmeca.save_json(tmp_path / "sub" / "f.json")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["summary"]["total_modes"] == 20 and len(d["modes"]) == 20


# ---- isolability ----------------------------------------------------------

def test_canonical_signature_collides_on_same_physics():
    assert canonical_signature("Raised cycle-to-cycle variation") == \
        canonical_signature("RAISED CYCLE-TO-CYCLE VARIATION")
    assert canonical_signature("some brand new wording") == "SIG_SOME_BRAND_NEW_WORDING"


def _toy():
    sm = SignatureMatrix()
    sm.add_mode("A", {"S_EGT_DROP": "EGT", "S_VIB": "VIB"})
    sm.add_mode("B", {"S_EGT_DROP": "EGT"})
    sm.add_mode("C", {"S_OIL": "OIL"})
    return sm


def test_toy_matrix_ambiguity_and_discriminator():
    sm = _toy()
    base = sm.analyse(["EGT", "OIL"])          # A and B look identical
    assert base.indistinguishable_classes == [["A", "B"]]
    assert base.isolable == ["C"]
    assert base.isolability == pytest.approx(1 / 3)
    assert base.detectability == pytest.approx(1.0)
    better = sm.analyse(["EGT", "OIL", "VIB"])  # add the discriminator
    assert better.isolability == pytest.approx(1.0)
    assert better.indistinguishable_classes == []
    assert sm.analyse(["OIL"]).undetectable == ["A", "B"]
    assert sorted(sm.minimum_channel_set(1.0)) == ["EGT", "OIL", "VIB"]
    assert "isolable" in better.summary_line()


def test_isolability_monotone_in_channels_and_channel_value():
    sm = _toy()
    chans = ["EGT", "OIL", "VIB"]
    prev = -1.0
    for k in range(len(chans) + 1):
        iso = sm.analyse(chans[:k]).isolability
        assert iso >= prev
        prev = iso
    cv = sm.channel_value()
    assert cv[0]["isolability_lost"] >= cv[-1]["isolability_lost"]
    assert {r["channel"] for r in cv} == set(chans)


def test_default_fmeca_isolability_current_value(fmeca):
    """DRIFT NOTE (B0.9): docs/reliability/ISOLABILITY.md claims 55% -> 95% for
    as-built vs proposed. The as-built channel list is not stored anywhere, and the
    CURRENT default FMECA gives 100%/100% with all channels. Pinned as-is."""
    sm = from_fmeca(fmeca)
    r = sm.analyse()
    assert r.n_modes == 20
    assert r.detectability == pytest.approx(1.0)
    assert r.isolability == pytest.approx(1.0)
    assert len(sm.channels) == 25
    assert r.indistinguishable_classes == []


def test_default_fmeca_dropping_channels_never_improves(fmeca):
    sm = from_fmeca(fmeca)
    chans = sm.channels
    full = sm.analyse(chans)
    fewer = sm.analyse([c for c in chans if not c.startswith("OIL_") and c != "CRANK_OMEGA"])
    assert fewer.isolability <= full.isolability
    assert fewer.detectability <= full.detectability
