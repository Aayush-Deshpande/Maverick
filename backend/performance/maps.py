"""Engine Performance Maps and Atmospheric Scaling (R9, B1.4, D16).

Provides:
1. BSFC (Brake Specific Fuel Consumption) mapping across (RPM, BMEP / Torque).
2. Turbocharger compressor / turbine map evaluation (pressure ratio, isentropic efficiency, surge/choke margins).
3. ISA standard atmosphere lapse rate and density altitude calculation.
4. Fuel flow and thermal efficiency estimation parameterized by EngineConfig.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import numpy as np

from backend.physics.engine_config import EngineConfig, IgnitionMode, InductionType


@dataclass
class AtmosphericState:
    altitude_m: float
    p_amb_bar: float
    t_amb_k: float
    density_kg_m3: float
    density_ratio: float


class PerformanceMaps:
    """Computes operational performance maps for any engine profile."""

    def __init__(self, cfg: EngineConfig) -> None:
        self.cfg = cfg
        self.is_turbo = cfg.induction == InductionType.TURBOCHARGED
        self.is_ci = cfg.ignition_mode == IgnitionMode.COMPRESSION

    @staticmethod
    def get_isa_atmosphere(altitude_m: float, delta_isa_c: float = 0.0) -> AtmosphericState:
        """Calculate standard atmospheric conditions up to 15,000m according to ICAO ISA."""
        alt = max(0.0, min(15000.0, altitude_m))
        t0 = 288.15 + delta_isa_c
        p0 = 1.01325  # bar
        l_rate = 0.0065  # K/m

        if alt <= 11000.0:
            t_amb = t0 - l_rate * alt
            p_amb = p0 * ((t_amb / t0) ** 5.25588)
        else:
            t_11k = t0 - l_rate * 11000.0
            p_11k = p0 * ((t_11k / t0) ** 5.25588)
            t_amb = t_11k
            p_amb = p_11k * math.exp(-9.80665 * 0.0289644 * (alt - 11000.0) / (8.31432 * t_11k))

        rho = (p_amb * 1e5) / (287.05 * t_amb)
        rho_0 = (1.01325 * 1e5) / (287.05 * 288.15)  # 1.225 kg/m3

        return AtmosphericState(
            altitude_m=alt,
            p_amb_bar=p_amb,
            t_amb_k=t_amb,
            density_kg_m3=rho,
            density_ratio=rho / rho_0,
        )

    def calculate_bsfc(self, rpm: float, power_kw: float) -> float:
        """Calculate Brake Specific Fuel Consumption (g / kWh).
        Uses sweet-spot island model calibrated to engine class (SI: ~250-310 g/kWh, CI: ~210-250 g/kWh).
        """
        if power_kw <= 0.5:
            return 800.0  # High specific consumption at idle

        power_frac = np.clip(power_kw / max(10.0, self.cfg.rated_power_kw), 0.05, 1.15)
        rpm_frac = np.clip(rpm / max(1000.0, self.cfg.rated_rpm), 0.2, 1.1)

        # Baseline minimum BSFC at sweet spot (typically ~70% load, 75% RPM)
        base_bsfc = self.cfg.nominal_bsfc_g_kwh or (220.0 if self.is_ci else 275.0)

        # Departure from sweet spot
        delta_power = (power_frac - 0.70) ** 2
        delta_rpm = (rpm_frac - 0.75) ** 2

        bsfc = base_bsfc + 180.0 * delta_power + 120.0 * delta_rpm
        return float(np.clip(bsfc, base_bsfc, 650.0))

    def calculate_fuel_flow_kg_h(self, rpm: float, power_kw: float) -> float:
        """Compute mass fuel flow in kg/h."""
        bsfc = self.calculate_bsfc(rpm, power_kw)
        return float((bsfc * power_kw) / 1000.0)

    def calculate_turbo_state(
        self,
        engine_power_kw: float,
        altitude_m: float,
        wastegate_duty: float = 0.5,
    ) -> Dict[str, float]:
        """Compute turbocharger operating point (boost pressure, compressor PR, turbine inlet temp)."""
        atm = self.get_isa_atmosphere(altitude_m)
        if not self.is_turbo or not self.cfg.turbo:
            return {
                "map_bar": atm.p_amb_bar,
                "boost_bar": 0.0,
                "compressor_pr": 1.0,
                "is_choked": False,
                "is_surging": False,
                "compressor_eta": 0.0,
            }

        max_boost_bar = self.cfg.turbo.max_boost_kpa / 100.0
        # Required manifold absolute pressure to maintain power at altitude
        target_map = min(max_boost_bar, atm.p_amb_bar + (engine_power_kw / max(1.0, self.cfg.rated_power_kw)) * (max_boost_bar - 1.0))
        target_pr = target_map / max(0.2, atm.p_amb_bar)

        # Compressor efficiency island model (peaks around PR ~ 1.8-2.2)
        pr_delta = (target_pr - 2.0) ** 2
        eta_c = float(np.clip(0.74 - 0.05 * pr_delta, 0.55, 0.78))

        is_choked = bool(target_pr > max_boost_bar / 0.5)
        is_surging = bool(target_pr > 3.2 and engine_power_kw < 0.3 * self.cfg.rated_power_kw)

        return {
            "map_bar": float(target_map),
            "boost_bar": float(max(0.0, target_map - atm.p_amb_bar)),
            "compressor_pr": float(target_pr),
            "compressor_eta": eta_c,
            "is_choked": is_choked,
            "is_surging": is_surging,
        }

    def max_available_power_kw(self, altitude_m: float, delta_isa_c: float = 0.0) -> float:
        """Compute maximum available engine shaft power at altitude."""
        atm = self.get_isa_atmosphere(altitude_m, delta_isa_c)
        if self.is_turbo and self.cfg.turbo:
            critical_alt_m = self.cfg.turbo.critical_altitude_ft * 0.3048
            if altitude_m <= critical_alt_m:
                # Flat rated up to critical altitude
                return float(self.cfg.rated_power_kw)
            else:
                # Lapses above critical altitude with density ratio relative to critical alt
                atm_crit = self.get_isa_atmosphere(critical_alt_m, delta_isa_c)
                lapse_ratio = atm.density_kg_m3 / max(0.1, atm_crit.density_kg_m3)
                return float(self.cfg.rated_power_kw * lapse_ratio)
        else:
            # Naturally aspirated: power drops directly with ambient air density ratio
            return float(self.cfg.rated_power_kw * (atm.density_ratio - (1.0 - atm.density_ratio) / 7.55))
