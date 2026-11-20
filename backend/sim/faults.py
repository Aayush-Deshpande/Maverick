"""Registry faults -> plant parameters (card M1-13, R 21.6, P Part 0 D3).

Every active fault contributes its registry `parameter_effects` (configs/faults.json) at its effective severity
  s(t) = severity * min(1, (t - t0) / ramp_s)        (simulated seconds; D8)
  scale: factor = 1 + (v - 1) s        add: delta = v s        set: value = default + (v - default) s
The result is the `health` dict that backend/sim/plant.py consumes. Faults NEVER edit an output: readings move only
because the equations run with these parameters. The vocabulary on the left (component.parameter) is the registry's;
the mapping below connects it to the model's inputs. Sensor faults (S01-S07) are returned separately for the sensor
layer (backend/sim/sensors.py): the engine itself is healthy.
"""
from __future__ import annotations

import math

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from backend.sim.params import physics_values

_IDX = re.compile(r"^(?P<name>[a-z_]+)\[\{cyl\}\]$")
SET_DEFAULTS = {"quality": 1.0, "injector_flow": 1.0, "lane_a_ok": 1.0, "lane_b_ok": 1.0, "glow_plug_ok": 1.0,
                "tooth_damage": 0.0, "prop_imbalance": 0.0, "leak": 0.0}


def effective_severity(fault: Any, t_s: float) -> float:
    ramp = max(float(fault.ramp_s), 1e-9)
    return float(fault.severity) * min(1.0, max(0.0, (t_s - float(fault.t0_s)) / ramp))


def ramp_integral_h(fault: Any, t_s: float) -> float:
    """Integral of s(t) over time, in hours (leak volumes)."""
    el = max(0.0, t_s - float(fault.t0_s))
    ramp = max(float(fault.ramp_s), 1e-9)
    integral = el * el / (2 * ramp) if el < ramp else ramp / 2 + (el - ramp)
    return float(fault.severity) * integral / 3600.0


def _value(op: str, v: float, s: float, default: float) -> float:
    if op == "scale":
        return 1.0 + (v - 1.0) * s
    if op == "add":
        return v * s
    return default + (v - default) * s


