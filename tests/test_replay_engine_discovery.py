"""
Unit tests for ReplayEngine path discovery and frame index lookup.
DRDO / iDEX Problem Statement ID: 26054
"""

import pytest
from backend.telemetry.replay_engine import ReplayEngine


def test_replay_engine_manifest_listing():
    re = ReplayEngine()
    manifests = re.list_manifests()
    assert len(manifests) > 0, "Expected at least one replayable manifest"
    assert "mission_id" in manifests[0]
    assert "status" in manifests[0]


def test_replay_engine_frame_seek():
    re = ReplayEngine()
    manifests = re.list_manifests()
    mid = manifests[0]["mission_id"]
    manifest = re.get_manifest(mid)
    assert manifest is not None
    assert manifest["total_duration_sec"] > 0

    frame = re.get_frame(mid, 2.0)
    assert frame is not None
    assert "ELAPSED_SEC" in frame
    assert "ENGINE_RPM" in frame or "ALTITUDE_FT" in frame


def test_replay_engine_live_sortie_lookup():
    re = ReplayEngine()
    # Test looking up live sortie if available
    live_manifests = [m for m in re.list_manifests() if m["mission_id"].startswith("SORTIE-")]
    if live_manifests:
        target = live_manifests[0]["mission_id"]
        frame = re.get_frame(target, 1.0)
        assert frame is not None
        assert frame.get("ENGINE_RPM") is not None
