"""Tests for FOUNDATION Stack (W8, W10, INN-06, D35).

Verifies:
1. Maintenance log text classification across ATA chapters (ATA 72, 73, 75, 79, 81).
2. Probabilistic time-series forecasting and threshold crossing prediction.
3. In-context tabular classification, uncertainty, and research-only licensing labeling.
"""

from __future__ import annotations

import numpy as np
import pytest

from backend.foundation.text_classifier import MaintenanceTextClassifier
from backend.foundation.forecast_chronos import TimeSeriesForecaster
from backend.foundation.tabpfn_wrapper import InContextTabularClassifier


def test_maintenance_text_classifier():
    clf = MaintenanceTextClassifier()

    # 1. ATA 75 Cooling PIREP
    res_cool = clf.classify_log("Pilot observed high CHT and cylinder head temperature overheat during climb.")
    assert res_cool.primary_ata == "ATA 75"
    assert res_cool.urgency in ("SAFETY_CRITICAL", "AOG_GROUNDING")
    assert len(res_cool.suggested_inspections) > 0

    # 2. ATA 73 Fuel & Injection PIREP
    res_fuel = clf.classify_log("Suspect fuel rail pressure drop and cylinder 2 injector coking.")
    assert res_fuel.primary_ata == "ATA 73"
    assert "injector" in res_fuel.matched_keywords or "fuel rail" in res_fuel.matched_keywords

    # 3. ATA 79 Oil System PIREP
    res_oil = clf.classify_log("Sudden oil pressure drop and high oil temp warning on descent.")
    assert res_oil.primary_ata == "ATA 79"

    # 4. ATA 81 Turbo PIREP
    res_turbo = clf.classify_log("Low boost and manifold pressure loss at high altitude, turbo wastegate suspect.")
    assert res_turbo.primary_ata == "ATA 81"


def test_time_series_forecaster():
    forecaster = TimeSeriesForecaster()

    # Linear degradation trend: oil pressure dropping from 4.5 down to 1.0 bar
    history = [4.5 - 0.05 * i for i in range(30)]  # 30 steps: ends at 3.05 bar
    res = forecaster.forecast_trajectory(
        channel_name="oil_p",
        history_values=history,
        horizon_steps=40,
        critical_threshold=1.5,
    )

    assert res.channel == "oil_p"
    assert len(res.p50) == 40
    # Monotonicity check
    for p10, p50, p90 in zip(res.p10, res.p50, res.p90):
        assert p10 <= p50 <= p90

    # Verify predicted threshold crossing is found
    assert res.predicted_threshold_crossing_step is not None
    assert 20 <= res.predicted_threshold_crossing_step <= 35


def test_in_context_tabular_classifier():
    clf = InContextTabularClassifier(mode="RESEARCH_ONLY")

    # 3 classes: NOMINAL, MISFIRE, OVERHEAT in 2D space
    train_x = np.array([
        [0.0, 0.0], [0.1, 0.1], [-0.1, 0.0],      # NOMINAL
        [3.0, 0.0], [3.1, 0.2], [2.9, -0.1],      # MISFIRE
        [0.0, 3.0], [0.1, 3.1], [-0.1, 2.9],      # OVERHEAT
    ])
    train_y = ["NOMINAL", "NOMINAL", "NOMINAL", "MISFIRE", "MISFIRE", "MISFIRE", "OVERHEAT", "OVERHEAT", "OVERHEAT"]

    clf.set_context(train_x, train_y)

    query_x = np.array([
        [0.05, 0.05],   # should be NOMINAL
        [3.05, 0.05],   # should be MISFIRE
        [0.05, 3.05],   # should be OVERHEAT
    ])

    preds = clf.predict(query_x)
    assert len(preds) == 3
    assert preds[0].predicted_class == "NOMINAL"
    assert preds[1].predicted_class == "MISFIRE"
    assert preds[2].predicted_class == "OVERHEAT"
    assert preds[0].evidence_class == "RESEARCH_ONLY"

    for p in preds:
        prob_sum = sum(p.probabilities.values())
        assert pytest.approx(prob_sum, rel=1e-2) == 1.0
