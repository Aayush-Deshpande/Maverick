"""M4-01/M4-03 smoke: a small simulated run-to-failure fleet (disjoint fleet seeds) trains the conformal RUL model,
which reports RMSE and coverage on held-out trajectories. The full 200-trajectory run is
python -m backend.evaluation.sim_rul <engine> 200 (reports/evaluation/sim_rul_*.json)."""
from backend.evaluation.sim_rul import evaluate, trajectory


def test_trajectory_wears_out_with_decreasing_rul():
    X, y = trajectory("rotax_912is", 5001)
    assert len(y) > 3 and all(a > b for a, b in zip(y, y[1:])) and y[-1] >= 0


def test_small_fleet_reports_rmse_and_coverage():
    res = evaluate("rotax_912is", 10, seeds=(0,))
    run = res["runs"][0]
    assert res["evidence_class"] == "SIMULATION" and res["trajectories"] >= 8
    assert run["rmse_h"] < res["mean_life_h"] and 0.0 <= run["coverage"] <= 1.0
