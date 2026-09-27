"""
Unit tests for newly exposed FastAPI endpoints:
- /api/mission/reliability
- /api/mission/prescriptive
- /api/diagnostics/bayesian
- /api/prognostics/dual-path-rul
- /api/debrief/latest
DRDO / iDEX Problem Statement ID: 26054
"""

import pytest
from fastapi.testclient import TestClient
from backend.server.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_mission_reliability_endpoint(client):
    res = client.get("/api/mission/reliability")
    assert res.status_code == 200
    data = res.json()
    assert "analytic_reliability" in data
    assert "monte_carlo_reliability" in data
    assert 0.0 <= data["monte_carlo_reliability"] <= 1.0
    assert "limiting_component" in data


def test_mission_prescriptive_endpoint(client):
    res = client.get("/api/mission/prescriptive")
    assert res.status_code == 200
    data = res.json()
    assert "derate_options" in data
    assert len(data["derate_options"]) > 0
    assert "advisory_sentences" in data


def test_bayesian_diagnostics_endpoint(client):
    res = client.get("/api/diagnostics/bayesian")
    assert res.status_code == 200
    data = res.json()
    assert "hypotheses" in data
    assert isinstance(data["hypotheses"], list)


def test_dual_path_rul_endpoint(client):
    res = client.get("/api/prognostics/dual-path-rul")
    assert res.status_code == 200
    data = res.json()
    assert "physics_rul_hours" in data
    assert "data_rul_hours" in data
    assert "blended_rul_hours" in data
    assert data["blended_rul_hours"] > 0


def test_engine_select_synchronization(client):
    res = client.post("/api/engines/select", json={"engine_id": "rotax_914"})
    assert res.status_code == 200
    assert res.json()["selected"] == "rotax_914"

    # Verify state reflects selected engine
    state_res = client.get("/api/state")
    assert state_res.status_code == 200
    state = state_res.json()
    assert state.get("engine_id") == "rotax_914"

    # Restore to 912
    client.post("/api/engines/select", json={"engine_id": "rotax_912is"})
