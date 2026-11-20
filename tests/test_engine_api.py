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
    import backend.server.api_v1 as api_v1
    api_v1._services = api_v1.Services(h)
    app = FastAPI()
    app.include_router(api.router)
    app.include_router(api_v1.router)
    yield TestClient(app)
    api._hub = None
    api_v1._services = None


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
    assert ok.status_code == 200 and ok.json()["fault"]["source"] == "legacy"
    # M0-10: the old endpoint goes through the ONE fault manager, so v1 clients see the same fault
    active = client.get("/api/v1/engines/rotax_914/faults").json()["active"]
    assert [(f["fault_id"], f["cylinder"]) for f in active] == [("F01", 2)]
    # numeric ids only through registry legacy_ids (audit #18): 4 = oil pressure loss, 9 is not mapped
    four = client.post("/api/engines/rotax_914/faults", json={"fault_id": 4})
    assert four.status_code == 200 and four.json()["fault"]["name"] == "OIL_PRESSURE_LOSS"
    assert client.post("/api/engines/rotax_914/faults", json={"fault_id": 9}).status_code == 422
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


def test_engine_schema(client):
    r = client.get("/api/engines/rotax_914/schema")
    assert r.status_code == 200
    data = r.json()
    assert data["engine_id"] == "rotax_914"
    assert "channels" in data
    assert "operating_limits" in data
    assert client.get("/api/engines/nonexistent_engine/schema").status_code == 404


def test_engine_wide_legacy_mode_injects_every_cylinder(client):
    """3D twin "Cooling" button: COOLING_DEGRADATION has no cylinder in the old library; the registry fault (F19) is
    per-cylinder, so the legacy route applies it to every cylinder instead of rejecting it (it used to 422)."""
    from backend.physics.engine_config import load_engine_config
    engine_id = "rotax_914"
    r = client.post(f"/api/engines/{engine_id}/faults", json={"mode": "COOLING_DEGRADATION", "severity": 0.8, "ramp_sec": 30})
    assert r.status_code == 200, r.text
    assert sorted(f["cylinder"] for f in r.json()["faults"]) == list(range(1, load_engine_config(engine_id).cylinder_count + 1))
    client.delete(f"/api/engines/{engine_id}/faults")


def test_every_twin_fault_button_injects(client):
    """The 3D twin draws its fault buttons from /api/engines faults; each one must be applicable and accepted (sensor
    modes go to the chosen cylinder's CHT sensor), so no button silently fails."""
    import time
    for profile in client.get("/api/engines").json()["engines"]:
        eid = profile["engine_id"]
        for f in profile["faults"]:
            body = {"mode": f["mode"], "severity": 0.8, "ramp_sec": 30}
            if f["per_cylinder"]:
                body["cylinder"] = 2
            r = client.post(f"/api/engines/{eid}/faults", json=body)
            assert r.status_code == 200, (eid, f["mode"], r.text)
            client.delete(f"/api/engines/{eid}/faults")
            time.sleep(0.12)                      # stay under the per-client command rate limit (D52)
