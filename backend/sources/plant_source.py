"""
PlantSource -- the current independent plant behind the canonical Frame contract (B1.2, part 1).

This is the WIRE side of docs/build/SUPERSEDED_VS_CURRENT.md S01: it exposes
``backend.plant.virtual_engine.VirtualEngine`` (independent physics, build variation,
its own sensor model) as a stream of ``(Frame, TruthRecord)`` pairs. It deliberately
does NOT touch the legacy ``can_streamer.TelemetryStreamer`` and does not go through
``plant/adapter.py`` (the stopgap blend that keeps the old streamer as the base).

The two halves of each pair are separated on purpose: pass only ``frame`` to
anything that infers, and only ``truth`` to evaluation code.
"""

from __future__ import annotations

from typing import Iterator, Optional, Tuple

from backend.core.frame import Frame, TruthRecord, frame_from_plant, truth_from_plant
from backend.plant.virtual_engine import VirtualEngine

__all__ = ["PlantSource"]


class PlantSource:
    def __init__(self, engine_config_id: str, seed: Optional[int] = None,
                 tail_id: str = "TAIL-PLANT", engine_serial: str = "SN-PLANT",
                 variation_spread: float = 1.0) -> None:
        self.engine_config_id = engine_config_id
        self.tail_id = tail_id
        self.engine_serial = engine_serial
        self.plant = VirtualEngine(engine_config_id, seed=seed, variation_spread=variation_spread)
        self.n_cylinders = self.plant.cfg.cylinder_count

    def inject_fault(self, name: str, cylinder: Optional[int] = None,
                     severity: float = 0.6, ramp_sec: float = 300.0) -> None:
        """Plant-side only. Nothing about the fault reaches the Frame stream."""
        self.plant.inject_fault(name, cylinder=cylinder, severity=severity, ramp_sec=ramp_sec)

    def clear_faults(self) -> None:
        self.plant.clear_faults()

    def step(self, dt_sec: float = 1.0, throttle_pct: float = 75.0, altitude_ft: float = 20000.0,
             oat_c: float = -25.0, dust_mg_m3: float = 0.15) -> Tuple[Frame, TruthRecord]:
        raw = self.plant.step(dt_sec, throttle_pct=throttle_pct, altitude_ft=altitude_ft,
                              oat_c=oat_c, dust_mg_m3=dust_mg_m3)
        frame = frame_from_plant(raw, self.engine_config_id, self.n_cylinders,
                                 self.tail_id, self.engine_serial)
        return frame, truth_from_plant(self.plant.truth())

    def run(self, n_steps: int, dt_sec: float = 1.0, **step_kwargs) -> Iterator[Tuple[Frame, TruthRecord]]:
        for _ in range(n_steps):
            yield self.step(dt_sec, **step_kwargs)

    @property
    def has_failed(self) -> bool:
        return self.plant.has_failed
