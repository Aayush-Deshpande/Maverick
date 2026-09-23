"""
Edge feature compression, bandwidth and power accounting — F08 / F67 / F68.

The architectural claim this project makes is that analysis has to happen onboard
because the datalink cannot carry what we are listening to. That claim is either
arithmetic or it is decoration, so here it is as arithmetic.

A crank-angle channel at 10 kHz, 16-bit, is 160 kbit/s from one accelerometer
before any other telemetry. A tactical UAV datalink shares a budget of order
100 kbit/s across video, command, navigation and housekeeping. The raw signal
does not fit, and no compression scheme makes it fit while preserving the
diagnostic content. What does fit is the *conclusion*: a few hundred bits per
second of order-domain features and per-cylinder verdicts.

Two further accountings that nobody in this field does, and that a defence
reviewer will immediately ask about:

  * **Power.** Every watt of edge compute costs endurance on a UAV. An analysis
    package that silently consumes 25 W has taken minutes of loiter away from the
    mission it is supposed to protect, and that trade should be stated rather
    than discovered.
  * **Latency.** "Real-time" is a measurement, not an adjective. This module
    times the actual pipeline so the claim carries a number.
"""

from __future__ import annotations

import math
import struct
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "LinkBudget",
    "EdgeFeatureFrame",
    "EdgeCompressor",
    "PowerBudget",
    "LatencyBudget",
]


@dataclass
class LinkBudget:
    """What the datalink can actually carry."""

    total_kbit_s: float = 100.0
    video_kbit_s: float = 64.0
    command_nav_kbit_s: float = 8.0
    housekeeping_kbit_s: float = 6.0

    @property
    def available_for_engine_kbit_s(self) -> float:
        used = self.video_kbit_s + self.command_nav_kbit_s + self.housekeeping_kbit_s
        return max(0.0, self.total_kbit_s - used)


@dataclass
class EdgeFeatureFrame:
    """The compressed diagnostic payload sent to the ground.

    Deliberately small and fixed-layout: on a lossy link a self-describing
    format costs more than it is worth, and a fixed layout can be decoded from a
    partial frame.
    """

    t_sec: float
    order_05: float          # misfire line
    order_1: float
    order_2: float           # firing order
    order_4: float
    crest_factor: float
    kurtosis: float
    per_cylinder_ratio: List[float] = field(default_factory=list)
    misfire_cylinder: int = 0     # 0 = none
    misfire_rate: float = 0.0
    verdict_code: int = 0         # 0 nominal, 1 weak, 2 misfiring, 3 instability

    _VERDICTS = {0: "NOMINAL", 1: "WEAK_CYLINDER", 2: "MISFIRING",
                 3: "COMBUSTION_INSTABILITY"}

    def pack(self) -> bytes:
        """Fixed binary layout. Half-precision where the dynamic range allows."""
        head = struct.pack(
            "<f6e", self.t_sec, self.order_05, self.order_1, self.order_2,
            self.order_4, self.crest_factor, self.kurtosis,
        )
        cyls = struct.pack(f"<B{len(self.per_cylinder_ratio)}e",
                           len(self.per_cylinder_ratio), *self.per_cylinder_ratio)
        tail = struct.pack("<BeB", self.misfire_cylinder, self.misfire_rate,
                           self.verdict_code)
        return head + cyls + tail

    @property
    def size_bytes(self) -> int:
        return len(self.pack())

    @property
    def verdict(self) -> str:
        return self._VERDICTS.get(self.verdict_code, "UNKNOWN")

    def as_dict(self) -> dict:
        return {
            "t_sec": round(self.t_sec, 2),
            "ORDER_0.5": round(self.order_05, 6),
            "ORDER_2": round(self.order_2, 6),
            "per_cylinder_ratio": [round(v, 3) for v in self.per_cylinder_ratio],
            "misfire_cylinder": self.misfire_cylinder or None,
            "misfire_rate": round(self.misfire_rate, 4),
            "verdict": self.verdict,
            "bytes": self.size_bytes,
        }


