"""
External validation, protocol correctness and novelty handling — F14/F16/F17/F62/F63.

Four instruments that exist to stop us fooling ourselves, and one that stops a
bad sensor fooling the rest of the stack.

**F16/F63 — validation against real flight data.** Every number this project
produces comes from a simulator we wrote. The NASA ACES dataset is real Rotax 914
telemetry from a real MALE-class UAV, and it is already in the repo. This module
scores the twin's expectation model against it and reports the sim2real gap
honestly: where the model matches real flight, where it does not, and by how
much. A model that only agrees with its own generator has demonstrated nothing.

**F62 — correct anomaly-detection protocol.** The point-adjust convention used in
much of the time-series anomaly literature marks an entire ground-truth window as
correctly detected if the detector fires anywhere inside it. That inflates F1 to
near 1.0 for detectors that are barely better than random, and it is why
published AD numbers are frequently not comparable. Both conventions are computed
here so the difference is visible rather than hidden.

**F17 — the UNKNOWN class.** A classifier trained on eight faults will confidently
name one of those eight when shown a ninth. Reporting "anomalous, matches no known
signature" is more useful and more honest than a confident wrong label, and it is
the behaviour a maintainer can actually act on.

**F14 — residual shielding.** We detect that a sensor has failed and then keep
feeding its residual into the health index. A quarantined channel must be
excluded from every downstream computation, or one bad thermocouple degrades the
whole diagnosis.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

__all__ = [
    "ResidualShield",
    "NoveltyGate",
    "ad_scores",
    "validate_against_aces",
    "Sim2RealReport",
]


# ---------------------------------------------------------------------------
# F14 — residual shielding
# ---------------------------------------------------------------------------


class ResidualShield:
    """Quarantines channels so a known-bad sensor cannot pollute the diagnosis.

    Detecting a failed sensor and then continuing to use it is worse than not
    detecting it, because the system now has evidence it is wrong and acts on it
    anyway. Quarantine is sticky with a dwell time: a channel that has misbehaved
    must prove itself for a sustained period before it is trusted again, or it
    will flap in and out and produce alternating diagnoses.
    """

    def __init__(self, recovery_sec: float = 300.0) -> None:
        self.recovery_sec = recovery_sec
        self._quarantined: Dict[str, float] = {}  # channel -> time quarantined
        self._clean_since: Dict[str, float] = {}

    def quarantine(self, channel: str, t_sec: float, reason: str = "") -> None:
        if channel not in self._quarantined:
            self._quarantined[channel] = t_sec
        self._clean_since.pop(channel, None)

    def report_clean(self, channel: str, t_sec: float) -> None:
        """Channel looks healthy now; start or continue its recovery dwell."""
        if channel not in self._quarantined:
            return
        self._clean_since.setdefault(channel, t_sec)
        if t_sec - self._clean_since[channel] >= self.recovery_sec:
            self._quarantined.pop(channel, None)
            self._clean_since.pop(channel, None)

    def is_quarantined(self, channel: str) -> bool:
        return channel in self._quarantined

    @property
    def quarantined(self) -> Set[str]:
        return set(self._quarantined)

    def shield(self, residuals: Dict[str, float]) -> Dict[str, float]:
        """Zero out quarantined channels' residuals."""
        return {k: (0.0 if self.is_quarantined(k) else v) for k, v in residuals.items()}

    def usable(self, residuals: Dict[str, float]) -> Dict[str, float]:
        """Drop quarantined channels entirely — preferred for aggregate health.

        Zeroing keeps a channel in the average and biases it toward 'healthy';
        dropping it shrinks the evidence base honestly instead.
        """
        return {k: v for k, v in residuals.items() if not self.is_quarantined(k)}

    def health_index(self, residuals: Dict[str, float],
                     scales: Optional[Dict[str, float]] = None) -> dict:
        """Aggregate health over usable channels only, with the count reported."""
        usable = self.usable(residuals)
        if not usable:
            return {"health_index": None, "channels_used": 0,
                    "channels_quarantined": len(self._quarantined),
                    "note": "no usable channels — diagnosis unavailable"}
        scales = scales or {}
        zs = [abs(v) / max(scales.get(k, 1.0), 1e-9) for k, v in usable.items()]
        worst = max(zs)
        health = 1.0 / (1.0 + max(0.0, worst - 1.0))
        return {
            "health_index": round(health, 4),
            "channels_used": len(usable),
            "channels_quarantined": len(self._quarantined),
            "quarantined": sorted(self._quarantined),
            "worst_normalised_residual": round(worst, 3),
        }


