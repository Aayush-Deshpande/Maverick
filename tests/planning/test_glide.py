"""M5-09 glide reachability and divert (I-10). Same synthetic terrain as test_planner: 3000 m valley split by a
5800 m east-west ridge. An airfield south of the ridge is reachable by glide from high enough, and BLOCKED_BY_TERRAIN
(not "reachable") when the straight glide line would hit the ridge although the arrival altitude alone looks fine."""
import math

import pytest

from backend.mission.glide import (FT_PER_M, DiversionAirfield, UAVGlidePolar, configured_airfields,
                                   haversine_m)
from backend.planning.performance import planning_config
from tests.planning.test_planner import POST, RIDGE_M, VALLEY_M, synthetic_tile

START = (35.0 - 60 * POST, 77.0 + 60 * POST)                          # north of the ridge, west end
SOUTH_FIELD = DiversionAirfield("S", "south", 35.0 - 540 * POST, 77.0 + 60 * POST, VALLEY_M * FT_PER_M)
NORTH_FIELD = DiversionAirfield("N", "north", 35.0 - 120 * POST, 77.0 + 200 * POST, VALLEY_M * FT_PER_M)
FAR_FIELD = DiversionAirfield("F", "off tile", 34.5, 76.2, VALLEY_M * FT_PER_M)


def test_polar_comes_from_the_planning_airframe_and_windmills_without_a_feathering_prop():
    c = planning_config()
    af, g = c["airframe"], c["glide"]
    p = UAVGlidePolar()
    ld_clean = 1.0 / (2.0 * math.sqrt(af["cd0"]["value"] * af["induced_k"]["value"]))
    assert p.ld_max_feathered == pytest.approx(ld_clean)
    ga = p.assess_glide(15000.0, *START, airfields=[])
    if not g["feathering_propeller"]["value"]:
        assert not ga.feathered and ga.ld_ratio == pytest.approx(ld_clean * g["windmill_ld_factor"]["value"])
    assert ga.sink_rate_fpm > 0 and ga.best_glide_tas_kt > 0
    # thinner air -> faster best-glide TAS, same L/D
    assert p.assess_glide(25000.0, *START, airfields=[]).best_glide_tas_kt > ga.best_glide_tas_kt


def test_ridge_blocks_a_glide_that_the_altitude_budget_alone_would_allow():
    p = UAVGlidePolar()
    t = synthetic_tile(with_pass=False)
    low = p.assess_glide(20000.0, *START, airfields=[SOUTH_FIELD], terrain=t).airfields[0]
    assert low.alt_margin_ft > 0                              # enough height to arrive over flat ground ...
    assert low.terrain_checked and low.status == "BLOCKED_BY_TERRAIN" and not low.is_reachable
    assert low.min_terrain_clearance_ft < planning_config()["glide"]["glide_clearance_ft"]["value"]
    high = p.assess_glide(25000.0, *START, airfields=[SOUTH_FIELD], terrain=t).airfields[0]
    assert high.is_reachable and high.min_terrain_clearance_ft >= planning_config()["glide"]["glide_clearance_ft"]["value"]


def test_ranking_recommends_the_reachable_field_and_off_tile_paths_are_not_assumed_clear():
    t = synthetic_tile(with_pass=False)
    ga = UAVGlidePolar().assess_glide(20000.0, *START, airfields=[SOUTH_FIELD, FAR_FIELD, NORTH_FIELD], terrain=t)
    assert ga.recommended_diversion is not None and ga.recommended_diversion.airfield_id == "N"
    far = next(a for a in ga.airfields if a.airfield_id == "F")
    assert not far.terrain_checked and far.min_terrain_clearance_ft is None
    assert [a.is_reachable for a in ga.airfields] == sorted([a.is_reachable for a in ga.airfields], reverse=True)


def test_headwind_shrinks_reach():
    p = UAVGlidePolar()
    calm = p.assess_glide(20000.0, *START, airfields=[NORTH_FIELD]).airfields[0]
    windy = p.assess_glide(20000.0, *START, headwind_kt=30.0, airfields=[NORTH_FIELD]).airfields[0]
    assert windy.alt_required_ft > calm.alt_required_ft


def test_footprint_stops_at_the_ridge_to_the_south():
    t = synthetic_tile(with_pass=False)
    fp = UAVGlidePolar().assess_glide(20000.0, *START, airfields=[], terrain=t, footprint=True).footprint
    assert fp and len(fp) == planning_config()["glide"]["footprint_bearings"]["value"]
    south = next(pt for pt in fp if pt["bearing_deg"] == 180.0)
    to_ridge_km = haversine_m(START[0], START[1], 35.0 - 280 * POST, START[1]) / 1000.0
    assert 0.5 * to_ridge_km < south["range_km"] <= to_ridge_km


def test_configured_airfields_carry_sources():
    fields = configured_airfields()
    assert len(fields) >= 3 and all(f.ref for f in fields)
