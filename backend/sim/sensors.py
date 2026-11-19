"""Sensor layer (card M1-13, R 21.2 sensors.py, S01-S07). The engine is healthy in a sensor fault: only the
measurement changes, so related channels do not move (that is how it is told apart from a process fault).
Each channel has its own seeded random stream (R 3.12) so a fault on one sensor never changes another's noise.
  S01 freeze: holds the last good value      S02 bias: constant offset       S03 drift: offset grows with time
  S04 noise: sigma x gain                    S05 dropout: no value (None)     S06 out of range: impossible value
  S07 lane split: lane B disagrees with lane A (published as <channel>.lane_b)
"""
from __future__ import annotations

import random
import zlib
from typing import Any, Dict, Iterable, Optional

from backend.sim.params import physics_values

KIND = {"temperature": ("cht", "egt", "oil_t", "coolant_t", "gearbox_t", "charge_t"),
        "pressure": ("oil_p", "fuel_p", "rail_p", "map_kpa"), "rpm": ("rpm", "prop_rpm"),
        "flow": ("fuel_flow",), "electrical": ("bus_v", "batt_i", "alt_i")}


def _kind(channel: str) -> Optional[str]:
    base = channel.split("[")[0]
    return next((k for k, names in KIND.items() if base in names), None)


class SensorLayer:
    def __init__(self, engine_id: str, seed: int) -> None:
        self.ph = physics_values(engine_id, "sensors")
        self.seed = seed
        self._rng: Dict[str, random.Random] = {}
        self._frozen: Dict[str, float] = {}

    def _rand(self, channel: str) -> random.Random:
        if channel not in self._rng:
            self._rng[channel] = random.Random(self.seed * 1_000_003 + zlib.crc32(channel.encode()))
        return self._rng[channel]

    def sigma(self, channel: str, value: float) -> float:
        k, ph = _kind(channel), self.ph
        if k == "temperature":
            return ph["noise_temperature_c"]
        if k == "pressure":
            return ph["noise_pressure_rel"] * abs(value)
        if k == "rpm":
            return ph["noise_rpm"]
        if k == "flow":
            return ph["noise_flow_rel"] * abs(value)
        if k == "electrical":
            return ph["noise_electrical_rel"] * abs(value)
        return 0.0

    def measure(self, true_values: Dict[str, Optional[float]], t_s: float,
                sensor_faults: Iterable[Dict[str, Any]] = ()) -> Dict[str, Any]:
        """true values -> measured values (+ '<ch>.lane_b' entries for S07). Unknown channels pass through noiseless."""
        by_channel: Dict[str, Dict[str, Any]] = {}
        for f in sensor_faults:
            by_channel.setdefault(f["channel"], {}).update({e: f for e in f["effects"]})
        out: Dict[str, Any] = {}
        ph = self.ph
        for ch, v in true_values.items():
            if v is None:
                out[ch] = None
                continue
            faults = by_channel.get(ch, {})
            sev = lambda e: faults[e]["severity"] if e in faults else 0.0          # noqa: E731
            if "dropout" in faults and sev("dropout") >= 0.5:
                out[ch] = None
                continue
            noise = self.sigma(ch, v) * (1 + (ph["noise_gain_s04"] - 1) * sev("noise"))
            m = v + self._rand(ch).gauss(0.0, noise) if noise > 0 else v
            m += ph["bias_rel_s02"] * abs(v) * sev("bias")
            if "drift" in faults:
                minutes = max(0.0, t_s - float(faults["drift"]["t0_s"])) / 60.0
                m += ph["drift_rel_per_min_s03"] * abs(v) * minutes * sev("drift")
            if "out_of_range" in faults and sev("out_of_range") >= 0.5:
                m = v * ph["out_of_range_factor_s06"] if v else ph["out_of_range_factor_s06"]
            if "freeze" in faults and sev("freeze") >= 0.5:
                m = self._frozen.setdefault(ch, m)
            else:
                self._frozen.pop(ch, None)
            out[ch] = m
            if "lane_split" in faults:
                out[f"{ch}.lane_b"] = m * (1 + ph["lane_split_rel_s07"] * sev("lane_split"))
        return out
