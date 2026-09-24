"""Characterization tests (B0.9): evaluation/harness, osacbm, physics/exposure, edge/compressor."""
import importlib
import struct

import pytest

from backend import osacbm
from backend.edge.compressor import (
    EdgeCompressor, EdgeFeatureFrame, LatencyBudget, LinkBudget, PowerBudget,
)
from backend.evaluation.harness import (
    DEFAULT_SCENARIOS, EvaluationHarness, Scenario,
)
from backend.physics.exposure import ExposureAccumulator, ExposureRecord


# ---- harness (short scenarios so the file stays fast) ---------------------

def test_harness_nominal_no_false_alarms_and_deterministic():
    s = Scenario("nom", duration_sec=600, is_nominal=True)
    a = EvaluationHarness().run_scenario(s).as_dict()
    b = EvaluationHarness().run_scenario(s).as_dict()
    assert a == b
    assert a["twin_detection_t_sec"] is None and a["baseline_alarm_t_sec"] is None
    assert a["twin_false_alarms"] == 0 and a["baseline_false_alarms"] == 0
    assert a["flight_hours"] == pytest.approx(600 / 3600, abs=1e-3)


def test_harness_misfire_detected_by_crank_channel_on_right_cylinder():
    s = Scenario("mf", duration_sec=1500, fault="MISFIRE", fault_cylinder=3,
                 fault_severity=0.9, fault_onset_sec=400, fault_ramp_sec=200)
    r = EvaluationHarness().run_scenario(s).as_dict()
    assert r["crank_cylinder"] == 3
    assert 400 <= r["crank_detection_t_sec"] <= 500      # measured 420 s
    assert r["twin_detection_t_sec"] is not None
    assert r["twin_detection_t_sec"] > 400               # never before onset
    assert r["detection_latency_sec"] == pytest.approx(r["twin_detection_t_sec"] - 400)
    assert r["baseline_alarm_t_sec"] is None             # thresholds never fire on a misfire


def test_harness_cooling_degradation_plant_fails_and_twin_warns_first():
    s = Scenario("cool", duration_sec=2400, fault="COOLING_DEGRADATION",
                 fault_severity=0.95, fault_onset_sec=400, fault_ramp_sec=1200)
    r = EvaluationHarness().run_scenario(s).as_dict()
    assert any("CHT_OVERTEMP" in n for n in r["notes"])
    assert r["twin_detection_t_sec"] is not None
    assert r["twin_warning_before_failure_sec"] > 0
    assert r["twin_classification"] == "ENGINE_FAULT"


def test_harness_run_all_summary_and_markdown():
    rep = EvaluationHarness().run_all([Scenario("n", duration_sec=600, is_nominal=True)])
    s = rep["summary"]
    assert s["scenarios"] == 1 and s["fault_scenarios"] == 0
    assert s["median_lead_time_sec"] is None
    assert s["twin_false_alarms_per_hour"] == 0.0
    assert "Detection evaluation" in EvaluationHarness.to_markdown(rep)


def test_default_scenarios_catalogue():
    names = [s.name for s in DEFAULT_SCENARIOS]
    assert names[0] == "nominal_cruise_2h"
    assert len(names) == len(set(names))
    assert sum(1 for s in DEFAULT_SCENARIOS if s.is_nominal) >= 2
    assert all(s.fault is None or s.fault.isupper() for s in DEFAULT_SCENARIOS)


# ---- osacbm ---------------------------------------------------------------

def test_osacbm_registry_headline():
    assert len(osacbm.OSACBM_REGISTRY) == 27
    assert osacbm.Layer.ORDER[0] == osacbm.Layer.DA and osacbm.Layer.index(osacbm.Layer.AG) == 5
    assert osacbm.check_layering() == []
    cov = osacbm.coverage()
    assert [cov[l]["modules"] for l in osacbm.Layer.ORDER] == [4, 6, 4, 4, 6, 3]
    pending = [m for c in cov.values() for m in c["pending"]]
    assert pending == ["backend.ml.spectral_analyser"]
    assert len({r.module for r in osacbm.OSACBM_REGISTRY}) == 27


def test_osacbm_registered_modules_import():
    for reg in osacbm.OSACBM_REGISTRY:
        importlib.import_module(reg.module)


def test_osacbm_layering_violation_is_detected():
    bad = osacbm.ModuleRegistration("x.y", osacbm.Layer.DA, "p", [], [osacbm.Layer.AG])
    osacbm.OSACBM_REGISTRY.append(bad)
    try:
        assert len(osacbm.check_layering()) == 1
    finally:
        osacbm.OSACBM_REGISTRY.remove(bad)
    assert osacbm.check_layering() == []
    md = osacbm.architecture_markdown()
    assert "No layering violations" in md and "OSA-CBM" in md


# ---- exposure -------------------------------------------------------------

def test_exposure_baseline_environment_is_baseline():
    a = ExposureAccumulator("S1")
    for _ in range(3600):
        a.update(1.0, dust_mg_m3=0.15, oat_c=15.0, cht_c=100.0, altitude_ft=5000.0)
    assert a.record.total_hours == pytest.approx(1.0)
    f = a.acceleration_factors()
    assert all(v == pytest.approx(1.0) for v in f.values())
    assert a.summary()["severity"] == "BASELINE"
    assert a.record.max_altitude_ft == 5000.0


