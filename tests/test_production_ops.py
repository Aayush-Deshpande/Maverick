"""M8-01 / T-OPS-1: Production operational endpoints (/health, /ready, /api/v1/health, /api/v1/ready)."""

import pytest
from fastapi.testclient import TestClient

from backend.server.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_root_liveness_and_readiness_probes(client):
    res_health = client.get("/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["status"] == "UP"
    assert data_health["ready"] is True
    assert data_health["loop_frequency_hz"] == 20.0

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    data_ready = res_ready.json()
    assert data_ready["ready"] is True
    assert data_ready["total_engines"] >= 5


def test_v1_health_and_ready(client):
    res_h = client.get("/api/v1/health")
    assert res_h.status_code == 200
    assert res_h.json()["status"] == "UP"

    res_r = client.get("/api/v1/ready")
    assert res_r.status_code == 200
    assert res_r.json()["ready"] is True
