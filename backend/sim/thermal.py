"""Heads, exhaust, coolant loop, oil system and gearbox as lumped heat balances (card M1-07, R 21.4).

Per cylinder i (fuel energy Q_i = mdot_f,i * LHV, burnt share q_i):
  C_h dCHT_i/dt = f_wall q_i Q_i - G_hc (CHT_i - T_c) - G_ha s_air eff_i (CHT_i - T_amb)
  EGT_i = T_man + (q_i Q_i - W_i - f_wall q_i Q_i) / (mdot_exh,i cp_exh), first-order lag
Coolant: C_c dT_c/dt = sum G_hc (CHT_i - T_c) - G_rad s_air rad flow (T_c - T_amb)
Oil:     C_o dT_o/dt = s_f P_friction + f_oil sum q_i Q_i - G_oil s_air cooler (T_o - T_amb)
         p_oil = min(p_relief, k * rpm * pump_health * mu(T_o) / mu_ref)   (Vogel viscosity)
         below the minimum pressure the bearing friction rises (boundary lubrication): the seizure chain
Gearbox: C_g dT_g/dt = (1 - eta_gear) P_brake - G_g s_air (T_g - T_amb)
s_air = (rho V / rho_cal V_cal)^0.8 scales every air-side conductance (hot day, altitude, slow flight run hotter).
Conductances and capacities are CALIBRATED once per engine (R 21.5 step 4): at max continuous power, ISA+15 and the
design airspeed the temperatures sit at the targets in configs/physics; time constants come from the same file.
Faults act only through the health inputs (F19 cooling_eff, F20 coolant_flow, F21 radiator, F23 pump_health,
F25 oil_cooler, F27 gear_loss).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from backend.sim.atmosphere import Atmosphere
from backend.sim.params import physics_values

KELVIN = 273.15


@dataclass
class HeatInputs:
    rpm: float
    fuel_kg_s: Sequence[float]            # per cylinder
    burnt: Sequence[float]                # per cylinder 0..1 (misfire 0)
    indicated_w: Sequence[float]          # per cylinder
    exhaust_kg_s: Sequence[float]         # per cylinder (air + fuel)
    friction_w: float
    brake_w: float
    manifold_t_k: float


def oil_viscosity_mpas(t_c: float, a: float, b: float, c: float) -> float:
    return a * math.exp(b / (t_c + c))


@dataclass
class Thermal:
    n_cyl: int
    lhv: float
    ph: Dict[str, float]
    oil: Dict[str, float]
    rho_v_cal: float = 0.0
    g_hc: float = 0.0
    g_ha: float = 0.0
    g_rad: float = 0.0
    g_oil: float = 0.0
    g_gear: float = 0.0
    c_head: float = 0.0
    c_cool: float = 0.0
    c_oil: float = 0.0
    c_gear: float = 0.0
    k_pump: float = 0.0
    mu_ref: float = 1.0
    cht: List[float] = field(default_factory=list)
    egt: List[float] = field(default_factory=list)
    coolant_c: float = 0.0
    oil_c: float = 0.0
    gearbox_c: float = 0.0
    oil_bar: float = 0.0
    friction_multiplier: float = 1.0

    @classmethod
    def for_engine(cls, cfg: Any, lhv_j_kg: float) -> "Thermal":
        return cls(n_cyl=cfg.cylinder_count, lhv=lhv_j_kg, ph=physics_values(cfg.engine_id, "thermal"),
                   oil=physics_values(cfg.engine_id, "oil"))

    # -- helpers -------------------------------------------------------------------------------------------
    def _mu(self, t_c: float) -> float:
        return oil_viscosity_mpas(t_c, self.oil["vogel_a_mpas"], self.oil["vogel_b"], self.oil["vogel_c"])

    def _opening(self, t_c: float, open_c: float, full_c: float, stuck: Optional[str]) -> float:
        """Thermostat opening 0..1 (F22: stuck OPEN or CLOSED overrides it)."""
        lo = self.ph["thermostat_min_open"]
        if stuck == "OPEN":
            return 1.0
        if stuck == "CLOSED":
            return lo
        return min(1.0, max(lo, (t_c - open_c) / (full_c - open_c)))

    def _air_scale(self, atm: Atmosphere, tas_kt: float) -> float:
        return (max(atm.density_kg_m3 * max(tas_kt, 1.0), 1e-6) / self.rho_v_cal) ** self.ph["cooling_flow_exponent"]

    def oil_pressure_bar(self, rpm: float, oil_c: float, pump_health: float = 1.0) -> float:
        return min(self.oil["relief_bar"], self.k_pump * max(rpm, 0.0) * pump_health * self._mu(oil_c) / self.mu_ref)

    # -- calibration (R 21.5 step 4) -----------------------------------------------------------------------
    def calibrate(self, h: HeatInputs, atm: Atmosphere, tas_kt: float, rated_rpm: float) -> None:
        ph = self.ph
        ta = atm.temperature_k - KELVIN
        tc, to, tg = ph["target_coolant_c"], ph["target_oil_c"], ph["target_gearbox_c"]
        th = tc + ph["target_head_minus_coolant_c"]
        q_cyl = h.fuel_kg_s[0] * self.lhv * h.burnt[0]
        wall = ph["wall_heat_fraction"] * q_cyl
        x = ph["head_to_coolant_fraction"]
        self.rho_v_cal = atm.density_kg_m3 * tas_kt
        self.g_hc = x * wall / (th - tc)
        self.g_ha = (1 - x) * wall / (th - ta)
        self.g_rad = self.n_cyl * x * wall / (tc - ta)
        q_oil = ph["oil_friction_heat_fraction"] * h.friction_w + ph["oil_fuel_heat_fraction"] * q_cyl * self.n_cyl
        self.g_oil = q_oil / (to - ta)
        self.g_gear = (1 - ph["gear_efficiency"]) * h.brake_w / (tg - ta)
        self.c_head = ph["tau_head_s"] * (self.g_hc + self.g_ha)
        self.c_cool = ph["tau_coolant_s"] * self.g_rad
        self.c_oil = ph["tau_oil_s"] * self.g_oil
        self.c_gear = ph["tau_gearbox_s"] * self.g_gear
        self.mu_ref = self._mu(to)
        self.k_pump = self.oil["calibration_pressure_bar"] / (self.oil["calibration_rpm_fraction"] * rated_rpm)
        self.cht = [th] * self.n_cyl
        self.egt = [self._egt_target(h, i) for i in range(self.n_cyl)]
        self.coolant_c, self.oil_c, self.gearbox_c = tc, to, tg
        self.oil_bar = self.oil_pressure_bar(h.rpm, to)

    def _egt_target(self, h: HeatInputs, i: int) -> float:
        q = h.fuel_kg_s[i] * self.lhv * h.burnt[i]
        q_exh = max(0.0, q - h.indicated_w[i] - self.ph["wall_heat_fraction"] * q)
        return h.manifold_t_k - KELVIN + q_exh / max(h.exhaust_kg_s[i] * self.ph["exhaust_cp_j_kgk"], 1e-9)

    # -- dynamics ------------------------------------------------------------------------------------------
    def step(self, dt: float, h: HeatInputs, atm: Atmosphere, tas_kt: float,
             health: Optional[Dict[str, Any]] = None) -> None:
        hl = health or {}
        cooling_eff = hl.get("cooling_eff") or [1.0] * self.n_cyl
        s = self._air_scale(atm, tas_kt)
        ta = atm.temperature_k - KELVIN
        f_wall = self.ph["wall_heat_fraction"]
        to_coolant = 0.0
        fuel_heat = 0.0
        for i in range(self.n_cyl):
            q = h.fuel_kg_s[i] * self.lhv * h.burnt[i]
            fuel_heat += q
            q_hc = self.g_hc * hl.get("coolant_flow", 1.0) * (self.cht[i] - self.coolant_c)
            q_ha = self.g_ha * s * cooling_eff[i] * (self.cht[i] - ta)
            self.cht[i] += dt * (f_wall * q - q_hc - q_ha) / self.c_head
            to_coolant += q_hc
            target = self._egt_target(h, i)
            self.egt[i] = target + (self.egt[i] - target) * math.exp(-dt / self.ph["tau_egt_s"])
        rad_open = self._opening(self.coolant_c, self.ph["coolant_thermostat_open_c"],
                                 self.ph["coolant_thermostat_full_c"], hl.get("coolant_thermostat_stuck"))
        q_rad = (self.g_rad * s * rad_open * hl.get("radiator", 1.0) * hl.get("coolant_flow", 1.0) *
                 (self.coolant_c - ta))
        self.coolant_c += dt * (to_coolant - q_rad) / self.c_cool
        q_oil_in = (self.ph["oil_friction_heat_fraction"] * h.friction_w * self.friction_multiplier +
                    self.ph["oil_fuel_heat_fraction"] * fuel_heat)
        oil_open = self._opening(self.oil_c, self.ph["oil_thermostat_open_c"], self.ph["oil_thermostat_full_c"],
                                 hl.get("oil_thermostat_stuck"))
        self.oil_c += dt * (q_oil_in - self.g_oil * s * oil_open * hl.get("oil_cooler", 1.0) * (self.oil_c - ta)) / self.c_oil
        gear_loss = (1 - self.ph["gear_efficiency"]) * h.brake_w * hl.get("gear_loss", 1.0)
        self.gearbox_c += dt * (gear_loss - self.g_gear * s * (self.gearbox_c - ta)) / self.c_gear
        self.oil_bar = self.oil_pressure_bar(h.rpm, self.oil_c, hl.get("pump_health", 1.0))
        p_min = hl.get("oil_p_min_bar")
        deficit = 0.0 if not p_min else max(0.0, (p_min - self.oil_bar) / p_min)
        self.friction_multiplier = 1.0 + self.oil["low_pressure_friction_gain"] * deficit ** 2
