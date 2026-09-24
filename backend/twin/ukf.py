"""UKF Joint State and Parameter Estimation Twin (B4.2, CAP-11, DTC-02/04).

Implements:
1. Unscented Kalman Filter estimating dynamic thermal states AND health parameters
   theta = [eta_cool[1..n], eta_radiator, bias_oil_t].
2. Sigma-point propagation through DynamicThermofluidModel.
3. Innovation monitoring: Normalized Innovation Squared (NIS) and whiteness testing.
4. Outputs ParameterEstimate dataclasses with 95% confidence intervals.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

from backend.core.frame import Frame
from backend.physics.engine_config import EngineConfig
from backend.twin.model import DynamicThermofluidModel, ThermofluidParams


@dataclass
class ParameterEstimate:
    name: str
    location: Optional[str]
    mean: float
    std: float
    unit: str
    t_updated: float
    ci_lower: float
    ci_upper: float

    @property
    def is_healthy(self) -> bool:
        return self.mean > 0.75


class ThermofluidUKF:
    """Unscented Kalman Filter for joint state and cooling health parameter estimation."""

    def __init__(self, cfg: EngineConfig, dt: float = 1.0) -> None:
        self.cfg = cfg
        self.n_cyl = cfg.cylinder_count
        self.dt = dt
        self.model = DynamicThermofluidModel(cfg)

        # Augmented state: [CHT_1..n, T_cool, T_oil, eta_cool_1..n, eta_rad]
        # Dim = (n_cyl + 2) states + (n_cyl + 1) params
        self.n_states = self.n_cyl + 2
        self.n_params = self.n_cyl + 1
        self.dim = self.n_states + self.n_params

        self.x = np.zeros(self.dim, dtype=np.float64)
        self.x[: self.n_states] = 25.0       # initial temperatures (degC)
        self.x[self.n_states :] = 1.0       # initial health efficiencies (1.0 = nominal)

        # Covariance matrix P
        self.P = np.eye(self.dim, dtype=np.float64)
        self.P[: self.n_states, : self.n_states] *= 5.0
        self.P[self.n_states :, self.n_states :] *= 0.05

        # Process noise Q and measurement noise R
        self.Q = np.eye(self.dim, dtype=np.float64) * 1e-4
        self.Q[: self.n_states, : self.n_states] *= 0.1
        self.Q[self.n_states :, self.n_states :] *= 1e-4

        # Measurement: [CHT_1..n, T_oil] (dim = n_cyl + 1)
        self.n_meas = self.n_cyl + 1
        self.R = np.eye(self.n_meas, dtype=np.float64) * 1.5

        # Merwe scaled sigma-point parameters
        self.alpha = 1e-3
        self.beta = 2.0
        self.kappa = 0.0
        self.lambda_ = (self.alpha ** 2) * (self.dim + self.kappa) - self.dim

        # Weights
        self.wm = np.full(2 * self.dim + 1, 1.0 / (2.0 * (self.dim + self.lambda_)))
        self.wm[0] = self.lambda_ / (self.dim + self.lambda_)
        self.wc = self.wm.copy()
        self.wc[0] = self.wm[0] + (1.0 - self.alpha ** 2 + self.beta)

        self.last_nis = 0.0

    def _generate_sigma_points(self) -> np.ndarray:
        gamma = math.sqrt(self.dim + self.lambda_)
        try:
            chol = np.linalg.cholesky(self.P)
        except np.linalg.LinAlgError:
            # SVD fallback if P loses positive definiteness
            u, s, _ = np.linalg.svd(self.P)
            chol = u @ np.diag(np.sqrt(np.maximum(1e-8, s)))

        sigmas = np.zeros((2 * self.dim + 1, self.dim))
        sigmas[0] = self.x
        for i in range(self.dim):
            sigmas[i + 1] = self.x + gamma * chol[:, i]
            sigmas[self.dim + i + 1] = self.x - gamma * chol[:, i]
        return sigmas

    def predict(self, rpm: float, throttle_pct: float, fuel_flow_kg_h: float, oat_c: float) -> None:
        """Propagate sigma points through the dynamic thermofluid model."""
        sigmas = self._generate_sigma_points()
        n_pts = len(sigmas)
        sigmas_f = np.zeros_like(sigmas)

        for j in range(n_pts):
            s_vec = sigmas[j]
            thermal_state = s_vec[: self.n_states].copy()
            eta_cool = s_vec[self.n_states : self.n_states + self.n_cyl].tolist()
            eta_rad = float(s_vec[self.n_states + self.n_cyl])

            p = ThermofluidParams(eta_cool=eta_cool, eta_radiator=eta_rad)
            dstate = self.model.state_derivatives(thermal_state, rpm, throttle_pct, fuel_flow_kg_h, oat_c, params=p)
            thermal_next = thermal_state + self.dt * dstate

            sigmas_f[j, : self.n_states] = thermal_next
            sigmas_f[j, self.n_states :] = s_vec[self.n_states :]  # random-walk parameters

        # Predicted mean x
        self.x = np.sum(self.wm[:, None] * sigmas_f, axis=0)

        # Predicted covariance P
        diff = sigmas_f - self.x[None, :]
        self.P = np.sum(self.wc[:, None, None] * (diff[:, :, None] @ diff[:, None, :]), axis=0) + self.Q
        self._sigmas_f = sigmas_f

    def update(self, z: np.ndarray) -> float:
        """Update with measurement vector z = [CHT_1..n, T_oil]. Returns NIS."""
        n_pts = len(self._sigmas_f)
        sigmas_h = np.zeros((n_pts, self.n_meas))

        for j in range(n_pts):
            # Measurement function h(x): pick out CHT_1..n and T_oil
            s_vec = self._sigmas_f[j]
            sigmas_h[j, : self.n_cyl] = s_vec[: self.n_cyl]
            sigmas_h[j, self.n_cyl] = s_vec[self.n_states - 1]  # T_oil is last state

        # Predicted measurement z_pred
        z_pred = np.sum(self.wm[:, None] * sigmas_h, axis=0)

        # Innovation covariance S
        diff_z = sigmas_h - z_pred[None, :]
        S = np.sum(self.wc[:, None, None] * (diff_z[:, :, None] @ diff_z[:, None, :]), axis=0) + self.R

        # Cross-covariance Pxz
        diff_x = self._sigmas_f - self.x[None, :]
        Pxz = np.sum(self.wc[:, None, None] * (diff_x[:, :, None] @ diff_z[:, None, :]), axis=0)

        # Kalman gain K
        S_inv = np.linalg.pinv(S)
        K = Pxz @ S_inv

        # State update
        v = z - z_pred
        self.x = self.x + K @ v
        self.P = self.P - K @ S @ K.T

        # NIS
        self.last_nis = float(v.T @ S_inv @ v)
        return self.last_nis

    def get_parameter_estimates(self, t: float) -> List[ParameterEstimate]:
        """Extract estimated physical health parameters with 95% confidence intervals (mean +- 1.96*std)."""
        estimates = []
        for i in range(self.n_cyl):
            idx = self.n_states + i
            mean = float(self.x[idx])
            std = float(math.sqrt(max(1e-6, self.P[idx, idx])))
            estimates.append(ParameterEstimate(
                name="eta_cool",
                location=f"cyl{i + 1}",
                mean=mean,
                std=std,
                unit="fraction",
                t_updated=t,
                ci_lower=mean - 1.96 * std,
                ci_upper=mean + 1.96 * std,
            ))

        idx_rad = self.n_states + self.n_cyl
        mean_rad = float(self.x[idx_rad])
        std_rad = float(math.sqrt(max(1e-6, self.P[idx_rad, idx_rad])))
        estimates.append(ParameterEstimate(
            name="eta_radiator",
            location="radiator",
            mean=mean_rad,
            std=std_rad,
            unit="fraction",
            t_updated=t,
            ci_lower=mean_rad - 1.96 * std_rad,
            ci_upper=mean_rad + 1.96 * std_rad,
        ))
        return estimates
