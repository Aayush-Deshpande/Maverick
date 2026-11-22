"""M7-02/04: CAN source switching, bus query, and real-time spoof injection endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.server.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_runtime_source_get_and_set(client):
    res = client.get("/api/v1/runtime/source")
    assert res.status_code == 200
    data = res.json()
    assert "data_source" in data
    assert "available_sources" in data
    assert "CAN" in data["available_sources"]

    # Switch to CAN
    res = client.post("/api/v1/runtime/source", json={"data_source": "CAN"})
    assert res.status_code == 200
    assert res.json()["data_source"] == "CAN"

    # Query engine CAN status
    res = client.get("/api/v1/engines/rotax_912is/can")
    assert res.status_code == 200
    can_info = res.json()
    assert can_info["data_source"] == "CAN"
    assert can_info["bus"] is not None
    assert can_info["bus"]["messages_per_frame"] == 6

    # Inject spoofed frame (UNKNOWN_ID)
    res = client.post("/api/v1/engines/rotax_912is/can/inject_spoof", json={"kind": "UNKNOWN_ID"})
    assert res.status_code == 200
    spoof_info = res.json()
    assert spoof_info["spoof_kind"] == "UNKNOWN_ID"
    assert len(spoof_info["alerts_generated"]) >= 1
    assert spoof_info["alerts_generated"][0]["kind"] == "UNKNOWN_ID"

    # Switch back to DIRECT
    res = client.post("/api/v1/runtime/source", json={"data_source": "DIRECT"})
    assert res.status_code == 200
    assert res.json()["data_source"] == "DIRECT"
