"""T-PRG-5 (M4-07): the RUL pipeline on NASA C-MAPSS FD001 produces RMSE and conformal coverage, labelled as a
turbofan PUBLIC_PROXY benchmark (units split into disjoint train / calibration / test sets)."""
from backend.evaluation.cmapss import DATA, evaluate


def test_cmapss_fd001_rmse_and_coverage_are_reported():
    assert DATA.exists()
    res = evaluate(seeds=(0,))
    assert res["evidence_class"] == "PUBLIC_PROXY" and "not a piston engine" in res["note"]
    run = res["runs"][0]
    assert run["rmse_all"] < 25.0                          # published FD001 methods report roughly 12-20 cycles
    assert 0.85 <= run["coverage"] <= 1.0                  # 95 % target, measured on disjoint units
