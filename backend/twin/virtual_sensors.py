"""Virtual Sensor Synthesis Module (B4.2, CAP-11, DRDO PS-26054).

Synthesizes unmeasured physical quantities from physical thermodynamic state and UKF estimates:
1. P_max (bar): Peak in-cylinder combustion pressure.
2. TIT (degC): Turbine Inlet Temperature (critical turbine/turbocharger thermal limit).
3. h_min (um): Minimum journal bearing hydrodynamic oil film thickness.
4. P_ind (kW): Indicated engine power.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional
import numpy as np

from backend.core.frame import Frame
from backend.physics.engine_config import EngineConfig


class VirtualSensorSynthesizer:
    """Synthesizes high-fidelity virtual sensor streams from measurable telemetry and UKF state."""

    def __init__(self, cfg: EngineConfig) -> None:
        self.cfg = cfg
        self.cr = cfg.layout.compression_ratio
        self.radial_clearance_um = 25.0  # 25 um nominal journal bearing clearance
        self.bore_m = cfg.layout.bore_mm / 1000.0
        self.stroke_m = cfg.layout.stroke_mm / 1000.0
        self.piston_area_m2 = math.pi * (self.bore_m / 2.0) ** 2
        self.disp_per_cyl_m3 = self.piston_area_m2 * self.stroke_m
        self.total_disp_m3 = self.disp_per_cyl_m3 * cfg.cylinder_count

    def synthesize(
        self,
        frame: Frame,
        eta_cool_mean: float = 1.0,
        eta_rad: float = 1.0,
    ) -> Dict[str, float]:
        """Synthesize virtual sensor values for one Frame."""
        rpm = max(100.0, float(frame.rpm or 0.0))
        throttle = max(0.0, min(100.0, float(frame.throttle or 0.0)))
        map_bar = max(0.2, (frame.map_kpa or 100.0) / 100.0)
        oil_t = float(frame.oil_t or 85.0)
        oil_p = max(0.1, float(frame.oil_p or 3.5))
        egt_vals = [float(x) for x in frame.egt] if frame.egt else [650.0]
        fuel_flow = float(frame.fuel_flow or 18.0)  # kg/h

        # 1. P_max (bar) - Peak in-cylinder pressure
        gamma = 1.33
        p_comp_bar = map_bar * (self.cr ** gamma)
        # Combustion rise scaled by throttle and cooling efficiency
        comb_mult = 1.0 + 1.85 * (throttle / 100.0) * max(0.3, eta_cool_mean)
        p_max = p_comp_bar * comb_mult

        # 2. TIT (degC) - Turbine Inlet Temperature
        mean_egt = sum(egt_vals) / len(egt_vals)
        # Turbochargers or exhaust manifolds concentrate heat before expansion
        tit_delta = 25.0 + 35.0 * (throttle / 100.0) if self.cfg.is_turbocharged else 15.0
        tit = mean_egt + tit_delta

        # 3. h_min (um) - Minimum oil film thickness (Raimondi-Boyd hydrodynamic lubrication)
        # Dynamic viscosity: mu_0 ~ 0.015 Pa*s at 80 degC, decaying exponentially with temperature
        mu_oil = 0.015 * math.exp(-0.032 * (oil_t - 80.0))
        n_rps = rpm / 60.0
        # Peak bearing load
        w_peak_n = max(1000.0, (p_max * 1e5) * self.piston_area_m2)
        # Sommerfeld number proxy
        p_bearing_pa = w_peak_n / (self.bore_m * 0.025)  # Projected bearing area
        sommerfeld = (mu_oil * n_rps / p_bearing_pa) * ((0.025 / (self.radial_clearance_um * 1e-6)) ** 2)
        # Pressure feed contribution
        press_factor = min(1.2, oil_p / 3.0)
        # Eccentricity ratio epsilon -> h_min = c * (1 - epsilon)
        epsilon = 1.0 / (1.0 + math.sqrt(max(1e-6, sommerfeld * 12.0 * press_factor)))
        h_min = self.radial_clearance_um * (1.0 - min(0.96, epsilon))

        # 4. P_ind (kW) - Indicated Power
        # IMEP estimate from p_max and CR
        imep_bar = p_max * 0.22 * (throttle / 100.0) + 1.5
        w_rad_s = rpm * 2.0 * math.pi / 60.0
        # Work per cycle: IMEP * V_disp
        p_ind_w = (imep_bar * 1e5 * self.total_disp_m3 * (n_rps / 2.0))
        p_ind_kw = max(0.0, p_ind_w / 1000.0)

        return {
            "P_max_bar": round(p_max, 2),
            "TIT_degC": round(tit, 1),
            "h_min_um": round(h_min, 2),
            "P_ind_kw": round(p_ind_kw, 2),
        }
