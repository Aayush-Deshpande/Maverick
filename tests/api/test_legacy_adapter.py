"""Card M0-08: the deprecated /api/state, /api/control and /ws/telemetry run on the ONE v1 runtime, plus the D52
command security (token, rate limit, command log, CORS).

Ported from tests/test_server_api.py (D38): state schema, SET_FAULT/CLEAR_FAULT, commanded-fault highlight,
throttle/environment, stop/start. Each port checks the same behaviour or stronger (values must equal the v1 runtime).
"""
import json

import pytest
from fastapi.testclient import TestClient

import backend.server.api_v1 as api_v1
import backend.server.security as security
from backend.runtime.hub import RuntimeHub, load_runtime_settings
from backend.server.legacy_adapter import LEGACY_ENGINE_ID
from backend.server.main import app

SEC = load_runtime_settings()["security"]


@pytest.fixture(scope="module")
def client():
    hub = RuntimeHub(engines=[LEGACY_ENGINE_ID])
    hub.calibrate_all(parallel=False)
    hub.tick_all()
    api_v1._services = api_v1.Services(hub)
    with TestClient(app) as c:
        c.hub = hub
        yield c
    api_v1._services = None


@pytest.fixture(autouse=True)
def fresh_limits(monkeypatch):
    monkeypatch.setattr(security, "RATE_LIMITER", security.RateLimiter(**SEC["command_rate_limit"]))
    monkeypatch.delenv(SEC["token_env"], raising=False)


def _state(client):
    client.hub.tick_all()
    r = client.get("/api/state")
    assert r.status_code == 200
    return r.json()


def test_state_comes_from_v1_runtime_with_nulls_not_defaults(client):     # was test_state_snapshot_schema
    data = _state(client)
    v1 = client.get(f"/api/v1/engines/{LEGACY_ENGINE_ID}/state").json()
    t, a = data["telemetry"], data["analytics"]
    for key in ("ENGINE_RPM", "PROP_RPM", "TPS", "CHT_1", "CHT_4", "EGT_1", "OIL_PRESS", "OIL_TEMP", "FUEL_FLOW",
                "MAP", "VIB_GEARBOX_RMS", "BUS_VOLTAGE"):
        assert key in t
    for key in ("residuals", "anomaly_score", "health_index", "diagnosed_fault_id", "go_no_go", "ata_chapter",
                "emergency_checklist"):
        assert key in a
    assert data["seq"] == v1["seq"]
    assert t["ENGINE_RPM"] == v1["readings"]["rpm"]["value"]
    assert t["OIL_PRESS"] == v1["readings"]["oil_p"]["value"]
    assert t["CHT_1"] == v1["readings"]["cht[1]"]["value"]
    # the old fixed values (audit section 4) are gone: unavailable fields are null with a reason
    for key in ("LAMBDA_AFR", "INJ_TIMING_BTDC", "BSFC_G_KWH", "THERMAL_EFFICIENCY", "POWER_KW"):
        assert t[key] is None and key in data["unavailable"]
    assert a["go_no_go"] is None and a["status_level"] == "UNKNOWN"


def test_set_fault_and_clear(client):                                     # was test_control_fault_activation_and_clearing
    res = client.post("/api/control", json={"action": "SET_FAULT", "fault_id": 1})
    assert res.status_code == 200 and res.json()["status"] == "SUCCESS"
    data = _state(client)
    assert data["active_commanded_fault_id"] == 1
    v1 = client.get(f"/api/v1/engines/{LEGACY_ENGINE_ID}/faults").json()["active"]
    assert [(f["fault_id"], f["cylinder"]) for f in v1] == [("F19", 2)]     # cylinder 2 overheat -> cooling, cyl 2
    res = client.post("/api/control", json={"action": "CLEAR_FAULT"})
    assert res.status_code == 200 and res.json()["status"] == "SUCCESS"
    assert _state(client)["active_commanded_fault_id"] == 0
    assert client.get(f"/api/v1/engines/{LEGACY_ENGINE_ID}/faults").json()["active"] == []


def test_legacy_fault_4_is_oil_pressure_loss(client):                      # card M0-08 done-when
    client.post("/api/control", json={"action": "SET_FAULT", "fault_id": 4})
    active = client.get(f"/api/v1/engines/{LEGACY_ENGINE_ID}/faults").json()["active"]
    assert [f["name"] for f in active] == ["OIL_PRESSURE_LOSS"]
    client.post("/api/control", json={"action": "CLEAR_FAULT"})


@pytest.mark.parametrize("fault_id", [0, 9, -1])
def test_unmapped_legacy_ids_get_422(client, fault_id):
    r = client.post("/api/control", json={"action": "SET_FAULT", "fault_id": fault_id})
    assert r.status_code == 422 and "legacy" in r.json()["detail"]["message"]


