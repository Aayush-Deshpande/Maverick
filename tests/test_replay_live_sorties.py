"""
Tests for live sortie telemetry replay and regression coverage for report_dump replay.
Verifies Phase 1b:
1. live_sorties/*.csv are indexed as additive manifests with 'live:' prefix.
2. Derivation of ELAPSED_SEC from TIMESTAMP_SEC allows both live_sorties and report_dump
   missions with telemetry_log.csv (mission_007, mission_009, mission_010) to replay correctly.
3. Fast seeking / bisect returns accurate chronological frames.
4. FastAPI endpoints (/api/replay/manifests, manifest, frame) serve both sources without 404s.
"""

import pytest
from fastapi.testclient import TestClient
from backend.telemetry.replay_engine import ReplayEngine, LIVE_SORTIE_PREFIX
from backend.server.main import app


@pytest.fixture(scope="module")
def replay_engine():
    return ReplayEngine()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_list_manifests_includes_both_sources(replay_engine):
    manifests = replay_engine.list_manifests()
    assert len(manifests) > 0

    report_dump_ids = [m["mission_id"] for m in manifests if not m["mission_id"].startswith(LIVE_SORTIE_PREFIX)]
    live_ids = [m["mission_id"] for m in manifests if m["mission_id"].startswith(LIVE_SORTIE_PREFIX)]

    # We must have both report_dump entries and live_sorties entries
    assert len(report_dump_ids) >= 10, f"Expected >= 10 report_dump manifests, found {len(report_dump_ids)}"
    assert len(live_ids) >= 15, f"Expected >= 15 live_sorties manifests, found {len(live_ids)}"

    # Sorties should be properly structured
    for m in manifests:
        assert "mission_id" in m
        assert "status" in m
        assert "duration_hours" in m


def test_live_sortie_manifest_and_event_markers(replay_engine):
    manifests = replay_engine.list_manifests()
    live_ids = [m["mission_id"] for m in manifests if m["mission_id"].startswith(LIVE_SORTIE_PREFIX)]
    assert live_ids, "No live sorties found"

    # Select a sortie that has recorded frames across time
    valid_manifests = [
        m for m in manifests
        if m["mission_id"].startswith(LIVE_SORTIE_PREFIX) and (m["duration_hours"] or 0) > 0
    ]
    assert valid_manifests, "Expected at least one live sortie with non-zero duration"
    sample_id = valid_manifests[0]["mission_id"]

    manifest = replay_engine.get_manifest(sample_id)
    assert manifest is not None
    assert manifest["mission_id"] == sample_id
    assert manifest["total_duration_sec"] > 0
    assert "start_epoch" in manifest
    assert isinstance(manifest["event_markers"], list)
    assert len(manifest["event_markers"]) >= 2  # At least START and END markers

    event_types = [ev["event_type"] for ev in manifest["event_markers"]]
    assert "MISSION_START" in event_types
    assert "MISSION_END" in event_types


def test_live_sortie_frame_seeking(replay_engine):
    manifests = replay_engine.list_manifests()
    valid_manifests = [
        m for m in manifests
        if m["mission_id"].startswith(LIVE_SORTIE_PREFIX) and (m["duration_hours"] or 0) > 0
    ]
    assert valid_manifests, "No valid live sorties with duration found"
    sample_id = valid_manifests[0]["mission_id"]

    manifest = replay_engine.get_manifest(sample_id)
    duration = manifest["total_duration_sec"]

    # Frame at start
    frame_0 = replay_engine.get_frame(sample_id, 0.0)
    assert frame_0 is not None
    assert "ELAPSED_SEC" in frame_0
    assert frame_0["ELAPSED_SEC"] == pytest.approx(0.0, abs=0.5)
    assert "ENGINE_RPM" in frame_0

    # Frame midway
    mid_time = duration / 2.0
    frame_mid = replay_engine.get_frame(sample_id, mid_time)
    assert frame_mid is not None
    assert frame_mid["ELAPSED_SEC"] <= mid_time + 0.1

    # End frame
    frame_end = replay_engine.get_frame(sample_id, duration)
    assert frame_end is not None
    assert frame_end["ELAPSED_SEC"] <= duration


def test_regression_report_dump_missions_with_csv(replay_engine):
    """
    Regression test: in pre-fix code, _load_frames required raw ELAPSED_SEC in CSV.
    Because writers only output TIMESTAMP_SEC, get_frame() returned None for mission_007,
    mission_009, and mission_010 despite having readings/telemetry_log.csv on disk.
    Now ELAPSED_SEC is derived and seeking must succeed.
    """
    for mid in ["mission_007", "mission_009", "mission_010"]:
        manifest = replay_engine.get_manifest(mid)
        assert manifest is not None, f"Manifest missing for {mid}"

        # Duration in mission.json
        duration = manifest.get("total_duration_sec", 60.0)
        frame = replay_engine.get_frame(mid, min(5.0, duration / 2.0))
        assert frame is not None, f"get_frame failed for {mid} which has readings/telemetry_log.csv"
        assert "ELAPSED_SEC" in frame
        assert frame["ELAPSED_SEC"] is not None


def test_replay_api_endpoints(client):
    # 1. Manifests list endpoint
    resp = client.get("/api/replay/manifests")
    assert resp.status_code == 200
    data = resp.json()
    assert "manifests" in data
    manifests = data["manifests"]
    assert len(manifests) > 0

    # Find one live and one report_dump
    valid_live = [
        m["mission_id"] for m in manifests
        if m["mission_id"].startswith(LIVE_SORTIE_PREFIX) and (m["duration_hours"] or 0) > 0
    ]
    report_dump_ids = [m["mission_id"] for m in manifests if not m["mission_id"].startswith(LIVE_SORTIE_PREFIX)]

    assert valid_live
    assert report_dump_ids

    # 2. Manifest detail endpoints
    resp_live = client.get(f"/api/replay/{valid_live[0]}/manifest")
    assert resp_live.status_code == 200
    live_man = resp_live.json()
    assert live_man["mission_id"] == valid_live[0]

    resp_rd = client.get(f"/api/replay/mission_007/manifest")
    assert resp_rd.status_code == 200
    rd_man = resp_rd.json()
    assert rd_man["mission_id"] == "mission_007"

    # 3. Frame query endpoints
    resp_frame_live = client.get(f"/api/replay/{valid_live[0]}/frame", params={"time_sec": 2.5})
    assert resp_frame_live.status_code == 200
    frame_live = resp_frame_live.json()
    assert "ENGINE_RPM" in frame_live and "ELAPSED_SEC" in frame_live

    resp_frame_rd = client.get("/api/replay/mission_007/frame", params={"time_sec": 2.5})
    assert resp_frame_rd.status_code == 200
    frame_rd = resp_frame_rd.json()
    assert "ENGINE_RPM" in frame_rd and "ELAPSED_SEC" in frame_rd

    # 4. Unknown mission returns 404
    resp_404 = client.get("/api/replay/nonexistent_mission_id/manifest")
    assert resp_404.status_code == 404
