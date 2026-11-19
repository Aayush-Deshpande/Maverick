"""Fixed-step simulation clock with a selectable time scale (card M1-01, DECISIONS D8, R 21.3).
The plant integrates at internal_step_s; each published frame runs scale * publish_period / internal_step steps, so
ramps, detection windows and RUL stay in simulated seconds at any speed."""
from __future__ import annotations

from typing import Any, Dict

from backend.runtime.hub import load_runtime_settings


def load_sim_settings() -> Dict[str, Any]:
    sim = load_runtime_settings().get("sim")
    if not sim or sim.get("internal_step_s", 0) <= 0 or not sim.get("time_scales"):
        raise ValueError("configs/runtime.json needs sim.internal_step_s > 0 and sim.time_scales")
    return sim


class SimClock:
    def __init__(self, internal_step_s: float, publish_period_s: float, time_scales=(1, 5, 20, 60)) -> None:
        self.internal_step_s = internal_step_s
        self.publish_period_s = publish_period_s
        self.time_scales = tuple(time_scales)
        self.time_scale = self.time_scales[0]
        self._steps = 0                       # integer step count: no float drift over long missions

    @property
    def sim_time_s(self) -> float:
        return self._steps * self.internal_step_s

    def set_time_scale(self, scale: int) -> None:
        if scale not in self.time_scales:
            raise ValueError(f"time scale {scale} not in {self.time_scales}")
        self.time_scale = scale

    def steps_for_publish(self) -> int:
        n = self.time_scale * self.publish_period_s / self.internal_step_s
        if abs(n - round(n)) > 1e-9 or round(n) < 1:
            raise ValueError(f"publish period x scale must be a whole number of internal steps (got {n})")
        return int(round(n))

    def advance(self) -> float:
        self._steps += 1
        return self.sim_time_s
