"""OSA-CBM stage executor (B1.3, D05): one pipeline for live, replay and evaluation.

Stages declare a layer (backend.osacbm.Layer) and a cadence.  The executor pushes one Frame through the stages
in layer order and returns the results dict; per-stage timing is recorded so latency claims are measurements.
Because live sources, replay sources and the evaluation harness all call ``Pipeline.push`` on Frames, "live =
replay at 1x" is structural: identical Frames in => identical outputs (tested in tests/test_pipeline.py).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

from backend.core.frame import Frame
from backend.osacbm import Layer


class Stage(Protocol):
    name: str
    layer: str
    every_n: int           # run on every n-th frame (1 = every frame)

    def process(self, frame: Frame, results: Dict[str, Any]) -> Any: ...


@dataclass
class StageStats:
    calls: int = 0
    total_s: float = 0.0
    max_s: float = 0.0

    @property
    def mean_ms(self) -> float:
        return 1000.0 * self.total_s / max(self.calls, 1)


@dataclass
class FunctionStage:
    """Adapter: wrap a plain callable ``fn(frame, results) -> Any`` as a Stage."""
    name: str
    layer: str
    fn: Callable[[Frame, Dict[str, Any]], Any]
    every_n: int = 1
    enabled: Callable[[], bool] = field(default=lambda: True)

    def process(self, frame: Frame, results: Dict[str, Any]) -> Any:
        return self.fn(frame, results)


class Pipeline:
    def __init__(self, stages: List[Stage]) -> None:
        idx = [Layer.index(s.layer) for s in stages]
        if idx != sorted(idx):
            raise ValueError("stages must be ordered by OSA-CBM layer (DA<DM<SD<HA<PA<AG); got "
                             + ", ".join(f"{s.name}:{s.layer}" for s in stages))
        if len({s.name for s in stages}) != len(stages):
            raise ValueError("stage names must be unique")
        self.stages = stages
        self.stats: Dict[str, StageStats] = {s.name: StageStats() for s in stages}
        self.frame_count = 0

    def push(self, frame: Frame) -> Dict[str, Any]:
        self.frame_count += 1
        results: Dict[str, Any] = {}
        for s in self.stages:
            if self.frame_count % max(getattr(s, "every_n", 1), 1) != 0:
                continue
            en = getattr(s, "enabled", None)
            if en is not None and not en():
                continue
            t0 = time.perf_counter()
            results[s.name] = s.process(frame, results)
            dt = time.perf_counter() - t0
            st = self.stats[s.name]
            st.calls += 1
            st.total_s += dt
            st.max_s = max(st.max_s, dt)
        return results

    def timing_report(self) -> Dict[str, Dict[str, float]]:
        return {n: {"calls": s.calls, "mean_ms": s.mean_ms, "max_ms": 1000.0 * s.max_s}
                for n, s in self.stats.items()}
