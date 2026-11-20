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

Model-informed (M3-04/M3-08): every channel is first predicted by the NOMINAL engine model from measured inputs
(backend/detect/reference.py: air path, fuel, ECU/TCU schedules, thermal network integrated in time, oil pump law,
propeller-balance rpm); the tail regression then learns only the small per-tail offset of measured minus predicted
on the smooth command polynomial, four model regressors and, per channel, the reference's own prediction (for
temperatures its rise above OAT), so a multiplicative build spread of that channel is linear too. A quadratic in the commands alone could not follow the
throttle-body, altitude, schedule and thermal-lag behaviour, and that misfit was the main source of nominal false
alarms on a varied-lever flight (PROGRESS M3-04). The reference is stateful: score frames in time order.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import numpy as np

from backend.core.frame import Frame, Q_SHIELDED
from backend.detect.reference import ModelReference

CALIBRATION_SCHEMA = "tail_calibration/2"
# scalar channels scored when the engine has them (frame value not None): the model predicts the first ones; bus
# voltage, fuel pressure and common-rail pressure have no model term yet and are learned per tail by the regression
# alone (rail_p: the FADEC's own pressure sensor on the CI engines; without it F09 rail decay was invisible)
SCALAR_CHANNELS = ("oil_p", "oil_t", "fuel_flow", "map_kpa", "rpm", "coolant_t", "gearbox_t", "bus_v", "fuel_p",
                   "rail_p", "batt_i", "vib_1X", "vib_prop_1X", "vib_gear_mesh", "vib_firing", "vib_turbo", "vib_knock")
VIB_PREFIX = "vib_"                              # vib_<order>: an order amplitude from Frame.vibration_orders


def _value(frame: Frame, name: str):
    """A scored channel's measured value (vibration orders live in a dict; None = not measured)."""
    if name.startswith(VIB_PREFIX):
        return (frame.vibration_orders or {}).get(name[len(VIB_PREFIX):])
    return getattr(frame, name)
FEATURE_SCALARS = SCALAR_CHANNELS[:5]            # detector feature vector (fixed 13 features, learned scorers)
Z_CLIP = 10.0
INPUT_CHANNELS = ("rpm", "oil_t")                # measured channels the nominal reference uses as inputs
MAD_TO_SIGMA = 1.4826                            # Gaussian consistency factor of the median absolute deviation
OUTLIER_SIGMA = 6.0                              # calibration rows beyond this are limiter events, not the nominal law




def _design(throttle: np.ndarray, alt: np.ndarray, oat: np.ndarray, reg: np.ndarray) -> np.ndarray:
    """Smooth command polynomial + the reference's regressors (brake power and balance rpm, both normalised)."""
    t, a, o = throttle / 100.0, alt / 1.0e4, oat / 50.0
    r = np.asarray(reg, dtype=float).reshape(len(t), ModelReference.N_REGRESSORS)
    return np.column_stack([t, a, o, t * t, a * a, t * a, o * t, r])


def _command(frame: Frame) -> tuple[float, float, float]:
    if frame.throttle is None or frame.alt is None or frame.oat is None:
        raise ValueError("Frame needs throttle, alt and oat to be calibrated against the operating point")
    return float(frame.throttle), float(frame.alt), float(frame.oat)


def _measure(frame: Frame, n_cyl: int, scalars: Sequence[str], strict: bool = True) -> np.ndarray:
    """Calibration (strict) needs every channel. Scoring accepts a missing reading (dropout) as NaN: it is
    unmeasured, so it contributes no evidence (z = 0), and is never replaced by a made-up number."""
    if len(frame.cht) != n_cyl or len(frame.egt) != n_cyl:
        raise ValueError(f"expected {n_cyl} CHT/EGT channels, got {len(frame.cht)}/{len(frame.egt)}")
    vals = list(frame.cht) + list(frame.egt) + [_value(frame, name) for name in scalars]
    if strict:
        missing = [n for n, v in zip(["cht"] * n_cyl + ["egt"] * n_cyl + list(scalars), vals) if v is None]
        if missing:
            raise ValueError(f"Frame is missing calibrated channel {missing[0]!r}")
    return np.asarray([np.nan if v is None else float(v) for v in vals], dtype=float)


