"""T-MIS-6 (cards M5-07/M5-08): the planner refuses an infeasible terrain route with a reason and replans when lost
engine power lowers the service ceiling. Synthetic terrain (no download needed): a 3000 m valley floor split by a
5800 m ridge with one 4500 m pass. The real Leh tile is checked only when var/dem holds it (external data, D33)."""
import numpy as np
import pytest

from backend.planning.performance import power_factor_from_frame, service_ceiling_ft
from backend.planning.planner import FT_PER_M, Planner
from backend.terrain.dem import DemTile, TerrainUnavailable, load_tile, tile_name

ENGINE = "rotax_912is"
POST = 1.0 / 3600.0
VALLEY_M, RIDGE_M, PASS_M = 3000.0, 5800.0, 4500.0


def synthetic_tile(with_pass: bool = True) -> DemTile:
    z = np.full((600, 600), VALLEY_M)
    z[280:320, :] = RIDGE_M                       # east-west ridge across the middle
    if with_pass:
        z[280:320, 480:540] = PASS_M              # one pass near the east end
    t = DemTile.__new__(DemTile)
    t.z, t.name, t.lat0, t.lon0, t.dlat, t.dlon = z, "synthetic", 35.0, 77.0, POST, POST
    t.rows, t.cols = z.shape
    return t


NORTH = (35.0 - 60 * POST, 77.0 + 60 * POST, 11000.0)          # start north of the ridge, west end
SOUTH = (35.0 - 540 * POST, 77.0 + 60 * POST)                   # goal south of the ridge, west end


def test_bilinear_elevation_and_tile_name():
    t = synthetic_tile()
    assert t.elevation_m(35.0 - 100 * POST, 77.01) == pytest.approx(VALLEY_M)
    assert t.elevation_m(35.0 - 300 * POST, 77.01) == pytest.approx(RIDGE_M)
    assert tile_name(34.13, 77.54) == "Copernicus_DSM_COG_10_N34_00_E077_00_DEM"
    with pytest.raises(ValueError):
        t.elevation_m(36.0, 77.5)


def test_missing_tile_is_unavailable_not_flat(tmp_path):
    with pytest.raises(TerrainUnavailable):
        DemTile(tmp_path / "nothing.tif")


def test_healthy_engine_routes_through_the_pass_with_clearance():
    p = Planner(synthetic_tile())
    plan = p.plan(ENGINE, NORTH, SOUTH, power_factor=1.0)
    assert plan.feasible, plan.reason
    pass_need_ft = PASS_M * FT_PER_M + p.clearance_ft
    assert pass_need_ft <= plan.max_altitude_ft <= service_ceiling_ft(ENGINE, 1.0)
    assert plan.min_clearance_ft >= p.clearance_ft
    assert plan.max_altitude_ft < RIDGE_M * FT_PER_M + p.clearance_ft   # it did not climb over the ridge


def test_refuses_infeasible_route_with_reason():
    p = Planner(synthetic_tile(with_pass=False))
    plan = p.plan(ENGINE, NORTH, SOUTH, power_factor=1.0)
    assert not plan.feasible and not plan.waypoints
    assert "service ceiling" in plan.reason and plan.required_altitude_ft > plan.service_ceiling_ft


def test_replans_when_a_fault_cuts_available_power():
    p = Planner(synthetic_tile())
    healthy = p.plan(ENGINE, NORTH, SOUTH, power_factor=1.0)
    assert healthy.feasible
    degraded_ceiling = service_ceiling_ft(ENGINE, 0.7)
    assert degraded_ceiling < PASS_M * FT_PER_M + p.clearance_ft            # the fault takes the pass away
    again = p.replan(ENGINE, NORTH, SOUTH, power_factor=0.7)
    assert not again.feasible and again.required_altitude_ft > degraded_ceiling
    home = p.replan(ENGINE, NORTH, (35.0 - 60 * POST, 77.0 + 400 * POST), power_factor=0.7)
    assert home.feasible and home.max_altitude_ft <= degraded_ceiling       # stays in the northern valley


def test_power_factor_from_measured_evidence_only():
    pf, used = power_factor_from_frame({"map_kpa": 80.0, "rpm": 5000.0}, {"map_kpa": 100.0, "rpm": 5000.0},
                                       governed=False)
    assert pf == pytest.approx(0.8) and set(used) == {"map_kpa", "rpm"}
    pf, _ = power_factor_from_frame({"map_kpa": 110.0}, {"map_kpa": 100.0}, governed=True)
    assert pf == 1.0                                                          # never more than the healthy model
    assert power_factor_from_frame({"map_kpa": None}, {"map_kpa": 100.0}, governed=True)[0] is None


def test_real_leh_tile_when_present():
    try:
        tile = load_tile("Copernicus_DSM_COG_10_N34_00_E077_00_DEM")
    except TerrainUnavailable as exc:
        pytest.skip(f"external data not downloaded (D33): {exc}")
    leh_m = tile.elevation_m(34.1359, 77.5465)                 # Leh airfield, published elevation about 3256 m
    assert abs(leh_m - 3256.0) < 40.0
    plan = Planner(tile).plan(ENGINE, (34.1359, 77.5465, 10700.0), (34.65, 77.375), power_factor=1.0)
    assert plan.feasible and plan.min_clearance_ft >= 1000.0


def test_tile_name_round_trips_through_load_tile():
    """The planner cache in the API reloads tiles by tile.name: it must be the tile id, not the file name."""
    try:
        tile = load_tile(tile_name(34.13, 77.54))
    except TerrainUnavailable:
        pytest.skip("Copernicus tile not in var/dem (external data, D33)")
    assert tile.name == tile_name(34.13, 77.54)
    assert load_tile(tile.name).name == tile.name