# ---------------------------------------------------------------------------
# F17 — novelty / UNKNOWN
# ---------------------------------------------------------------------------


class NoveltyGate:
    """Lets the classifier decline to name a fault it has no signature for.

    Works on the classifier's own posterior plus a distance-to-known-signature
    measure. Either a low-confidence posterior or a large distance is enough to
    withhold the label: a confident posterior over a signature nothing resembles
    is exactly the failure mode this exists to catch.
    """

    def __init__(self, min_confidence: float = 0.55,
                 max_distance: float = 3.0,
                 min_margin: float = 0.15) -> None:
        self.min_confidence = min_confidence
        self.max_distance = max_distance
        self.min_margin = min_margin

    def decide(self, posterior: Dict[str, float],
               distance_to_nearest: Optional[float] = None) -> dict:
        if not posterior:
            return {"label": "UNKNOWN", "reason": "no posterior", "confident": False}
        ranked = sorted(posterior.items(), key=lambda kv: -kv[1])
        top_label, top_p = ranked[0]
        second_p = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = top_p - second_p

        reasons: List[str] = []
        if top_p < self.min_confidence:
            reasons.append(f"posterior {top_p:.2f} below {self.min_confidence:.2f}")
        if margin < self.min_margin:
            reasons.append(f"margin {margin:.2f} below {self.min_margin:.2f} "
                           f"(ambiguous between {ranked[0][0]} and {ranked[1][0]})"
                           if len(ranked) > 1 else "no margin")
        if distance_to_nearest is not None and distance_to_nearest > self.max_distance:
            reasons.append(f"distance {distance_to_nearest:.2f} beyond any known "
                           f"signature (> {self.max_distance:.2f})")

        if reasons:
            return {
                "label": "UNKNOWN",
                "candidate": top_label,
                "candidate_posterior": round(top_p, 4),
                "margin": round(margin, 4),
                "distance": (round(distance_to_nearest, 3)
                             if distance_to_nearest is not None else None),
                "reason": "; ".join(reasons),
                "confident": False,
                "advisory": ("Anomalous behaviour that matches no known fault "
                             "signature. Recommend inspection rather than acting "
                             "on a fault code."),
            }
        return {"label": top_label, "candidate": top_label,
                "candidate_posterior": round(top_p, 4), "margin": round(margin, 4),
                "distance": (round(distance_to_nearest, 3)
                             if distance_to_nearest is not None else None),
                "reason": "", "confident": True}


# ---------------------------------------------------------------------------
# F62 — anomaly-detection scoring, both conventions
# ---------------------------------------------------------------------------


def ad_scores(predictions: Sequence[int], labels: Sequence[int]) -> dict:
    """Point-wise and point-adjusted precision/recall/F1, side by side.

    Point-adjust marks every sample in a ground-truth anomaly window as detected
    if the detector fires anywhere in that window. It is widely used and it
    massively inflates F1 — a detector that fires once at random inside a long
    window scores as if it had found the whole thing. Reporting both makes the
    inflation visible instead of letting it pass as a result.
    """
    if len(predictions) != len(labels):
        raise ValueError("predictions and labels must be the same length")
    p = [int(bool(x)) for x in predictions]
    y = [int(bool(x)) for x in labels]

    def prf(pred: Sequence[int]) -> Tuple[float, float, float]:
        tp = sum(1 for a, b in zip(pred, y) if a == 1 and b == 1)
        fp = sum(1 for a, b in zip(pred, y) if a == 1 and b == 0)
        fn = sum(1 for a, b in zip(pred, y) if a == 0 and b == 1)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        return prec, rec, f1

    pw = prf(p)

    # Build the point-adjusted prediction.
    adjusted = list(p)
    i = 0
    n = len(y)
    while i < n:
        if y[i] == 1:
            j = i
            while j < n and y[j] == 1:
                j += 1
            if any(p[k] == 1 for k in range(i, j)):
                for k in range(i, j):
                    adjusted[k] = 1
            i = j
        else:
            i += 1
    pa = prf(adjusted)

    return {
        "point_wise": {"precision": round(pw[0], 4), "recall": round(pw[1], 4),
                       "f1": round(pw[2], 4)},
        "point_adjusted": {"precision": round(pa[0], 4), "recall": round(pa[1], 4),
                           "f1": round(pa[2], 4)},
        "f1_inflation": round(pa[2] - pw[2], 4),
        "note": ("Point-adjusted F1 is reported only for comparability with "
                 "published work. Point-wise is the honest figure."),
    }


