"""Adaptive per-tail baseline (card M4-06, P Part 4 Step 4.6, T-PRG-3) - the PS "adaptive learning capability", made
safe against learning a fault as normal.

An engine's healthy behaviour drifts slowly (run-in, seasonal fuel, sensor ageing). The tail calibration's offset
(intercept) and scale (sigma) of every residual channel are re-estimated with an EWMA of the residual, but ONLY on
frames where all guards hold:
  - status GO continuously for >= hold_go_s,
  - CUSUM drift statistic below cusum_fraction x its threshold,
  - novelty channel quiet and no confirmed detector alarm,
  - no open maintenance work order for this engine.
Accepted learning is committed as a new numbered version every commit_every_s of accepted time; one version may move
a channel by at most offset_step_limit_sigma and change its sigma by at most sigma_step_limit, so a slow fault cannot
be absorbed in one step (and the guards stop learning once it shows). Every version is kept for rollback and
persisted under var/baselines/. Reads only residuals, status and work-order counts (no truth).
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from backend.detect.cusum import load_detect_config


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


class AdaptiveBaseline:
    def __init__(self, calibration: Any, tail_id: str, cfg: Optional[Dict[str, Any]] = None,
                 path: Optional[Path] = None) -> None:
        c = cfg or load_detect_config()["adaptive"]
        self.alpha = float(c["ewma_alpha"]["value"])
        self.hold_go_s = float(c["hold_go_s"]["value"])
        self.cusum_fraction = float(c["cusum_fraction"]["value"])
        self.commit_every_s = float(c["commit_every_s"]["value"])
        self.sigma_step = float(c["sigma_step_limit"]["value"])
        self.offset_step = float(c["offset_step_limit_sigma"]["value"])
        self.max_versions = int(c["max_versions"]["value"])
        self.cal = calibration
        if path is None:
            from backend.runtime.paths import var_path        # lazy: backend.runtime imports this module
            path = var_path("baselines") / f"{tail_id}.json"
        self.path = path
        n = len(calibration.sigma)
        self.mean = np.zeros(n)
        self.sq = np.square(np.asarray(calibration.sigma, dtype=float))
        self.accepted_s = 0.0
        self.go_since: Optional[float] = None
        self.last_t: Optional[float] = None
        self.last_reason = "starting"
        self.versions: List[Dict[str, Any]] = [self._snapshot(0, None, "calibration")]

    # -- guards ---------------------------------------------------------------------------------------------------
    def _blocked(self, t: float, status_level: Optional[str], det: Any, open_orders: int) -> Optional[str]:
        if status_level != "GO":
            self.go_since = None
            return f"status {status_level}"
        if self.go_since is None:
            self.go_since = t
        if t - self.go_since < self.hold_go_s:
            return "GO for less than the hold time"
        if det is None or det.z_raw is None:
            return "no residual"
        if det.confirmed or det.raw_alarm:
            return "detector alarm"
        if (det.drift or {}).get("ratio", 0.0) > self.cusum_fraction:
            return "CUSUM above h/2"
        if (det.novelty or {}).get("raw"):
            return "novelty"
        if open_orders:
            return "open work order"
        return None

    # -- learning -------------------------------------------------------------------------------------------------
    def update(self, t: float, status_level: Optional[str], det: Any, open_orders: int = 0) -> bool:
        """One frame. Returns True when the frame was learned from."""
        dt = 0.0 if self.last_t is None or t < self.last_t else t - self.last_t
        self.last_t = t
        reason = self._blocked(t, status_level, det, open_orders)
        self.last_reason = reason or "learning"
        if reason:
            return False
        r = np.nan_to_num(np.asarray(det.z_raw, dtype=float) * self.cal.sigma, nan=0.0)
        self.mean += self.alpha * (r - self.mean)
        self.sq += self.alpha * (np.square(r - self.mean) - self.sq)
        self.accepted_s += dt
        if self.accepted_s >= self.commit_every_s:
            self.commit(t)
        return True

    def commit(self, t: float) -> Dict[str, Any]:
        sigma = np.asarray(self.cal.sigma, dtype=float)
        step = np.clip(self.mean, -self.offset_step * sigma, self.offset_step * sigma)
        self.cal.intercept = np.asarray(self.cal.intercept, dtype=float) + step
        new_sigma = np.clip(np.sqrt(np.maximum(self.sq, 1e-12)), sigma / self.sigma_step, sigma * self.sigma_step)
        self.cal.sigma = new_sigma
        self.mean = np.zeros_like(self.mean)
        self.sq = np.square(new_sigma)
        self.accepted_s = 0.0
        v = self._snapshot(self.versions[-1]["version"] + 1, t, "learned while GO")
        self.versions = (self.versions + [v])[-self.max_versions:]
        self._save()
        return v

    def rollback(self, version: int) -> Dict[str, Any]:
        v = next((x for x in self.versions if x["version"] == version), None)
        if v is None:
            raise KeyError(version)
        self.cal.intercept = np.array(v["intercept"])
        self.cal.sigma = np.array(v["sigma"])
        self.mean = np.zeros_like(self.mean)
        self.sq = np.square(self.cal.sigma)
        self.accepted_s = 0.0
        rb = self._snapshot(self.versions[-1]["version"] + 1, self.last_t, f"rollback to v{version}")
        self.versions = (self.versions + [rb])[-self.max_versions:]
        self._save()
        return rb

    # -- reporting / persistence ----------------------------------------------------------------------------------
    def _snapshot(self, version: int, t: Optional[float], note: str) -> Dict[str, Any]:
        return {"version": version, "sim_t": t, "wall": _now(), "note": note,
                "intercept": np.asarray(self.cal.intercept, dtype=float).tolist(),
                "sigma": np.asarray(self.cal.sigma, dtype=float).tolist()}

    def status(self) -> Dict[str, Any]:
        v = self.versions[-1]
        return {"version": v["version"], "updated_sim_t": v["sim_t"], "updated_wall": v["wall"], "note": v["note"],
                "learning": self.last_reason == "learning", "reason": self.last_reason,
                "accepted_s": round(self.accepted_s, 1)}

    def _save(self) -> None:
        self.path.write_text(json.dumps({"channels": self.cal.channel_names(), "versions": self.versions}),
                             encoding="utf-8")
