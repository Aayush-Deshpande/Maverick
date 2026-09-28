"""API Integration Tests for Mission Planning & Simulation Endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.server.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_list_mission_templates(client):
    res = client.get("/api/missions/templates")
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) >= 4
    engine_ids = {t["engine_id"] for t in templates}
    assert "rotax_912is" in engine_ids
    assert "austro_ae300" in engine_ids


def test_get_mission_definition_and_state(client):
    res_def = client.get("/api/missions/definition")
    assert res_def.status_code == 200
    assert "mission_id" in res_def.json()

    res_state = client.get("/api/missions/state")
    assert res_state.status_code == 200
    state = res_state.json()
    assert "status" in state
    assert "time_elapsed_sec" in state
    assert "engine_id" in state


def test_mission_control_actions(client):
    # Start
    res = client.post("/api/missions/start")
    assert res.status_code == 200
    assert res.json()["status"] == "RUNNING"

    # Timescale
    res = client.post("/api/missions/timescale", json={"scale": 5.0})
    assert res.status_code == 200
    assert res.json()["time_scale"] == 5.0

    # Derate
    res = client.post("/api/missions/derate", json={"scale": 0.85})
    assert res.status_code == 200
    assert res.json()["status"] == "DERATED"

    # Pause
    res = client.post("/api/missions/pause")
    assert res.status_code == 200

    # Resume
    res = client.post("/api/missions/resume")
    assert res.status_code == 200
    assert res.json()["status"] == "RUNNING"

    # Abort
    res = client.post("/api/missions/abort")
    assert res.status_code == 200
    assert res.json()["status"] == "ABORTED"
    assert "artifacts" in res.json()


def test_blender_status_endpoint(client):
    res = client.get("/api/missions/blender-status")
    assert res.status_code == 200
    data = res.json()
    assert "blender_available" in data
    assert "canyon_sim_bat_exists" in data
    assert "mission_client_bat_exists" in data
    assert data["canyon_sim_bat_exists"] is True
    assert data["mission_client_bat_exists"] is True
