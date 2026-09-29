"""Operating levers with first-order dynamics (R3, closes G02).

The operator sets *targets*; the plant sees smoothed values, so a throttle step produces an rpm/thermal
transient instead of an instant overwrite of the displayed number."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Levers:
    throttle_pct: float = 60.0
    altitude_ft: float = 9000.0
    oat_c: float = 10.0
    throttle_target: float = 60.0
    altitude_target: float = 9000.0
    oat_target: float = 10.0
    throttle_tau_s: float = 2.0
    climb_rate_fps: float = 33.0        # ~2000 ft/min
    oat_tau_s: float = 30.0

    def set_targets(self, throttle_pct=None, altitude_ft=None, oat_c=None, snap=False, climb_rate_fps=None) -> None:
        if climb_rate_fps is not None:
            self.climb_rate_fps = float(climb_rate_fps)
        if throttle_pct is not None:
            self.throttle_target = min(100.0, max(0.0, float(throttle_pct)))
            if snap:
                self.throttle_pct = self.throttle_target
        if altitude_ft is not None:
            self.altitude_target = min(30000.0, max(0.0, float(altitude_ft)))
            if snap:
                self.altitude_ft = self.altitude_target
        if oat_c is not None:
            self.oat_target = min(55.0, max(-70.0, float(oat_c)))
            if snap:
                self.oat_c = self.oat_target

    def advance(self, dt: float) -> None:
        a = 1.0 - math.exp(-dt / self.throttle_tau_s)
        self.throttle_pct += a * (self.throttle_target - self.throttle_pct)
        step = self.climb_rate_fps * dt
        self.altitude_ft += max(-step, min(step, self.altitude_target - self.altitude_ft))
        b = 1.0 - math.exp(-dt / self.oat_tau_s)
        self.oat_c += b * (self.oat_target - self.oat_c)
