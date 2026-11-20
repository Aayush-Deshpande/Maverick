"""T-MIS-1 (M5-01/M5-02): each PS scenario runs from its config through the mission executive (the operator's lever
path) and shows its effect: the NA 912 loses manifold pressure climbing out of Leh while the turbo 915 holds it to its
critical altitude; Thar ISA+30 runs hotter than the same leg at ISA; the rapid-throttle preset performs its throttle
transitions; the endurance preset becomes the mission-reliability profile."""
import pytest

from backend.mission.executive import list_missions, load_mission
from backend.runtime.engine_runtime import EngineRuntime


def _runtime(engine):
    rt = EngineRuntime(engine, seed=21, warmup_ticks=400)
    rt.calibrate()
    return rt


def _fly(rt, mission_id, seconds):
    rt.start_mission(mission_id)
    out = []
    for _ in range(int(seconds)):
        t = rt.tick()
        out.append(t)
    return out


def test_every_preset_is_listed_with_provenance():
    ids = {m["id"] for m in list_missions()}
    assert {"high_altitude_leh", "hot_weather_thar", "rapid_throttle", "endurance_18h", "endurance_24h_vrde"} <= ids
    assert all(m["provenance"]["ref"] for m in list_missions())


def _climb_map(ticks, lo, hi):
    v = [t.frame.map_kpa for t in ticks if lo <= t.frame.alt <= hi and 85 < t.frame.throttle < 95]
    return sum(v) / len(v)


def test_high_altitude_na_loses_map_turbo_holds_it():
    na = _fly(_runtime("rotax_912is"), "high_altitude_leh", 2100)
    assert _climb_map(na, 20000, 25000) < 0.75 * _climb_map(na, 11000, 13500)   # NA MAP follows ambient pressure
    tb = _fly(_runtime("rotax_915is"), "high_altitude_leh", 2100)
    low, crit, above = _climb_map(tb, 12500, 13500), _climb_map(tb, 13500, 15000), _climb_map(tb, 20000, 25000)
    assert crit >= 0.97 * low                          # the TCU holds boost up to the critical altitude ...
    assert above < 0.85 * crit                         # ... and above it the boost decays


def test_thar_runs_hotter_than_isa():
    hot = _fly(_runtime("rotax_912is"), "hot_weather_thar", 1500)
    rt = _runtime("rotax_912is")
    rt.set_levers(throttle_pct=75, altitude_ft=8000, oat_c=15 - 0.0019812 * 8000, snap=True)
    cool = [rt.tick() for _ in range(1500)]
    h, c = hot[-1].frame, cool[-1].frame
    assert h.oat > c.oat + 25
    # thermostats regulate oil and coolant, so the hot day shows as smaller margins on every temperature
    assert max(h.cht) > max(c.cht) + 3 and h.coolant_t > c.coolant_t + 2 and h.oil_t > c.oil_t and max(h.egt) > max(c.egt) + 10


def test_rapid_throttle_cycles_and_endurance_profile():
    rt = _runtime("rotax_914")
    ticks = _fly(rt, "rapid_throttle", 820)
    m = ticks[-1].mission
    assert m["state"] == "COMPLETE" or m["throttle_changes"] >= 39
    rpms = [t.frame.rpm for t in ticks[:120]]
    assert max(rpms) - min(rpms) > 1000                # the engine follows idle <-> take-off
    rt.start_mission("endurance_18h")
    t = [rt.tick() for _ in range(10)][-1]
    assert t.mission["remaining_s"] > 17 * 3600
    with pytest.raises(ValueError):
        rt.start_mission("endurance_24h_vrde")         # defined for the VRDE only
    assert load_mission("endurance_24h_vrde")["engines"] == ["vrde_jayem_2_2l"]
