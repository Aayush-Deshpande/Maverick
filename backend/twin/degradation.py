"""Degradation Particle Filter and SINDy Law Identification (B4.4, CAP-05/13, INN-01).

Implements:
1. Degradation particle filter propagating non-linear physics-of-failure wear trajectories.
2. SINDy (Sparse Identification of Nonlinear Dynamics) discovering governing wear laws
   d(theta)/dt = Xi * Theta(theta, u) via sequential thresholded least squares (STLS).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


class SINDyIdentifier:
    """Sparse Identification of Nonlinear Dynamics (Brunton et al., PNAS 2016)."""

    def __init__(self, threshold: float = 0.05, max_iter: int = 10) -> None:
        self.threshold = threshold
        self.max_iter = max_iter
        self.xi: Optional[np.ndarray] = None
        self.feature_names: List[str] = []

    def build_library(self, X: np.ndarray, U: Optional[np.ndarray] = None) -> np.ndarray:
        """Build polynomial feature candidate library Theta(X, U).
        X: (n_samples, n_vars) - state trajectories e.g. [damage, wear]
        U: (n_samples, n_inputs) - operating conditions e.g. [temperature, rpm]
        """
        n_samples, n_vars = X.shape
        cols = [np.ones((n_samples, 1))]
        self.feature_names = ["1"]

        # Linear state terms
        for i in range(n_vars):
            cols.append(X[:, i : i + 1])
            self.feature_names.append(f"x{i+1}")

        # Quadratic terms
        for i in range(n_vars):
            for j in range(i, n_vars):
                cols.append((X[:, i] * X[:, j])[:, None])
                self.feature_names.append(f"x{i+1}*x{j+1}")

        # Input interaction terms if U provided
        if U is not None:
            n_inputs = U.shape[1]
            for k in range(n_inputs):
                cols.append(U[:, k : k + 1])
                self.feature_names.append(f"u{k+1}")
                for i in range(n_vars):
                    cols.append((X[:, i] * U[:, k])[:, None])
                    self.feature_names.append(f"x{i+1}*u{k+1}")

        return np.hstack(cols)

    def fit(self, X: np.ndarray, X_dot: np.ndarray, U: Optional[np.ndarray] = None) -> np.ndarray:
        """Sequential Thresholded Least Squares (STLS) to identify sparse coefficient matrix Xi."""
        Theta = self.build_library(X, U)
        n_features = Theta.shape[1]
        n_targets = X_dot.shape[1]

        # Initial least-squares solve
        Xi = np.linalg.pinv(Theta) @ X_dot

        # STLS iterations: zero out small coefficients below threshold and re-solve
        for _ in range(self.max_iter):
            small_idx = np.abs(Xi) < self.threshold
            Xi[small_idx] = 0.0

            for k in range(n_targets):
                big_idx = ~small_idx[:, k]
                if np.sum(big_idx) > 0:
                    Xi[big_idx, k] = np.linalg.pinv(Theta[:, big_idx]) @ X_dot[:, k]

        self.xi = Xi
        return Xi

    def predict_derivative(self, X: np.ndarray, U: Optional[np.ndarray] = None) -> np.ndarray:
        """Evaluate identified governing equations dX/dt = Theta(X, U) @ Xi."""
        if self.xi is None:
            raise RuntimeError("SINDy model not fitted yet")
        Theta = self.build_library(X, U)
        return Theta @ self.xi


class DegradationParticleFilter:
    """Propagates wear and damage accumulation state using Sequential Importance Resampling (SIR)."""

    def __init__(self, n_particles: int = 500, seed: int = 42) -> None:
        self.n_particles = n_particles
        self.rng = np.random.default_rng(seed)

        # Particles: [wear_state_0..1, wear_rate]
        self.particles = np.zeros((n_particles, 2), dtype=np.float64)
        self.particles[:, 0] = self.rng.uniform(0.0, 0.05, size=n_particles)  # initial wear
        self.particles[:, 1] = self.rng.normal(1e-4, 2e-5, size=n_particles)  # initial wear rate
        self.weights = np.full(n_particles, 1.0 / n_particles)

    def predict(self, dt: float, stress_multiplier: float = 1.0) -> None:
        """Advance particles through physics-of-failure degradation step."""
        # Random walk on wear rate + stress acceleration
        rate_noise = self.rng.normal(0.0, 1e-6, size=self.n_particles)
        self.particles[:, 1] = np.maximum(1e-7, self.particles[:, 1] + rate_noise)

        # Accumulate wear: dW = rate * stress * dt
        dW = self.particles[:, 1] * stress_multiplier * dt
        self.particles[:, 0] = np.clip(self.particles[:, 0] + dW, 0.0, 1.0)

    def update(self, observed_wear: float, sensor_sigma: float = 0.03) -> None:
        """Update particle weights from observed parameter wear indicator."""
        # Gaussian likelihood
        errors = self.particles[:, 0] - observed_wear
        likelihood = np.exp(-0.5 * (errors / sensor_sigma) ** 2) / (math.sqrt(2 * math.pi) * sensor_sigma)
        self.weights *= likelihood
        sum_w = np.sum(self.weights)
        if sum_w > 1e-12:
            self.weights /= sum_w
        else:
            self.weights = np.full(self.n_particles, 1.0 / self.n_particles)

        # Resample if effective particle count is low
        n_eff = 1.0 / np.sum(self.weights ** 2)
        if n_eff < self.n_particles / 2.0:
            indices = self.rng.choice(self.n_particles, size=self.n_particles, p=self.weights)
            self.particles = self.particles[indices].copy()
            self.weights = np.full(self.n_particles, 1.0 / self.n_particles)

    def estimate(self) -> Tuple[float, float, float]:
        """Returns (median_wear, p05_lower, p95_upper)."""
        wear_samples = self.particles[:, 0]
        med = float(np.median(wear_samples))
        p05 = float(np.percentile(wear_samples, 5.0))
        p95 = float(np.percentile(wear_samples, 95.0))
        return med, p05, p95
