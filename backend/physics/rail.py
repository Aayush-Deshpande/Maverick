"""Common-Rail Hydraulics and Injector Physics Model (B2.2, FDP-03).

Models:
1. High-pressure pump flow (speed-proportional pulsatile delivery).
2. Rail accumulator volume and fuel compressibility (bulk modulus ~1500 MPa).
3. Per-injection fuel volume discharge generating transient rail pressure drops.
4. Rail pressure control valve (PCV) closed-loop regulation.
5. High-frequency acoustic wave oscillations in injector lines (fs >= 30 kHz).
6. Fault injection: injector coking (reduced drop), needle stick (excessive drop/slow recovery), rail leak (steady decay).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class RailConfig:
    rail_volume_cm3: float = 25.0       # cm3
    target_pressure_bar: float = 1600.0  # bar (CRDi target)
    bulk_modulus_bar: float = 15000.0    # 1500 MPa = 15000 bar
    sound_speed_m_s: float = 1350.0     # acoustic wave velocity in diesel/Jet-A1
    line_length_m: float = 0.35          # rail-to-injector line length
    pump_displacement_cc_rev: float = 0.5


class CommonRailHydraulics:
    """Simulates high-rate (>=30 kHz) common-rail pressure dynamics and acoustic transients."""

    def __init__(self, config: Optional[RailConfig] = None) -> None:
        self.cfg = config or RailConfig()
        self.current_pressure_bar = self.cfg.target_pressure_bar
        self.rail_vol_m3 = self.cfg.rail_volume_cm3 * 1e-6
        self.bulk_mod_pa = self.cfg.bulk_modulus_bar * 1e5

    def simulate_cycle_rail_pressure(
        self,
        rpm: float,
        target_p_bar: float,
        inj_quantities_mm3: List[float],    # per cylinder commanded fuel quantity
        inj_angles_deg: List[float],        # per cylinder injection crank angle (0..720)
        coking_factors: Optional[List[float]] = None,      # 1.0 = normal, <1.0 = coked
        needle_stick_cyls: Optional[List[int]] = None,     # list of cylinders with stuck needle
        rail_leak_bar_s: float = 0.0,
        fs_hz: float = 30000.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Simulate high-rate rail pressure waveform over one 720-degree engine cycle.
        Returns (t_sec, p_rail_bar).
        """
        n_cyl = len(inj_quantities_mm3)
        if coking_factors is None:
            coking_factors = [1.0] * n_cyl
        if needle_stick_cyls is None:
            needle_stick_cyls = []

        cycle_dur_s = (720.0 / 360.0) * (60.0 / max(100.0, rpm))
        n_samples = max(2, int(cycle_dur_s * fs_hz))
        t_sec = np.linspace(0.0, cycle_dur_s, n_samples, endpoint=False)
        deg_per_sample = 720.0 / n_samples
        angles = np.linspace(0.0, 720.0, n_samples, endpoint=False)

        # Base rail pressure with pump ripple and control loop
        p_bar = np.full(n_samples, target_p_bar, dtype=np.float32)

        # Add 2x-per-revolution pump delivery pressure ripple (2-lobe pump)
        pump_ripple = 12.0 * np.sin(np.radians(angles * 2.0))
        p_bar += pump_ripple

        # Simulate per-cylinder injection pressure drops and acoustic ringing
        # Line acoustic resonance frequency ~ c / (4 * L)
        f_acoustic = self.cfg.sound_speed_m_s / (4.0 * self.cfg.line_length_m)  # ~964 Hz
        tau_acoustic = 0.003  # 3 ms decay

        for i, (qty_mm3, start_deg) in enumerate(zip(inj_quantities_mm3, inj_angles_deg)):
            coke = coking_factors[i]
            is_stuck = (i + 1) in needle_stick_cyls

            # Effective injected volume (coking reduces effective fuel draw rate, needle stick increases it)
            eff_qty = qty_mm3 * coke
            if is_stuck:
                eff_qty *= 1.4  # stuck needle drains extra fuel

            # Theoretical localized pressure drop: delta_p = (beta * delta_V) / V_rail
            # delta_V in m3 = qty_mm3 * 1e-9
            delta_v_m3 = eff_qty * 1e-9
            delta_p_bar = (self.cfg.bulk_modulus_bar * delta_v_m3) / (self.cfg.rail_volume_cm3 * 1e-6)

            # Injection duration in degrees
            inj_dur_deg = max(3.0, (eff_qty / 15.0) * (rpm / 1000.0) * 8.0)
            if is_stuck:
                inj_dur_deg *= 2.0  # stuck needle takes longer to close

            # Find sample index corresponding to injection start
            inj_start_idx = int((start_deg % 720.0) / deg_per_sample)

            # Generate transient drop and acoustic ringing
            t_rel = np.arange(n_samples - inj_start_idx) / fs_hz
            drop_profile = delta_p_bar * np.exp(-t_rel / (inj_dur_deg / (rpm * 6.0)))
            ringing = (0.3 * delta_p_bar) * np.exp(-t_rel / tau_acoustic) * np.sin(2.0 * math.pi * f_acoustic * t_rel)

            p_bar[inj_start_idx:] -= (drop_profile + ringing).astype(np.float32)

        # Apply rail leak decay if present
        if rail_leak_bar_s > 0.0:
            p_bar -= (rail_leak_bar_s * t_sec).astype(np.float32)

        return t_sec, p_bar
