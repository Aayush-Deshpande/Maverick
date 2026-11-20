"""Sensor validation: fault detection and isolation for the sensors themselves (card M3-03, idea text section 6,
PS C "sensor drift/failure").

Per channel, every frame, from the measured Frame only:
  DROPOUT       the reading is missing (S05)
  OUT_OF_RANGE  outside the sender's measuring range (S06)
  RATE_SPIKE    a jump faster than the physical process can move (open thermocouple, ADC glitch)
  FROZEN        window variance far below the sender's own noise (S01 stuck)
  NOISY         successive-difference variance far above the sender's noise (S04)
  LANE_DISAGREE lane A and lane B differ by more than the lane tolerance (S07)
A failed channel is quarantined: detection, the observer and status stop using it, and the runtime publishes the
observer's estimate in its place with quality VIRTUAL. Automatic quarantines recover after a run of clean frames;
operator quarantines stay until cleared. Bias and slow drift (S02/S03) move a channel the way a real fault does, so
one sensor alone cannot tell them apart: they are left to the diagnosis (hypotheses "sensor" vs "process", M3-05),
never silently quarantined - a real failure must not be hidden (lesson of the legacy validator, M2-02).
Sender noise comes from configs/physics sensors (the same datasheet figures the simulator uses); ranges, rates and
windows from configs/detect.json fdi.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Set

from backend.detect.cusum import load_detect_config
from backend.sim.params import physics_values

MAD_TO_SIGMA = 0.6745          # median |x| of a unit normal
SQRT6 = 6 ** 0.5               # sigma of a second difference of white noise = sqrt(6) sigma


@dataclass
class ChannelVerdict:
    channel: str
    fault: str
    detail: str


@dataclass
class FdiReport:
    failed: List[str]
    verdicts: List[ChannelVerdict]
    latency_ms: float
    quarantined: List[str] = field(default_factory=list)

    @property
    def all_valid(self) -> bool:
        return not self.quarantined

    def to_dict(self) -> Dict[str, Any]:
        return {"all_sensors_valid": self.all_valid, "failed_channels": list(self.quarantined),
                "new_faults": [{"channel": v.channel, "fault": v.fault, "detail": v.detail} for v in self.verdicts],
                "latency_ms": round(self.latency_ms, 3),
                "advisory": (f"{len(self.quarantined)} sensor(s) quarantined: {', '.join(self.quarantined)}"
                             if self.quarantined else None)}


def frame_channels(frame: Any) -> Dict[str, Optional[float]]:
    out: Dict[str, Optional[float]] = {}
    for name in ("rpm", "prop_rpm", "map_kpa", "coolant_t", "oil_p", "oil_t", "fuel_flow", "fuel_p", "rail_p",
                 "gearbox_t", "bus_v"):
        if hasattr(frame, name):
            out[name] = getattr(frame, name)
    for prefix in ("cht", "egt"):
        for i, v in enumerate(getattr(frame, prefix, []) or [], start=1):
            out[f"{prefix}_{i}"] = v
    return out


class SensorFDI:
    def __init__(self, engine_id: str) -> None:
        c = load_detect_config()["fdi"]
        self.kinds: Dict[str, str] = c["kinds"]
        self.range = {k: v for k, v in c["range"].items() if k != "ref"}
        self.rate = {k: v for k, v in c["max_rate_per_s"].items() if k != "ref"}
        self.freeze_n = int(c["freeze_window"]["value"])
        self.freeze_frac = float(c["freeze_var_fraction"]["value"])
        self.noise_n = int(c["noise_window"]["value"])
        self.noise_factor = float(c["noise_var_factor"]["value"])
        self.lane_sigma = float(c["lane_sigma"]["value"])
        self.recover_n = int(c["recover_frames"]["value"])
        self.noise = physics_values(engine_id, "sensors")
        self._hist: Dict[str, Deque[float]] = {}
        self._prev: Dict[str, tuple] = {}
        self._auto: Dict[str, int] = {}          # channel -> clean frames since quarantine
        self._manual: Set[str] = set()

    # -- sender model ---------------------------------------------------------------------------------------
    def kind(self, channel: str) -> Optional[str]:
        return self.kinds.get(channel.rsplit("_", 1)[0] if channel[-1:].isdigit() else channel)

    def sigma(self, channel: str, value: float) -> float:
        k, n = self.kind(channel), self.noise
        if k in ("temperature", "egt"):
            return n["noise_temperature_c"]
        if k in ("pressure_bar", "rail_bar", "pressure_kpa"):
            s = n["noise_pressure_rel"] * abs(value)
            return max(s, n.get("noise_pressure_floor_bar", 0.0)) if channel == "oil_p" else s
        if k == "speed":
            return n["noise_rpm"]
        if k == "flow":
            return n["noise_flow_rel"] * abs(value)
        if k == "voltage":
            return n["noise_electrical_rel"] * abs(value)
        return 0.0

    # -- operator -------------------------------------------------------------------------------------------
    def quarantine(self, channel: str) -> None:
        self._manual.add(channel.lower())

    def reset(self) -> None:
        self._hist.clear()
        self._prev.clear()
        self._auto.clear()
        self._manual.clear()

    # -- one frame ------------------------------------------------------------------------------------------
    def validate(self, frame: Any) -> FdiReport:
        t0 = time.perf_counter()
        t = float(frame.t)
        verdicts: List[ChannelVerdict] = []
        lane_b = getattr(frame, "lane_b", {}) or {}
        for ch, v in frame_channels(frame).items():
            k = self.kind(ch)
            if k is None:
                continue
            fault = self._check(ch, k, v, t, lane_b.get(ch))
            if fault:
                verdicts.append(ChannelVerdict(ch, fault[0], fault[1]))
        # a disturbance that moves several channels together is the process (transient, limit cycle), not a sender
        if sum(1 for x in verdicts if x.fault == "NOISY") >= 2:
            verdicts = [x for x in verdicts if x.fault != "NOISY"]
        bad = {x.channel for x in verdicts}
        for ch in bad:
            self._auto[ch] = 0
        for ch in [c for c in self._auto if c not in bad]:
            self._auto[ch] += 1
            if self._auto[ch] >= self.recover_n:
                del self._auto[ch]                                         # trusted again after clean frames
        quarantined = sorted(set(self._auto) | self._manual)
        return FdiReport([x.channel for x in verdicts], verdicts, (time.perf_counter() - t0) * 1000.0, quarantined)

    def _check(self, ch: str, k: str, v: Optional[float], t: float, lane_b: Optional[float]):
        hist = self._hist.setdefault(ch, deque(maxlen=max(self.freeze_n, self.noise_n)))
        prev = self._prev.get(ch)
        if v is None:
            if prev is not None:
                return "DROPOUT", f"{ch}: no reading"
            return None
        self._prev[ch] = (t, v)
        lo, hi = self.range[k]
        if not lo <= v <= hi:
            return "OUT_OF_RANGE", f"{ch} {v:.3g} outside the sender range [{lo}, {hi}]"
        if prev is not None and t > prev[0]:
            rate = abs(v - prev[1]) / (t - prev[0])
            if rate > self.rate[k]:
                hist.clear()
                return "RATE_SPIKE", f"{ch} moved {rate:.3g}/s (physical max {self.rate[k]}/s)"
        if lane_b is not None:
            s = self.sigma(ch, v)
            if s > 0 and abs(v - lane_b) > self.lane_sigma * s:
                return "LANE_DISAGREE", f"{ch} lane A {v:.4g} vs lane B {lane_b:.4g}"
        hist.append(v)
        s = self.sigma(ch, v)
        if s <= 0:
            return None
        if len(hist) >= self.freeze_n:
            w = list(hist)[-self.freeze_n:]
            m = sum(w) / len(w)
            if sum((x - m) ** 2 for x in w) / len(w) < self.freeze_frac * s * s:
                return "FROZEN", f"{ch} has not moved for {self.freeze_n} frames (sender noise {s:.3g})"
        if len(hist) >= self.noise_n:
            w = list(hist)[-self.noise_n:]
            d2 = sorted(abs(c - 2 * b + a) for a, b, c in zip(w, w[1:], w[2:]))   # cancels ramps
            sigma_est = d2[len(d2) // 2] / MAD_TO_SIGMA / SQRT6     # robust: one throttle step does not count
            if sigma_est * sigma_est > self.noise_factor * s * s:
                return "NOISY", f"{ch} noise far above the sender's {s:.3g}"
        return None
