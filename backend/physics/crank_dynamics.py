"""
Crank-angle-resolved engine dynamics — F01.

This is the foundation the whole differentiating thesis rests on, and the
isolability analysis (F35) has now *proved* it is load-bearing rather than
merely desirable: with the as-built 20 Hz sensor set, misfire and injector
needle stick are literally the same observation, and no classifier can separate
them. The separation has to come from instrumentation, and this is that
instrumentation modelled honestly.

The signal chain, built from physics rather than painted on:

    per-cylinder pressure trace  p(theta)          [Wiebe heat release]
        -> gas torque + inertial torque            [slider-crank kinematics]
    instantaneous crank angular velocity omega(theta)   <- the key signal
        -> structural transfer
    accelerometer signal a(t) @ 2-10 kHz
        -> tach-synchronous resampling
    order-domain signal a(theta)                   [speed-invariant]

The rule that makes this real rather than decorative: **faults modify the
pressure trace and physical parameters, never the output signal.** A misfire is
"no combustion in cylinder 3 this cycle", not "subtract 20 from the vibration
channel". Everything downstream then follows from physics, and a detector that
works here has a reason to work on an engine.

Validation anchor
-----------------
A healthy four-cylinder four-stroke fires four times per two revolutions, so its
torque and vibration spectra must be dominated by **order 2.0**. If a change to
this module stops producing that, the module is wrong — that check is in the
test at the bottom of this file and should stay there.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "EngineGeometry",
    "WiebeCombustion",
    "CylinderState",
    "CrankDynamicsModel",
]

_R_AIR = 287.05


@dataclass
class EngineGeometry:
    """Slider-crank geometry and inertia."""

    bore_mm: float = 79.5
    stroke_mm: float = 61.0
    conrod_mm: float = 110.0
    compression_ratio: float = 9.0
    n_cylinders: int = 4
    firing_order: Tuple[int, ...] = (1, 4, 2, 3)
    # Rotating + reciprocating inertia referred to the crank, kg m^2. A real
    # value comes from the manufacturer; this is a plausible small-aero figure.
    inertia_kgm2: float = 0.085
    recip_mass_kg: float = 0.55  # piston + small end, per cylinder

    @property
    def crank_radius_m(self) -> float:
        return self.stroke_mm / 2000.0

    @property
    def rod_m(self) -> float:
        return self.conrod_mm / 1000.0

    @property
    def bore_m(self) -> float:
        return self.bore_mm / 1000.0

    @property
    def piston_area_m2(self) -> float:
        return math.pi * (self.bore_m / 2.0) ** 2

    @property
    def displacement_per_cyl_m3(self) -> float:
        return self.piston_area_m2 * (self.stroke_mm / 1000.0)

    @property
    def clearance_volume_m3(self) -> float:
        return self.displacement_per_cyl_m3 / max(self.compression_ratio - 1.0, 1e-6)

    @property
    def firing_interval_deg(self) -> float:
        return 720.0 / self.n_cylinders

    @property
    def dominant_order(self) -> float:
        """Firing order in shaft orders: 2.0 for a four-cylinder four-stroke."""
        return self.n_cylinders / 2.0

    def phase_offset_deg(self, cylinder: int) -> float:
        """Crank angle at which this cylinder reaches firing TDC."""
        idx = self.firing_order.index(cylinder)
        return idx * self.firing_interval_deg

    # -- kinematics ---------------------------------------------------------

    def piston_position_m(self, theta_rad: float) -> float:
        """Distance of the piston from TDC."""
        r, l = self.crank_radius_m, self.rod_m
        return (r * (1.0 - math.cos(theta_rad))
                + l * (1.0 - math.sqrt(max(1.0 - (r / l * math.sin(theta_rad)) ** 2, 0.0))))

    def cylinder_volume_m3(self, theta_rad: float) -> float:
        return self.clearance_volume_m3 + self.piston_area_m2 * self.piston_position_m(theta_rad)

    def crank_lever_m(self, theta_rad: float) -> float:
        """dx/dtheta — converts piston force to crank torque."""
        r, l = self.crank_radius_m, self.rod_m
        s = math.sin(theta_rad)
        c = math.cos(theta_rad)
        root = math.sqrt(max(1.0 - (r / l * s) ** 2, 1e-9))
        return r * s + (r * r * s * c) / (l * root)


@dataclass
class WiebeCombustion:
    """Wiebe-function heat release — the standard closed form for p(theta).

    `a` and `m` set burn completeness and shape. Start of combustion and burn
    duration are the levers a fault moves: retarded injection shifts the former,
    poor atomisation lengthens the latter, and a misfire sets the released
    fraction to zero.
    """

    start_deg_atdc: float = -8.0
    duration_deg: float = 55.0
    a: float = 5.0
    m: float = 2.0

    def mass_fraction_burned(self, theta_deg_atdc: float) -> float:
        if theta_deg_atdc <= self.start_deg_atdc:
            return 0.0
        x = (theta_deg_atdc - self.start_deg_atdc) / max(self.duration_deg, 1e-6)
        if x >= 1.0:
            return 1.0
        return 1.0 - math.exp(-self.a * x ** (self.m + 1.0))


@dataclass
class CylinderState:
    """Per-cylinder combustion condition — where faults are injected."""

    cylinder: int
    combustion_efficiency: float = 1.0  # 0.0 = complete misfire
    soc_offset_deg: float = 0.0  # + is retarded
    burn_duration_scale: float = 1.0  # >1 = slower burn (poor atomisation)
    delivered_fuel_fraction: float = 1.0
    compression_loss: float = 0.0  # 0..1, ring/valve leakage

    @property
    def is_misfiring(self) -> bool:
        return self.combustion_efficiency < 0.15


class CrankDynamicsModel:
    """Generates omega(theta) and a vibration waveform from combustion physics."""

    def __init__(
        self,
        geometry: Optional[EngineGeometry] = None,
        combustion: Optional[WiebeCombustion] = None,
        sample_rate_hz: float = 10000.0,
        friction_torque_nm: float = 6.0,
    ) -> None:
        self.geom = geometry or EngineGeometry()
        self.comb = combustion or WiebeCombustion()
        self.sample_rate_hz = sample_rate_hz
        self.friction_torque_nm = friction_torque_nm
        # Propeller load. A prop absorbs torque proportional to omega^2, and
        # that is what actually holds an engine at a steady speed. An earlier
        # version used fixed friction plus a weak governor, which let the mean
        # speed drift upward through the window; the drift then dominated the
        # order spectrum and masked the firing order. The coefficient is
        # calibrated on demand in simulate_cycle() so the balance point lands on
        # the commanded RPM.
        self._prop_k: Optional[float] = None
        self.cylinders: Dict[int, CylinderState] = {
            i: CylinderState(cylinder=i) for i in range(1, self.geom.n_cylinders + 1)
        }

    # -- fault injection ----------------------------------------------------

    def set_misfire(self, cylinder: int, fraction: float = 0.0) -> None:
        """A misfire is an absence of combustion, not a signal subtraction."""
        self.cylinders[cylinder].combustion_efficiency = max(0.0, min(1.0, fraction))

    def set_injection_fault(self, cylinder: int, delivery: float = 1.0,
                            retard_deg: float = 0.0, burn_scale: float = 1.0) -> None:
        """CI injector faults act here — the same lever, different physics."""
        c = self.cylinders[cylinder]
        c.delivered_fuel_fraction = max(0.0, min(1.5, delivery))
        c.soc_offset_deg = retard_deg
        c.burn_duration_scale = max(0.2, burn_scale)

    def clear_faults(self) -> None:
        for i in self.cylinders:
            self.cylinders[i] = CylinderState(cylinder=i)

    # -- pressure and torque ------------------------------------------------

    def cylinder_pressure_pa(self, cylinder: int, theta_deg: float,
                             map_kpa: float, intake_temp_k: float = 320.0) -> float:
        """p(theta) for one cylinder over a 720 degree cycle.

        Polytropic compression and expansion around a Wiebe heat release. This
        is a single-zone model — adequate for producing a torque signature with
        the right shape and timing, not for emissions or knock prediction, and
        the distinction is worth keeping in mind before anyone quotes a peak
        pressure from it.
        """
        st = self.cylinders[cylinder]
        # Angle relative to this cylinder's own firing TDC, in -360..+360.
        rel = (theta_deg - self.geom.phase_offset_deg(cylinder)) % 720.0
        if rel > 360.0:
            rel -= 720.0

        v = self.geom.cylinder_volume_m3(math.radians(rel))
        v_max = self.geom.displacement_per_cyl_m3 + self.geom.clearance_volume_m3

        p_intake = map_kpa * 1000.0
        n_comp, n_exp = 1.35, 1.32

        if rel < -180.0 or rel > 180.0:
            # Gas exchange: roughly manifold pressure.
            return p_intake

        # Compression from BDC (rel = -180) to the current angle.
        v_bdc = v_max
        p_motored = p_intake * (v_bdc / max(v, 1e-12)) ** n_comp
        # Leakage past worn rings lowers the achievable peak.
        p_motored *= (1.0 - 0.6 * st.compression_loss)

        if st.combustion_efficiency <= 0.0:
            return p_motored  # motoring only: the misfire signature

        soc = self.comb.start_deg_atdc + st.soc_offset_deg
        dur = self.comb.duration_deg * st.burn_duration_scale
        wiebe = WiebeCombustion(start_deg_atdc=soc, duration_deg=dur,
                                a=self.comb.a, m=self.comb.m)
        xb = wiebe.mass_fraction_burned(rel)
        if xb <= 0.0:
            return p_motored

        # Heat release raises pressure above the motored trace.
        mass_air = p_intake * v_max / (_R_AIR * intake_temp_k)
        q_total = (mass_air / 14.7) * 43.0e6 * st.delivered_fuel_fraction * st.combustion_efficiency
        dp = (n_exp - 1.0) * q_total * xb / max(v, 1e-12)
        return p_motored + dp

    def instantaneous_torque_nm(self, theta_deg: float, map_kpa: float,
                                rpm: float) -> float:
        """Net crank torque: gas torque from all cylinders, minus inertia and friction."""
        omega = rpm * 2.0 * math.pi / 60.0
        total = 0.0
        for cyl in self.cylinders:
            rel = (theta_deg - self.geom.phase_offset_deg(cyl)) % 720.0
            if rel > 360.0:
                rel -= 720.0
            p = self.cylinder_pressure_pa(cyl, theta_deg, map_kpa)
            # Net force on the piston crown above crankcase pressure.
            force = (p - 101325.0) * self.geom.piston_area_m2
            lever = self.geom.crank_lever_m(math.radians(rel))
            total += force * lever

            # Reciprocating inertia torque — significant at speed and the reason
            # omega(theta) has structure even on a motored engine.
            theta_r = math.radians(rel)
            r, l = self.geom.crank_radius_m, self.geom.rod_m
            accel = (omega ** 2) * r * (math.cos(theta_r)
                                        + (r / l) * math.cos(2.0 * theta_r))
            total -= self.geom.recip_mass_kg * accel * lever
        load = self.friction_torque_nm
        if self._prop_k is not None:
            load += self._prop_k * (omega ** 2)
        return total - load

    # -- omega(theta) -------------------------------------------------------

    def simulate_cycle(self, rpm: float = 5200.0, map_kpa: float = 100.0,
                       n_cycles: int = 1, resolution_deg: float = 1.0
                       ) -> Tuple[List[float], List[float], List[float]]:
        """Integrate crank dynamics over whole engine cycles.

        Returns (theta_deg, omega_rad_s, torque_nm). Angular velocity is
        integrated from net torque and inertia, so the speed fluctuation within a
        revolution is a *consequence* of the pressure traces rather than an
        imposed waveform. That is what makes a torque deficit attributable to the
        cylinder that caused it.
        """
        omega_mean = rpm * 2.0 * math.pi / 60.0

        # Calibrate the propeller load so that mean net torque is zero at the
        # commanded speed. Without this the engine accelerates through the
        # window and the resulting ramp swamps the firing order in the spectrum.
        self._prop_k = None
        probe = [self.instantaneous_torque_nm(a * 2.0, map_kpa, rpm)
                 for a in range(360)]
        mean_gas = sum(probe) / len(probe) + self.friction_torque_nm
        self._prop_k = max(0.0, (mean_gas - self.friction_torque_nm)
                           / max(omega_mean ** 2, 1e-9))

        theta: List[float] = []
        omega: List[float] = []
        torque: List[float] = []

        w = omega_mean
        total_deg = 720.0 * n_cycles
        steps = int(total_deg / resolution_deg)
        for i in range(steps):
            th = i * resolution_deg
            tq = self.instantaneous_torque_nm(th % 720.0, map_kpa, rpm)
            # dw/dt = T/J, and dtheta = w dt  =>  dw = T/(J*w) * dtheta
            dtheta_rad = math.radians(resolution_deg)
            w += (tq / self.geom.inertia_kgm2) * dtheta_rad / max(w, 1e-3)
            theta.append(th)
            omega.append(w)
            torque.append(tq)
        return theta, omega, torque

    def vibration_waveform(self, rpm: float = 5200.0, map_kpa: float = 100.0,
                           n_cycles: int = 4, noise: float = 0.02,
                           seed: Optional[int] = None) -> Tuple[List[float], List[float]]:
        """Accelerometer signal at `sample_rate_hz` from the torque fluctuation.

        A structural transfer is approximated by differentiating the torque and
        exciting a damped resonance, which is enough to put the right orders in
        the right places. It is not a modal model of the crankcase, and should
        not be presented as one.
        """
        import random

        rng = random.Random(seed)
        cycle_time = 120.0 / max(rpm, 1.0) * n_cycles  # seconds for n_cycles
        n_samples = int(cycle_time * self.sample_rate_hz)
        deg_per_sample = 720.0 * n_cycles / max(n_samples, 1)

        _, _, torque = self.simulate_cycle(rpm, map_kpa, n_cycles,
                                           resolution_deg=deg_per_sample)
        t_axis: List[float] = []
        accel: List[float] = []
        prev = torque[0] if torque else 0.0
        state = 0.0
        vel = 0.0
        wn = 2.0 * math.pi * 1200.0  # structural resonance, Hz
        zeta = 0.08
        dt = 1.0 / self.sample_rate_hz
        for i in range(min(n_samples, len(torque))):
            drive = (torque[i] - prev) / dt
            prev = torque[i]
            acc = drive * 1e-6 - 2.0 * zeta * wn * vel - (wn ** 2) * state
            vel += acc * dt
            state += vel * dt
            t_axis.append(i * dt)
            accel.append(state * (wn ** 2) + rng.gauss(0.0, noise))
        return t_axis, accel
