"""Sensor-layer fault levers (R7, D30): bias, drift, stuck, noise, dropout, and spoofing.

These levers modify the Frame after acquisition / synthesis to emulate sensor failure
modes, electrical issues, or CAN injection attacks. Any sensor-layer manipulation
sets TruthRecord.origin = 'MANUAL' (excluding the run from autonomous KPIs).
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.core.frame import FaultTruth, Frame


@dataclass
class SensorFault:
    kind: str           # bias | drift | stuck | noise | dropout | spoof
    channel: str        # e.g. "map_kpa", "oil_p", "cht_2", "rpm"
    param: float = 0.0  # bias offset, drift rate/s, noise sigma, etc.
    frozen_value: Optional[float] = None
    accumulated: float = 0.0


class SensorLevers:
    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)
        self.faults: Dict[str, SensorFault] = {}  # keyed by channel

    def inject_bias(self, channel: str, offset: float) -> None:
        self.faults[channel] = SensorFault(kind="bias", channel=channel, param=float(offset))

    def inject_drift(self, channel: str, rate_per_sec: float) -> None:
        self.faults[channel] = SensorFault(kind="drift", channel=channel, param=float(rate_per_sec))

    def inject_stuck(self, channel: str, frozen_value: Optional[float] = None) -> None:
        self.faults[channel] = SensorFault(kind="stuck", channel=channel, frozen_value=frozen_value)

    def inject_noise(self, channel: str, sigma: float) -> None:
        self.faults[channel] = SensorFault(kind="noise", channel=channel, param=float(sigma))

    def inject_dropout(self, channel: str) -> None:
        self.faults[channel] = SensorFault(kind="dropout", channel=channel)

    def inject_spoof(self, channel: str, spoof_value: float) -> None:
        self.faults[channel] = SensorFault(kind="spoof", channel=channel, param=float(spoof_value))

    def clear(self, channel: Optional[str] = None) -> None:
        if channel is not None:
            self.faults.pop(channel, None)
        else:
            self.faults.clear()

    @property
    def has_active_faults(self) -> bool:
        return len(self.faults) > 0

    def active_fault_truths(self, t: float) -> List[FaultTruth]:
        records = []
        for ch, f in self.faults.items():
            loc = None
            if ch.startswith("cht_") or ch.startswith("egt_"):
                try:
                    loc = int(ch.split("_")[1])
                except (IndexError, ValueError):
                    pass
            records.append(FaultTruth(
                mode=f"SENSOR_{f.kind.upper()}_{ch.upper()}",
                location=loc,
                severity=1.0,
                onset_t=t,
            ))
        return records

    def apply(self, frame: Frame, dt: float) -> Frame:
        if not self.faults:
            return frame

        # Shallow copy frame attributes into a modified Frame
        f = copy.copy(frame)
        f.cht = list(frame.cht)
        f.egt = list(frame.egt)

        def _get_val(chan: str) -> Optional[float]:
            if chan.startswith("cht_"):
                idx = int(chan.split("_")[1]) - 1
                return f.cht[idx] if 0 <= idx < len(f.cht) else None
            elif chan.startswith("egt_"):
                idx = int(chan.split("_")[1]) - 1
                return f.egt[idx] if 0 <= idx < len(f.egt) else None
            elif chan in ("map", "map_kpa"):
                return f.map_kpa
            elif hasattr(f, chan):
                return getattr(f, chan)
            return None

        def _set_val(chan: str, val: Optional[float]) -> None:
            if chan.startswith("cht_"):
                idx = int(chan.split("_")[1]) - 1
                if 0 <= idx < len(f.cht) and val is not None:
                    f.cht[idx] = val
            elif chan.startswith("egt_"):
                idx = int(chan.split("_")[1]) - 1
                if 0 <= idx < len(f.egt) and val is not None:
                    f.egt[idx] = val
            elif chan in ("map", "map_kpa"):
                f.map_kpa = val
            elif hasattr(f, chan):
                setattr(f, chan, val)

        for ch, sf in self.faults.items():
            val = _get_val(ch)
            if val is None:
                continue

            if sf.kind == "bias":
                _set_val(ch, val + sf.param)
            elif sf.kind == "drift":
                sf.accumulated += sf.param * dt
                _set_val(ch, val + sf.accumulated)
            elif sf.kind == "stuck":
                if sf.frozen_value is None:
                    sf.frozen_value = val
                _set_val(ch, sf.frozen_value)
            elif sf.kind == "noise":
                noise = self.rng.gauss(0.0, sf.param)
                _set_val(ch, val + noise)
            elif sf.kind == "dropout":
                _set_val(ch, 0.0)
            elif sf.kind == "spoof":
                _set_val(ch, sf.param)

        return f
