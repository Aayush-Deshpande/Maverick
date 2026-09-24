"""
Per-tail calibration ("twin-lite") -- backlog W1, decision D31.

Engine universality lives here, not in the detector: for one *tail* (one physical engine) we
regress every measured channel on the commanded operating point using NOMINAL frames only, and
score everything afterwards as a z-scored residual.  Different engines, altitudes and build
variation then land on the same dimensionless scale, so one detector serves every engine
(experiment E17: universal 0.974 AUROC vs per-engine 0.976 vs new-engine 0.973).

Contract: consumes canonical ``Frame`` objects only (no ground truth is reachable -- see
tests/test_no_truth_leak.py).  Cylinder-count agnostic: per-cylinder blocks are summarised by
mean/max/min/std, so 4- and 6-cylinder engines yield the same 13-feature vector.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import numpy as np

from backend.core.frame import Frame

CALIBRATION_SCHEMA = "tail_calibration/1"
SCALAR_CHANNELS = ("oil_p", "oil_t", "fuel_flow", "map_kpa", "rpm")
Z_CLIP = 10.0


def _design(throttle: np.ndarray, alt: np.ndarray, oat: np.ndarray) -> np.ndarray:
    t, a, o = throttle / 100.0, alt / 1.0e4, oat / 50.0
    return np.column_stack([t, a, o, t * t, a * a, t * a, o * t])


def _command(frame: Frame) -> tuple[float, float, float]:
    if frame.throttle is None or frame.alt is None or frame.oat is None:
        raise ValueError("Frame needs throttle, alt and oat to be calibrated against the operating point")
    return float(frame.throttle), float(frame.alt), float(frame.oat)


def _measure(frame: Frame, n_cyl: int, scalars: Sequence[str]) -> np.ndarray:
    if len(frame.cht) != n_cyl or len(frame.egt) != n_cyl:
        raise ValueError(f"expected {n_cyl} CHT/EGT channels, got {len(frame.cht)}/{len(frame.egt)}")
    vals = list(frame.cht) + list(frame.egt)
    for name in scalars:
        v = getattr(frame, name)
        if v is None:
            raise ValueError(f"Frame is missing calibrated channel {name!r}")
        vals.append(float(v))
    return np.asarray(vals, dtype=float)


class TailCalibration:
    """Nominal-only operating-point regression + residual scale for one tail."""

    def __init__(self, engine_config_id: str, tail_id: str, n_cyl: int,
                 scalars: Sequence[str], coef: np.ndarray, intercept: np.ndarray, sigma: np.ndarray,
                 n_frames: int) -> None:
        self.engine_config_id = engine_config_id
        self.tail_id = tail_id
        self.n_cyl = n_cyl
        self.scalars = tuple(scalars)
        self.coef = coef            # (n_design, n_channels)
        self.intercept = intercept  # (n_channels,)
        self.sigma = sigma          # (n_channels,)
        self.n_frames = n_frames

    # ---- fit -----------------------------------------------------------------------------
    @classmethod
    def fit(cls, frames: Iterable[Frame], alpha: float = 1e-3) -> "TailCalibration":
        frames = list(frames)
        if len(frames) < 50:
            raise ValueError(f"need >= 50 nominal frames to calibrate, got {len(frames)}")
        f0 = frames[0]
        n_cyl = len(f0.cht)
        scalars = tuple(s for s in SCALAR_CHANNELS if getattr(f0, s) is not None)
        X = _design(*[np.array(c) for c in zip(*[_command(f) for f in frames])])
        Y = np.vstack([_measure(f, n_cyl, scalars) for f in frames])
        Xm = X.mean(0)
        Yc = Y - Y.mean(0)
        Xc = X - Xm
        A = Xc.T @ Xc + alpha * len(frames) * np.eye(X.shape[1])
        coef = np.linalg.solve(A, Xc.T @ Yc)
        intercept = Y.mean(0) - Xm @ coef
        res = Y - (X @ coef + intercept)
        sigma = np.maximum(res.std(0), 1e-3 * np.maximum(np.abs(Y.mean(0)), 1.0))
        return cls(f0.engine_config_id, f0.tail_id, n_cyl, scalars, coef, intercept, sigma, len(frames))

    # ---- apply ---------------------------------------------------------------------------
    def z(self, frame: Frame) -> np.ndarray:
        """Per-channel z-scored residual, order: cht[0..n), egt[0..n), *scalars."""
        thr, alt, oat = _command(frame)
        pred = _design(np.array([thr]), np.array([alt]), np.array([oat]))[0] @ self.coef + self.intercept
        z = (_measure(frame, self.n_cyl, self.scalars) - pred) / self.sigma
        return np.clip(z, -Z_CLIP, Z_CLIP)

    def channel_names(self) -> List[str]:
        n = self.n_cyl
        return [f"cht_{i + 1}" for i in range(n)] + [f"egt_{i + 1}" for i in range(n)] + list(self.scalars)

    def features(self, z: np.ndarray) -> np.ndarray:
        """n_cyl-agnostic feature vector: [mean,max,min,std]x(CHT,EGT) + scalar z."""
        n = self.n_cyl
        f: List[float] = []
        for blk in (z[:n], z[n:2 * n]):
            f += [blk.mean(), blk.max(), blk.min(), blk.std()]
        f += list(z[2 * n:])
        return np.asarray(f, dtype=float)

    def feature_names(self) -> List[str]:
        names = []
        for grp in ("cht", "egt"):
            names += [f"{grp}_{s}" for s in ("mean", "max", "min", "std")]
        return names + list(self.scalars)

    # ---- persistence (sidecar) -----------------------------------------------------------
    def to_dict(self) -> Dict:
        return {
            "schema": CALIBRATION_SCHEMA, "engine_config_id": self.engine_config_id, "tail_id": self.tail_id,
            "n_cyl": self.n_cyl, "scalars": list(self.scalars), "n_frames": self.n_frames,
            "coef": self.coef.tolist(), "intercept": self.intercept.tolist(), "sigma": self.sigma.tolist(),
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "TailCalibration":
        if d.get("schema") != CALIBRATION_SCHEMA:
            raise ValueError(f"unsupported calibration schema {d.get('schema')!r}")
        return cls(d["engine_config_id"], d["tail_id"], int(d["n_cyl"]), d["scalars"],
                   np.array(d["coef"]), np.array(d["intercept"]), np.array(d["sigma"]), int(d["n_frames"]))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict()), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "TailCalibration":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
