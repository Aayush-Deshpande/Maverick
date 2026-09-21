# Part VII — Anomaly Detection

*"Something is wrong" — without being told in advance what wrong looks like.*

---

## 7.1 Anomaly detection versus fault classification

These are different problems. Conflating them is one of the most common design errors in PHM.

| | Anomaly detection | Fault classification |
|---|---|---|
| **Question** | Is this normal? | Which known fault is this? |
| **Output** | A score, 0→1 | A label + confidence |
| **Training data** | Healthy data only | Labelled examples of every fault |
| **Learning type** | Unsupervised / one-class | Supervised, multi-class |
| **Handles unknown faults** | ✅ Yes — anything unlike normal scores high | ❌ No — forced into a known class |
| **Data availability** | Abundant (every healthy flight) | Scarce (faults are rare) |
| **Where it belongs** | Edge and ground | Ground |

**Why you need both.** Anomaly detection is your safety net: it catches the fault mode nobody anticipated, which on a one-engine aircraft is exactly the scenario that kills you. Classification is your actionability: "anomaly score 0.89" does not tell a maintainer what to do; "injector fault on cylinder 2, 94% confidence" does.

**The operational pattern:**

```
  Anomaly detector (always on, unsupervised)
           │  score crosses threshold
           ▼
  Fault classifier (invoked on the flagged window)
           │
      ┌────┴────┐
      ▼         ▼
  Known fault   No class above confidence
  → named       → "UNKNOWN ANOMALY" ← this is a FEATURE, not a failure.
    advisory       It means the safety net caught something new.
```

⬜ Our system must be able to say "anomalous, but unclassified". A classifier forced to always pick from eight known faults will confidently mislabel a ninth, which is worse than admitting ignorance.

---

## 7.2 The methods

### 7.2.1 Statistical control charts

**What it is.** Track a statistic over time; alarm when it leaves control limits derived from healthy operation. Typically `μ ± 3σ`, or better, CUSUM/EWMA which accumulate small persistent deviations.

| Property | Assessment |
|---|---|
| Detects | Shifts and drifts in a single monitored variable |
| Input | One scalar (raw or residual) |
| Assumes | Roughly stationary, roughly Gaussian in healthy state |
| Cost | Trivial — O(1) per sample, a few bytes of state |
| Advantages | Completely interpretable, no training, decades of industrial acceptance, trivially certifiable |
| Disadvantages | Univariate — blind to correlation breakdown between variables |
| Edge | ✅ Ideal |
| GCS | ✅ Useful as a baseline |

**Why we should absolutely include this.** It is the honest baseline. If a sophisticated model cannot beat EWMA on residuals, the sophistication is not earning its place. 🔶 It is also the component most likely to survive a certification review, and it makes an excellent always-on fallback layer.

**Important subtlety:** applied to **residuals** (actual − physics-expected) rather than raw values, a control chart becomes far more powerful, because the residual is already regime-normalised. Much of the "AI" benefit people attribute to models actually comes from computing good residuals first.

### 7.2.2 Mahalanobis distance

**What it is.** A multivariate distance that accounts for correlation between variables:

```
D²(x) = (x − μ)ᵀ Σ⁻¹ (x − μ)
```

where `Σ` is the covariance matrix of healthy data.

**The key insight.** Euclidean distance treats all directions equally. Mahalanobis asks: *given how these variables normally co-vary, how surprising is this combination?*

Concrete example: on a healthy engine, CHT and EGT on the same cylinder rise and fall together. Suppose CHT is high and EGT is high — individually each may be within limits, and jointly it is *normal*. Now suppose CHT is high while EGT is **low**. Each may still be within its own limits, but the combination violates the normal correlation. Mahalanobis flags it; two independent control charts do not.

| Property | Assessment |
|---|---|
| Detects | Breakdown of normal correlation structure between variables |
| Input | A feature vector |
| Assumes | Approximately multivariate Gaussian, stable covariance |
| Cost | Very low — one matrix multiply; `Σ⁻¹` precomputed |
| Advantages | Multivariate, principled, fast, one interpretable number, no iterative training |
| Disadvantages | Gaussian assumption; covariance estimation needs enough data; breaks if regimes are mixed |
| Edge | ✅ Excellent |
| GCS | ✅ Good |

⬜ **This is an underrated choice and we should use it.** It is nearly free, genuinely multivariate, and catches the cross-sensor inconsistencies that are the hallmark of real engine faults. Fit `Σ` on healthy residuals, per flight regime.

### 7.2.3 PCA residuals (reconstruction error)

**What it is.** Fit PCA on healthy data, keep the top `k` components, project a new sample down and back up, and measure reconstruction error (the "Q statistic" / SPE).

**The intuition.** Healthy data lies on a low-dimensional manifold — the sensors are heavily correlated because they are all driven by a few underlying physical states. A sample that cannot be reconstructed from that manifold has left the healthy subspace.

