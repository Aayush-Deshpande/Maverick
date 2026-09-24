"""CI (Compression Ignition / CRDi) Combustion Physics Model (B2.1).

Implements:
1. Ignition-delay correlation (Arrhenius formulation vs charge pressure and temperature).
2. Double-Wiebe heat release model (pilot + main/post injection).
3. In-cylinder pressure synthesis p(theta) with peak cylinder pressure in 120-180 bar class.
4. Per-cylinder parameterisation (so faults act on individual cylinders).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

from backend.physics.engine_config import EngineConfig


@dataclass
class CICombustionParams:
    soi_pilot_deg: float = 12.0    # deg BTDC
    soi_main_deg: float = 4.0      # deg BTDC
    pilot_fraction: float = 0.15   # fraction of total fuel in pilot
    wiebe_m_pilot: float = 1.8
    wiebe_m_main: float = 2.4
    wiebe_dur_pilot_deg: float = 10.0
    wiebe_dur_main_deg: float = 35.0
    gamma: float = 1.35            # polytropic index
    cr: float = 17.5               # compression ratio
    q_lhv_mj_kg: float = 42.8      # Jet-A1 / Diesel LHV (MJ/kg)


def calc_ignition_delay_deg(rpm: float, p_charge_kpa: float, t_charge_k: float, cr: float = 17.5, gamma: float = 1.35) -> float:
    """Calculate ignition delay in crank angle degrees via Arrhenius correlation at compressed conditions.
    Near TDC compression: T_comp ~ T_charge * CR^(gamma-1) (~850-1000 K), p_comp ~ p_charge * CR^gamma (~60-100 bar).
    tau_id (ms) = 0.0406 * (p_comp_bar)^(-0.75) * exp(4500 / T_comp_K)
    deg = tau_id_sec * (rpm * 360 / 60)
    """
    t_comp_k = max(600.0, t_charge_k * (cr ** (gamma - 1.0)))
    p_comp_bar = max(10.0, (p_charge_kpa / 100.0) * (cr ** gamma))
    tau_ms = 0.0406 * (p_comp_bar ** (-0.75)) * math.exp(min(12.0, 4500.0 / t_comp_k))
    deg_per_ms = (rpm * 360.0) / 60000.0
    return max(0.5, min(25.0, tau_ms * deg_per_ms))


def double_wiebe_mass_burned(
    theta_deg: np.ndarray,
    soi_pilot_deg: float,
    soi_main_deg: float,
    ign_delay_deg: float,
    pilot_frac: float = 0.15,
    dur_pilot_deg: float = 10.0,
    dur_main_deg: float = 35.0,
    m_pilot: float = 1.8,
    m_main: float = 2.4,
    a_wiebe: float = 5.0,
) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate cumulative mass burned fraction x_b(theta) and rate of heat release dx_b/dtheta.
    theta_deg: crank angles relative to TDC compression (TDC = 0, BTDC < 0, ATDC > 0).
    """
    soc_pilot = -soi_pilot_deg + ign_delay_deg
    soc_main = -soi_main_deg + ign_delay_deg

    xb_pilot = np.zeros_like(theta_deg, dtype=np.float64)
    xb_main = np.zeros_like(theta_deg, dtype=np.float64)
    dxb_dtheta = np.zeros_like(theta_deg, dtype=np.float64)

    # Pilot
    idx_p = (theta_deg >= soc_pilot) & (theta_deg <= soc_pilot + dur_pilot_deg)
    tau_p = (theta_deg[idx_p] - soc_pilot) / dur_pilot_deg
    xb_pilot[idx_p] = 1.0 - np.exp(-a_wiebe * (tau_p ** (m_pilot + 1)))
    xb_pilot[theta_deg > soc_pilot + dur_pilot_deg] = 1.0

    # Derivative pilot
    dxb_p = (a_wiebe * (m_pilot + 1) / dur_pilot_deg) * (tau_p ** m_pilot) * np.exp(-a_wiebe * (tau_p ** (m_pilot + 1)))
    dxb_dtheta[idx_p] += pilot_frac * dxb_p

    # Main
    idx_m = (theta_deg >= soc_main) & (theta_deg <= soc_main + dur_main_deg)
    tau_m = (theta_deg[idx_m] - soc_main) / dur_main_deg
    xb_main[idx_m] = 1.0 - np.exp(-a_wiebe * (tau_m ** (m_main + 1)))
    xb_main[theta_deg > soc_main + dur_main_deg] = 1.0

    # Derivative main
    dxb_m = (a_wiebe * (m_main + 1) / dur_main_deg) * (tau_m ** m_main) * np.exp(-a_wiebe * (tau_m ** (m_main + 1)))
    dxb_dtheta[idx_m] += (1.0 - pilot_frac) * dxb_m

    xb_total = pilot_frac * xb_pilot + (1.0 - pilot_frac) * xb_main
    return xb_total, dxb_dtheta


