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
        assert seen.status.level != "UNKNOWN"                    # M2-01 evaluator runs on every tick
    client.delete("/api/v1/engines/rotax_912is/faults")


def test_latest_only_queue_drops_old_messages():
    """Latest-only per engine (T-WS-1): an unsent older message of the same engine is replaced and counted."""
    c = api_v1.Client(ws=None, id="x")
    c.offer("a", "rotax_912is")
    c.offer("b", "rotax_912is")
    assert c.take() == ["b"] and c.dropped == 1
    assert c.take() == []


def test_fleet_client_keeps_the_latest_message_of_every_engine():
    """A fleet subscriber must not starve: one engine's frame never replaces another engine's unsent frame
    (found 20 Nov 2026: a single size-1 queue let only the last engine of each broadcast cycle through)."""
    c = api_v1.Client(ws=None, id="x")
    for engine in ("austro_ae300", "rotax_914", "rotax_912is"):
        c.offer(f"m-{engine}", engine)
    assert sorted(c.take()) == ["m-austro_ae300", "m-rotax_912is", "m-rotax_914"] and c.dropped == 0


def test_component_manifest_endpoint_serves_the_web_model_and_exact_nodes(client):
    """M6-05: the viewer gets the GLB and the component -> node map from the API, never from code."""
    r = client.get("/api/v1/engines/rotax_912is/components")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model_url"] == "/models/rotax_912is.glb"
    oil = next(c for c in body["components"] if c["component_id"] == "oil_tank")
    assert oil["nodes"] and all(n.startswith("Oil_Tank_") for n in oil["nodes"])
    assert client.get("/api/v1/engines/nope/components").status_code == 404


def test_engine_list_names_the_configured_default_engine(client):
    """Prasad 20 Nov 2026 (D25/D47): every first-time visitor starts on the Rotax 912 iS Sport. The choice is
    configuration (configs/runtime.json default_engine_id), served by the API, never a literal in the UI."""
    import json
    from pathlib import Path
    want = json.loads((Path(__file__).resolve().parents[2] / "configs" / "runtime.json").read_text())["default_engine_id"]
    body = client.get("/api/v1/engines").json()
    assert body["default_engine_id"] == want
    assert want in [e["engine_id"] for e in body["engines"]]


def test_ui_labels_are_served_from_config(client):
    """M6-06: human names for channels, parts and status come from configs/ui/labels_<lang>.json."""
    body = client.get("/api/v1/ui/labels").json()
    assert body["channels"]["oil_p"] == "Oil pressure"
    assert set(body["status"]) >= {"GO", "ADVISORY", "CAUTION", "NO-GO", "ENGINE_OFF", "UNKNOWN"}
    assert client.get("/api/v1/ui/labels", params={"lang": "xx"}).status_code == 404
    assert client.get("/api/v1/ui/labels", params={"lang": "../runtime"}).status_code == 422


def test_ui_demo_scenario_is_served_from_config_and_injectable(client):
    """Landing "Run the demo" (D57): the scenario comes from configs/ui/demo.json and its fault is accepted by the normal
    fault endpoint for its engine, with source "demo"."""
    demo = client.get("/api/v1/ui/demo").json()
    engines = {e["engine_id"] for e in client.get("/api/v1/engines").json()["engines"]}
    assert demo["engine_id"] in engines
    applicable = {f["id"] for f in client.get("/api/v1/faults", params={"engine": demo["engine_id"]}).json()["faults"]}
    assert demo["inject"]["fault_id"] in applicable
    r = client.post(f"/api/v1/engines/{demo['engine_id']}/faults",
                    json={**demo["inject"], "source": "demo", "request_id": "demo-test-1"})
    assert r.status_code in (200, 201), r.text
    client.delete(f"/api/v1/engines/{demo['engine_id']}/faults")


def test_state_carries_estimated_efficiency_from_measured_fuel_flow(client):
    """P Part 3.10 efficiency trends: indicated power (twin estimate) with the measured fuel flow gives indicated BSFC
    and thermal efficiency; a missing input gives null, never a default."""
    from backend.server.state_builder import _derived
    from types import SimpleNamespace
    d = _derived(SimpleNamespace(virtual_sensors={"P_ind_kw": 60.0}, fuel_flow=15.0), "rotax_912is")
    assert d["bsfc_ind_g_kwh_est"] == 250.0
    assert 0.25 < d["thermal_eff_ind_est"] < 0.45                    # 60 kW from 15 kg/h of avgas at 43.5 MJ/kg
    gone = _derived(SimpleNamespace(virtual_sensors={}, fuel_flow=15.0), "rotax_912is")
    assert gone == {"power_ind_kw_est": None, "bsfc_ind_g_kwh_est": None, "thermal_eff_ind_est": None}
