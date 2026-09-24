"""R4: engine API over the hub (uses a small hub injected into the router module)."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.server.engine_api as api
from backend.runtime import RuntimeHub


@pytest.fixture(scope="module")
def client():
    h = RuntimeHub(["rotax_912is", "rotax_914"], seed=0, warmup_ticks=600)
    h.calibrate_all()
    for _ in range(5):
        h.tick_all()
    api._hub = h
    app = FastAPI()
    app.include_router(api.router)
    yield TestClient(app)
    api._hub = None


def test_list_and_profiles(client):
    r = client.get("/api/engines").json()
    ids = {e["engine_id"]: e for e in r["engines"]}
    assert set(ids) == {"rotax_912is", "rotax_914"}
    assert "BOOST_LEAK" not in {f["mode"] for f in ids["rotax_912is"]["faults"]}
    assert "BOOST_LEAK" in {f["mode"] for f in ids["rotax_914"]["faults"]}


def test_state_has_no_truth_fields(client):
    s = client.get("/api/engines/rotax_914/state").json()
    assert s["evidence_class"] == "SIMULATION" and "detection" in s
    flat = str(s).upper()
    for banned in ("FAULT_ID", "HEALTH_INDEX", "RUL_HOURS"):
        assert banned not in flat


def test_fault_validation_and_select(client):
    assert client.post("/api/engines/rotax_912is/faults", json={"mode": "BOOST_LEAK"}).status_code == 422
    assert client.post("/api/engines/rotax_914/faults", json={"mode": "MISFIRE"}).status_code == 422
    ok = client.post("/api/engines/rotax_914/faults", json={"mode": "MISFIRE", "cylinder": 2})
    assert ok.status_code == 200 and ok.json()["origin"] == "MANUAL"
    assert client.delete("/api/engines/rotax_914/faults").status_code == 200
    assert client.post("/api/engines/select", json={"engine_id": "nope"}).status_code == 404
    assert client.post("/api/engines/select", json={"engine_id": "rotax_912is"}).json()["selected"] == "rotax_912is"
    assert client.get("/api/engines/ghost/state").status_code == 404


def test_levers(client):
    r = client.post("/api/engines/rotax_914/levers", json={"throttle_pct": 90, "altitude_ft": 15000}).json()
    assert r["throttle_target"] == 90 and r["altitude_target"] == 15000


def test_ws_engine_streams(client):
    with client.websocket_connect("/ws/engines/rotax_914") as ws:
        api._hub.tick_all()
        msg = ws.receive_json()
        assert msg["engine_id"] == "rotax_914"


def test_ws_fleet(client):
    with client.websocket_connect("/ws/fleet") as ws:
        msg = ws.receive_json()
        assert {e["engine_id"] for e in msg["engines"]} == {"rotax_912is", "rotax_914"}