# ---------------------------------------------------------------------------
# F16 / F63 — validation against real flight data
# ---------------------------------------------------------------------------


@dataclass
class Sim2RealReport:
    channel: str
    n_samples: int
    real_mean: float
    real_std: float
    model_mean: float
    bias: float
    mae: float
    rmse: float
    correlation: Optional[float]
    within_1_std_pct: float

    def as_dict(self) -> dict:
        return {
            "channel": self.channel,
            "n": self.n_samples,
            "real_mean": round(self.real_mean, 2),
            "real_std": round(self.real_std, 2),
            "model_mean": round(self.model_mean, 2),
            "bias": round(self.bias, 2),
            "mae": round(self.mae, 2),
            "rmse": round(self.rmse, 2),
            "correlation": (round(self.correlation, 3)
                            if self.correlation is not None else None),
            "within_1_real_std_pct": round(self.within_1_std_pct, 1),
        }


def validate_against_aces(granule, expectation_model,
                          max_samples: int = 3000) -> dict:
    """Score the twin's expectation model against real Altus II / Rotax 914 data.

    What this can and cannot establish is fixed by the data, and the loader
    records it: ACES contains no faults and no run-to-failure trajectories, so
    this validates the *nominal physics* and nothing else. It cannot support any
    claim about detection or RUL.

    Channel bindings in ACES are recovered from a fixed-width char matrix and
    some are known to be suspect; only channels that pass the loader's
    plausibility check are used, and the count is reported so a thin result
    cannot masquerade as a thorough one.
    """
    import numpy as np

    available = granule.available()
    rpm = granule.series("ENGINE_RPM")
    alt = granule.series("ALTITUDE_FT")
    oat = granule.series("OAT_C")
    if rpm is None:
        return {"error": "ENGINE_RPM did not bind or failed plausibility; "
                         "cannot build an operating point",
                "available_channels": sorted(available)}

    n = min(len(rpm), max_samples)
    idx = [i for i in range(n) if np.isfinite(rpm[i]) and rpm[i] > 1500.0]
    if len(idx) < 60:
        return {"error": "too few in-flight samples (engine running) in this granule",
                "available_channels": sorted(available)}

    reports: List[Sim2RealReport] = []
    comparable = {"EGT_1": "EGT_1", "COOLANT_TEMP": "CHT_1"}
    for aces_ch, model_ch in comparable.items():
        real = granule.series(aces_ch)
        if real is None:
            continue
        preds: List[float] = []
        actual: List[float] = []
        for i in idx:
            if not np.isfinite(real[i]):
                continue
            frame = {
                "ENGINE_RPM": float(rpm[i]),
                "ALTITUDE_FT": float(alt[i]) if alt is not None and np.isfinite(alt[i]) else 0.0,
                "OAT_C": float(oat[i]) if oat is not None and np.isfinite(oat[i]) else 15.0,
                "TPS": 75.0,
            }
            exp = expectation_model.expected(frame)
            if model_ch not in exp:
                continue
            preds.append(exp[model_ch])
            actual.append(float(real[i]))
        if len(actual) < 60:
            continue
        a = np.asarray(actual); p = np.asarray(preds)
        err = p - a
        std = float(np.std(a))
        corr = None
        if np.std(p) > 1e-9 and std > 1e-9:
            corr = float(np.corrcoef(a, p)[0, 1])
        reports.append(Sim2RealReport(
            channel=f"{aces_ch}->{model_ch}",
            n_samples=len(a),
            real_mean=float(np.mean(a)), real_std=std,
            model_mean=float(np.mean(p)),
            bias=float(np.mean(err)),
            mae=float(np.mean(np.abs(err))),
            rmse=float(np.sqrt(np.mean(err ** 2))),
            correlation=corr,
            within_1_std_pct=100.0 * float(np.mean(np.abs(err) <= max(std, 1e-9))),
        ))

    return {
        "granule": granule.path.name,
        "in_flight_samples": len(idx),
        "channels_bound": sorted(available),
        "comparisons": [r.as_dict() for r in reports],
        "caveat": ("ACES contains no faults and no run-to-failure data. This "
                   "validates nominal physics only and supports no claim about "
                   "detection performance or RUL."),
    }
