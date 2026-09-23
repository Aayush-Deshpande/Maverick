"""
Physics-residual detector with per-tail calibration — F50, and the detector the
evaluation harness actually needs.

Two detectors were tried before this one and both failed in instructive ways,
which is worth recording because the failures are the argument for the design:

  1. **Frozen-baseline z-score.** Learned each channel's mean and variance over a
     240 s warm-up, then flagged 6-sigma departures. It fired at the same instant
     in every scenario including the nominal ones — the plant is still thermally
     settling at 240 s, and the warm-up variance of a settling channel is tiny.
     3 143 false alarms per flight hour. It was measuring the clock.

  2. **Fast/slow change detector.** Tracked a fast and a slow exponential average
     and watched the gap. False alarms went to zero, but it missed four of six
     faults — including a cooling degradation that overheated the engine to
     destruction — because a slow average absorbs any ramp slower than its own
     time constant. Degradation is *exactly* a slow ramp, so the detector was
     blind to the failure mode that matters most.

The lesson is that a detector referenced to a channel's own history cannot see
gradual degradation, because the history degrades with it. The reference has to
come from outside the measurement: from physics.

This detector computes what each channel *should* read given the current
operating point (load, altitude, OAT), and watches the residual. A slow ramp
cannot hide, because the expectation does not move with it.

Per-tail calibration (F50)
--------------------------
The twin's model and the engine never match exactly — build variation, sensor
bias, and an imperfect model all contribute a standing offset. That offset is
estimated over an early window of confirmed-nominal operation and then **frozen**.
Freezing matters: an offset that keeps adapting would slowly absorb a real fault,
which is the single most dangerous behaviour an adaptive monitor can have. This
is what makes the system a twin of *this* engine rather than of a generic one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

__all__ = ["ExpectationModel", "ResidualDetector", "DetectionVerdict"]


class ExpectationModel:
    """What each channel should read at a given operating point.

    Deliberately a *different* model from the plant's: coarser, algebraic, and
    written independently. If it were the same model the residuals would be pure
    noise and detection would be meaningless — which was the original G01 defect.
    """

    def __init__(self, rated_power_kw: float = 84.5, rated_rpm: float = 5800.0) -> None:
        self.rated_power_kw = rated_power_kw
        self.rated_rpm = rated_rpm

    @staticmethod
    def ambient_kpa(altitude_ft: float) -> float:
        return 101.325 * (1.0 - 2.25577e-5 * max(altitude_ft, 0.0) * 0.3048) ** 5.25588

    def expected(self, frame: Dict[str, float]) -> Dict[str, float]:
        thr = float(frame.get("TPS", 75.0))
        alt = float(frame.get("ALTITUDE_FT", 0.0))
        oat = float(frame.get("OAT_C", 15.0))
        rpm = float(frame.get("ENGINE_RPM", 5000.0))
        amb = self.ambient_kpa(alt)
        load = max(0.05, min(1.3, rpm / self.rated_rpm))

        out: Dict[str, float] = {}
        # Cooling falls off with air density; the same physical effect the plant
        # models, expressed differently and with different coefficients.
        alt_penalty = 20.0 * (1.0 - max(0.30, amb / 101.325))
        cht = 72.0 + 46.0 * load + alt_penalty + 0.25 * oat
        for i in range(1, 5):
            out[f"CHT_{i}"] = cht
            out[f"EGT_{i}"] = 365.0 + 425.0 * load
        out["OIL_PRESS"] = 0.6 + 0.00058 * rpm
        out["OIL_TEMP"] = 62.0 + 52.0 * load + 0.2 * oat
        out["MAP"] = min(140.0, amb * (0.22 + 0.80 * thr / 100.0))
        out["POWER_KW"] = self.rated_power_kw * load * (out["MAP"] / 101.325)
        out["FUEL_FLOW"] = out["POWER_KW"] * 0.30 + 1.5
        return out


@dataclass
class DetectionVerdict:
    detected: bool
    classification: Optional[str]
    channel: Optional[str]
    score: float
    residuals: Dict[str, float] = field(default_factory=dict)
    calibrated: bool = False

    def as_dict(self) -> dict:
        return {
            "detected": self.detected,
            "classification": self.classification,
            "channel": self.channel,
            "score": round(self.score, 3),
            "calibrated": self.calibrated,
        }


class ResidualDetector:
    """Physics-expectation residuals, per-tail calibrated, with sensor triage."""

    # Channels worth watching, and how much residual is normal on each. The
    # tolerance is a floor on the learned scale so that a channel which happened
    # to be very quiet during calibration does not become hair-triggered.
    _FLOOR = {
        "CHT_1": 3.0, "CHT_2": 3.0, "CHT_3": 3.0, "CHT_4": 3.0,
        "EGT_1": 25.0, "EGT_2": 25.0, "EGT_3": 25.0, "EGT_4": 25.0,
        "OIL_PRESS": 0.08, "OIL_TEMP": 3.0, "MAP": 1.5,
        "POWER_KW": 4.0, "FUEL_FLOW": 1.2,
    }

    def __init__(self, model: Optional[ExpectationModel] = None,
                 calibration_sec: float = 420.0,
                 settle_sec: float = 180.0,
                 k_sigma: float = 6.0,
                 persist_samples: int = 25) -> None:
        self.model = model or ExpectationModel()
        self.calibration_sec = calibration_sec
        self.settle_sec = settle_sec
        self.k_sigma = k_sigma
        self.persist_samples = persist_samples

        self._n: Dict[str, int] = {}
        self._sum: Dict[str, float] = {}
        self._sumsq: Dict[str, float] = {}
        self.bias: Dict[str, float] = {}
        self.scale: Dict[str, float] = {}
        self._streak: Dict[str, int] = {}
        self._calibrated = False

    @property
    def calibrated(self) -> bool:
        return self._calibrated

    def _finish_calibration(self) -> None:
        for ch, n in self._n.items():
            if n < 10:
                continue
            mean = self._sum[ch] / n
            var = max(self._sumsq[ch] / n - mean * mean, 0.0)
            self.bias[ch] = mean
            self.scale[ch] = max(math.sqrt(var), self._FLOOR.get(ch, 1.0))
        self._calibrated = True

    def update(self, frame: Dict[str, float], t_sec: float) -> DetectionVerdict:
        expected = self.model.expected(frame)
        residuals: Dict[str, float] = {}
        for ch, exp in expected.items():
            if ch in frame and isinstance(frame[ch], (int, float)):
                residuals[ch] = float(frame[ch]) - exp

        # Phase 1: settle. Phase 2: estimate the per-tail offset. Phase 3: watch.
        if t_sec < self.settle_sec:
            return DetectionVerdict(False, None, None, 0.0, residuals, False)

        if not self._calibrated:
            for ch, r in residuals.items():
                self._n[ch] = self._n.get(ch, 0) + 1
                self._sum[ch] = self._sum.get(ch, 0.0) + r
                self._sumsq[ch] = self._sumsq.get(ch, 0.0) + r * r
            if t_sec >= self.calibration_sec:
                self._finish_calibration()
            return DetectionVerdict(False, None, None, 0.0, residuals, False)

        detected = False
        worst_score = 0.0
        worst_ch: Optional[str] = None
        scores: Dict[str, float] = {}
        for ch, r in residuals.items():
            if ch not in self.bias:
                continue
            # The bias is FROZEN. It is never updated after calibration, so a
            # slow degradation cannot be absorbed into the reference.
            z = abs(r - self.bias[ch]) / max(self.scale[ch], 1e-6)
            scores[ch] = z
            self._streak[ch] = self._streak.get(ch, 0) + 1 if z > self.k_sigma else 0
            if self._streak[ch] >= self.persist_samples and z > worst_score:
                worst_score, worst_ch = z, ch
                detected = True

        classification = None
        if detected and worst_ch:
            classification = self._classify(worst_ch, scores)
        return DetectionVerdict(detected, classification, worst_ch, worst_score,
                                residuals, True)

    def _classify(self, channel: str, scores: Dict[str, float]) -> str:
        """Separate a bad sensor from a bad engine.

        The naive redundancy rule — "one channel moving while its peers hold
        station means a sensor" — is wrong, and the harness caught it: a misfire
        on cylinder 3 moves only cylinder 3's channels, and was duly reported as
        a sensor fault. A serviceable-aircraft abort avoided in one direction
        became a missed engine fault in the other.

        The distinguishing fact is that a sensor measures exactly one thing,
        whereas a sick cylinder shows up on *both* of its own channels. So:

          CHT_n and EGT_n both anomalous   -> that cylinder is genuinely sick
          several cylinders anomalous      -> a system fault (cooling, fuel)
          exactly one channel anomalous    -> that sensor is lying
        """
        if not (channel.startswith("CHT_") or channel.startswith("EGT_")):
            return "ENGINE_FAULT"

        prefix, idx = channel.split("_", 1)
        partner_prefix = "EGT" if prefix == "CHT" else "CHT"
        partner = f"{partner_prefix}_{idx}"

        # Corroboration has to be RELATIVE, not an absolute threshold. A misfire
        # drops EGT by ~150 C almost immediately but moves CHT by only ~2.5 C,
        # because the head has a 25 s thermal time constant and far more mass.
        # An absolute partner threshold therefore reported a genuine misfire as a
        # sensor fault. What matters is that the partner channel points at *this*
        # cylinder more than at any other.
        partner_score = scores.get(partner, 0.0)
        partner_peers = [v for c, v in scores.items()
                         if c.startswith(partner_prefix + "_") and c != partner]
        partner_peer_max = max(partner_peers) if partner_peers else 0.0
        if partner_score > 1.0 and partner_score > 2.5 * max(partner_peer_max, 1e-6):
            return "ENGINE_FAULT"

        # Several cylinders anomalous on the same measurand is a system fault
        # (cooling, fuel supply), not a sensor.
        peers = [v for c, v in scores.items()
                 if c.startswith(prefix + "_") and c != channel]
        if peers and max(peers) > self.k_sigma * 0.5:
            return "ENGINE_FAULT"

        return "SENSOR_FAULT"

    def reset(self) -> None:
        self._n.clear(); self._sum.clear(); self._sumsq.clear()
        self.bias.clear(); self.scale.clear(); self._streak.clear()
        self._calibrated = False