class FaultParameters:
    def __init__(self, cfg: Any, registry: Any) -> None:
        self.cfg = cfg
        self.registry = registry
        self.n = cfg.cylinder_count
        self.fx = physics_values(cfg.engine_id, "fault_effects")
        self.oil_capacity_l = float(cfg.oil_capacity_l or 0.0)

    def health(self, active: Iterable[Any], t_s: float, combustion: Any = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        n, fx = self.n, self.fx
        h: Dict[str, Any] = {"quality": [1.0] * n, "late_burn": [1.0] * n, "injector": [1.0] * n, "turbo": {}, "fuel": {}, "thermal": {},
                             "electrical": {}, "vibration": {}, "egt_factor": [1.0] * n, "glow_failed": [False] * n}
        sensor_faults: List[Dict[str, Any]] = []
        oil_lost_l = 0.0
        for f in active:
            spec = self.registry.get(f.fault_id)
            s = effective_severity(f, t_s)
            if spec.kind == "SENSOR":
                sensor_faults.append({"fault_id": f.fault_id, "channel": f.channel, "severity": s, "t0_s": f.t0_s,
                                      "effects": [e["parameter"].split(".")[-1] for e in spec.raw["parameter_effects"]]})
                continue
            for e in spec.raw["parameter_effects"]:
                comp, param, op, v = e["component"], e["parameter"], e["op"], float(e["at_full_severity"])
                m = _IDX.match(param)
                name = m.group("name") if m else param
                cyls = [f.cylinder - 1] if (m and f.cylinder) else list(range(n)) if m else []
                val = _value(op, v, s, SET_DEFAULTS.get(name, 1.0))
                if op == "add" and name == "leak_rate_l_per_h":
                    oil_lost_l += v * ramp_integral_h(f, t_s)
                    continue
                self._apply(h, comp, name, op, val, v, s, cyls, combustion)
        if oil_lost_l > 0:
            h["oil_lost_l"] = oil_lost_l            # always recorded; starvation needs the oil capacity (config)
        if oil_lost_l > 0 and self.oil_capacity_l > 0:
            remaining = max(0.0, self.oil_capacity_l - oil_lost_l)
            h["oil_qty_l"] = remaining
            starve = fx["oil_starvation_fraction"] * self.oil_capacity_l
            if remaining < starve:
                h["thermal"]["pump_health"] = h["thermal"].get("pump_health", 1.0) * remaining / starve
        return h, sensor_faults

    def _apply(self, h: Dict[str, Any], comp: str, name: str, op: str, val: float, v: float, s: float,
               cyls: List[int], combustion: Any) -> None:
        fx, th, tb, fu, el, vb = self.fx, h["thermal"], h["turbo"], h["fuel"], h["electrical"], h["vibration"]
        mul = lambda d, k, x: d.__setitem__(k, d.get(k, 1.0) * x)        # noqa: E731
        if name == "quality":
            for c in cyls:
                h["quality"][c] *= val
        elif name == "compression_health":             # leak: part of the charge escapes (less burns) and the rest
            for c in cyls:                              # burns at a lower effective compression ratio (lost work
                h["quality"][c] *= math.sqrt(val)       # leaves as exhaust heat)
                h["late_burn"][c] *= math.sqrt(val)
        elif name == "cycle_variation":
            h["cov_factor"] = max(h.get("cov_factor", 1.0), val)
            for c in cyls:
                h["quality"][c] *= 1.0 - fx["cycle_variation_quality_loss"] * (val - 1.0)
                h.setdefault("cov_cylinders", set()).add(c)
        elif name == "burn_duration":
            loss = combustion.timing_factor((val - 1.0) * fx["burn_duration_deg_per_unit"]) if combustion else 1.0
            for c in cyls:                        # the fuel still burns, late in the expansion: work falls and the
                h["late_burn"][c] *= loss         # lost share leaves as exhaust heat (EGT rises), not as unburnt fuel
        elif name == "glow_plug_ok":
            for c in cyls:
                h["glow_failed"][c] = h["glow_failed"][c] or val < 0.5
        elif name == "knock_margin":
            h["knock_factor"] = h.get("knock_factor", 1.0) / max(val, 1e-3)
        elif name in ("lane_a_ok", "lane_b_ok"):
            if val < 0.5:
                h["lane_lost"] = True
                h["lanes_failed"] = h.get("lanes_failed", 0) + 1
        elif name == "timing_offset_deg":
            h["timing_error_deg"] = h.get("timing_error_deg", 0.0) - val      # negative offset = retard
        elif name == "injector_flow":
            for c in cyls:
                h["injector"][c] *= val
        elif name == "injector_leak":
            for c in cyls:
                h["injector"][c] += val
            mul(fu, "rail_health", 1.0 - fx["injector_leak_rail_loss"] * val)
        elif name == "hp_pump_health":
            mul(fu, "rail_health", val)
        elif name == "lp_supply_health":
            mul(fu, "supply_health", val)
        elif name == "carb_throat_area":
            h["throttle_area"] = h.get("throttle_area", 1.0) * val
        elif name == "filter_loss_coeff":
            h["filter_factor"] = h.get("filter_factor", 1.0) * val
        elif name == "charge_leak_fraction":
            tb["boost_leak"] = tb.get("boost_leak", 0.0) + val
        elif name == "wastegate_position":
            if s >= 0.5:
                tb["wastegate_stuck"] = "OPEN" if v >= 0.5 else "CLOSED"
        elif name == "bearing_friction":
            tb["bearing_wear"] = max(tb.get("bearing_wear", 0.0), s)
        elif name == "intercooler_effectiveness":
            tb["intercooler_fouling"] = max(tb.get("intercooler_fouling", 0.0), 1.0 - val)
        elif name == "air_cooling_effectiveness":
            eff = th.setdefault("cooling_eff", [1.0] * self.n)
            for c in cyls:
                eff[c] *= val
        elif name == "pump_flow_health":
            mul(th, "coolant_flow", val)
        elif name == "radiator_effectiveness":
            mul(th, "radiator", val)
        elif name == "thermostat_opening":
            if s >= 0.5:
                th["coolant_thermostat_stuck"] = "OPEN" if v >= 0.5 else "CLOSED"
        elif name == "pump_health":
            mul(th, "pump_health", val)
        elif name == "cooler_effectiveness":
            mul(th, "oil_cooler", val)
        elif name == "bearing_clearance":
            mul(th, "pump_health", val ** -fx["bearing_clearance_exponent"])
            vb["bearing_looseness"] = vb.get("bearing_looseness", 0.0) + max(0.0, val - 1.0)
        elif name == "tooth_damage":
            vb["gear_damage"] = max(vb.get("gear_damage", 0.0), val)
            mul(th, "gear_loss", 1.0 + fx["gear_damage_loss_gain"] * val)
        elif name == "prop_imbalance":
            vb["prop_imbalance"] = max(vb.get("prop_imbalance", 0.0), val)
        elif name == "mount_transmissibility":
            vb["mount_degradation"] = max(vb.get("mount_degradation", 0.0), s)
        elif name == "leak" and comp == "exhaust":
            for c in cyls:
                h["egt_factor"][c] *= 1.0 - fx["exhaust_leak_egt_drop"] * val
            tb["boost_leak"] = tb.get("boost_leak", 0.0) + fx["exhaust_leak_boost_loss"] * val
        elif name == "alternator_health":
            mul(el, "alternator_health", val)
        elif name in ("battery_capacity", "battery_resistance"):
            factor = val if name == "battery_capacity" else 1.0 / max(val, 1e-3)
            el["battery_health"] = min(el.get("battery_health", 1.0), factor)
        elif name == "regulator_setpoint_offset_v":
            el["regulator_offset_v"] = el.get("regulator_offset_v", 0.0) + val
        elif name == "governor_gain":
            h["governor_gain"] = h.get("governor_gain", 1.0) * val
        else:
            raise KeyError(f"registry parameter {comp}.{name} has no model input (backend/sim/faults.py)")
