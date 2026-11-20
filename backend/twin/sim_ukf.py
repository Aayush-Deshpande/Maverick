"""Thermal state observer on the M1 model (card M3-01; P Part 4 M3; DECISIONS D19: "Kalman-filter state observer,
unscented variant").

Unscented Kalman filter whose process model is backend/sim/thermal.py driven by MEASURED inputs only:
  rpm, throttle, altitude, OAT, airspeed -> steady heat inputs from backend/sim/engine.py, scaled so the total fuel
  equals the measured fuel flow (sensor fusion: the model's split per cylinder, the meter's total).
State x = [CHT_k (k = 1..n), T_coolant, T_oil,  k_head_k, k_radiator, k_oil_cooler]
  temperatures follow the heat balances; the k's are health parameters (1 = as calibrated) as random walks, so a
  cooling problem appears as "cylinder 2 head cooling at 0.7" with a confidence interval, not only as a hot reading.
Measurement z = [CHT_k (k = 1..n), T_coolant (when measured), T_oil]. Noise R from configs/physics sensors; Q from
configs/physics twin. NIS (normalised innovation squared) feeds the validity monitor.
The twin builds its OWN model instance from the engine config: it never sees the plant, its build spread or its
faults (T-DYN-4).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from backend.physics.engine_config import EngineConfig
from backend.sim.atmosphere import Atmosphere
from backend.sim.engine import MeanValueEngine
from backend.sim.params import physics_values
from backend.twin.ukf import ParameterEstimate

KG_PER_H = 3600.0


@dataclass
class _Sigma:
    alpha: float = 1e-3
    beta: float = 2.0
    kappa: float = 0.0


class SimThermalUKF:
    def __init__(self, cfg: EngineConfig) -> None:
        self.cfg = cfg
        self.n = cfg.cylinder_count
        self.model = MeanValueEngine(cfg)
        self.thermal = self.model.thermal
        self.tw = physics_values(cfg.engine_id, "twin")
        sens = physics_values(cfg.engine_id, "sensors")
        self.n_states = self.n + 2
        self.n_params = self.n + 2
        self.dim = self.n_states + self.n_params
        self.x = np.zeros(self.dim)
        self.x[self.n_states:] = 1.0
        self.P = np.diag([self.tw["init_temp_var"]] * self.n_states + [self.tw["init_param_var"]] * self.n_params)
        self.q_temp = self.tw["q_temp_per_s"]
        self.q_param = self.tw["q_param_per_s"]
        self.r_temp = sens["noise_temperature_c"] ** 2 + self.tw["r_model_temp"]
        s = _Sigma()
        self.lam = s.alpha ** 2 * (self.dim + s.kappa) - self.dim
        self.wm = np.full(2 * self.dim + 1, 1.0 / (2.0 * (self.dim + self.lam)))
        self.wm[0] = self.lam / (self.dim + self.lam)
        self.wc = self.wm.copy()
        self.wc[0] += 1.0 - s.alpha ** 2 + s.beta
        self.last_nis = 0.0
        self.last_t: Optional[float] = None
        self.initialised = False

    # -- helpers --------------------------------------------------------------------------------------------
    def _sigmas(self) -> np.ndarray:
        g = math.sqrt(self.dim + self.lam)
        try:
            c = np.linalg.cholesky(self.P)
        except np.linalg.LinAlgError:
            u, s, _ = np.linalg.svd(self.P)
            c = u @ np.diag(np.sqrt(np.maximum(s, 1e-10)))
        sig = np.repeat(self.x[None, :], 2 * self.dim + 1, axis=0)
        sig[1:self.dim + 1] += g * c.T
        sig[self.dim + 1:] -= g * c.T
        return sig

    def _heat(self, frame: Any):
        atm = Atmosphere.at(float(frame.alt), oat_c=float(frame.oat))
        op = self.model.steady_point(float(frame.throttle), max(float(frame.rpm), 1.0), atm)
        h = self.model.heat_inputs(op, atm)
        total = sum(h.fuel_kg_s)
        if total > 0:
            k = float(frame.fuel_flow) / KG_PER_H / total
            h.fuel_kg_s = [f * k for f in h.fuel_kg_s]
        return h, atm

    def _propagate(self, s: np.ndarray, dt: float, h: Any, atm: Atmosphere, tas: float) -> np.ndarray:
        n, th = self.n, self.thermal
        th.cht = list(s[:n])
        th.coolant_c, th.oil_c = float(s[n]), float(s[n + 1])
        k = np.clip(s[self.n_states:], 0.05, 3.0)
        health = {"head_conductance": list(k[:n]), "radiator": float(k[n]), "oil_cooler": float(k[n + 1])}
        steps = max(1, int(math.ceil(dt / self.tw["max_step_s"])))
        for _ in range(steps):
            th.step(dt / steps, h, atm, tas, health)
        out = s.copy()
        out[:n] = th.cht
        out[n], out[n + 1] = th.coolant_c, th.oil_c
        return out

    def ready(self, frame: Any) -> bool:
        """The process model needs its measured inputs; temperatures may be partly missing (they are skipped)."""
        need = (frame.rpm, frame.throttle, frame.fuel_flow, frame.oat, frame.alt)
        if not all(v is not None for v in need) or len(frame.cht) != self.n:
            return False
        return self.initialised or (frame.oil_t is not None and all(v is not None for v in frame.cht))

    # -- one observer step ----------------------------------------------------------------------------------
    def step(self, frame: Any, skip: Iterable[str] = ()) -> float:
        """Predict to frame.t with the measured inputs, then update with the measured temperatures that are present
        and not in `skip` (quarantined channels: cht_<k>, coolant_t, oil_t). Returns NIS."""
        n = self.n
        if not self.initialised:
            self.x[:n] = frame.cht
            self.x[n] = frame.coolant_t if frame.coolant_t is not None else frame.oil_t
            self.x[n + 1] = frame.oil_t
            self.last_t, self.initialised = float(frame.t), True
            return 0.0
        dt = max(float(frame.t) - float(self.last_t), 1e-3)
        self.last_t = float(frame.t)
        h, atm = self._heat(frame)
        tas = self.model.design_tas_kt if frame.tas is None else float(frame.tas)
        sig = np.array([self._propagate(s, dt, h, atm, tas) for s in self._sigmas()])
        self.x = self.wm @ sig
        d = sig - self.x
        q = np.diag([self.q_temp * dt] * self.n_states + [self.q_param * dt] * self.n_params)
        self.P = (self.wc[:, None] * d).T @ d + q
        # measurement: whichever of CHT_k, coolant, oil are measured and trusted
        skip = set(skip)
        cand = [(i, frame.cht[i], f"cht_{i + 1}") for i in range(n)] + [(n, frame.coolant_t, "coolant_t"),
                                                                         (n + 1, frame.oil_t, "oil_t")]
        use = [(i, v) for i, v, name in cand if v is not None and name not in skip]
        if not use:
            self.last_nis = 0.0
            return 0.0                                                    # nothing trusted to update with
        idx = [i for i, _ in use]
        z = np.array([v for _, v in use], dtype=float)
        zs = sig[:, idx]
        zp = self.wm @ zs
        dz = zs - zp
        S = (self.wc[:, None] * dz).T @ dz + np.eye(len(idx)) * self.r_temp
        Pxz = (self.wc[:, None] * d).T @ dz
        S_inv = np.linalg.inv(S)
        K = Pxz @ S_inv
        v = z - zp
        self.x = self.x + K @ v
        self.P = self.P - K @ S @ K.T
        self.P = 0.5 * (self.P + self.P.T)
        self.last_nis = float(v @ S_inv @ v)
        return self.last_nis

    def get_parameter_estimates(self, t: float) -> List[ParameterEstimate]:
        names = [("eta_cool", f"cyl{i + 1}") for i in range(self.n)] + [("eta_radiator", "radiator"),
                                                                         ("eta_oil_cooler", "oil_cooler")]
        out = []
        for j, (name, loc) in enumerate(names):
            i = self.n_states + j
            mean, std = float(self.x[i]), float(math.sqrt(max(self.P[i, i], 1e-12)))
            out.append(ParameterEstimate(name=name, location=loc, mean=mean, std=std, unit="fraction", t_updated=t,
                                         ci_lower=mean - 1.96 * std, ci_upper=mean + 1.96 * std))
        return out

    def estimates(self) -> Dict[str, float]:
        n = self.n
        return {**{f"cht_{i + 1}": float(self.x[i]) for i in range(n)}, "coolant_t": float(self.x[n]),
                "oil_t": float(self.x[n + 1])}
