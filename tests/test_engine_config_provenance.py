"""
Engine config provenance (B0.4).

Every numeric field in every engine config must be classified PUBLIC / MANUAL /
ASSUMED / PLACEHOLDER (docs/build/INTERFACES.md Sec 8) rather than presented as
an undifferentiated "specification" -- the exact mistake vrde_jayem_2_2l.json
made before this fix (see docs/build/RESEARCH_LEDGER.md Sec 4).
"""

from __future__ import annotations

import json

import pytest

from backend.physics.engine_config import (
    PROVENANCE_STATUSES,
    available_engines,
    load_engine_config,
)


def test_all_configs_load():
    engines = available_engines()
    assert len(engines) >= 5, f"expected at least 5 engine configs, found {engines}"
    for engine_id in engines:
        cfg = load_engine_config(engine_id)
        assert cfg.engine_id == engine_id


def test_rotax_915is_exists_for_heron_mk_ii():
    """docs/audit/10_red_team_readiness_review.md Sec 2.8: the IAF/Army fly the
    Heron Mk II on a Rotax 915 iS, not the 914 -- there was previously no
    config for it at all."""
    cfg = load_engine_config("rotax_915is")
    assert cfg.manufacturer == "BRP-Rotax"
    assert cfg.layout.displacement_cc == pytest.approx(1352.0)
    assert cfg.is_turbocharged
    assert cfg.provenance_status("layout.displacement_cc") == "PUBLIC"
    assert cfg.provenance_status("rated_power_kw") == "PUBLIC"


@pytest.mark.parametrize("engine_id", available_engines())
def test_every_numeric_field_has_a_classified_provenance_entry(engine_id):
    cfg = load_engine_config(engine_id)
    missing = cfg.unlabelled_numeric_fields()
    assert not missing, (
        f"{engine_id}: numeric fields with no provenance entry (implicitly "
        f"UNVERIFIED) -- classify each as PUBLIC/MANUAL/ASSUMED/PLACEHOLDER: "
        f"{missing}"
    )


@pytest.mark.parametrize("engine_id", available_engines())
def test_every_provenance_entry_has_a_valid_status_and_ref(engine_id):
    cfg = load_engine_config(engine_id)
    for field_path, entry in cfg.provenance.items():
        assert entry.get("status") in PROVENANCE_STATUSES, (
            f"{engine_id}.{field_path}: status {entry.get('status')!r} not in "
            f"{sorted(PROVENANCE_STATUSES)}"
        )
        assert entry.get("ref"), f"{engine_id}.{field_path}: empty ref"


def test_vrde_config_does_not_overclaim_as_a_verified_specification():
    """Regression pin: the file used to call itself a 'specification' and cite
    numbers with a single undifferentiated source string. It must now be
    explicit that most of its numbers are assumptions."""
    cfg = load_engine_config("vrde_jayem_2_2l")
    assert "specification" not in cfg.display_name.lower()
    assumed_or_placeholder = sum(
        1 for e in cfg.provenance.values() if e["status"] in ("ASSUMED", "PLACEHOLDER")
    )
    public_or_manual = sum(
        1 for e in cfg.provenance.values() if e["status"] in ("PUBLIC", "MANUAL")
    )
    assert assumed_or_placeholder > public_or_manual, (
        "vrde_jayem_2_2l.json should have more assumed/placeholder numeric "
        "fields than public/manual ones -- that is the honest state of what is "
        "publicly known about this engine as of Sep 2025"
    )
    # The specific facts that ARE public must be marked as such.
    assert cfg.provenance_status("rated_power_kw") == "PUBLIC"
    assert cfg.provenance_status("layout.count") == "PUBLIC"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
