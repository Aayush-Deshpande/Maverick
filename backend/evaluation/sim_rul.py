"""Simulated run-to-failure fleet and the RUL pipeline on it (cards M4-01 fleet / M4-03, idea text I-08, D18).
Evidence class: SIMULATION.

Fleet: each trajectory is one tail (seed) with its own build spread, sensor noise and wear-rate multipliers
(backend/sim/wear.py). It flies a cruise point; every plant second stands for HOURS_PER_STEP flight hours of wear
(wear is slow, so the thermal state follows quasi-statically). End of life = the first wear process reaching
severity 1. The tail's own residual detector is calibrated at the start (healthy), exactly as in service.

Features at each sample (every SAMPLE_EVERY plant seconds): the mean residual z-vector of the tail over the last
window (what the twin can see) and the flight hours so far. Label: flight hours to end of life (the plant knows it;
labels are training data, never runtime inputs). RUL model: backend/prognose/rul_model.ConformalRUL, split by
TRAJECTORY into train / calibration / test (disjoint seeds, D17), 95 % target (D18). Coverage is measured on the
test trajectories and reported.
Run: python -m backend.evaluation.sim_rul [engine_id] [n_trajectories]
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from backend.evaluation.tail import calibrated
from backend.prognose.rul_model import ConformalRUL, split_groups
from backend.sim.wear import WearModel

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "evaluation"
HOURS_PER_STEP = 2.0
SAMPLE_EVERY = 20
MAX_STEPS = 4000
CRUISE = (70.0, 8000.0, 10.0)
FIRST_SEED = 5000                        # fleet seeds: 5000.. (disjoint from signature 11/12 and test 1001/1002)


def trajectory(engine_id: str, seed: int) -> Tuple[np.ndarray, np.ndarray]:
    src, det = calibrated(engine_id, seed)
    wear = WearModel(src, seed)
    feats, hours, window = [], [], []
    fail_h = None
    for step in range(MAX_STEPS):
        f, _ = src.step(1.0, *CRUISE)
        wear.advance(HOURS_PER_STEP * 3600.0)
        window.append(det.score(f).z_raw)
        h = (step + 1) * HOURS_PER_STEP
        if (step + 1) % SAMPLE_EVERY == 0:
            feats.append(np.r_[np.mean(window, axis=0), h])
            hours.append(h)
            window = []
        if max(wear.state().values(), default=0.0) >= 1.0:
            fail_h = h
            break
    if fail_h is None:                                  # did not wear out within MAX_STEPS: right-censored, dropped
        return np.empty((0, 0)), np.empty(0)
    return np.array(feats), fail_h - np.array(hours)


def fleet(engine_id: str, n: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    X, y, g = [], [], []
    for k in range(n):
        seed = FIRST_SEED + k
        Xi, yi = trajectory(engine_id, seed)
        if len(yi):
            X.append(Xi)
            y.append(yi)
            g.append(np.full(len(yi), seed))
    return np.vstack(X), np.concatenate(y), np.concatenate(g)


def evaluate(engine_id: str, n: int, alpha: float = 0.05, seeds=(0, 1, 2)) -> Dict:
    return evaluate_arrays(engine_id, *fleet(engine_id, n), alpha=alpha, seeds=seeds)


def evaluate_arrays(engine_id: str, X: np.ndarray, y: np.ndarray, g: np.ndarray, alpha: float = 0.05,
                    seeds=(0, 1, 2)) -> Dict:
    runs = []
    for s in seeds:
        tr, ca, te = split_groups(g, seed=s)
        m = ConformalRUL(alpha=alpha).fit(X[np.isin(g, list(tr))], y[np.isin(g, list(tr))])
        m.calibrate(X[np.isin(g, list(ca))], y[np.isin(g, list(ca))])
        sel = np.isin(g, list(te))
        r = m.predict(X[sel])
        yt = y[sel]
        runs.append({"split": s, "test_trajectories": int(len(np.unique(g[sel]))),
                     "rmse_h": float(np.sqrt(np.mean((r.point - yt) ** 2))),
                     "coverage": float(np.mean((yt >= r.lower) & (yt <= r.upper))),
                     "mean_width_h": float(np.mean(r.upper - r.lower))})
    return {"engine_id": engine_id, "evidence_class": "SIMULATION", "trajectories": int(len(np.unique(g))),
            "samples": int(len(y)), "target_coverage": 1 - alpha, "hours_per_step": HOURS_PER_STEP,
            "mean_life_h": float(np.mean([y[g == k].max() for k in np.unique(g)])), "runs": runs,
            "mean": {k: float(np.mean([r[k] for r in runs])) for k in ("rmse_h", "coverage", "mean_width_h")}}


def train_and_save(engine_id: str, X: np.ndarray, y: np.ndarray, g: np.ndarray, alpha: float = 0.05) -> Path:
    """Final service model: fit on 80 % of the trajectories, conformal-calibrate on the other 20 % (by trajectory),
    saved to var/models/rul_<engine>.pkl (local runtime artefact, never committed)."""
    import pickle
    from backend.runtime.paths import var_path
    ids = np.array(sorted(set(g)))
    rng = np.random.default_rng(0)
    rng.shuffle(ids)
    cal = set(ids[: max(1, len(ids) // 5)])
    m = ConformalRUL(alpha=alpha).fit(X[~np.isin(g, list(cal))], y[~np.isin(g, list(cal))])
    m.calibrate(X[np.isin(g, list(cal))], y[np.isin(g, list(cal))])
    path = var_path("models") / f"rul_{engine_id}.pkl"
    with path.open("wb") as fh:
        pickle.dump({"model": m, "sample_every": SAMPLE_EVERY, "hours_per_step": HOURS_PER_STEP,
                     "trajectories": int(len(ids)), "trained": _dt.date.today().isoformat(),
                     "evidence_class": "SIMULATION"}, fh)
    return path


def main(engine_id: str, n: int) -> None:
    X, y, g = fleet(engine_id, n)
    train_and_save(engine_id, X, y, g)
    res = evaluate_arrays(engine_id, X, y, g)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"sim_rul_{engine_id}_{_dt.date.today().isoformat()}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("engine_id", "trajectories", "mean_life_h", "mean")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "rotax_912is", int(sys.argv[2]) if len(sys.argv) > 2 else 200)
