"""Trends and time-to-limit (card M4-02, P Part 4 Step 4.2, T-PRG-1).

What is trended: the model-informed RESIDUAL of each limited channel (measured minus the nominal model for this
tail, backend/detect/calibration.py), in physical units. Lever, altitude and OAT changes are explained by the model,
so a residual slope is wear or a developing fault, not the operating point.

Slope: Theil-Sen (median of pairwise slopes, robust to outliers and sensor spikes; scipy.stats.theilslopes with its
confidence interval) over sliding windows (configs/prognose.json). A trend is reported only when the WHOLE slope
interval points toward a limit of that channel (engine-manual warning limits, configs/engines limits). Then, with
the gap = limit - current value (median of the last samples, so one noisy reading does not move it):
    linear:     t_lin  = gap / slope
    quadratic:  smallest positive root of  c2 x^2 + c1 x = gap   (least-squares fit of the same window)
A developing fault usually accelerates (a growing blockage, an opening thermostat at its stop), which a straight
line extrapolates too late; the quadratic is used as the point estimate when it is accelerating, the line otherwise.
The interval spans both estimates, the Theil-Sen slope interval and the uncertainty of the current value
(z * sigma_reading / sqrt(samples) over the slope). This is assuming the present operating point is held. Beyond the
horizon nothing is reported (no long extrapolation).
Reads only measured readings and residuals (no truth).
"""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.stats import theilslopes

ROOT = Path(__file__).resolve().parents[2]
S_PER_H = 3600.0
CURRENT_SAMPLES = 3                    # current value = median of the last samples (one noisy reading does not move it)
Z_INTERVAL = 2.0                       # current-value uncertainty band (about 95 %)


def load_prognose_config() -> Dict[str, Any]:
    return json.loads((ROOT / "configs" / "prognose.json").read_text(encoding="utf-8"))


def limit_name(detector_channel: str) -> str:
    """Detector channel name (cht_<k>) -> limits / readings name (cht[<k>])."""
    for prefix in ("cht", "egt"):
        if detector_channel.startswith(prefix + "_"):
            return f"{prefix}[{detector_channel[len(prefix) + 1:]}]"
    return detector_channel


def _limits_for(limits: Dict[str, Any], name: str) -> Tuple[Optional[float], Optional[float]]:
    base = name.split("[")[0]
    lim = limits.get(base) or {}
    if "[" in name and not lim.get("per_cylinder"):
        return None, None
    return lim.get("warning_low"), lim.get("warning_high")


class TrendTracker:
    def __init__(self, limits: Dict[str, Any], channels: Sequence[str], sigma: Sequence[float],
                 cfg: Optional[Dict[str, Any]] = None) -> None:
        c = cfg or load_prognose_config()
        self.sample_s = float(c["trend_sample_s"]["value"])
        self.windows = sorted(float(w) for w in c["trend_windows_s"]["value"])
        self.min_points = int(c["trend_min_points"]["value"])
        self.conf = float(c["trend_confidence"]["value"])
        self.horizon = float(c["trend_horizon_s"]["value"])
        self.names = [limit_name(ch) for ch in channels]
        self.sigma = np.asarray(sigma, dtype=float)
        self.bounds = [_limits_for(limits, n) for n in self.names]
        self.tracked = [i for i, b in enumerate(self.bounds) if b != (None, None)]
        self.samples: Deque[Tuple[float, np.ndarray, np.ndarray]] = deque(maxlen=int(self.windows[-1] / self.sample_s) + 1)
        self._next_t: Optional[float] = None

    def reset(self) -> None:
        self.samples.clear()
        self._next_t = None

    def update(self, t: float, z_raw: Optional[Sequence[float]], readings: Dict[str, Optional[float]]) -> None:
        """Feed every frame's unclipped residual z (detector channel order) and readings; kept once per sample_s."""
        if z_raw is None:
            return
        if self._next_t is not None and t < self._next_t:
            return
        if self.samples and t < self.samples[-1][0]:          # time went backwards: a new sequence
            self.reset()
        vals = np.array([np.nan if readings.get(n) is None else float(readings[n]) for n in self.names])
        self.samples.append((t, np.asarray(z_raw, dtype=float) * self.sigma, vals))
        self._next_t = t + self.sample_s

    def time_to_limit(self) -> List[Dict[str, Any]]:
        """Significant trends toward a limit, shortest window that has enough points first (most recent behaviour)."""
        if len(self.samples) < self.min_points:
            return []
        t_all = np.array([s[0] for s in self.samples])
        r_all = np.vstack([s[1] for s in self.samples])
        v_all = np.vstack([s[2] for s in self.samples])
        out: List[Dict[str, Any]] = []
        for i in self.tracked:
            name = self.names[i]
            recent = v_all[-CURRENT_SAMPLES:, i]
            if not np.all(np.isfinite(recent)):
                continue
            current = float(np.median(recent))
            current_sd = self.sigma[i] / np.sqrt(len(recent))
            low, high = self.bounds[i]
            for w in self.windows:
                sel = t_all >= t_all[-1] - w
                if sel.sum() < self.min_points:
                    continue
                y = r_all[sel, i]
                if not np.all(np.isfinite(y)):
                    continue
                res = theilslopes(y, t_all[sel], alpha=self.conf)
                lo, hi = float(res.low_slope), float(res.high_slope)
                if high is not None and lo > 0 and current < high:
                    limit, toward = high, (lo, hi)
                elif low is not None and hi < 0 and current > low:
                    limit, toward = low, (hi, lo)
                else:
                    continue
                gap = limit - current
                t_lin = gap / float(res.slope)
                x = t_all[sel] - t_all[-1]
                c2, c1, _c0 = np.polyfit(x, y, 2)
                roots = np.roots([c2, c1, -gap])
                roots = roots[(np.abs(roots.imag) < 1e-12) & (roots.real > 0)].real
                t_quad = float(roots.min()) if len(roots) else None
                accelerating = t_quad is not None and c2 * np.sign(gap) > 0
                ttl = t_quad if accelerating else t_lin
                if ttl > self.horizon:
                    continue
                spread = Z_INTERVAL * current_sd / abs(float(res.slope))
                cands = [gap / toward[1], gap / toward[0], t_lin] + ([t_quad] if t_quad is not None else [])
                out.append({"channel": name, "limit": limit, "time_to_limit_s": round(ttl, 1),
                            "low_s": round(max(0.0, min(cands) - spread), 1), "high_s": round(max(cands) + spread, 1),
                            "slope_per_h": round(float(res.slope) * S_PER_H, 3), "window_s": w,
                            "model": "quadratic" if accelerating else "linear",
                            "method": "Theil-Sen / quadratic on the model-informed residual"})
                break
        return sorted(out, key=lambda d: d["time_to_limit_s"])
