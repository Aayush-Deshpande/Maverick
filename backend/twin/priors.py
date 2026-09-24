"""Hierarchical Fleet Priors and Empirical Bayes Personalization (B4.5, SYS-09).

Maintains fleet-wide sufficient statistics (mean and covariance of health parameters theta)
and produces tail-specific prior distributions to accelerate estimator convergence on new tails.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np


@dataclass
class FleetPrior:
    param_names: List[str]
    mean: np.ndarray             # shape (d,)
    covariance: np.ndarray       # shape (d, d)
    sample_count: int = 100

    @classmethod
    def default_nominal(cls, param_names: List[str]) -> "FleetPrior":
        d = len(param_names)
        mean = np.ones(d, dtype=np.float64)
        cov = np.eye(d, dtype=np.float64) * 0.04  # 20% standard deviation across tails
        return cls(param_names=param_names, mean=mean, covariance=cov, sample_count=50)

    def update_with_tail(self, tail_theta: np.ndarray) -> None:
        """Online Welford-style update of fleet prior with a new tail's converged parameters."""
        self.sample_count += 1
        n = self.sample_count
        delta = tail_theta - self.mean
        self.mean += delta / n
        delta2 = tail_theta - self.mean
        self.covariance = ((n - 2) / (n - 1)) * self.covariance + np.outer(delta, delta2) / (n - 1)


class TailPriorEngine:
    """Combines fleet prior with limited initial calibration frames to produce tail initialisation."""

    def __init__(self, fleet_prior: Optional[FleetPrior] = None) -> None:
        self.fleet_prior = fleet_prior or FleetPrior.default_nominal(["eta_cool_1", "eta_cool_2", "eta_cool_3", "eta_cool_4", "eta_rad"])

    def personalize(self, tail_samples: np.ndarray, observation_noise_sigma: float = 0.05) -> Tuple[np.ndarray, np.ndarray]:
        """Empirical Bayes conjugate Gaussian update:
        Prior ~ N(mu_0, Sigma_0)
        Likelihood ~ N(x_bar, (sigma^2 / N) * I)
        Returns (mu_post, Sigma_post).
        """
        mu_0 = self.fleet_prior.mean
        cov_0 = self.fleet_prior.covariance
        inv_cov_0 = np.linalg.pinv(cov_0)

        n_obs = len(tail_samples)
        if n_obs == 0:
            return mu_0.copy(), cov_0.copy()

        x_bar = np.mean(tail_samples, axis=0)
        inv_cov_lik = np.eye(len(mu_0)) * (n_obs / (observation_noise_sigma ** 2))

        cov_post = np.linalg.pinv(inv_cov_0 + inv_cov_lik)
        mu_post = cov_post @ (inv_cov_0 @ mu_0 + inv_cov_lik @ x_bar)

        return mu_post, cov_post