def test_commanded_fault_highlights_immediately(client):                  # was the same name
    try:
        for fault_id in range(1, 9):
            assert client.post("/api/control", json={"action": "SET_FAULT", "fault_id": fault_id}).status_code == 200
            data = _state(client)
            a = data["analytics"]
            assert data["active_commanded_fault_id"] == fault_id
            assert a["target_parts"] or a["target_markers"], f"fault {fault_id}: no highlight target"
            assert a["target_parts_kind"] == "INJECTED"
            if fault_id == 2:     # no injector mesh in the 912 model: a locator, not the whole engine
                assert any("injector 1" in m for m in a["target_markers"])
            client.post("/api/control", json={"action": "CLEAR_FAULT"})
    finally:
        client.post("/api/control", json={"action": "CLEAR_FAULT"})
    a = _state(client)["analytics"]
    assert a["target_parts"] == [] and a["target_markers"] == []


def test_throttle_and_environment_read_back(client):                      # was test_control_throttle_and_environment
    for body, key, value in ((({"action": "SET_THROTTLE", "throttle": 95.0}), "throttle_target", 95.0),
                             (({"action": "SET_ALTITUDE", "altitude_ft": 18000.0}), "altitude_target", 18000.0),
                             (({"action": "SET_OAT", "oat_c": -15.0}), "oat_target", -15.0)):
        r = client.post("/api/control", json=body)
        assert r.status_code == 200 and r.json()["status"] == "SUCCESS"
        assert r.json()["levers"][key] == value
    rt = client.hub.runtimes[LEGACY_ENGINE_ID]
    assert rt.levers.throttle_target == 95.0
    r = client.post("/api/control", json={"action": "SET_THROTTLE", "throttle": 150.0})
    assert r.status_code == 422                                           # same range as /api/v1 levers


def test_stop_and_start_rejected_with_reason_until_m1_12(client):         # was test_control_engine_stop_and_start
    for action in ("STOP_ENGINE", "START_ENGINE"):
        r = client.post("/api/control", json={"action": action})
        assert r.status_code == 422 and "M1-12" in r.json()["detail"]["message"]


@pytest.mark.xfail(strict=True, reason="T-M0-4: engine start/stop needs the engine state machine (card M1-12)")
def test_stop_really_stops_the_engine(client):
    assert client.post("/api/control", json={"action": "STOP_ENGINE"}).status_code == 200


def test_ws_telemetry_streams_v1_state_and_takes_commands(client):
    with client.websocket_connect("/ws/telemetry") as ws:
        first = json.loads(ws.receive_text())
        assert first["engine_id"] == LEGACY_ENGINE_ID and "telemetry" in first
        ws.send_text(json.dumps({"action": "SET_FAULT", "fault_id": 4}))
        for _ in range(50):
            msg = json.loads(ws.receive_text())
            if msg.get("type") in ("COMMAND_RESULT", "ERROR"):
                break
        assert msg["type"] == "COMMAND_RESULT" and msg["fault"]["fault_id"] == "F23"
    client.post("/api/control", json={"action": "CLEAR_FAULT"})


# ---- D52 security -------------------------------------------------------------------------------------------------

def test_token_required_when_set(client, monkeypatch):                     # T-OPS-4
    monkeypatch.setenv(SEC["token_env"], "s3cret-token")
    hdr = SEC["token_header"]
    url = f"/api/v1/engines/{LEGACY_ENGINE_ID}/levers"
    assert client.post(url, json={"throttle_pct": 60}).status_code == 401
    assert client.post(url, json={"throttle_pct": 60}, headers={hdr: "wrong"}).status_code == 401
    assert client.post(url, json={"throttle_pct": 60}, headers={hdr: "s3cret-token"}).status_code == 200
    assert client.post("/api/control", json={"action": "CLEAR_FAULT"}).status_code == 401
    assert client.get(f"/api/v1/engines/{LEGACY_ENGINE_ID}/state").status_code == 200    # reads stay open
    log = client.get("/api/v1/commands").json()["commands"]
    assert all("s3cret" not in json.dumps(e) for e in log)                               # token never logged


def test_rate_limit_per_client(client):
    limit = SEC["command_rate_limit"]["max_commands"]
    codes = [client.post(f"/api/v1/engines/{LEGACY_ENGINE_ID}/levers", json={"throttle_pct": 60}).status_code
             for _ in range(limit + 3)]
    assert codes[:limit] == [200] * limit and codes[limit:] == [429] * 3


def test_command_log_records_source_request_id_and_result(client):
    client.post(f"/api/v1/engines/{LEGACY_ENGINE_ID}/faults",
                json={"fault_id": "F99", "source": "console", "request_id": "log-1"})
    entry = [e for e in client.get("/api/v1/commands").json()["commands"] if e["request_id"] == "log-1"][-1]
    assert entry["source"] == "console" and entry["result"].startswith("422")


def test_cors_never_wildcard(monkeypatch):
    monkeypatch.setenv(SEC["cors_origins_env"], "*")
    with pytest.raises(ValueError):
        security.cors_origins()
    monkeypatch.setenv(SEC["cors_origins_env"], "https://a.example, https://b.example")
    assert security.cors_origins() == ["https://a.example", "https://b.example"]
    monkeypatch.delenv(SEC["cors_origins_env"])
    assert security.cors_origins() == SEC["cors_dev_origins"]
