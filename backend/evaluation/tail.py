"""One calibrated test tail for offline evaluation (cards M3-05/M3-08): a PlantSource with its own build spread and
noise stream (seed), run through the same nominal calibration schedule as the runtime, and its ResidualDetector.
Used by scripts/diagnose (signatures, isolation report), backend/evaluation/run_matrix.py and the tests.
Seeds: signature/training tails < 1000, test tails >= 1000 (D17)."""
from __future__ import annotations

from typing import Tuple

import numpy as np

from backend.detect import ResidualDetector
from backend.runtime.engine_runtime import _WARM_SCHEDULE
from backend.sources import PlantSource

CAL_TICKS, SETTLE_TICKS, DWELL = 424, 24, 30          # same run-up as EngineRuntime.calibrate (1 s frames)


def calibrated(engine_id: str, seed: int) -> Tuple[PlantSource, ResidualDetector]:
    src = PlantSource(engine_id, seed=seed)
    rng = np.random.default_rng(seed + 12345)
    frames, order, op = [], [], _WARM_SCHEDULE[0]
    for i in range(CAL_TICKS):
        if i % DWELL == 0:
            if not order:
                order = list(rng.permutation(len(_WARM_SCHEDULE)))
            op = _WARM_SCHEDULE[int(order.pop())]
        f, _ = src.step(1.0, throttle_pct=op[0], altitude_ft=op[1], oat_c=op[2])
        if i >= SETTLE_TICKS:
            frames.append(f)
    return src, ResidualDetector.calibrate(frames, alpha=0.01)
