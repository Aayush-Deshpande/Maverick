"""Card M0-06: /api/v1 REST + /ws/v1 fan-out against a real (one-engine) RuntimeHub.
T-API-1 (422 with reason on invalid/inapplicable faults) and the cross-client rule: a fault injected by one client
appears in another client's next state message."""
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.server.api_v1 as api_v1
from backend.runtime.hub import RuntimeHub
from backend.server.state_schema import StateMessage


@pytest.fixture(scope="module")
def client():
    hub = RuntimeHub(engines=["rotax_912is"])
    hub.calibrate_all(parallel=False)
    hub.tick_all()
    api_v1._services = api_v1.Services(hub)
    app = FastAPI()
    app.include_router(api_v1.router)
    with TestClient(app) as c:
        c.hub = hub
        yield c
    api_v1._services = None


def test_engines_and_faults_lists(client):
    engines = client.get("/api/v1/engines").json()["engines"]
    assert engines[0]["engine_id"] == "rotax_912is" and engines[0]["fuel_system"] == "PORT_INJECTION"
    faults = client.get("/api/v1/faults", params={"engine": "rotax_912is"}).json()["faults"]
    ids = {f["id"] for f in faults}
    assert "F01" in ids and "F12" not in ids and "F06" not in ids          # applicability per engine


def test_inject_list_clear_roundtrip(client):
    r = client.post("/api/v1/engines/rotax_912is/faults",
                    json={"fault_id": "F23", "severity": 0.7, "ramp_s": 5, "source": "console", "request_id": "r1"})
    assert r.status_code == 200 and r.json()["fault"]["simulated"]
    uuid = r.json()["fault"]["uuid"]
    again = client.post("/api/v1/engines/rotax_912is/faults", json={"fault_id": "F23", "request_id": "r1"})
    assert again.json()["fault"]["uuid"] == uuid                            # idempotent retry
    active = client.get("/api/v1/engines/rotax_912is/faults").json()["active"]
    assert [f["uuid"] for f in active] == [uuid]
    assert client.delete(f"/api/v1/engines/rotax_912is/faults/{uuid}").status_code == 200
    assert client.get("/api/v1/engines/rotax_912is/faults").json()["active"] == []


@pytest.mark.parametrize("body,needle", [
    ({"fault_id": "F12"}, "fuel_system"),                  # carburettor icing on an injected engine
    ({"fault_id": "F01"}, "cylinder"),                     # per-cylinder fault without a cylinder
    ({"fault_id": "F99"}, "unknown"),
])
def test_invalid_faults_get_422_with_reason(client, body, needle):  # T-API-1
    r = client.post("/api/v1/engines/rotax_912is/faults", json=body)
    assert r.status_code == 422 and needle in r.json()["detail"]["message"]


def test_unknown_engine_404(client):
    assert client.get("/api/v1/engines/nope/faults").status_code == 404


def test_websocket_subscriber_sees_fault_injected_by_another_client(client):
    with client.websocket_connect("/ws/v1") as ws:
        ws.send_text(json.dumps({"subscribe": "rotax_912is"}))
        assert json.loads(ws.receive_text())["type"] == "subscribed"
        # another surface (the "3D view") injects through REST
        client.post("/api/v1/engines/rotax_912is/faults",
                    json={"fault_id": "F01", "cylinder": 2, "severity": 0.8, "ramp_s": 1, "source": "3d"})
        client.hub.tick_all()                               # the hub owns the clock; advance one tick
        seen = None
        for _ in range(50):
            data = json.loads(ws.receive_text())
            if data.get("type"):
                continue
            msg = StateMessage.model_validate(data)
            if any(f.fault_id == "F01" for f in msg.active_faults):
                seen = msg
                break
            client.hub.tick_all()
        assert seen is not None, "subscriber never saw the injected fault"
        f = next(f for f in seen.active_faults if f.fault_id == "F01")
        assert f.cylinder == 2 and f.source == "3d" and f.components == ["wiring_harness"]
        assert seen.status.level == "UNKNOWN"
    client.delete("/api/v1/engines/rotax_912is/faults")


def test_latest_only_queue_drops_old_messages():
    import asyncio
    c = api_v1.Client(ws=None, id="x")
    c.offer("a")
    c.offer("b")
    assert c.queue.get_nowait() == "b" and c.dropped == 1
    with pytest.raises(asyncio.QueueEmpty):
        c.queue.get_nowait()
