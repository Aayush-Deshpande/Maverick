"""Tests for DIAG Stack (B5.3, B5.4, B5.5, B6.1, B6.3): BN diagnosis, active test selection, XAI, RUL, ISA-18.2."""

import pytest
from backend.alarms.rationalisation import AlarmPriority, AlarmState, ISA18AlarmManager
from backend.diagnose.active import ActiveDiagnosticPlanner, TestRequest
from backend.diagnose.bn import DiagnosticBayesianNetwork, Evidence, Hypothesis
from backend.diagnose.explain import ExplanationGenerator
from backend.physics.engine_config import load_engine_config
from backend.prognose.rul import DualPathRULEstimator


def test_bayesian_network_diagnosis():
    cfg = load_engine_config("rotax_914")
    bn = DiagnosticBayesianNetwork(cfg)

    evidence = [
        Evidence(detector="RESIDUAL", target="cht", statistic=12.0, threshold=3.0, location="cyl1"),
        Evidence(detector="PARAM_CHANGE", target="coolant_t", statistic=7.5, threshold=2.0),
    ]
    hyps = bn.diagnose(evidence)
    assert len(hyps) > 0
    top = hyps[0]
    assert top.mode_id == "COOLING_DEGRADATION"
    assert top.location == "cyl1"
    assert top.probability > 0.5


def test_active_diagnostic_planner():
    planner = ActiveDiagnosticPlanner()
    hyps = [
        Hypothesis(mode_id="INJECTOR_COKING_IDID", location="cyl2", probability=0.55, ambiguity_group_id="AG_INJECTOR"),
        Hypothesis(mode_id="INJECTOR_NEEDLE_STICK", location="cyl2", probability=0.45, ambiguity_group_id="AG_INJECTOR"),
    ]
    test_req = planner.evaluate_tests(hyps, current_flight_phase="CRUISE")
    assert test_req is not None
    assert test_req.test_id in ("CUT_OUT", "RAIL_STEP")
    assert test_req.target == "cyl2"
    assert test_req.requires_approval is True
    assert test_req.expected_info_gain_bits > 0.5


def test_explanation_generator():
    explainer = ExplanationGenerator()
    hyp = Hypothesis(mode_id="OIL_PRESSURE_LOSS", location=None, probability=0.88, ambiguity_group_id="AG_OIL")
    bundle = explainer.explain(hyp, {})

    assert "Oil" in bundle.operator_text
    assert "OIL_PRESSURE_LOSS" in bundle.engineer_text
    assert "ATA 79" in bundle.ata_chapter
    assert bundle.faithfulness_score == 1.0


def test_dual_path_rul_and_disagreement():
    rul_est = DualPathRULEstimator(tbo_hours=1200.0, alpha=0.10)

    # 1. Consistent paths
    history_consistent = [(float(t), 1.0 - 0.001 * t) for t in range(20)]
    res1 = rul_est.estimate_rul(
        component="Cylinder_Head",
        location="cyl3",
        current_flight_hours=200.0,
        current_damage_0_1=0.20,
        damage_rate_per_hour=0.001,
        parameter_history=history_consistent,
        param_failure_limit=0.20,
    )
    assert res1.rul_hours_lower <= res1.rul_hours_median <= res1.rul_hours_upper
    assert res1.disagreement_alarm is False

    # 2. Diverging paths (PoF says rate=0.005 -> 160h, but data trend says rate=0.0001 -> 3500h)
    history_diverging = [(float(t), 1.0 - 0.0001 * t) for t in range(20)]
    res2 = rul_est.estimate_rul(
        component="Cylinder_Head",
        location="cyl3",
        current_flight_hours=200.0,
        current_damage_0_1=0.20,
        damage_rate_per_hour=0.005,
        parameter_history=history_diverging,
    )
    assert res2.disagreement_alarm is True


def test_isa18_alarm_management_and_shelving():
    mgr = ISA18AlarmManager(flood_limit_per_min=3)

    # Trigger 1
    a1 = mgr.trigger_alarm("ALARM_CHT_OVERHEAT", t=10.0)
    assert a1 is not None and a1.state == AlarmState.ACTIVE_UNACK
    assert a1.priority == AlarmPriority.HIGH

    # Acknowledge
    mgr.acknowledge("ALARM_CHT_OVERHEAT")
    assert mgr.active_alarms["ALARM_CHT_OVERHEAT"].state == AlarmState.ACTIVE_ACK

    # Shelve for 60 seconds
    mgr.shelve("ALARM_CHT_OVERHEAT", duration_sec=60.0, t=15.0)
    assert mgr.active_alarms["ALARM_CHT_OVERHEAT"].state == AlarmState.SHELVED

    # Trigger while shelved is suppressed
    assert mgr.trigger_alarm("ALARM_CHT_OVERHEAT", t=30.0) is None

    # Flood suppression (triggering > 3 unique alarms in 1 minute)
    a2 = mgr.trigger_alarm("ALARM_1", t=20.0)
    a3 = mgr.trigger_alarm("ALARM_2", t=21.0)
    a4 = mgr.trigger_alarm("ALARM_3", t=22.0)  # should be suppressed by flood limit
    assert a2 is not None and a3 is not None
    assert a4 is None
