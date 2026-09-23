"""
Independent virtual engine — the plant, not the twin. Closes G01.

The single most damaging structural problem in this project has been that the
"actual" sensor readings were generated from the twin's own expected state plus
noise plus an injected offset. The twin then compared actual against that same
expected state, so residuals were always exactly noise plus the injected fault
and detection could not meaningfully fail. Every accuracy figure produced under
that arrangement measured the generator, not the diagnosis.

This module is the plant. It stands in for the real engine and it is deliberately
*not* the twin:

  * It composes the higher-fidelity physics — crank dynamics, turbocharger,
    induction, fuel thermal, injectors, oil — rather than the twin's algebraic
    expected-state model.
  * It carries properties the twin does not know: engine-to-engine parameter
    variation, sensor bias, sensor lag, sensor noise, and slow wear.
  * It publishes **only sensor frames**. Nothing here returns the ground-truth
    fault id, the true damage state, or an internal parameter.
  * Faults are injected here and here only.

The honesty property that matters: because the plant's physics differs from the
twin's model, nominal residuals are non-zero and *structured* (model mismatch),
not white noise. That is what a real deployment looks like, and it is the only
setting in which a detection claim means anything.

`truth()` exists for the evaluation harness alone. It is a separate method, not
part of the frame, precisely so that wiring it into the twin by accident is
difficult rather than easy.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..physics.crank_dynamics import CrankDynamicsModel, EngineGeometry
from ..physics.engine_config import EngineConfig, load_engine_config
from ..physics.fuel_thermal import AVGAS_100LL, JET_A1, FuelThermalModel
from ..physics.induction import InductionModel
from ..physics.injector_faults import InjectorBank
from ..physics.oil_system import OilSystemModel
from ..physics.turbo_model import TurbochargerModel, isa_ambient

__all__ = ["EngineVariation", "SensorModel", "VirtualEngine", "PLANT_FAULTS"]


PLANT_FAULTS = (
    "MISFIRE", "INJECTOR_COKING", "INJECTOR_NEEDLE_STICK", "RAIL_PRESSURE_DECAY",
    "COOLING_DEGRADATION", "OIL_PRESSURE_LOSS", "WASTEGATE_STUCK_OPEN",
    "TURBO_BEARING_WEAR", "BOOST_LEAK", "AIR_FILTER_BLOCKAGE",
    "SENSOR_BIAS_DRIFT", "SENSOR_STUCK",
)


@dataclass
class EngineVariation:
    """Build-to-build variation the twin has no knowledge of.

    Two engines off the same line differ. A twin calibrated on a nominal engine
    will see a standing residual on a different airframe, and a detector tuned
    without this will false-alarm on delivery.
    """

    volumetric_efficiency: float = 1.0
    friction_scale: float = 1.0
    heat_transfer_scale: float = 1.0
    compression_scale: float = 1.0
    injector_trim: Dict[int, float] = field(default_factory=dict)
    turbo_efficiency_scale: float = 1.0

    @classmethod
    def sample(cls, rng: random.Random, n_cyl: int = 4,
               spread: float = 1.0) -> "EngineVariation":
        g = lambda s: 1.0 + rng.gauss(0.0, s * spread)
        return cls(
            volumetric_efficiency=g(0.020),
            friction_scale=g(0.060),
            heat_transfer_scale=g(0.045),
            compression_scale=g(0.012),
            injector_trim={i: g(0.018) for i in range(1, n_cyl + 1)},
            turbo_efficiency_scale=g(0.035),
        )


@dataclass
class SensorChannel:
    """One measurement path: bias, scale error, lag, noise, quantisation."""

    bias: float = 0.0
    scale: float = 1.0
    tau_sec: float = 0.0
    noise_sigma: float = 0.0
    resolution: float = 0.0
    drift_per_hour: float = 0.0
    stuck_at: Optional[float] = None
    _state: Optional[float] = None

    def read(self, true_value: float, dt_sec: float, rng: random.Random,
             elapsed_hours: float = 0.0) -> float:
        if self.stuck_at is not None:
            return self.stuck_at
        target = true_value * self.scale + self.bias + self.drift_per_hour * elapsed_hours
        if self.tau_sec > 0:
            if self._state is None:
                self._state = target
            else:
                alpha = 1.0 - math.exp(-max(dt_sec, 0.0) / self.tau_sec)
                self._state += (target - self._state) * alpha
            out = self._state
        else:
            out = target
        if self.noise_sigma > 0:
            out += rng.gauss(0.0, self.noise_sigma)
        if self.resolution > 0:
            out = round(out / self.resolution) * self.resolution
        return out


class SensorModel:
    """The measurement chain between the plant and the twin."""

    def __init__(self, rng: random.Random, n_cyl: int = 4) -> None:
        self.channels: Dict[str, SensorChannel] = {}
        for i in range(1, n_cyl + 1):
            self.channels[f"CHT_{i}"] = SensorChannel(
                bias=rng.gauss(0.0, 1.8), tau_sec=2.5, noise_sigma=0.6, resolution=0.5)
            self.channels[f"EGT_{i}"] = SensorChannel(
                bias=rng.gauss(0.0, 7.0), tau_sec=0.8, noise_sigma=4.0, resolution=1.0)
        self.channels["ENGINE_RPM"] = SensorChannel(noise_sigma=3.0, resolution=1.0)
        self.channels["MAP"] = SensorChannel(
            bias=rng.gauss(0.0, 0.6), tau_sec=0.15, noise_sigma=0.35, resolution=0.1)
        self.channels["OIL_PRESS"] = SensorChannel(
            bias=rng.gauss(0.0, 0.04), tau_sec=0.4, noise_sigma=0.02, resolution=0.01)
        self.channels["OIL_TEMP"] = SensorChannel(
            bias=rng.gauss(0.0, 1.2), tau_sec=8.0, noise_sigma=0.4, resolution=0.5)
        self.channels["FUEL_FLOW"] = SensorChannel(
            scale=1.0 + rng.gauss(0.0, 0.012), tau_sec=1.0, noise_sigma=0.12)
        self.channels["BUS_VOLTAGE"] = SensorChannel(noise_sigma=0.05, resolution=0.1)
        self.channels["CHARGE_TEMP_C"] = SensorChannel(
            bias=rng.gauss(0.0, 1.5), tau_sec=1.5, noise_sigma=0.5)
        self.channels["FUEL_TEMP_C"] = SensorChannel(tau_sec=20.0, noise_sigma=0.3)

    def read_all(self, truth: Dict[str, float], dt_sec: float,
                 rng: random.Random, elapsed_hours: float) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for name, value in truth.items():
            ch = self.channels.get(name)
            out[name] = (ch.read(value, dt_sec, rng, elapsed_hours)
                         if ch is not None else value)
        return out


class VirtualEngine:
    """The plant. Publishes sensor frames; never exposes its internals."""

    def __init__(self, config: EngineConfig | str = "rotax_914",
                 seed: Optional[int] = None,
                 variation_spread: float = 1.0,
                 crank_every_n_steps: int = 0) -> None:
        # Running the full crank integration on every telemetry step is both
        # slow and architecturally wrong: a real edge node analyses crank data on
        # its own cadence, not at the 1 Hz rate the thermal channels publish at.
        # 0 means never (use crank_signal() explicitly); N means every N steps.
        self.crank_every_n_steps = crank_every_n_steps
        self._step_count = 0
        self.cfg = (load_engine_config(config) if isinstance(config, str) else config)
        self._rng = random.Random(seed)
        n = self.cfg.cylinder_count

        self.variation = EngineVariation.sample(self._rng, n, variation_spread)
        self.sensors = SensorModel(self._rng, n)

        geom = EngineGeometry(
            bore_mm=self.cfg.layout.bore_mm,
            stroke_mm=self.cfg.layout.stroke_mm,
            compression_ratio=self.cfg.layout.compression_ratio
            * self.variation.compression_scale,
            n_cylinders=n,
            firing_order=tuple(self.cfg.layout.firing_order),
        )
        self.crank = CrankDynamicsModel(
            geometry=geom,
            friction_torque_nm=6.0 * self.variation.friction_scale,
        )
        self.turbo = (TurbochargerModel(self.cfg.turbo,
                                        base_efficiency=0.72 * self.variation.turbo_efficiency_scale)
                      if self.cfg.is_turbocharged else None)
        self.induction = InductionModel()
        self.fuel = FuelThermalModel(JET_A1 if self.cfg.is_heavy_fuel else AVGAS_100LL)
        self.injectors = InjectorBank(n, self.cfg.rail_pressure_bar,
                                      self.cfg.nominal_inj_timing_btdc,
                                      seed=self._rng.randint(0, 10 ** 6))
        self.oil = OilSystemModel()

        # Hidden true state. Nothing below is ever published in a frame.
        self._elapsed_sec = 0.0
        self._active_faults: List[Tuple[str, Optional[int], float, float, float]] = []
        self._cht_true = [95.0] * n
        self._egt_true = [720.0] * n
        self._oil_temp_true = 92.0
        self._cooling_degradation = 0.0
        self._oil_press_loss = 0.0
        self._failed = False
        self._failure_reason: Optional[str] = None
        self._failure_t: Optional[float] = None
        self._last_rpm = 0.0

    # -- fault injection (plant side only) ---------------------------------

    def inject_fault(self, name: str, cylinder: Optional[int] = None,
                     severity: float = 0.6, ramp_sec: float = 300.0) -> None:
        """Faults exist only here. The twin is never told."""
        if name not in PLANT_FAULTS:
            raise ValueError(f"unknown plant fault {name!r}")
        self._active_faults.append((name, cylinder, severity, ramp_sec, self._elapsed_sec))

    def clear_faults(self) -> None:
        self._active_faults.clear()
        self.crank.clear_faults()
        self.injectors.clear_faults()
        if self.turbo:
            self.turbo.clear_faults()
        self._cooling_degradation = 0.0
        self._oil_press_loss = 0.0
        for ch in self.sensors.channels.values():
            ch.stuck_at = None
            ch.drift_per_hour = 0.0

    def _apply_faults(self) -> None:
        for name, cyl, sev, ramp, t0 in self._active_faults:
            progress = min(1.0, (self._elapsed_sec - t0) / max(ramp, 1e-6))
            s = sev * max(0.0, progress)
            if s <= 0:
                continue
            if name == "MISFIRE" and cyl:
                self.crank.set_misfire(cyl, max(0.0, 1.0 - s))
            elif name == "INJECTOR_COKING" and cyl:
                self.crank.set_injection_fault(cyl, delivery=1.0 - 0.3 * s,
                                               retard_deg=1.8 * s,
                                               burn_scale=1.0 + 0.5 * s)
            elif name == "INJECTOR_NEEDLE_STICK" and cyl:
                self.crank.set_injection_fault(cyl, delivery=max(0.0, 1.0 - 0.85 * s))
            elif name == "RAIL_PRESSURE_DECAY":
                for c in range(1, self.cfg.cylinder_count + 1):
                    self.crank.set_injection_fault(c, delivery=1.0 - 0.35 * s)
            elif name == "COOLING_DEGRADATION":
                self._cooling_degradation = s
            elif name == "OIL_PRESSURE_LOSS":
                self._oil_press_loss = s
            elif name == "WASTEGATE_STUCK_OPEN" and self.turbo:
                self.turbo.inject_fault("WASTEGATE_STUCK_OPEN", s)
            elif name == "TURBO_BEARING_WEAR" and self.turbo:
                self.turbo.inject_fault("TURBO_BEARING_WEAR", s)
            elif name == "BOOST_LEAK" and self.turbo:
                self.turbo.inject_fault("BOOST_LEAK", s)
            elif name == "AIR_FILTER_BLOCKAGE":
                self.induction._captured_g = (self.induction.filter_capacity_g
                                              * min(0.999, s))
            elif name == "SENSOR_BIAS_DRIFT":
                target = f"CHT_{cyl}" if cyl else "CHT_1"
                if target in self.sensors.channels:
                    self.sensors.channels[target].drift_per_hour = 30.0 * s
            elif name == "SENSOR_STUCK":
                target = f"CHT_{cyl}" if cyl else "CHT_2"
                if target in self.sensors.channels and self.sensors.channels[target].stuck_at is None:
                    self.sensors.channels[target].stuck_at = self._cht_true[
                        (cyl or 2) - 1]

    # -- the plant step -----------------------------------------------------

    def step(self, dt_sec: float, throttle_pct: float = 75.0,
             altitude_ft: float = 20000.0, oat_c: float = -25.0,
             dust_mg_m3: float = 0.15) -> Dict[str, float]:
        """Advance the plant and return a **sensor frame**.

        The frame is what a real ECU would publish. It contains no ground truth.
        """
        self._elapsed_sec += dt_sec
        hours = self._elapsed_sec / 3600.0
        self._apply_faults()

        amb_p, amb_t = isa_ambient(altitude_ft)
        throttle = max(0.0, min(100.0, throttle_pct))

        # Induction and boost
        ind = self.induction.update(dt_sec, "TEMPERATE_INLAND" if dust_mg_m3 < 1.0
                                    else "DESERT_THAR",
                                    5200.0, self.cfg.rated_rpm, amb_p)
        if self.turbo:
            tst = self.turbo.update(dt_sec, throttle, altitude_ft, 5200.0,
                                    isa_deviation_c=oat_c - (amb_t - 273.15))
            map_kpa = tst.manifold_pressure_kpa - ind.map_deficit_kpa
            charge_t = tst.charge_temp_k - 273.15
        else:
            map_kpa = amb_p * (0.2 + 0.8 * throttle / 100.0) - ind.map_deficit_kpa
            charge_t = oat_c + 12.0
        map_kpa = max(15.0, map_kpa * self.variation.volumetric_efficiency)

        # Fuel thermal
        fst = self.fuel.update(dt_sec, oat_c, True,
                               power_fraction=throttle / 100.0)

        # Crank / combustion
        self.injectors.update(dt_sec, fuel_temp_factor=fst.injector_cold_soak_factor)
        rpm_cmd = 3000.0 + 2600.0 * (throttle / 100.0)
        self._step_count += 1
        run_crank = (self.crank_every_n_steps > 0
                     and self._step_count % self.crank_every_n_steps == 0)
        if run_crank:
            _, omega, _ = self.crank.simulate_cycle(rpm_cmd, map_kpa, n_cycles=1,
                                                    resolution_deg=6.0)
            rpm_true = sum(omega) / len(omega) * 60.0 / (2.0 * math.pi)
            self._last_rpm = rpm_true
        else:
            # Mean-value speed: the load balance a governor would settle at,
            # degraded by any cylinder not pulling its weight. The intra-cycle
            # structure lives in crank_signal(), which is where the per-cylinder
            # diagnostics read it from.
            fire_mean = (sum(c.combustion_efficiency for c in self.crank.cylinders.values())
                         / max(len(self.crank.cylinders), 1))
            rpm_true = rpm_cmd * (0.55 + 0.45 * fire_mean) * self.variation.volumetric_efficiency
            self._last_rpm = rpm_true

        contrib = self.injectors.torque_contributions()
        power_kw = (self.cfg.rated_power_kw * (rpm_true / self.cfg.rated_rpm)
                    * (map_kpa / 101.325)
                    * (sum(contrib.values()) / max(len(contrib), 1))
                    * ind.volumetric_efficiency_factor)
        power_kw = max(0.0, power_kw)

        # Thermal states — first-order lags toward a load- and cooling-driven target
        # Cooling effectiveness: degradation reduces it, build variation shifts it.
        cooling_eff = max(0.20, (1.0 - 0.55 * self._cooling_degradation)
                          / max(self.variation.heat_transfer_scale, 0.5))
        # Reduced air density at altitude reduces cooling mass flow. This is a
        # modest penalty on the temperature RISE, not a multiplier on absolute
        # temperature: an earlier version scaled the whole target and produced
        # 226 C in cruise, which would have destroyed the engine and made every
        # scenario fail instantly.
        cool_mass_flow = max(0.30, amb_p / 101.325)
        alt_penalty_c = 22.0 * (1.0 - cool_mass_flow)
        load = power_kw / max(self.cfg.rated_power_kw, 1.0)
        for i in range(self.cfg.cylinder_count):
            cyl = i + 1
            fire = self.crank.cylinders[cyl].combustion_efficiency
            # Cylinder head temperature is dominated by combustion, not by
            # ambient: OAT shifts it, it does not set it. An earlier version
            # used ambient as the base and produced 43 C at altitude.
            target_cht = (70.0 + 48.0 * load * (0.45 + 0.55 * fire)) / cooling_eff
            target_cht += alt_penalty_c + 0.25 * oat_c
            tau = 25.0
            a = 1.0 - math.exp(-dt_sec / tau)
            self._cht_true[i] += (target_cht - self._cht_true[i]) * a
            target_egt = (360.0 + 430.0 * load) * fire * contrib.get(cyl, 1.0)
            self._egt_true[i] += (target_egt - self._egt_true[i]) * (1.0 - math.exp(-dt_sec / 3.0))

        target_oil_t = 60.0 + 55.0 * (power_kw / max(self.cfg.rated_power_kw, 1.0)) + 0.2 * oat_c
        self._oil_temp_true += (target_oil_t - self._oil_temp_true) * (1.0 - math.exp(-dt_sec / 60.0))
        oil_press_true = max(0.3, (0.6 + 0.00058 * rpm_true) * (1.0 - 0.75 * self._oil_press_loss))

        self.oil.update(dt_sec / 3600.0, power_kw / max(self.cfg.rated_power_kw, 1.0),
                        self._oil_temp_true, ind.bore_wear_index, 0.0, 0.0)

        # Hard failure conditions — the plant can actually break.
        if max(self._cht_true) > 165.0 and not self._failed:
            self._failed, self._failure_reason = True, "CHT_OVERTEMP"
            self._failure_t = self._elapsed_sec
        if oil_press_true < 0.8 and rpm_true > 2000 and not self._failed:
            self._failed, self._failure_reason = True, "OIL_PRESSURE"
            self._failure_t = self._elapsed_sec

        truth: Dict[str, float] = {
            "ENGINE_RPM": rpm_true,
            "MAP": map_kpa,
            "TPS": throttle,
            "ALTITUDE_FT": altitude_ft,
            "OAT_C": oat_c,
            "POWER_KW": power_kw,
            "FUEL_FLOW": power_kw * 0.30 + 1.5,
            "OIL_PRESS": oil_press_true,
            "OIL_TEMP": self._oil_temp_true,
            "CHARGE_TEMP_C": charge_t,
            "FUEL_TEMP_C": fst.fuel_temp_c,
            "BUS_VOLTAGE": 14.2,
            "BATTERY_CURRENT": 0.0,
        }
        for i in range(self.cfg.cylinder_count):
            truth[f"CHT_{i+1}"] = self._cht_true[i]
            truth[f"EGT_{i+1}"] = self._egt_true[i]

        frame = self.sensors.read_all(truth, dt_sec, self._rng, hours)
        frame["T_SEC"] = self._elapsed_sec
        return frame

    # -- evaluation-only access --------------------------------------------

    def truth(self) -> Dict[str, Any]:
        """Ground truth, for the harness only. Never wire this into the twin."""
        return {
            "t_sec": self._elapsed_sec,
            "active_faults": [
                {"name": n, "cylinder": c, "severity": s, "ramp_sec": r, "onset_t": t}
                for (n, c, s, r, t) in self._active_faults
            ],
            "failed": self._failed,
            "failure_reason": self._failure_reason,
            "failure_t_sec": self._failure_t,
            "cht_true": list(self._cht_true),
            "cooling_degradation": self._cooling_degradation,
            "bore_wear": self.induction.state.bore_wear_index,
        }

    @property
    def has_failed(self) -> bool:
        return self._failed

    def crank_signal(self, rpm: float, map_kpa: float, n_cycles: int = 1):
        """kHz crank data, published on its own channel as a real edge node would."""
        return self.crank.simulate_cycle(rpm, map_kpa, n_cycles=n_cycles,
                                         resolution_deg=2.0)
