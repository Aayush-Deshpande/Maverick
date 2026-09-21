# Synthetic — our physics-based generator

Our own data. The only source covering all eight PS fault modes for a piston engine.

Design specification: [Part XVII](../../ANUMAAN/docs/study/17_simulation_design.md).

---

## Why this exists

No public dataset contains aero piston engine telemetry with the eight PS fault modes labelled ([`../Piston_Engine/`](../Piston_Engine/README.md)). The PS permits demonstration using "simulated or real engine datasets", so simulation is our primary data source — which makes its quality the ceiling on everything else.

---

## The central design rule

> **Faults modify physical parameters, never output signals directly.**

```python
# WRONG — teaches the model to detect "someone added a constant"
if fault: cht_2 += 30

# RIGHT — physics propagates it, correlations stay correct
if fault: cooling_effectiveness[2] *= 0.6
```

Adding 30 °C to one channel leaves every other channel unchanged, which is the signature of a **sensor** fault, not an engine fault. Degrading cooling effectiveness lets the physics propagate: CHT rises with the correct thermal time constant, oil temperature follows, and cross-sensor correlation is automatically right.

**This single choice determines whether the synthetic data teaches anything real.**

---

## Pipeline

```
Mission profile → Environment (ISA + deviation) → Engine physics (healthy)
    → Degradation model → Fault injection (parameters!) → Sensor model
    → Transport model (CAN framing, link loss, latency)
```

---

## The eight fault models

| # | Fault | Parameter modified | Onset | Emergent signature |
|---|---|---|---|---|
| 1 | Misfire | `combustion_quality[i]` → intermittent 0 | Sudden/intermittent | EGT[i]↓, 0.5-order vibration↑↑, RPM roughness↑ |
| 2 | Injector | `fuel_split[i]` reduced | Gradual | EGT[i] deviates, commanded ≠ achieved |
| 3 | Cooling degradation | `cool_eff[all]` ×0.98/h | Slow | All CHT residuals rise together; worse at altitude |
| 4 | Lubrication | `clearance_factor`↑, `pump_gain`↓ | Very slow | Oil pressure residual↓ at matched RPM/temp |
| 5 | **Sensor drift** | **Sensor model, not physics** | Ramp or step | **Uncorrelated with neighbours** — the tell |
| 6 | Combustion instability | `combustion_quality` variance↑ | Gradual | EGT cycle variance↑, irregular vibration |
| 7 | **Overheating trend** | `cool_eff`↓ **within limits** | Very slow | CHT trending up inside the legal band |
| 8 | Bearing/vibration | `bearing_severity`↑ | Gradual | Envelope line at BPFO, kurtosis↑, RMS↑ late |

**Fault 5 is deliberately injected into the sensor model**, because that is what a sensor fault physically is. This is what makes it separable — the physics never changed, so neighbours are unaffected and the cross-sensor validation test fires correctly.

**Fault 7 is the PS's core ask** — a degradation that never exceeds a limit within the sortie, so only trend detection can catch it. If our generator lets it cross a threshold, we are testing a threshold system, not a predictive one.

---

## Scenario library

| Scenario | Duration | Environment | Fault | Purpose |
|---|---|---|---|---|
| `NOMINAL_CRUISE` | 2 h | Standard | None | Baseline, false-alarm rate |
| `FULL_SORTIE` | 18 h | Standard | None | Endurance, drift behaviour |
| `LADAKH_COOLING_DEGRADE` | 6 h | High, cold | Cooling | Trend detection, large margin |
| `THAR_COOLING_DEGRADE` | 6 h | Hot | **Identical fault** | ★ Same fault, different verdict |
| `MISFIRE_ONSET` | 3 h | Standard | Misfire @T+2h | Vibration detection, latency |
| `BEARING_RUN_TO_FAILURE` | 40 h | Standard | Progressive | RUL development |
| `OIL_DEGRADATION` | 8 h | Standard | Lubrication | Multi-sensor correlation |
| `SENSOR_DRIFT` | 4 h | Standard | CHT₂ drift | ★ Must NOT be classed as engine fault |
| `LINK_LOSS` | 4 h | Standard | Cooling + 20 min outage | ★ Edge autonomy |
| `THROTTLE_TRANSIENTS` | 1 h | Standard | None | Transients must not false-alarm |

The three starred scenarios demonstrate the **architecture** rather than the models, and are the most convincing in a review.

---

## ⚠️ The leakage trap

**If the same generator with the same parameters produces training and test data, the evaluation measures the model's ability to invert our simulator — not to diagnose an engine.**

### Mitigations, in increasing strength

1. **Different parameters for test** — degradation rates, noise levels, environments, mission profiles
2. **Held-out simulated airframes** — different baseline `cool_eff`, `h_base`, wear history
3. **Unseen corruptions in test** — dropouts, drift, packet-loss patterns absent from training
4. **Unseen fault severities and onset rates**
5. **Cross-validate on public proxies** — the strongest defence

### How to report it

> "Fault classification: 0.89 macro F1 on held-out simulated airframes with unseen degradation rates. This is synthetic data from our own physics model, so it validates the pipeline rather than field accuracy. The same methods achieve [X] on C-MAPSS and [Y] on Paderborn, independent public benchmarks."

That sentence is worth more to a knowledgeable evaluator than an unqualified 99%.

---

## Validating the generator

A wrong generator produces a confidently wrong system.

| Check | Test |
|---|---|
| Steady-state plausibility | Cruise values within published Rotax ranges |
| Altitude response | Climb → correct direction and magnitude |
| Thermal time constants | Step throttle → CHT settles over tens of seconds, not instantly |
| **Correlation structure** | 🔶 **Hardest to verify without real data — state as a limitation** |
| Residuals near zero | Our physics model on healthy synthetic data |
| Fault signatures emerge | Each fault produces its signature *without being told to* |
| Spectral content | Order spectrum has correct lines at correct orders |
| Envelope analysis works | Injected bearing fault detectable via envelope FFT |

**The correlation-structure row is the honest weak point.** Without real engine data we cannot confirm our inter-channel correlations match reality — and those correlations are exactly what multivariate detectors learn. State it as a known limitation rather than assuming it away.

---

## Storage

```
Synthetic/
├── README.md              (this file)
├── scenarios/             scenario definition files (YAML/JSON)
└── generated/             output — gitignored
    ├── <scenario>/
    │   ├── telemetry.parquet
    │   ├── vibration.npy
    │   ├── labels.json
    │   └── metadata.json    ← generator version, parameters, seed
```

**Every generated dataset must carry `metadata.json`** recording generator version, parameters and random seed. Without it, results are not reproducible and the split cannot be audited later.
