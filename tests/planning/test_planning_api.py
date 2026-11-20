"""/api/v1 terrain + planning (M5-07/M5-08, T-MIS-6 through the API). Synthetic terrain from test_planner."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.server.api_v1 as api_v1
from backend.planning.planner import Planner
from backend.runtime.hub import RuntimeHub
from backend.terrain.dem import TerrainUnavailable
from tests.planning.test_planner import NORTH, SOUTH, synthetic_tile

ENGINE = "rotax_912is"


@pytest.fixture(scope="module")
def client():
    hub = RuntimeHub(engines=[ENGINE])
    hub.calibrate_all(parallel=False)
    for _ in range(3):
        hub.tick_all()
    api_v1._services = api_v1.Services(hub)
    app = FastAPI()
    app.include_router(api_v1.router)
    tile = synthetic_tile()
    mp = pytest.MonkeyPatch()
    mp.setattr(api_v1, "_terrain_tile", lambda: tile)
    mp.setitem(api_v1._PLANNERS, tile.name, Planner(tile))
    with TestClient(app) as c:
        yield c
    mp.undo()
    api_v1._services = None


def _route(**kw):
    body = {"engine_id": ENGINE, "start": {"lat": NORTH[0], "lon": NORTH[1], "altitude_ft": NORTH[2]},
            "goal": {"lat": SOUTH[0], "lon": SOUTH[1]}}
    body.update(kw)
    return body


def test_elevation(client):
    r = client.get("/api/v1/terrain/elevation", params={"lat": 34.95, "lon": 77.05})
    assert r.status_code == 200 and r.json()["elevation_m"] == pytest.approx(3000.0)
    assert client.get("/api/v1/terrain/elevation", params={"lat": 20.0, "lon": 77.05}).status_code == 422


def test_route_feasible_then_refused_when_power_drops(client):
    ok = client.post("/api/v1/planning/route", json=_route(power_factor=1.0)).json()
    assert ok["feasible"] and ok["waypoints"] and ok["power_factor_source"]["kind"] == "OPERATOR"
    bad = client.post("/api/v1/planning/route", json=_route(power_factor=0.7)).json()
    assert not bad["feasible"] and "service ceiling" in bad["reason"]


def test_route_uses_measured_power_when_not_given(client):
    r = client.post("/api/v1/planning/route", json=_route())
    assert r.status_code == 200, r.text
    src = r.json()["power_factor_source"]
    assert src["kind"] == "MEASURED" and "map_kpa" in src["ratios"]
    assert 0.9 < r.json()["power_factor"] <= 1.0                     # healthy tail reads close to the nominal model


@pytest.mark.parametrize("bad", [{"power_factor": 1.5}, {"isa_dev_c": 90}, {"surprise": 1}])
def test_route_input_validation(client, bad):
    assert client.post("/api/v1/planning/route", json=_route(**bad)).status_code == 422


def test_terrain_unavailable_is_503_not_flat(client, monkeypatch):
    def missing():
        raise api_v1.HTTPException(503, {"code": "TERRAIN_UNAVAILABLE", "message": "x"})
    monkeypatch.setattr(api_v1, "_terrain_tile", missing)
    assert client.get("/api/v1/terrain/elevation", params={"lat": 34.9, "lon": 77.1}).status_code == 503
    assert issubclass(TerrainUnavailable, RuntimeError)


def test_airfield_presets_carry_sources(client):
    body = client.get("/api/v1/planning/airfields").json()
    assert body["status"] == "PUBLIC" and body["airfields"]
    assert all(a["ref"] and -90 <= a["lat"] <= 90 for a in body["airfields"])


def _glide_body(**kw):
    body = {"position": {"lat": NORTH[0], "lon": NORTH[1], "altitude_ft": 20000.0}}
    body.update(kw)
    return body


def test_glide_endpoint_ranks_configured_airfields(client):
    r = client.post("/api/v1/planning/glide", json=_glide_body())
    assert r.status_code == 200, r.text
    g = r.json()
    assert g["evidence_class"] == "SIMULATION" and g["terrain"] == "synthetic" and g["footprint"]
    assert len(g["reachable_airfields"]) >= 3
    assert all(not a["terrain_checked"] for a in g["reachable_airfields"])   # Ladakh fields are off the synthetic tile
    assert client.post("/api/v1/planning/glide", json={"position": {"lat": 35.0, "lon": 77.0}}).status_code == 422
    assert client.post("/api/v1/planning/glide", json=_glide_body(headwind_kt=500)).status_code == 422


def test_divert_reports_glide_and_powered_route_parts(client):
    r = client.post("/api/v1/planning/divert", json={"engine_id": ENGINE, "airfield_id": "VILH", "power_factor": 1.0,
                                                    "position": {"lat": NORTH[0], "lon": NORTH[1], "altitude_ft": 20000.0}})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["airfield"]["id"] == "VILH" and d["airfield"]["ref"]
    assert d["glide"]["airfield_id"] == "VILH"
    assert d["powered_route"]["feasible"] is False and "outside" in d["powered_route"]["reason"]   # Leh is off this tile
    bad = {"engine_id": ENGINE, "airfield_id": "NOPE", "position": {"lat": 35.0, "lon": 77.0, "altitude_ft": 9000.0}}
    assert client.post("/api/v1/planning/divert", json=bad).status_code == 422


def test_position_lever_moves_the_runtime_glide(client):
    assert client.post(f"/api/v1/engines/{ENGINE}/levers", json={"lat": 34.5}).status_code == 422
    r = client.post(f"/api/v1/engines/{ENGINE}/levers", json={"lat": 34.6, "lon": 77.4})
    assert r.status_code == 200 and r.json()["targets"]["position"] == {"lat": 34.6, "lon": 77.4}
