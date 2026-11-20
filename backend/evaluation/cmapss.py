"""NASA C-MAPSS FD001 benchmark for the RUL pipeline (card M4-07, deliverable 6, P Step 4.7, T-PRG-5).

EVIDENCE CLASS: PUBLIC_PROXY. C-MAPSS is a simulated TURBOFAN dataset (NASA Prognostics Center of Excellence,
Saxena et al. 2008). It validates the RUL METHOD (features, gradient boosting, split conformal by unit); it is not a
piston engine and these numbers are not piston-engine performance.

Data: data/telemetry/source2_nasa_benchmarks/train_FD001.txt (100 run-to-failure units; columns: unit, cycle, 3
operating settings, 21 sensors). Only the training file is in the repository, so the units are split into disjoint
train / calibration / test units (seeded). Target: RUL capped at RUL_CAP cycles (piecewise-linear degradation, the
usual FD001 convention). Features per cycle: each informative sensor's rolling mean and slope over WINDOW cycles, and
the cycle count. Reported: RMSE on all test cycles, RMSE on the last cycle of each test unit, interval coverage
(target 1 - alpha) and mean interval width.
Run: python -m backend.evaluation.cmapss
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Dict

import numpy as np

from backend.prognose.rul_model import ConformalRUL, split_groups

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "telemetry" / "source2_nasa_benchmarks" / "train_FD001.txt"
OUT = ROOT / "reports" / "evaluation"
RUL_CAP = 125
WINDOW = 15
MIN_STD = 1e-6
SEEDS = (0, 1, 2)


def load(path: Path = DATA) -> np.ndarray:
    return np.loadtxt(path)


def features(raw: np.ndarray):
    units, cycles, sensors = raw[:, 0].astype(int), raw[:, 1], raw[:, 5:]
    keep = sensors.std(0) > MIN_STD                       # constant sensors carry nothing
    S = sensors[:, keep]
    X, y, g = [], [], []
    for u in np.unique(units):
        sel = units == u
        s, c = S[sel], cycles[sel]
        life = c.max()
        for i in range(len(s)):
            lo = max(0, i - WINDOW + 1)
            w = s[lo:i + 1]
            t = np.arange(len(w))
            slope = np.polyfit(t, w, 1)[0] if len(w) > 2 else np.zeros(w.shape[1])
            X.append(np.r_[w.mean(0), slope, c[i]])
            y.append(min(life - c[i], RUL_CAP))
            g.append(u)
    return np.array(X), np.array(y, dtype=float), np.array(g)


def evaluate(alpha: float = 0.05, seeds=SEEDS) -> Dict:
    X, y, g = features(load())
    runs = []
    for seed in seeds:
        tr, ca, te = split_groups(g, seed=seed)
        m = ConformalRUL(alpha=alpha).fit(X[np.isin(g, list(tr))], y[np.isin(g, list(tr))])
        m.calibrate(X[np.isin(g, list(ca))], y[np.isin(g, list(ca))])
        sel = np.isin(g, list(te))
        r = m.predict(X[sel])
        yt, gt = y[sel], g[sel]
        last = np.array([np.where(gt == u)[0].max() for u in np.unique(gt)])
        runs.append({"seed": seed, "test_units": int(len(np.unique(gt))),
                     "rmse_all": float(np.sqrt(np.mean((r.point - yt) ** 2))),
                     "rmse_last_cycle": float(np.sqrt(np.mean((r.point[last] - yt[last]) ** 2))),
                     "coverage": float(np.mean((yt >= r.lower) & (yt <= r.upper))),
                     "mean_width": float(np.mean(r.upper - r.lower))})
    return {"dataset": "NASA C-MAPSS FD001 (train file, units split by seed)", "evidence_class": "PUBLIC_PROXY",
            "note": "turbofan benchmark used to validate the RUL method; not a piston engine",
            "target_coverage": 1 - alpha, "rul_cap": RUL_CAP, "window": WINDOW, "runs": runs,
            "mean": {k: float(np.mean([r[k] for r in runs])) for k in ("rmse_all", "rmse_last_cycle", "coverage", "mean_width")}}


def main() -> None:
    res = evaluate()
    OUT.mkdir(parents=True, exist_ok=True)
    day = _dt.date.today().isoformat()
    (OUT / f"cmapss_fd001_{day}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res["mean"], indent=1))


if __name__ == "__main__":
    main()