def test_exposure_harsh_environment_accelerates_wear():
    a = ExposureAccumulator("S2")
    for _ in range(3600):
        a.update(1.0, dust_mg_m3=6.0, oat_c=-30.0, cht_c=130.0, altitude_ft=25000.0,
                 over_water=True)
    r = a.record
    assert r.cold_soak_hours == pytest.approx(1.0)
    assert r.hours_above_cht_caution == pytest.approx(1.0)
    assert r.hours_above_critical_altitude == pytest.approx(1.0)
    assert r.salt_exposure_hours == pytest.approx(1.0)
    f = a.acceleration_factors()
    assert f["air_filter"] == pytest.approx(40.0)          # 40x dust -> 40x filter loading
    assert 1.0 < f["cylinder_bore"] < f["air_filter"]      # bore wear saturates
    assert f["cylinder_head"] == pytest.approx(3.5)
    assert f["turbocharger"] == pytest.approx(1.6)
    assert f["fuel_system"] == pytest.approx(2.2)
    assert f["corrosion"] == pytest.approx(1.8)
    assert f["overall"] == pytest.approx(2.71, abs=0.02)
    assert a.summary()["severity"] == "SEVERE"
    assert "S2" in a.summary()["interpretation"]


def test_exposure_start_stop_transitions():
    a = ExposureAccumulator()
    a.update(1.0, engine_running=False)
    a.update(1.0, engine_running=True, oat_c=-5.0)          # cold start
    a.update(1.0, engine_running=False, egt_c=600.0)        # hot shutdown
    assert a.record.cold_start_cycles == 1
    assert a.record.hot_shutdown_events == 1
    assert a.record.total_hours == pytest.approx(1.0 / 3600)


def test_exposure_save_load_roundtrip(tmp_path):
    a = ExposureAccumulator("SN9")
    a.update(3600.0, dust_mg_m3=1.0, oat_c=-25.0)
    p = a.save(tmp_path / "x" / "exp.json")
    b = ExposureAccumulator.load(p)
    assert b.record == a.record and b.record.engine_serial == "SN9"
    assert isinstance(ExposureRecord().as_dict(), dict)


@pytest.mark.xfail(reason="BUG (B0.9): brownout_events increments on every tick with "
                          "dust >= 30 mg/m3, so one continuous brownout of N samples "
                          "counts as N events; the field is documented as 'events'.",
                   strict=True)
def test_exposure_one_continuous_brownout_is_one_event():
    a = ExposureAccumulator()
    for _ in range(10):
        a.update(1.0, dust_mg_m3=40.0)
    assert a.record.brownout_events == 1


# ---- edge compressor ------------------------------------------------------

def test_edge_frame_pack_layout_and_size():
    f = EdgeFeatureFrame(t_sec=1.0, order_05=0.1, order_1=0.2, order_2=0.6, order_4=0.1,
                         crest_factor=3.0, kurtosis=3.0,
                         per_cylinder_ratio=[1.0, 1.0, 0.4, 1.0],
                         misfire_cylinder=3, misfire_rate=0.6, verdict_code=2)
    blob = f.pack()
    assert len(blob) == 4 + 6 * 2 + 1 + 4 * 2 + 1 + 2 + 1 == f.size_bytes == 29
    t, o05, o1, o2, *_ = struct.unpack("<f6e", blob[:16])
    assert t == 1.0 and o2 == pytest.approx(0.6, abs=1e-3)
    assert f.verdict == "MISFIRING"
    assert f.as_dict()["misfire_cylinder"] == 3
    assert EdgeFeatureFrame(0, 0, 0, 0, 0, 0, 0).as_dict()["misfire_cylinder"] is None


def test_edge_compressor_build_publish_and_bandwidth():
    class Rep:
        contribution_ratio = {2: 1.0, 1: 0.9, 3: 0.4, 4: 1.0}
        cylinder = 3
        misfire_rate = 0.6
        verdict = "MISFIRING"

    ec = EdgeCompressor()
    fr = ec.build_frame(2.0, {"ORDER_2_FRAC": 0.5, "ORDER_0.5_FRAC": 0.2}, Rep())
    assert fr.per_cylinder_ratio == [0.9, 1.0, 0.4, 1.0]     # sorted by cylinder
    assert fr.misfire_cylinder == 3 and fr.verdict_code == 2
    assert len(ec.publish(fr)) == fr.size_bytes
    assert ec.published_kbit_s == pytest.approx(fr.size_bytes * 8 / 1000)
    bw = ec.bandwidth_report()                              # no frame given: 40-byte frame assumed
    assert bw["raw_kbit_s"] == 160.0
    assert bw["link_available_for_engine_kbit_s"] == 22.0
    assert bw["raw_fits_in_link"] is False and bw["compressed_fits_in_link"] is True
    assert bw["raw_over_budget_by_x"] == pytest.approx(7.3)
    bare = ec.build_frame(0.0, {})
    assert bare.verdict == "NOMINAL" and bare.size_bytes == 21
    assert ec.bandwidth_report(bare)["compression_ratio"] == pytest.approx(952.4)


def test_link_power_latency_budgets():
    assert LinkBudget().available_for_engine_kbit_s == 22.0
    assert LinkBudget(total_kbit_s=10).available_for_engine_kbit_s == 0.0
    pc = PowerBudget().endurance_cost()
    assert pc["total_w"] == 9.5 and pc["energy_per_sortie_wh"] == 171.0
    assert pc["endurance_penalty_min"] == pytest.approx(0.62)
    lb = LatencyBudget(deadline_ms=1e6)
    out, dt = lb.time_call(lambda: 42)
    assert out == 42 and dt >= 0
    rep = lb.report()
    assert rep["samples"] == 1 and rep["deadline_met"] is True
    assert LatencyBudget().report() == {"samples": 0}
