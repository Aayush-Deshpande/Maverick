"""M2-01/M2-02 through the API: the v1 state carries the evaluator's verdict with reasons, the engine commands drive
the state machine, and acknowledge releases a latched NO-GO only after its cause is gone."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.server.api_v1 as api_v1
from backend.runtime.hub import RuntimeHub

ENGINE = "rotax_912is"


@pytest.fixture(scope="module")
def client():
    hub = RuntimeHub(engines=[ENGINE])
    hub.calibrate_all(parallel=False)
    hub.tick_all()
    api_v1._services = api_v1.Services(hub)
    app = FastAPI()
    app.include_router(api_v1.router)
    with TestClient(app) as c:
        c.hub = hub
        yield c
    api_v1._services = None


def _state(client):
    return client.get(f"/api/v1/engines/{ENGINE}/state").json()


def _tick(client, n):
    for _ in range(n):
        client.hub.tick_all()


def test_engine_command_validation(client):
    assert client.post(f"/api/v1/engines/{ENGINE}/engine", json={"command": "FLY"}).status_code == 422
    assert client.post(f"/api/v1/engines/{ENGINE}/engine", json={"command": "STOP", "x": 1}).status_code == 422


def test_failed_oil_pump_gives_caution_with_the_reading_and_ack_reaches_the_evaluator(client):
    """F23 at full severity leaves ~1.7 bar at cruise rpm: below the OM 2-5 bar band (CAUTION, with the reading as
    the reason). The NO-GO latch itself is T-STS-5 (tests/status); here the API's acknowledge must reach it."""
    r = client.post(f"/api/v1/engines/{ENGINE}/faults", json={"fault_id": "F23", "severity": 1.0, "ramp_s": 5,
                                                              "source": "test"})
    assert r.status_code == 200
    _tick(client, 20)
    st = _state(client)["status"]
    assert st["level"] == "CAUTION"
    oil = [x for x in st["reasons"] if x["channel"] == "oil_p"]
    assert oil and oil[0]["limit"] == 2.0 and oil[0]["value"] < 2.0
    client.delete(f"/api/v1/engines/{ENGINE}/faults")
    ev = client.hub.runtimes[ENGINE].status_evaluator
    assert client.post(f"/api/v1/engines/{ENGINE}/status/acknowledge").status_code == 200
    assert ev._acknowledged