TEMPERATURE_PREFIXES = ("cht", "egt", "oil_t", "coolant_t", "gearbox_t")
FRICTION_PROBES = (0.9, 1.0, 1.1)                # friction factors tried for the oil-temperature fit
FRICTION_RANGE = (0.7, 1.3)
THERMAL_SETTLE_FRAMES = 60                       # the reference starts at the measured temperatures; skip the start
OWN_SCALE = 100.0                                # brings the per-channel regressor to O(1) like the others


def _own(P: np.ndarray, oat: np.ndarray, names: Sequence[str]) -> np.ndarray:
    """Per-channel regressor: the reference prediction (temperatures: rise above OAT), scaled."""
    own = np.array(P, dtype=float, copy=True).reshape(len(oat), len(names))
    for c, name in enumerate(names):
        if name.startswith(TEMPERATURE_PREFIXES):
            own[:, c] -= oat
    return own / OWN_SCALE


def _fit_channels(X: np.ndarray, own: np.ndarray, Y: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray]:
    """One ridge fit per channel on [shared design, that channel's own regressor]. coef: (n_design + 1, n_channels)."""
    coef = np.zeros((X.shape[1] + 1, Y.shape[1]))
    intercept = np.zeros(Y.shape[1])
    for c in range(Y.shape[1]):
        k, b = _ridge(np.column_stack([X, own[:, c]]), Y[:, c:c + 1], alpha)
        coef[:, c], intercept[c] = k[:, 0], b[0]
    return coef, intercept


def _apply(X: np.ndarray, own: np.ndarray, coef: np.ndarray, intercept: np.ndarray) -> np.ndarray:
    return X @ coef[:-1] + own * coef[-1] + intercept


def _ridge(X: np.ndarray, Y: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray]:
    Xm = X.mean(0)
    Xc = X - Xm
    A = Xc.T @ Xc + alpha * len(X) * np.eye(X.shape[1])
    coef = np.linalg.solve(A, Xc.T @ (Y - Y.mean(0)))
    return coef, Y.mean(0) - Xm @ coef


def _identify_tail(engine_config_id: str, n_cyl: int, scalars: Sequence[str], frames: Sequence[Frame]) -> Dict[str, float]:
    """Tail parameters observable in nominal data.
    - Volumetric efficiency: fuel follows the air on a mixture-controlled (spark-ignition) engine, so measured /
      predicted fuel flow is this tail's air-path factor (median: robust to limiter events). A quality-governed
      diesel meters fuel by the lever, so it is not identified there.
    - Friction: friction heat goes to the oil, so the friction factor is the one that best explains the measured oil
      temperature (parabola through FRICTION_PROBES, clipped to FRICTION_RANGE). The oil thermostat hides it on cold
      days, which is why a cold-day calibration alone misses hot-day oil temperatures."""
    tail: Dict[str, float] = {}
    names = list(scalars)
    ref = ModelReference(engine_config_id, n_cyl, scalars)
    if "fuel_flow" in names and ref.core.combustion.spark_ignition:
        k = 2 * n_cyl + names.index("fuel_flow")
        ratios = []
        for f in frames:
            p, _ = ref.predict(f)
            if f.fuel_flow and np.isfinite(p[k]) and p[k] > 0:
                ratios.append(f.fuel_flow / p[k])
        if ratios:
            tail["volumetric_efficiency"] = float(np.median(ratios))
    if "oil_t" in names:
        k = 2 * n_cyl + names.index("oil_t")
        meas = np.array([np.nan if f.oil_t is None else f.oil_t for f in frames])
        errs = []
        for fr in FRICTION_PROBES:
            r = ModelReference(engine_config_id, n_cyl, scalars, {**tail, "friction": fr})
            p = np.array([r.predict(f)[0][k] for f in frames])
            d = (meas - p)[THERMAL_SETTLE_FRAMES:]
            errs.append(float(np.nanmean(d * d)))
        a, b, _c = np.polyfit(FRICTION_PROBES, errs, 2)
        best = -b / (2 * a) if a > 0 else FRICTION_PROBES[int(np.argmin(errs))]
        tail["friction"] = float(np.clip(best, *FRICTION_RANGE))
    return tail


