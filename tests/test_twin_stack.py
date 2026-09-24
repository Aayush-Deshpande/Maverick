"""Tests for Twin Stack (B4.1, B4.2, B4.4, B4.5, B4.6): dynamic twin, UKF estimation, SINDy, priors."""

import numpy as np
import pytest

from backend.physics.engine_config import load_engine_config
from backend.twin.degradation import DegradationParticleFilter, SINDyIdentifier
from backend.twin.model import DynamicThermofluidModel, ThermofluidParams
from backend.twin.priors import FleetPrior, TailPriorEngine
from backend.twin.ukf import ThermofluidUKF


def test_dynamic_thermofluid_model():
    cfg = load_engine_config("rotax_914")
    model = DynamicThermofluidModel(cfg)
    model.reset(t_ambient_c=20.0)

    # Initial state is at ambient
    assert np.allclose(model.state, 20.0)

    # Step for 30 seconds at cruise power
    for _ in range(30):
        state = model.step(dt=1.0, rpm=4800.0, throttle_pct=75.0, fuel_flow_kg_h=20.0, oat_c=20.0)

    # Temperatures should rise above ambient
    assert np.all(state[:4] > 35.0)  # CHTs
    assert state[4] > 25.0           # Coolant
    assert state[5] > 25.0           # Oil


def test_thermofluid_ukf_parameter_tracking():
    cfg = load_engine_config("rotax_914")
    ukf = ThermofluidUKF(cfg, dt=1.0)

    # Synthetic measurements with cylinder 1 degraded cooling
    rng = np.random.default_rng(42)
    for _ in range(60):
        ukf.predict(rpm=4500.0, throttle_pct=70.0, fuel_flow_kg_h=18.0, oat_c=15.0)
        # Injected measurement
        z = np.array([125.0, 105.0, 105.0, 105.0, 85.0]) + rng.normal(0.0, 0.2, size=5)
        nis = ukf.update(z)
        assert not np.isnan(nis)

    estimates = ukf.get_parameter_estimates(60.0)
    assert len(estimates) == 5  # 4 cylinders + radiator
    # Cylinder 1 with hot CHT has lower estimated cooling efficiency
    cyl1_est = [e for e in estimates if e.location == "cyl1"][0]
    cyl2_est = [e for e in estimates if e.location == "cyl2"][0]
    assert cyl1_est.mean < cyl2_est.mean


def test_sindy_sparse_law_discovery():
    sindy = SINDyIdentifier(threshold=0.01)
    # y_dot = 0.5 * x + 0.1 * x^2
    X = np.linspace(0.1, 2.0, 50)[:, None]
    X_dot = 0.5 * X + 0.1 * (X ** 2)

    xi = sindy.fit(X, X_dot)
    pred_dot = sindy.predict_derivative(X)
    assert np.allclose(pred_dot, X_dot, atol=1e-3)


def test_degradation_particle_filter():
    pf = DegradationParticleFilter(n_particles=200, seed=42)
    for _ in range(20):
        pf.predict(dt=1.0, stress_multiplier=1.2)
        pf.update(observed_wear=0.02)

    med, p05, p95 = pf.estimate()
    assert 0.0 <= p05 <= med <= p95 <= 1.0


def test_hierarchical_fleet_priors_personalization():
    prior = FleetPrior.default_nominal(["eta_1", "eta_2", "eta_3", "eta_4", "rad"])
    engine = TailPriorEngine(prior)

    # 10 observed samples from a specific tail with slightly lower efficiency
    tail_obs = np.ones((10, 5)) * 0.92
    mu_post, cov_post = engine.personalize(tail_obs, observation_noise_sigma=0.04)

    # Posterior mean should be between prior (1.0) and tail observation (0.92)
    assert np.all(0.90 <= mu_post) and np.all(mu_post <= 1.0)
    # Posterior covariance should be tighter than prior covariance
    assert np.trace(cov_post) < np.trace(prior.covariance)
