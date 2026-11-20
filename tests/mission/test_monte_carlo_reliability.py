"""M4-04 (idea text I-09): forward Monte Carlo mission reliability. Seeded runs are identical, the healthy result
agrees with the closed form within its Wilson interval, and a predicted limit crossing inside the mission becomes the
limiting abort cause, in the phase where it falls; a crossing far beyond the mission changes nothing."""
from backend.mission.reliability import ISR_18H_PROFILE, MissionReliabilityEngine


def test_seeded_and_agrees_with_analytic():
    a = MissionReliabilityEngine(seed=5).simulate_with_limits(ISR_18H_PROFILE, 20000)
    b = MissionReliabilityEngine(seed=5).simulate_with_limits(ISR_18H_PROFILE, 20000)
    assert a == b
    exact = MissionReliabilityEngine(seed=5).analytic_reliability(ISR_18H_PROFILE)["reliability"]
    assert a["ci_lower"] - 1e-3 <= exact <= a["ci_upper"] + 1e-3


def test_limit_crossing_drives_the_abort():
    e = MissionReliabilityEngine(seed=6)
    near = e.simulate_with_limits(ISR_18H_PROFILE, 5000, limit_crossings=[
        {"channel": "oil_t", "time_to_limit_s": 2 * 3600, "low_s": 1.5 * 3600, "high_s": 3 * 3600}])
    assert near["reliability"] < 0.05 and near["limiting_component"] == "limit:oil_t"
    assert max(near["failure_phase_distribution"], key=near["failure_phase_distribution"].get) == "TRANSIT"
    far = e.simulate_with_limits(ISR_18H_PROFILE, 5000, limit_crossings=[
        {"channel": "oil_t", "time_to_limit_s": 400 * 3600, "low_s": 300 * 3600, "high_s": 500 * 3600}])
    assert far["reliability"] > 0.99