class CICombustionModel:
    """Generates per-cylinder pressure p(theta) and dp/dtheta curves for compression-ignition engines."""

    def __init__(self, cfg: EngineConfig) -> None:
        self.cfg = cfg
        self.bore_m = cfg.layout.bore_mm / 1000.0
        self.stroke_m = cfg.layout.stroke_mm / 1000.0
        self.cr = cfg.layout.compression_ratio
        self.displ_m3 = (math.pi / 4.0) * (self.bore_m ** 2) * self.stroke_m
        self.vc_m3 = self.displ_m3 / (self.cr - 1.0)
        self.con_rod_m = self.stroke_m * 1.7  # rod-to-crank ratio ~3.4

    def cylinder_volume(self, theta_rad: np.ndarray) -> np.ndarray:
        """Cylinder volume as function of crank angle from TDC (0 rad)."""
        r = self.stroke_m / 2.0
        l = self.con_rod_m
        s = r * (1.0 - np.cos(theta_rad)) + l * (1.0 - np.sqrt(1.0 - ((r / l) * np.sin(theta_rad)) ** 2))
        return self.vc_m3 + (math.pi / 4.0) * (self.bore_m ** 2) * s

    def simulate_cycle_pressure(
        self,
        rpm: float,
        map_kpa: float,
        t_charge_k: float,
        fuel_mg_per_stroke: float,
        params: Optional[CICombustionParams] = None,
        theta_deg: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Synthesize in-cylinder pressure p_bar(theta) and dp/dtheta over 720 deg cycle.
        Returns (theta_deg, p_bar, dp_dtheta_bar_deg).
        Peak pressure typically reaches 120-180 bar for turbocharged CRDi diesel at full load.
        """
        p = params or CICombustionParams(cr=self.cr)
        if theta_deg is None:
            theta_deg = np.linspace(-360.0, 360.0, 720, endpoint=False)

        theta_rad = np.radians(theta_deg)
        V = self.cylinder_volume(theta_rad)
        v_bdc = self.vc_m3 + self.displ_m3
        gamma = p.gamma
        r_gas = 287.0
        cv_j_kg_k = 718.0

        p_intake_pa = map_kpa * 1000.0
        m_air_kg = (p_intake_pa * v_bdc) / (r_gas * max(200.0, t_charge_k))
        m_fuel_kg = fuel_mg_per_stroke * 1e-6
        m_tot_kg = m_air_kg + m_fuel_kg

        # Polytropic temperature before combustion
        t_poly_k = t_charge_k * ((v_bdc / V) ** (gamma - 1.0))

        ign_delay = calc_ignition_delay_deg(rpm, map_kpa, t_charge_k)
        xb, dxb_dtheta = double_wiebe_mass_burned(
            theta_deg,
            soi_pilot_deg=p.soi_pilot_deg,
            soi_main_deg=p.soi_main_deg,
            ign_delay_deg=ign_delay,
            pilot_frac=p.pilot_fraction,
            dur_pilot_deg=p.wiebe_dur_pilot_deg,
            dur_main_deg=p.wiebe_dur_main_deg,
            m_pilot=p.wiebe_m_pilot,
            m_main=p.wiebe_m_main,
        )

        # Heat release temperature rise: delta_T = (Q_sensible * xb) / (m_tot * cv)
        # Accounting for wall heat transfer, dissociation and piston work (Heywood Ch 14)
        q_total_j = m_fuel_kg * (p.q_lhv_mj_kg * 1e6) * 0.55
        delta_t_k = (q_total_j * xb) / (m_tot_kg * cv_j_kg_k)

        t_total_k = t_poly_k + delta_t_k

        # Closed cycle (compression & power strokes: -180 deg to +180 deg)
        closed_idx = (theta_deg >= -180.0) & (theta_deg <= 180.0)
        p_total_bar = np.full_like(theta_deg, p_intake_pa * 1e-5)

        # Gas exchange: exhaust stroke (180 to 360 deg) ~ 1.2 bar, intake stroke (-360 to -180 deg) ~ intake pressure
        p_total_bar[theta_deg > 180.0] = 1.2

        # Closed-cycle thermodynamic pressure
        p_closed = (m_tot_kg * r_gas * t_total_k[closed_idx] / V[closed_idx]) * 1e-5
        p_total_bar[closed_idx] = p_closed

        # Numerical gradient dp/dtheta
        dp_dtheta = np.gradient(p_total_bar, theta_deg)

        return theta_deg, p_total_bar, dp_dtheta
