"""Electrical system: alternators, regulator, battery state of charge, bus loads (card M1-08, R 21.4, P 1.3h).

  alternator current available = I_rated * clamp((rpm - cut_in) / (full - cut_in), 0, 1) * health      (F32)
  supply covers load + charge  -> bus = regulator setpoint (+ F33 offset); battery charges (limited)
  supply short of load         -> battery supplies the rest; bus = OCV(SOC) - I_batt * R_int / health   (F34)
  SOC integrates the battery current over its capacity (capacity also scales with battery health).
Installation data comes from configs/installations/electrical.json (per engine id, else 'default').
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]


def _v(block: Dict[str, Any]) -> float:
    return float(block["value"])


@dataclass
class Alternator:
    name: str
    rated_a: float
    cut_in_rpm: float
    full_rpm: float

    def available_a(self, rpm: float, health: float) -> float:
        frac = (rpm - self.cut_in_rpm) / max(self.full_rpm - self.cut_in_rpm, 1.0)
        return self.rated_a * min(1.0, max(0.0, frac)) * max(0.0, health)


@dataclass
class Electrical:
    alternators: List[Alternator]
    regulator_v: float
    capacity_ah: float
    ocv_full: float
    ocv_empty: float
    r_int: float
    charge_limit_a: float
    load_w: float
    soc: float = 1.0
    bus_v: float = 0.0
    alternator_a: float = 0.0
    battery_a: float = 0.0              # + charging, - discharging
    load_a: float = 0.0
    per_alternator_a: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def for_engine(cls, engine_id: str) -> "Electrical":
        data = json.loads((ROOT / "configs" / "installations" / "electrical.json").read_text(encoding="utf-8"))
        block = {**data["default"], **data.get(engine_id, {})}
        alts = [Alternator(a["name"], _v(a["rated_a"]), _v(a["cut_in_rpm"]), _v(a["full_output_rpm"]))
                for a in block["alternators"]]
        e = cls(alternators=alts, regulator_v=_v(block["regulator_setpoint_v"]),
                capacity_ah=_v(block["battery_capacity_ah"]), ocv_full=_v(block["battery_ocv_full_v"]),
                ocv_empty=_v(block["battery_ocv_empty_v"]), r_int=_v(block["battery_internal_ohm"]),
                charge_limit_a=_v(block["battery_charge_limit_a"]), load_w=_v(block["load_w"]))
        e.bus_v = e.ocv(1.0)
        return e

    def ocv(self, soc: float) -> float:
        return self.ocv_empty + (self.ocv_full - self.ocv_empty) * min(1.0, max(0.0, soc))

    def step(self, dt: float, rpm: float, alternator_health: float = 1.0, regulator_offset_v: float = 0.0,
             battery_health: float = 1.0, extra_load_w: float = 0.0) -> None:
        self.per_alternator_a = {a.name: a.available_a(rpm, alternator_health) for a in self.alternators}
        available = sum(self.per_alternator_a.values())
        reg_v = self.regulator_v + regulator_offset_v
        load = self.load_w + extra_load_w
        r = self.r_int / max(battery_health, 0.05)
        cap_as = self.capacity_ah * 3600.0 * max(battery_health, 0.05)
        load_at_reg = load / reg_v
        if available > 0 and available >= load_at_reg:
            # regulated bus; the battery takes what is left, limited by its acceptance and by OCV vs bus
            accept = max(0.0, (reg_v - self.ocv(self.soc)) / r)
            self.battery_a = min(available - load_at_reg, self.charge_limit_a, accept)
            self.bus_v = reg_v
            self.alternator_a = load_at_reg + self.battery_a
        else:
            # battery supplies the shortfall: solve V = OCV - I r with I = load/V - available
            v = self.ocv(self.soc)
            for _ in range(20):
                i_b = max(0.0, load / max(v, 1.0) - available)
                v = self.ocv(self.soc) - i_b * r
            self.battery_a = -max(0.0, load / max(v, 1.0) - available)
            self.bus_v = v
            self.alternator_a = available
        self.load_a = load / max(self.bus_v, 1.0)
        self.soc = min(1.0, max(0.0, self.soc + self.battery_a * dt / cap_as))
