"""
Unit & Integration Tests for Backend FastAPI Telemetry & Control Server
DRDO / iDEX Problem Statement ID: 26054
"""

import os
import pytest
from fastapi.testclient import TestClient
from backend.server.main import app
from backend.server.engine_service import EngineStateService


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert data["drdo_ps_id"] == "26054"
    assert "endpoints" in data


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "sortie_id" in data
    assert "is_engine_running" in data
    assert data["loop_frequency_hz"] == 20.0


def test_state_snapshot_schema(client):
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.json()
    
    assert "telemetry" in data
    assert "analytics" in data
    assert "timestamp" in data
    assert "sortie_id" in data
    
    t = data["telemetry"]
    assert "ENGINE_RPM" in t
    assert "PROP_RPM" in t
    assert "TPS" in t
    assert "CHT_1" in t
    assert "CHT_2" in t
    assert "CHT_3" in t
    assert "CHT_4" in t
    assert "EGT_1" in t
    assert "OIL_PRESS" in t
    assert "OIL_TEMP" in t
    assert "FUEL_FLOW" in t
    assert "MAP" in t
    assert "VIB_GEARBOX_RMS" in t
    assert "BUS_VOLTAGE" in t
    
    a = data["analytics"]
    assert "residuals" in a
    assert "anomaly_score" in a
    assert "health_index" in a
    assert "diagnosed_fault_id" in a
    assert "go_no_go" in a
    assert "ata_chapter" in a
    assert "emergency_checklist" in a


def test_control_fault_activation_and_clearing(client):
    # 1. Activate Fault 1 (Cyl #2 Overheat)
    res = client.post("/api/control", json={"action": "SET_FAULT", "fault_id": 1})
    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"
    
    # Check state reflects commanded fault
    state_res = client.get("/api/state")
    data = state_res.json()
    assert data["active_commanded_fault_id"] == 1
    
    # 2. Clear fault
    res_clear = client.post("/api/control", json={"action": "CLEAR_FAULT"})
    assert res_clear.status_code == 200
    assert res_clear.json()["status"] == "SUCCESS"
    
    state_res = client.get("/api/state")
    data = state_res.json()
    assert data["active_commanded_fault_id"] == 0


def test_control_throttle_and_environment(client):
    # Set throttle to 85%
    res = client.post("/api/control", json={"action": "SET_THROTTLE", "throttle": 85.0})
    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"
    
    # Set altitude to 18,000 ft
    res_alt = client.post("/api/control", json={"action": "SET_ALTITUDE", "altitude_ft": 18000.0})
    assert res_alt.status_code == 200
    assert res_alt.json()["status"] == "SUCCESS"
    
    # Set OAT
    res_oat = client.post("/api/control", json={"action": "SET_OAT", "oat_c": -15.0})
    assert res_oat.status_code == 200
    assert res_oat.json()["status"] == "SUCCESS"


def test_control_engine_stop_and_start(client):
    # Stop engine
    res = client.post("/api/control", json={"action": "STOP_ENGINE"})
    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"
    
    state = client.get("/api/state").json()
    assert state["is_engine_running"] is False
    assert state["telemetry"]["ENGINE_RPM"] == 0.0
    
    # Restart engine
    res_start = client.post("/api/control", json={"action": "START_ENGINE"})
    assert res_start.status_code == 200
    assert res_start.json()["status"] == "SUCCESS"
    
    state = client.get("/api/state").json()
    assert state["is_engine_running"] is True


def test_debrief_export_endpoint(client):
    res = client.post("/api/debrief")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert "report_path" in data

    # MissionReporter (via the real EngineStateService singleton) always writes into the
    # actual data/mission_reports/ folder - there's no output_dir override reachable through
    # this HTTP endpoint the way test_agent_and_graph.py's unit test uses tempfile.mkdtemp()
    # for its own direct MissionReporter instance. Clean up so repeated local/CI runs don't
    # leave growing untracked cruft in the real data directory.
    report_path = data.get("report_path")
    if report_path and os.path.exists(report_path):
        os.remove(report_path)
