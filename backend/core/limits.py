"""Operating-limit (redline) evaluation from the engine profile (U3).  Cylinder-count agnostic.

Limits come from ``EngineConfig.operating_limits`` with provenance; PLACEHOLDER-status limits are reported with
``quotable=False`` so a UI/report never presents them as OEM limits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from backend.core.frame import Frame
from backend.physics.engine_config import EngineConfig


@dataclass(frozen=True)
class Exceedance:
    limit: str            # e.g. cht_max_c
    channel: str          # e.g. cht_3
    value: float
    threshold: float
    status: str           # provenance status of the limit
    quotable: bool


def check_limits(frame: Frame, cfg: EngineConfig) -> List[Exceedance]:
    lim = cfg.operating_limits
    out: List[Exceedance] = []

    def add(key, chan, val, thr, over):
        if val is None or key not in lim:
            return
        if over(val, thr):
            st = cfg.provenance_status(f"operating_limits.{key}")
            out.append(Exceedance(key, chan, float(val), float(thr), st, st in ("PUBLIC", "MANUAL")))

    for i, v in enumerate(frame.cht, 1):
        add("cht_max_c", f"cht_{i}", v, lim.get("cht_max_c"), lambda a, b: a > b)
    for i, v in enumerate(frame.egt, 1):
        add("egt_max_c", f"egt_{i}", v, lim.get("egt_max_c"), lambda a, b: a > b)
    add("oil_t_max_c", "oil_t", frame.oil_t, lim.get("oil_t_max_c"), lambda a, b: a > b)
    if frame.rpm is not None and frame.rpm > 0.35 * cfg.rated_rpm:      # oil-pressure floor applies when running
        add("oil_p_min_bar", "oil_p", frame.oil_p, lim.get("oil_p_min_bar"), lambda a, b: a < b)
    return out
