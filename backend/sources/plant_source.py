"""
PlantSource -- the simulated plant behind the canonical Frame contract (B1.2; card M1-14, P Step 1.4).

Since M1-14 this is a facade over backend/sim (backend.sim.source.SimSource): the M1 engine model, registry fault
parameters and the sensor layer. The old backend.plant.virtual_engine internals no longer run behind it.

The two halves of each pair are separated on purpose: pass only ``frame`` to
anything that infers, and only ``truth`` to evaluation code.
"""

from __future__ import annotations

import math
from typing import Iterator, Optional, Tuple

from backend.core.frame import Frame, TruthRecord
from backend.sim.source import SimSource

__all__ = ["PlantSource"]


class PlantSource(SimSource):
    def __init__(self, engine_config_id: str, seed: Optional[int] = None,
                 tail_id: str = "TAIL-PLANT", engine_serial: str = "SN-PLANT") -> None:
        super().__init__(engine_config_id, seed=seed, tail_id=tail_id, engine_serial=engine_serial)
        from backend.sim.clock import load_sim_settings      # runtime settings import the hub: load lazily
        self.internal_step_s = float(load_sim_settings()["internal_step_s"])

    def step(self, dt_sec: float = 1.0, throttle_pct: float = 75.0, altitude_ft: float = 20000.0,
             oat_c: Optional[float] = -25.0, tas_kt: Optional[float] = None) -> Tuple[Frame, TruthRecord]:
        """Advance dt_sec of simulated time in fixed internal steps; return the last Frame."""
        n = max(1, math.ceil(dt_sec / self.internal_step_s - 1e-9))
        self.set_conditions(throttle_pct, altitude_ft, oat_c, tas_kt)
        for i in range(n):
            self.advance(dt_sec / n, publish=(i == n - 1))
        return self.emit()                       # sensors measure the published frame only

    def run(self, n_steps: int, dt_sec: float = 1.0, **step_kwargs) -> Iterator[Tuple[Frame, TruthRecord]]:
        for _ in range(n_steps):
            yield self.step(dt_sec, **step_kwargs)
