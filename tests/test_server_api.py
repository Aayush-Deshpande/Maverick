"""
Unit & Integration Tests for Backend FastAPI Telemetry & Control Server
DRDO / iDEX Problem Statement ID: 26054
"""

import os
import pytest
from fastapi.testclient import TestClient
from backend.server.main import app
from backend.server.engine_service import EngineStateService


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["drdo_ps_id"] == "26054"
    assert "endpoints" in data


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "sortie_id" in data
    assert "is_engine_running" in data
    assert data["loop_frequency_hz"] == 20.0


# Ported to tests/api/test_legacy_adapter.py in card M0-08 (D38): /api/state, /api/control and /ws/telemetry now
# run on the v1 runtime. test_state_snapshot_schema, test_control_fault_activation_and_clearing,
# test_commanded_fault_highlights_immediately, test_control_throttle_and_environment and
# test_control_engine_stop_and_start live there, each checking the same behaviour or stronger.


def test_debrief_export_endpoint(client):
    res = client.post("/api/debrief")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "report_path" in data

    # MissionReporter (via the real EngineStateService singleton) always writes into the
    # actual data/mission_reports/ folder - there's no output_dir override reachable through
    # this HTTP endpoint the way test_agent_and_graph.py's unit test uses tempfile.mkdtemp()
    # for its own direct MissionReporter instance. Clean up so repeated local/CI runs don't
    # leave growing untracked cruft in the real data directory.
    report_path = data.get("report_path")
    if report_path and os.path.exists(report_path):
        os.remove(report_path)