class TailCalibration:
    """Nominal-only operating-point regression + residual scale for one tail."""

    def __init__(self, engine_config_id: str, tail_id: str, n_cyl: int,
                 scalars: Sequence[str], coef: np.ndarray, intercept: np.ndarray, sigma: np.ndarray,
                 n_frames: int, tail: Dict[str, float] | None = None) -> None:
        self.engine_config_id = engine_config_id
        self.tail_id = tail_id
        self.n_cyl = n_cyl
        self.scalars = tuple(scalars)
        self.coef = coef            # (n_design, n_channels)
        self.intercept = intercept  # (n_channels,)
        self.sigma = sigma          # (n_channels,)
        self.n_frames = n_frames
        self.tail = dict(tail or {})            # identified tail parameters applied to the reference model
        self.reference = ModelReference(engine_config_id, n_cyl, self.scalars, self.tail)

    # ---- fit -----------------------------------------------------------------------------
    @classmethod
    def fit(cls, frames: Iterable[Frame], alpha: float = 1e-3) -> "TailCalibration":
        frames = list(frames)
        if len(frames) < 50:
            raise ValueError(f"need >= 50 nominal frames to calibrate, got {len(frames)}")
        f0 = frames[0]
        n_cyl = len(f0.cht)
        scalars = tuple(s for s in SCALAR_CHANNELS if _value(f0, s) is not None)
        cmds = [_command(f) for f in frames]
        tail = _identify_tail(f0.engine_config_id, n_cyl, scalars, frames)
        ref = ModelReference(f0.engine_config_id, n_cyl, scalars, tail)
        preds = [ref.predict(f) for f in frames]
        P = np.vstack([p for p, _ in preds])
        X = _design(*[np.array(c) for c in zip(*cmds)], np.vstack([r for _, r in preds]))
        own = _own(P, np.array([c[2] for c in cmds]), ref.channels())
        Y = np.vstack([_measure(f, n_cyl, scalars) for f in frames]) - P
        keep = np.all(np.isfinite(Y), 1) & np.all(np.isfinite(X), 1) & np.all(np.isfinite(own), 1)
        if keep.sum() < 50:
            raise ValueError("nominal calibration frames need every channel and a running engine (model prediction)")
        finite = keep.copy()
        for _ in range(2):                       # robust: drop limiter events (e.g. an overspeed fuel cut), refit once
            coef, intercept = _fit_channels(X[keep], own[keep], Y[keep], alpha)
            res = Y - _apply(X, own, coef, intercept)
            scale = MAD_TO_SIGMA * np.median(np.abs(res[keep] - np.median(res[keep], 0)), 0)
            keep = finite & np.all(np.abs(np.nan_to_num(res, nan=np.inf)) <= OUTLIER_SIGMA * np.maximum(scale, 1e-12), axis=1)
        res = res[keep]
        sigma = np.maximum(res.std(0), 1e-3 * np.maximum(np.abs(Y[keep].mean(0)), 1.0))
        return cls(f0.engine_config_id, f0.tail_id, n_cyl, scalars, coef, intercept, sigma, len(frames), tail)

    # ---- apply ---------------------------------------------------------------------------
    def z(self, frame: Frame, shielded_channels: Sequence[str] | None = None, clip: bool = True) -> np.ndarray:
        """Per-channel z-scored residual, order: cht[0..n), egt[0..n), *scalars. clip=False keeps the magnitude
        (fault signatures, isolation); the detector scores the clipped value."""
        pred = self._predict(self.reference, frame)
        meas = _measure(frame, self.n_cyl, self.scalars, strict=False)
        z = np.nan_to_num((meas - pred) / self.sigma, nan=0.0)
        names = self.channel_names()
        shielded = set(s.lower() for s in (shielded_channels or []))
        q = getattr(frame, "quality", {}) or {}
        for i, ch in enumerate(names):
            ch_low = ch.lower()
            if (ch_low in shielded or
                (q.get(ch, 0) & Q_SHIELDED != 0) or
                (q.get(ch_low, 0) & Q_SHIELDED != 0)):
                z[i] = 0.0
        return np.clip(z, -Z_CLIP, Z_CLIP) if clip else z

    def _predict(self, reference: ModelReference, frame: Frame) -> np.ndarray:
        thr, alt, oat = _command(frame)
        base, reg = reference.predict(frame)
        X = _design(np.array([thr]), np.array([alt]), np.array([oat]), reg[None, :])
        return _apply(X, _own(base[None, :], np.array([oat]), self.channel_names()), self.coef, self.intercept)[0] + base

    def sensor_coupling(self, frame: Frame) -> np.ndarray:
        """(n_channels, n_channels): column c = residual z response to a +1 sigma bias of sensor c. Most columns are
        the unit vector; a sensor the reference uses as an INPUT (INPUT_CHANNELS: rpm, oil temperature) also moves
        the channels predicted from it - e.g. a biased oil-temperature sender shifts the predicted oil pressure,
        a real oil-temperature rise does not. Finite difference on the reference at the frame just scored (no time step; its small
        mutable state is saved and restored)."""
        names = self.channel_names()
        C = np.eye(len(names))
        ref = self.reference
        if ref.last_t != frame.t:                    # only right after scoring this frame (no time step, no restart)
            return C
        saved = ref.snapshot()
        base = self._predict(ref, frame)
        for c, name in enumerate(names):
            if name not in INPUT_CHANNELS or getattr(frame, name) is None:
                continue
            biased = copy.copy(frame)
            setattr(biased, name, getattr(frame, name) + self.sigma[c])
            moved = self._predict(ref, biased)
            dz = -np.nan_to_num((moved - base) / self.sigma, nan=0.0)
            dz[c] = 1.0
            C[:, c] = dz
        ref.restore(saved)
        return C

    def channel_names(self) -> List[str]:
        n = self.n_cyl
        return [f"cht_{i + 1}" for i in range(n)] + [f"egt_{i + 1}" for i in range(n)] + list(self.scalars)

    def features(self, z: np.ndarray) -> np.ndarray:
        """n_cyl-agnostic feature vector: [mean,max,min,std]x(CHT,EGT) + the FEATURE_SCALARS z (13 features on every
        engine). The other scored channels stay in the full z-vector (CUSUM drift channel, isolation)."""
        n = self.n_cyl
        f: List[float] = []
        for blk in (z[:n], z[n:2 * n]):
            f += [blk.mean(), blk.max(), blk.min(), blk.std()]
        f += [z[2 * n + k] for k in self._feature_idx()]
        return np.asarray(f, dtype=float)

    def _feature_idx(self) -> List[int]:
        return [k for k, name in enumerate(self.scalars) if name in FEATURE_SCALARS]

    def feature_names(self) -> List[str]:
        names = []
        for grp in ("cht", "egt"):
            names += [f"{grp}_{s}" for s in ("mean", "max", "min", "std")]
        return names + [self.scalars[k] for k in self._feature_idx()]

    # ---- persistence (sidecar) -----------------------------------------------------------
    def to_dict(self) -> Dict:
        return {
            "schema": CALIBRATION_SCHEMA, "engine_config_id": self.engine_config_id, "tail_id": self.tail_id,
            "n_cyl": self.n_cyl, "scalars": list(self.scalars), "n_frames": self.n_frames,
            "coef": self.coef.tolist(), "intercept": self.intercept.tolist(), "sigma": self.sigma.tolist(),
            "tail": self.tail,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "TailCalibration":
        if d.get("schema") != CALIBRATION_SCHEMA:
            raise ValueError(f"unsupported calibration schema {d.get('schema')!r}")
        return cls(d["engine_config_id"], d["tail_id"], int(d["n_cyl"]), d["scalars"],
                   np.array(d["coef"]), np.array(d["intercept"]), np.array(d["sigma"]), int(d["n_frames"]), d.get("tail"))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict()), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "TailCalibration":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