class EdgeCompressor:
    """Turns a kHz crank/vibration stream into a few hundred bits per second."""

    _VERDICT_CODES = {"NOMINAL": 0, "WEAK_CYLINDER": 1, "MISFIRING": 2,
                      "COMBUSTION_INSTABILITY": 3}

    def __init__(self, sample_rate_hz: float = 10000.0, bits_per_sample: int = 16,
                 publish_hz: float = 1.0, link: Optional[LinkBudget] = None) -> None:
        self.sample_rate_hz = sample_rate_hz
        self.bits_per_sample = bits_per_sample
        self.publish_hz = publish_hz
        self.link = link or LinkBudget()
        self._frames_published = 0
        self._bytes_published = 0

    # -- the arithmetic that justifies the architecture --------------------

    @property
    def raw_kbit_s(self) -> float:
        return self.sample_rate_hz * self.bits_per_sample / 1000.0

    def build_frame(self, t_sec: float, order_features: Dict[str, float],
                    misfire_report: Any = None) -> EdgeFeatureFrame:
        ratios: List[float] = []
        cyl = 0
        rate = 0.0
        code = 0
        if misfire_report is not None:
            ratios = [float(v) for _, v in
                      sorted(getattr(misfire_report, "contribution_ratio", {}).items())]
            cyl = int(getattr(misfire_report, "cylinder", None) or 0)
            rate = float(getattr(misfire_report, "misfire_rate", 0.0))
            code = self._VERDICT_CODES.get(getattr(misfire_report, "verdict", "NOMINAL"), 0)
        return EdgeFeatureFrame(
            t_sec=t_sec,
            order_05=float(order_features.get("ORDER_0.5_FRAC", 0.0)),
            order_1=float(order_features.get("ORDER_1_FRAC", 0.0)),
            order_2=float(order_features.get("ORDER_2_FRAC", 0.0)),
            order_4=float(order_features.get("ORDER_4_FRAC", 0.0)),
            crest_factor=float(order_features.get("ORDER_CREST_FACTOR", 0.0)),
            kurtosis=float(order_features.get("ORDER_KURTOSIS", 0.0)),
            per_cylinder_ratio=ratios,
            misfire_cylinder=cyl,
            misfire_rate=rate,
            verdict_code=code,
        )

    def publish(self, frame: EdgeFeatureFrame) -> bytes:
        payload = frame.pack()
        self._frames_published += 1
        self._bytes_published += len(payload)
        return payload

    def bandwidth_report(self, frame: Optional[EdgeFeatureFrame] = None) -> dict:
        """Raw versus compressed versus what the link actually has spare."""
        frame_bytes = frame.size_bytes if frame else 40
        compressed_kbit_s = frame_bytes * 8 * self.publish_hz / 1000.0
        available = self.link.available_for_engine_kbit_s
        return {
            "raw_kbit_s": round(self.raw_kbit_s, 1),
            "compressed_kbit_s": round(compressed_kbit_s, 3),
            "compression_ratio": round(self.raw_kbit_s / max(compressed_kbit_s, 1e-9), 1),
            "frame_bytes": frame_bytes,
            "publish_hz": self.publish_hz,
            "link_total_kbit_s": self.link.total_kbit_s,
            "link_available_for_engine_kbit_s": round(available, 1),
            "raw_fits_in_link": self.raw_kbit_s <= available,
            "compressed_fits_in_link": compressed_kbit_s <= available,
            "raw_over_budget_by_x": round(self.raw_kbit_s / max(available, 1e-9), 1),
            "link_utilisation_pct": round(100.0 * compressed_kbit_s / max(available, 1e-9), 2),
            "verdict": (
                f"Raw crank data needs {self.raw_kbit_s:.0f} kbit/s but only "
                f"{available:.0f} kbit/s is spare — it cannot be downlinked. "
                f"Features need {compressed_kbit_s:.2f} kbit/s, "
                f"{100.0 * compressed_kbit_s / max(available, 1e-9):.1f}% of what is spare. "
                f"The analysis has to happen onboard."
            ),
        }

    @property
    def published_kbit_s(self) -> float:
        return self._bytes_published * 8 / 1000.0


@dataclass
class PowerBudget:
    """What the edge analytics costs the aircraft, in endurance.

    A defence reviewer will ask what the box weighs and what it draws. Answering
    'a few watts' is not an answer; this turns it into minutes of loiter.
    """

    compute_watts: float = 8.0
    sensor_watts: float = 1.5
    battery_wh: float = 450.0
    nominal_endurance_hours: float = 18.0

    @property
    def total_watts(self) -> float:
        return self.compute_watts + self.sensor_watts

    def endurance_cost(self) -> dict:
        energy_wh = self.total_watts * self.nominal_endurance_hours
        fraction = energy_wh / max(self.battery_wh, 1e-9)
        # Electrical load is carried by the alternator, so the real cost is the
        # fuel burned to generate it rather than battery depletion; a 30%
        # alternator-to-shaft efficiency is a conservative assumption.
        shaft_watts = self.total_watts / 0.30
        return {
            "compute_w": self.compute_watts,
            "sensors_w": self.sensor_watts,
            "total_w": round(self.total_watts, 2),
            "energy_per_sortie_wh": round(energy_wh, 1),
            "battery_fraction_if_unpowered": round(fraction, 3),
            "shaft_power_required_w": round(shaft_watts, 1),
            "endurance_penalty_min": round(
                self.nominal_endurance_hours * 60.0 * (shaft_watts / 55000.0), 2),
            "note": ("Cost is stated against a 55 kW cruise shaft power. The "
                     "analytics must buy back more endurance in avoided aborts "
                     "than it spends here."),
        }


class LatencyBudget:
    """Measured pipeline latency. 'Real-time' is a number or it is nothing."""

    def __init__(self, deadline_ms: float = 50.0) -> None:
        self.deadline_ms = deadline_ms
        self._samples: List[float] = []

    def time_call(self, fn: Callable[[], Any]) -> Tuple[Any, float]:
        t0 = time.perf_counter()
        result = fn()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        self._samples.append(dt_ms)
        return result, dt_ms

    def report(self) -> dict:
        if not self._samples:
            return {"samples": 0}
        s = sorted(self._samples)
        n = len(s)
        pct = lambda p: s[min(n - 1, int(p * n))]
        worst = s[-1]
        return {
            "samples": n,
            "mean_ms": round(sum(s) / n, 3),
            "median_ms": round(pct(0.50), 3),
            "p95_ms": round(pct(0.95), 3),
            "p99_ms": round(pct(0.99), 3),
            "worst_observed_ms": round(worst, 3),
            "deadline_ms": self.deadline_ms,
            "deadline_met": worst <= self.deadline_ms,
            "margin_ms": round(self.deadline_ms - worst, 3),
            "note": ("Worst observed, not worst case. A hard real-time claim needs "
                     "static WCET analysis on the target hardware; this is a "
                     "measurement on a development machine and is labelled as such."),
        }
