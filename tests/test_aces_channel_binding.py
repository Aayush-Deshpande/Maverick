"""
ACES EGT/CHT channel-binding fix (B0.3).

The .mat name matrix's 16-character decoded name for column j reliably starts
with column j's own true name and may run on into column j+1's name if there
is spare room in the field (see backend/telemetry/aces_loader.py's module-level
comment on CHANNEL_ALIASES for the full mechanism). The old "fragment anywhere
in the string" match therefore sometimes bound to the PRECEDING column's
decoded name, which happens to contain the fragment as trailing bleed-through.

Concretely: EGT_1's alias "egt 1" used to bind to column 91 ("Water Temp EGT 1"
-- the coolant/water temperature channel, wearing a borrowed tail) instead of
column 92 ("EGT 1 EGT 2 Altn" -- genuinely EGT 1). This is exactly the
mis-binding docs/IMPLEMENTATION_LOG.md's session 4 entry flagged (median
170.2C, "too low for an EGT").

Requires the real M080001.mat granule on disk (data/telemetry/nasa_aces/); the
whole module is skipped if it isn't present, since this data isn't checked
into git.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ACES_ROOT = Path(__file__).resolve().parent.parent / "data" / "telemetry" / "nasa_aces" / "extracted"
GRANULE = ACES_ROOT / "M080001.mat"

pytestmark = pytest.mark.skipif(
    not GRANULE.exists(),
    reason=f"real ACES granule not present at {GRANULE} (not checked into git)",
)


def test_egt_channels_bind_to_distinct_named_columns_not_to_water_temp():
    from backend.telemetry.aces_loader import load_granule

    g = load_granule(GRANULE)

    idx_egt1 = g.resolve("EGT_1")
    idx_egt2 = g.resolve("EGT_2")
    idx_coolant = g.resolve("COOLANT_TEMP")

    assert idx_egt1 is not None and idx_egt2 is not None and idx_coolant is not None
    # The historical bug: EGT_1 bound to the same column as COOLANT_TEMP.
    assert idx_egt1 != idx_coolant, "EGT_1 must not bind to the coolant/water temp column"
    assert idx_egt2 != idx_coolant
    assert idx_egt1 != idx_egt2, "EGT_1 and EGT_2 must resolve to distinct columns"

    assert g.names[idx_egt1].lower().startswith("egt 1")
    assert g.names[idx_egt2].lower().startswith("egt 2")
    assert g.names[idx_coolant].lower().startswith("water temp")


def test_egt_values_are_no_longer_the_170_degree_misbinding():
    """Regression pin for the specific number IMPLEMENTATION_LOG flagged."""
    import numpy as np

    from backend.telemetry.aces_loader import load_granule

    g = load_granule(GRANULE)
    series = g.series("EGT_1")
    assert series is not None, "EGT_1 must resolve and pass the plausibility envelope"
    finite = series[np.isfinite(series)]
    median = float(np.median(finite))
    # The old (wrong) binding read a median of ~170. The correct EGT_1 channel
    # reads far higher on ACES's native scale (see the unit caveat -- this is
    # NOT asserted to be degrees Celsius, only confirmed to be a materially
    # different, EGT-named signal).
    assert median > 500.0, f"EGT_1 median {median} looks like the old mis-binding, not EGT"


def test_cht_egt3_egt4_now_resolve():
    """New coverage added alongside the binding fix -- these channels exist in
    the data (4-cylinder Rotax 914) but had no alias at all before B0.3."""
    from backend.telemetry.aces_loader import load_granule

    g = load_granule(GRANULE)
    for canonical in ("CHT", "EGT_3", "EGT_4"):
        idx = g.resolve(canonical)
        assert idx is not None, f"{canonical} should resolve on M080001.mat"
        series = g.series(canonical)
        assert series is not None, f"{canonical} should pass its plausibility envelope"


def test_find_channel_requires_start_of_string_match():
    """Unit-level pin on the actual mechanism of the fix."""
    from backend.telemetry.aces_loader import load_granule

    g = load_granule(GRANULE)
    # "egt 1" occurs at position 0 of one column and at a trailing position of
    # the preceding column; find_channel must return the position-0 one.
    idx = g.find_channel("egt 1")
    assert idx is not None
    assert g.names[idx].lower().startswith("egt 1")


def test_manifest_records_the_unit_caveat():
    from backend.telemetry.aces_loader import ACES_PROVENANCE

    assert "unit_caveat" in ACES_PROVENANCE
    assert "not confirmed to be Celsius" in ACES_PROVENANCE["unit_caveat"] or \
        "NOT confirmed to be Celsius" in ACES_PROVENANCE["unit_caveat"]


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
