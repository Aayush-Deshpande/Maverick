"""
Fuel thermal management and cold-fuel risk — F42.

At 28,000 ft the ambient is around -40 C, and a MALE UAV loiters there for
hours. For a kerosene-burning compression-ignition engine (AE300 on TAPAS) this
creates a failure chain that simply does not exist for an AVGAS spark engine,
and that nobody in this field models:

    fuel cools toward ambient during a long high-altitude loiter
        -> below the CLOUD POINT, paraffin wax begins to crystallise
        -> at the CFPP (cold filter plugging point) crystals block the filter
        -> filter differential pressure rises, supply pressure falls
        -> injection system is starved

The observable that matters is not a temperature limit, it is a **margin**:
how many degrees of cooling remain before wax starts forming, given the fuel's
own cloud point. That is a live, physically-grounded, altitude-specific health
indicator, and it is computed from channels an aircraft already has (fuel
temperature, filter dP, OAT).

The second mechanism is cold-soaked injectors. Common-rail injectors hold
micron-level clearances; cold metal contraction increases the hydraulic force
needed to lift the needle, degrading injected quantity and timing. This is a
*restart* risk after a long cold loiter — precisely the endurance mission the
problem statement names.

Fuel property defaults are for Jet A-1 (DEF STAN 91-091 / ASTM D1655): max
freeze point -47 C. Cloud point is typically a few degrees above freeze point.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

__all__ = ["FuelProperties", "FuelThermalState", "FuelThermalModel", "JET_A1", "AVGAS_100LL"]


@dataclass(frozen=True)
class FuelProperties:
    name: str
    cloud_point_c: Optional[float]  # wax onset; None for gasoline-type fuels
    cfpp_c: Optional[float]  # cold filter plugging point
    freeze_point_c: Optional[float]
    density_kg_m3: float = 800.0
    specific_heat_j_kgk: float = 2010.0
    waxing_possible: bool = True
    source: str = ""


JET_A1 = FuelProperties(
    name="JET_A1",
    cloud_point_c=-42.0,
    cfpp_c=-47.0,
    freeze_point_c=-47.0,
    density_kg_m3=804.0,
    specific_heat_j_kgk=2010.0,
    waxing_possible=True,
    source="DEF STAN 91-091 / ASTM D1655 max freeze point -47 C",
)

AVGAS_100LL = FuelProperties(
    name="AVGAS_100LL",
    cloud_point_c=None,
    cfpp_c=None,
    freeze_point_c=-58.0,
    density_kg_m3=720.0,
    specific_heat_j_kgk=2100.0,
    waxing_possible=False,  # gasoline does not wax; vapour lock is its risk
    source="ASTM D910",
)


@dataclass
class FuelThermalState:
    fuel_temp_c: float = 15.0
    cloud_point_margin_c: float = float("inf")
    cfpp_margin_c: float = float("inf")
    wax_fraction: float = 0.0  # 0..1 proxy for crystallised wax in the filter
    filter_dp_kpa: float = 2.0
    supply_pressure_ratio: float = 1.0  # 1.0 = unrestricted
    injector_cold_soak_factor: float = 1.0  # 1.0 = nominal delivery
    risk: str = "NONE"  # NONE | ADVISORY | CAUTION | WARNING

    def as_dict(self) -> dict:
        return {
            "FUEL_TEMP_C": round(self.fuel_temp_c, 2),
            "FUEL_CLOUD_MARGIN_C": (None if math.isinf(self.cloud_point_margin_c)
                                    else round(self.cloud_point_margin_c, 2)),
            "FUEL_CFPP_MARGIN_C": (None if math.isinf(self.cfpp_margin_c)
                                   else round(self.cfpp_margin_c, 2)),
            "FUEL_WAX_FRACTION": round(self.wax_fraction, 4),
            "FUEL_FILTER_DP_KPA": round(self.filter_dp_kpa, 3),
            "FUEL_SUPPLY_P_RATIO": round(self.supply_pressure_ratio, 4),
            "INJECTOR_COLD_FACTOR": round(self.injector_cold_soak_factor, 4),
            "FUEL_COLD_RISK": self.risk,
        }


class FuelThermalModel:
    """First-order fuel bulk temperature with wax formation and filter blockage.

    The tank is treated as a lumped thermal mass exchanging with ambient, warmed
    by engine return flow (common-rail systems return a large fraction of lifted
    fuel, which is the main thing keeping fuel warm on a long cold cruise) and by
    any tank heater.
    """

    def __init__(
        self,
        properties: FuelProperties = JET_A1,
        tank_mass_kg: float = 90.0,
        ua_w_per_k: float = 55.0,
        return_flow_heat_w: float = 700.0,
        nominal_filter_dp_kpa: float = 2.0,
    ) -> None:
        self.props = properties
        self.tank_mass_kg = tank_mass_kg
        self.ua_w_per_k = ua_w_per_k
        self.return_flow_heat_w = return_flow_heat_w
        self.nominal_filter_dp_kpa = nominal_filter_dp_kpa
        self.state = FuelThermalState()
        self._heater_w = 0.0

    def set_heater(self, watts: float) -> None:
        self._heater_w = max(0.0, watts)

    def update(
        self,
        dt_sec: float,
        oat_c: float,
        engine_running: bool = True,
        fuel_mass_kg: Optional[float] = None,
        power_fraction: float = 1.0,
    ) -> FuelThermalState:
        s = self.state
        mass = max(fuel_mass_kg if fuel_mass_kg is not None else self.tank_mass_kg, 1.0)

        # Lumped thermal balance: loss to ambient, gain from return flow + heater.
        q_loss = self.ua_w_per_k * (s.fuel_temp_c - oat_c)
        q_gain = (self.return_flow_heat_w * max(0.0, power_fraction)) if engine_running else 0.0
        q_gain += self._heater_w
        dT = (q_gain - q_loss) * dt_sec / (mass * self.props.specific_heat_j_kgk)
        s.fuel_temp_c += dT

        # Margins. Infinite for fuels that cannot wax, so an AVGAS engine never
        # reports a meaningless cold-fuel indication.
        if self.props.waxing_possible and self.props.cloud_point_c is not None:
            s.cloud_point_margin_c = s.fuel_temp_c - self.props.cloud_point_c
            s.cfpp_margin_c = s.fuel_temp_c - (self.props.cfpp_c or self.props.cloud_point_c)
        else:
            s.cloud_point_margin_c = float("inf")
            s.cfpp_margin_c = float("inf")

        # Wax fraction grows once below cloud point, saturating by CFPP.
        if self.props.waxing_possible and self.props.cloud_point_c is not None:
            cp = self.props.cloud_point_c
            cfpp = self.props.cfpp_c if self.props.cfpp_c is not None else cp - 5.0
            span = max(cp - cfpp, 1e-3)
            if s.fuel_temp_c >= cp:
                # Wax redissolves on rewarming, but not instantly.
                s.wax_fraction = max(0.0, s.wax_fraction - 0.02 * dt_sec / 60.0)
            else:
                target = min(1.0, (cp - s.fuel_temp_c) / span)
                s.wax_fraction += (target - s.wax_fraction) * min(1.0, dt_sec / 120.0)
                s.wax_fraction = min(1.0, max(0.0, s.wax_fraction))
        else:
            s.wax_fraction = 0.0

        # Filter blockage: dP rises steeply as wax accumulates.
        s.filter_dp_kpa = self.nominal_filter_dp_kpa * (1.0 + 18.0 * s.wax_fraction ** 2)
        s.supply_pressure_ratio = 1.0 / (1.0 + 4.0 * s.wax_fraction ** 2)

        # Cold-soaked injector: needle lift degrades as the body contracts.
        if s.fuel_temp_c < 0.0:
            deficit = min(1.0, (-s.fuel_temp_c) / 60.0)
            s.injector_cold_soak_factor = 1.0 - 0.22 * deficit ** 1.5
        else:
            s.injector_cold_soak_factor = 1.0

        s.risk = self._classify(s)
        return s

    @staticmethod
    def _classify(s: FuelThermalState) -> str:
        if math.isinf(s.cloud_point_margin_c):
            return "NONE"
        if s.wax_fraction > 0.25 or s.cfpp_margin_c <= 0.0:
            return "WARNING"
        if s.cloud_point_margin_c <= 0.0:
            return "CAUTION"
        if s.cloud_point_margin_c <= 8.0:
            return "ADVISORY"
        return "NONE"

    def restart_risk(self) -> dict:
        """Can the engine be relit after this cold soak?

        Reported as a fraction of nominal injected quantity plus a plain verdict,
        because "will it restart" is the operator's actual question during a
        high-altitude descent after a long loiter.
        """
        s = self.state
        delivery = s.injector_cold_soak_factor * s.supply_pressure_ratio
        if delivery >= 0.92:
            verdict = "NOMINAL"
        elif delivery >= 0.80:
            verdict = "DEGRADED_START"
        elif delivery >= 0.65:
            verdict = "MARGINAL"
        else:
            verdict = "RESTART_NOT_ASSURED"
        return {
            "delivery_fraction": round(delivery, 4),
            "verdict": verdict,
            "fuel_temp_c": round(s.fuel_temp_c, 2),
            "wax_fraction": round(s.wax_fraction, 4),
        }