| Property | Assessment |
|---|---|
| Detects | Departures from the healthy correlation manifold |
| Input | Feature vector |
| Assumes | Healthy behaviour is approximately linear/low-rank |
| Cost | Very low — two matrix multiplies |
| Advantages | **Contribution analysis tells you which sensor drove the error** — built-in explainability |
| Disadvantages | Linear only; misses nonlinear relationships |
| Edge | ✅ Excellent |
| GCS | ✅ Good |

🔶 The contribution-analysis property is valuable and often overlooked: PCA gives you a per-sensor attribution for free, from the same computation, with no separate explainer. See [Part XX](20_novelty_and_research.md) on explainability cost.

### 7.2.4 Isolation Forest

**What it is.** Build random trees that split on random features at random thresholds. Anomalies get isolated in fewer splits because they sit in sparse regions. The anomaly score is derived from average path length.

**The clever inversion:** most methods model normality and measure deviation. Isolation Forest directly exploits the fact that *anomalies are easier to separate*.

| Property | Assessment |
|---|---|
| Detects | Points in low-density regions of feature space |
| Input | Feature vector |
| Assumes | Anomalies are few and different — no distributional assumption |
| Cost | Training moderate; inference cheap (tree traversal) |
| Advantages | No Gaussian assumption, handles nonlinearity, robust, minimal tuning, good with mixed feature scales |
| Disadvantages | Scores are not calibrated probabilities; less interpretable than PCA/Mahalanobis; struggles in very high dimensions |
| Edge | 🔶 Feasible — inference is cheap, but the forest must be stored |
| GCS | ✅ Excellent |

✅ Isolation forests are explicitly named among standard anomaly-detection approaches in the PHM literature and in the team's own architecture doc.

### 7.2.5 One-Class SVM

**What it is.** Learn a boundary enclosing the healthy data in a kernel-induced feature space. Anything outside is anomalous.

| Property | Assessment |
|---|---|
| Detects | Points outside the learned healthy boundary |
| Input | Feature vector, **scaling-sensitive** |
| Assumes | Healthy data forms a coherent region |
| Cost | Training O(n²)–O(n³) — poor scaling; inference depends on support-vector count |
| Advantages | Nonlinear via kernels, strong theory, effective on modest datasets |
| Disadvantages | Sensitive to `ν` and `γ`; scales badly; needs careful normalisation; boundary not interpretable |
| Edge | ❌ Generally not — inference cost depends on support vectors |
| GCS | 🔶 Workable but usually outperformed in practice by Isolation Forest or an autoencoder |

⬜ **Honest assessment:** include it as a benchmark comparator, not as the primary detector. Its hyperparameter sensitivity is a real operational liability.

### 7.2.6 Autoencoders

**What it is.** A neural network trained to reconstruct its input through a narrow bottleneck, using healthy data only. High reconstruction error on new data indicates something the network never learned to represent.

```
input (14–40 features) → encode → bottleneck (2–8) → decode → reconstruction
                                                                   │
                            anomaly score = ‖input − reconstruction‖
```

| Property | Assessment |
|---|---|
| Detects | Departures from a learned nonlinear manifold of normality |
| Input | Feature vector, or a sequence (with LSTM/conv layers) |
| Assumes | Enough healthy data to learn the manifold |
| Cost | Training moderate; inference cheap for small nets |
| Advantages | Nonlinear, flexible, scales to high dimensions, per-feature error gives attribution |
| Disadvantages | Needs substantial data; can generalise *too well* and reconstruct anomalies; bottleneck size is a sensitive hyperparameter; less interpretable |
| Edge | ✅ Yes if small and quantised (✅ int8 MLPs are standard in TinyML vibration pipelines) |
| GCS | ✅ Excellent |

**The failure mode to watch:** an over-capacity autoencoder learns the identity function and reconstructs everything, including faults, giving uniformly low error. The bottleneck must be genuinely narrow. Validate by confirming the error distribution on held-out *faulty* data is clearly separated from healthy.

---

## 7.3 Comparison table

| Method | Multivariate | Nonlinear | Training data | Inference cost | Interpretable | Edge | GCS |
|---|---|---|---|---|---|---|---|
| Control chart / EWMA | ❌ | ❌ | Minimal | Trivial | ★★★★★ | ✅ | ✅ |
| Mahalanobis | ✅ | ❌ | Small | Very low | ★★★★ | ✅ | ✅ |
| PCA residual | ✅ | ❌ | Small | Very low | ★★★★ | ✅ | ✅ |
| Isolation Forest | ✅ | ✅ | Moderate | Low | ★★ | 🔶 | ✅ |
| One-Class SVM | ✅ | ✅ | Moderate | Medium | ★ | ❌ | 🔶 |
| Autoencoder | ✅ | ✅ | Large | Low–medium | ★★ | ✅ | ✅ |

---

## 7.4 The regime problem — the mistake that sinks naive anomaly detection

A UAV engine operates across takeoff, climb, cruise, loiter, descent, at altitudes from sea level to 30,000 ft, and ambient temperatures from +45 °C to −40 °C.

**If you fit one "normal" model across all of that, you get a model that is either so wide it detects nothing, or so narrow it alarms constantly.**

Three ways to handle it, in increasing order of quality:

