"""Remaining useful life in service (card M4-03, idea text I-08, D18).

Uses the conformal RUL model trained on the simulated run-to-failure fleet of this engine type
(backend/evaluation/sim_rul.py -> var/models/rul_<engine>.pkl). In service it builds the SAME features from what the
twin sees: the mean residual z-vector over the last sample window and the engine's operating hours, and returns the
point estimate with its 95 % conformal interval. Mission planning uses the LOWER bound. Without a trained model the
service reports UNAVAILABLE with the command that trains it - it never invents a number.
"""
from __future__ import annotations

import pickle
from typing import Any, Dict, List, Optional

import numpy as np

S_PER_H = 3600.0


class RULService:
    def __init__(self, engine_id: str, path: Optional[Any] = None) -> None:
        from backend.runtime.paths import var_path          # lazy: backend.runtime imports this module
        self.engine_id = engine_id
        self.path = path or var_path("models") / f"rul_{engine_id}.pkl"
        self.bundle: Optional[Dict[str, Any]] = None
        if self.path.exists():
            with self.path.open("rb") as fh:
                self.bundle = pickle.load(fh)
        self.window: List[np.ndarray] = []
        self.hours = 0.0
        self.last_t: Optional[float] = None
        self.latest: Dict[str, Any] = self._unavailable()

    def _unavailable(self) -> Dict[str, Any]:
        return {"status": "UNAVAILABLE",
                "reason": f"no trained RUL model for {self.engine_id}: run python -m backend.evaluation.sim_rul "
                          f"{self.engine_id} 200"}

    @property
    def available(self) -> bool:
        return self.bundle is not None

    def update(self, t: float, z_raw: Optional[np.ndarray], running: bool) -> None:
        if self.last_t is not None and t > self.last_t and running:
            self.hours += (t - self.last_t) / S_PER_H
        self.last_t = t
        if not self.available or z_raw is None:
            return
        self.window.append(np.asarray(z_raw, dtype=float))
        if len(self.window) >= self.bundle["sample_every"]:
            x = np.r_[np.nan_to_num(np.mean(self.window, axis=0)), self.hours][None, :]
            self.window = []
            m = self.bundle["model"]
            if x.shape[1] != m.model.n_features_in_:
                self.latest = {"status": "UNAVAILABLE", "reason": "trained on a different channel set: retrain"}
                return
            r = m.predict(x)
            self.latest = {"status": "OK", "rul_h": round(float(r.point[0]), 1), "rul_lower_h": round(float(r.lower[0]), 1),
                           "rul_upper_h": round(float(r.upper[0]), 1), "coverage_target": round(1 - m.alpha, 3),
                           "engine_hours": round(self.hours, 3), "method": "gradient boosting + split conformal",
                           "trained_on": f"{self.bundle['trajectories']} simulated run-to-failure tails "
                                         f"({self.bundle['trained']})", "evidence_class": self.bundle["evidence_class"]}