| Approach | How | Assessment |
|---|---|---|
| **Regime segmentation** | Separate models per flight phase | Simple; needs enough data per regime; boundaries are arbitrary |
| **Condition normalisation** | Include altitude/OAT/RPM/throttle as features | Standard ML practice; ✅ this is what C-MAPSS's 3 operational settings exist for |
| **Physics residuals** ⬜ | Model the *residual* from a physics-based expectation | **Best.** Regime dependence is removed by the physics, not learned from data |

⬜ **Our choice: physics residuals, with regime tagging as a secondary feature.**

The reasoning matters. If the thermodynamic model already accounts for altitude and ambient temperature, then the residual should be near zero in *every* regime for a healthy engine. The anomaly detector then works on a signal that is intrinsically regime-independent, and needs far less data to characterise. This is what "physics-informed" ✅ (a PS-named innovation area) actually buys you in practice — it is not decoration, it is the thing that makes the statistics tractable.

---

## 7.5 Sensor fault versus engine fault

✅ A key PS fault target is "sensor drift / failure". Critically, a sensor failure must **never** be reported as engine destruction.

The discriminators:

| Test | Sensor fault | Real engine fault |
|---|---|---|
| **Rate of change** | Physically impossible (e.g. +30 °C in one 50 ms frame) | Follows heat-transfer physics (≲1–2 °C/s for a cylinder head) |
| **Cross-sensor correlation** | Isolated — neighbours unaffected | Correlated — adjacent CHT, oil temp, EGT move consistently |
| **Noise floor** | Perfectly flat (frozen ADC) or railed (open circuit) | Retains natural analog ripple (±0.2 °C typical) |
| **Physics plausibility** | Violates energy balance | Consistent with a physical mechanism |
| **Lane comparison** | Diverges between redundant lanes | Both lanes agree |

🔶 The lane-comparison row is a real opportunity: ✅ the Rotax 912 iS has two ECU lanes, and interface hardware can read both. A growing divergence between lane A and lane B on the same nominal parameter is a strong, nearly unambiguous sensor-fault indicator — and, as a slowly-widening gap, it is also a clean degradation signal suitable for RUL ([Part IX](09_rul_prognostics.md)).

⬜ **Architectural placement: this check runs first, at the edge, before anything else.** A validated-sensor flag accompanies every value. Downstream models must never see a value that failed validation, because a single railed thermocouple will otherwise dominate every anomaly score in the system.

---

## 7.6 Our recommended stack

⬜ A layered design, each layer catching what the previous one misses:

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 0 — SENSOR VALIDITY (edge, always)                    │
│   Range, rate-of-change, noise-floor, lane divergence       │
│   → Output: per-sensor valid/invalid flag                   │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1 — PHYSICS RESIDUALS (edge)                          │
│   residual = measured − thermodynamic_expected(alt,OAT,RPM) │
│   → Output: regime-independent residual vector              │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2 — STATISTICAL (edge, cheap, always on)              │
│   EWMA control charts + Mahalanobis on residuals            │
│   → Survives link loss. Certifiable. The honest baseline    │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3 — LEARNED (edge for vibration, GCS for the rest)    │
│   Small autoencoder on residuals + vibration features       │
│   → Catches nonlinear/multivariate patterns Layer 2 misses  │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│ LAYER 4 — FUSION (GCS)                                      │
│   Combine scores with sensor-validity context and flight    │
│   phase into a single health index + severity               │
└─────────────────────────────────────────────────────────────┘
```

**Why layered rather than one model.** Different layers fail differently. The statistical layer is transparent and always available. The learned layer is more sensitive but needs data and is harder to justify. Running both, and requiring agreement for high-severity alerts, reduces false alarms — which, as [Part XIX](19_evaluation.md) argues, is the metric that actually determines whether operators keep the system switched on.

---

## 7.7 Choosing the threshold

The model outputs a score. Somebody must choose where the alarm fires. **This is a policy decision, not a modelling one, and it should be made explicitly rather than by accepting a library default.**

The trade-off:

```
Threshold too low  → false alarms → operators stop trusting alerts
                                  → the system is ignored → worthless
Threshold too high → missed faults → the aircraft is lost
```

⬜ Practical approach:

1. Set the threshold from the **healthy-data false-alarm rate** you can tolerate — e.g. the 99.9th percentile of healthy scores, yielding roughly one false alarm per 1,000 windows.
2. **Convert to alarms per flight hour**, which is the number an operator actually cares about. At 20 Hz, 0.1% of windows is ~72 alarms per hour — obviously unusable. This calculation is sobering and necessary.
3. Require **persistence**: N consecutive windows above threshold before alarming. This trades a little detection latency for an enormous reduction in false alarms, and is standard practice.
4. Use **severity tiers** (advisory / caution / warning) rather than a single binary alarm.

🔶 Step 2 is the one teams skip, and it is the one that determines whether the system is usable. A per-sample false positive rate that looks excellent becomes an alarm storm once multiplied by the sample rate and the flight duration.

---

**Next:** [Part VIII — Fault Diagnosis and Classification](08_fault_diagnosis.md)
