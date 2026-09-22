# Part IX — RUL and Prognostics

*Predicting the future, why it is much harder than detecting the present, and how to be honest about uncertainty.*

---

## 9.1 What RUL means

**Remaining Useful Life** is the estimated time a component can continue operating before it is no longer fit for use.

```
RUL(t) = t_failure − t_now
```

Units are flight hours, cycles, or minutes. The difficulty hides entirely inside `t_failure`, which has not happened yet and may never happen if you intervene.

### What "failure" actually means — four different definitions

This is the first thing most teams get wrong. "Failure" is not one thing:

| Definition | Example | Who decides |
|---|---|---|
| **Functional failure** | Engine stops producing usable power | Physics |
| **Limit exceedance** | CHT exceeds the certified limit | Manufacturer/certification |
| **Serviceability limit** | Vibration exceeds the level permitted for continued operation | Maintenance manual |
| **Economic/operational limit** | Repair now becomes cheaper/safer than continuing | Operator policy |

⬜ **Our choice:** predict time until a defined **health-index threshold** is crossed, and state that definition explicitly in every output. An RUL number without a stated failure criterion is meaningless — "4 hours until what?" must always have an answer.

### Degradation versus failure

Failure is an event. Degradation is the process leading to it, and it is what you can actually measure.

```
health
  100 │━━━━━━━━━━──────╲
      │                 ╲___              ← degradation: measurable, gradual
   50 │                     ╲___
      │                         ╲__
    0 │─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─╲─ ─ ─  ← failure threshold (a CHOICE)
      └────────────────────────────┴────── time
                                   ▲
                              predicted t_failure
      ├────────── now ─────────────┤
                  └──── RUL ───────┘
```

**Prognostics requires a monotonic (or nearly monotonic) degradation indicator.** If your health index goes up and down, you cannot extrapolate it. Finding a good indicator is usually harder, and more valuable, than choosing the model that extrapolates it.

---

## 9.2 Why prognosis is much harder than diagnosis

| | Diagnosis | Prognosis |
|---|---|---|
| Question | What is happening now? | What will happen, and when? |
| Ground truth | Observable — inspect the engine | Only known after failure |
| Training data | Labelled fault examples | **Complete run-to-failure trajectories** |
| Data availability | Hard | **Very** hard |
| Validation | Immediate | Must wait for the failure |
| Output | A label | A number, ideally with a distribution |
| Sensitivity | Moderate | Extreme — small trend-slope errors compound over the horizon |

**The data problem is the crux.** ✅ It is stated plainly in the federated-learning literature: "A major challenge when developing prognostics is the limited number of run-to-failure data samples," which motivates federated approaches so multiple operators can pool learning without sharing data. ([Federated RUL prognostics](https://www.sciencedirect.com/science/article/pii/S0167739X25002407))

Think about what a run-to-failure sample costs: you must operate a real engine until it actually fails, instrumented throughout. For an aero engine this is enormously expensive and hazardous. **This is why C-MAPSS — a simulator — is the field's standard benchmark.** Real run-to-failure data barely exists.

🔶 **INFERENCE for us:** honest RUL from real UAV engine data is not achievable within an SIH prototype, because nobody has the data. What *is* achievable, and defensible, is a physically-grounded degradation model with clearly-stated assumptions, validated on simulated trajectories and on public proxy data such as C-MAPSS. Claiming validated RUL on a real Rotax would be a claim we cannot support.

**The error-compounding problem.** RUL extrapolates a trend. A small slope error becomes a large time error:

```
Health at 60, threshold 30, true decline 2 units/hour  →  true RUL = 15 h
Estimated decline 2.4 units/hour (20% slope error)     →  est. RUL = 12.5 h
                                                          17% RUL error
```

And the error grows as the horizon lengthens. **Long-horizon RUL is intrinsically imprecise, and any system that reports it as a bare number without uncertainty is misleading its operator.**

---

## 9.3 Health index construction

Before predicting RUL you need a single scalar that degrades monotonically.

⬜ Approaches, roughly in increasing sophistication:

| Method | How | Comment |
|---|---|---|
| **Single physical indicator** | Pick one degrading quantity (vibration RMS, oil pressure residual) | Transparent; may be noisy or miss multi-mode degradation |
| **Weighted composite** | Normalise several residuals, weight by engineering judgment | Simple, explainable, needs expert input |
| **PCA first component** | Largest-variance direction of residuals over time | Data-driven; sign/scale are arbitrary and need anchoring |
| **Autoencoder reconstruction error** | Deviation from healthy manifold | Captures nonlinear degradation; less interpretable |
| **Physics-derived efficiency** ⬜ | Thermodynamic efficiency, SFC trend | **Most defensible** — a real engineering quantity |

⬜ **Our recommendation: a composite with named, physically meaningful contributors**, so the dashboard can always answer "why did health drop?" with "because vibration band energy rose and oil-pressure residual fell", rather than "because component 1 decreased".

Requirements for a usable health index:
- **Monotonic** in expectation (it may be noisy, but must not systematically reverse)
- **Normalised** so 100 = healthy, threshold = defined limit
- **Regime-independent** — built from residuals, not raw values, or it will fall during every climb
- **Decomposable** — you can name its contributors

---

## 9.4 RUL modelling approaches

### 9.4.1 Trend extrapolation — the honest baseline

Fit a curve to recent health history, extrapolate to the threshold.

```python
# Linear extrapolation with an explicit uncertainty band
slope, intercept = np.polyfit(t_recent, health_recent, 1)
rul = (threshold - health_now) / slope        # slope is negative
```

| Property | Assessment |
|---|---|
| Data needed | Only this engine's own history |
| Assumes | Degradation continues at the current rate |
| Cost | Trivial |
| Advantages | Fully transparent; uncertainty from the fit is principled; works with **no** training data |
| Disadvantages | Blind to acceleration; sensitive to the window length |

**Do not dismiss this.** ✅ The team's own PS breakdown already notes that simple linear extrapolation is "a reasonable, honest starting point", and that a black-box number with no visible degradation trend behind it is not RUL at all. For a prototype with no run-to-failure data, extrapolation with visible trend lines and confidence bands is both defensible and demonstrable. It should be the baseline every fancier model must beat.

### 9.4.2 LSTM

Recurrent network with gates that let it retain information over long sequences.

✅ **VERIFIED** — LSTM is the standard workhorse for C-MAPSS RUL, typically with min-max normalisation and sequence generation from the time series, trained against RMSE. ([RUL prediction for aircraft engines using LSTM](https://arxiv.org/pdf/2401.07590))

| Property | Assessment |
|---|---|
| Input | Sequence of feature vectors (a sliding window of cycles) |
| Captures | Long-range temporal dependencies, degradation dynamics |
| Data needed | Many run-to-failure trajectories |
| Cost | Moderate training; sequential inference (cannot parallelise over time) |
| Edge | 🔶 Possible if small, but unnecessary — RUL does not need to be onboard |

### 9.4.3 GRU

Simplified LSTM with two gates instead of three. Fewer parameters, faster, often comparable accuracy. ⬜ A reasonable default when data is limited, precisely because it has fewer parameters to overfit.

### 9.4.4 CNN-LSTM hybrids

Convolutional layers extract local temporal features; recurrent layers model long-range evolution.

✅ **VERIFIED** — CNN-LSTM with attention is an established architecture for aircraft-engine RUL. ([Enhanced CNN-LSTM with attention, PeerJ](https://peerj.com/articles/cs-1084/), [CNN-LSTM adaptations, Aeronautical Journal](https://www.cambridge.org/core/journals/aeronautical-journal/article/introducing-cnnlstm-network-adaptations-to-improve-remaining-useful-life-prediction-of-complex-systems/323F3E31FBD379FC5CED9A1170594AC9))

### 9.4.5 Attention and Transformers

Attention lets the model weight which past time steps matter for the current prediction, rather than compressing everything into a fixed hidden state.

✅ Temporal deep degradation networks with attention-based feature extraction are established on C-MAPSS. ([TDDN](https://arxiv.org/pdf/2202.10916)) ✅ Spatio-temporal attention combined with physics-informed networks has also been applied. ([Hidden physics-informed RUL](https://arxiv.org/pdf/2405.12377))

| Property | Assessment |
|---|---|
| Advantages | Parallel training; long-range dependencies; attention weights give some interpretability |
| Disadvantages | **Data-hungry** — the weakest fit for our situation; more hyperparameters |

🔶 **INFERENCE:** Transformers are the wrong choice for a project with scarce data. Their advantage appears at scale, and we do not have scale.

### 9.4.6 Graph Neural Networks

Model sensors as graph nodes with relationships as edges, letting the model reason over sensor topology.

✅ There is a survey specifically on GNNs for RUL. ([GNN RUL survey](https://arxiv.org/pdf/2409.19629))

🔶 Intellectually appealing for an engine, where physical coupling between sensors is real and known. But it adds complexity for a gain that is unlikely to be demonstrable on our data volume. ⬜ Note it as future work; do not build it now.

---

## 9.5 Model comparison

| Model | Input | Data needed | Train cost | Inference | Interpretable | Fit for us |
|---|---|---|---|---|---|---|
| Linear extrapolation | Health history | None | None | Trivial | ★★★★★ | ✅ **Baseline — build first** |
| Exponential/power-law fit | Health history | None | Trivial | Trivial | ★★★★ | ✅ Good second step |
| Particle filter | Health + degradation model | Model, not data | Low | Low | ★★★★ | ✅ **Natural uncertainty** |
| GRU | Sequences | Many trajectories | Moderate | Low | ★ | 🔶 If enough simulated data |
| LSTM | Sequences | Many trajectories | Moderate | Low | ★ | 🔶 Same |
| CNN-LSTM + attention | Sequences | Many | High | Moderate | ★★ | 🔶 Only if data supports it |
| Transformer | Long sequences | **Very** many | High | Moderate | ★★ | ❌ Data-starved here |
| GNN | Graph + sequences | Many | High | Moderate | ★★ | ❌ Future work |

---

## 9.6 Uncertainty — non-negotiable

**A point-estimate RUL is unsafe.** "RUL = 3.4 hours" invites an operator to plan a 3-hour sortie. "RUL = 3.4 h, 80% confidence interval [1.8, 6.1] h" invites them to plan a 1.5-hour sortie, which is the correct decision.

✅ Uncertainty quantification in prognostics is a recognised field with its own tutorial literature. ([UQ in ML for engineering design and health prognostics](https://arxiv.org/pdf/2305.04933))

⬜ Ways to produce intervals, in increasing sophistication:

| Method | How | Comment |
|---|---|---|
| **Regression prediction interval** | From the fit's residual variance | Free with linear extrapolation; assumes the trend model is right |
| **Bootstrap / ensemble** | Train N models, use the spread | Simple, robust, N× cost |
| **MC Dropout** | Keep dropout on at inference, sample | Cheap for neural models; approximate |
| **Quantile regression** | Predict quantiles directly | Gives asymmetric intervals, which is what we want |
| **Particle filter** | Propagate a particle distribution through a degradation model | ✅ Principled; naturally produces a full RUL distribution |

⬜ **Our recommendation:** trend extrapolation with prediction intervals for the prototype; a particle filter as the sophisticated option, because it fuses a physical degradation model with observations and yields a genuine distribution rather than a bolt-on error bar.

**Presentation rule:** the dashboard must never show an RUL number without its interval, and should display the underlying degradation trend line alongside it. An RUL with no visible trend behind it is decoration.

---

## 9.7 Asymmetric scoring — why late prediction is worse

✅ **VERIFIED** — this is built into the standard C-MAPSS evaluation: "RMSE is a symmetric loss that assigns the same penalties for over- and under-prediction; however, the scoring function assigns more penalty when the predicted RUL is larger than the true RUL, which would delay the maintenance plan." ([Asymmetric-loss RUL modelling](https://arxiv.org/pdf/2604.13459))

```
Predicted 10 h, actual 15 h  → early. Cost: unnecessary maintenance, lost availability
Predicted 15 h, actual 10 h  → late.  Cost: in-flight engine failure, aircraft lost
```

These are not comparable costs, so the loss function must not treat them as comparable. The standard C-MAPSS score uses exponential penalties with a steeper branch for late predictions:

```
d = RUL_predicted − RUL_true

d < 0 (early):  s = exp(−d/13) − 1       ← gentler
d ≥ 0 (late):   s = exp( d/10) − 1       ← steeper
```

⬜ **We should train with an asymmetric loss, report both RMSE and the asymmetric score, and say why.** Doing so demonstrates that we understand the operational consequence, which is exactly the kind of judgment a defence evaluator is looking for.

---

## 9.8 Prognostic-specific metrics

✅ **VERIFIED** — Saxena et al. introduced four metrics now standard in the PHM community: **Prognostic Horizon**, **α-λ performance**, **Relative Accuracy**, and **Convergence**. NASA maintains a Prognostics Metrics Library. ([On applying prognostic performance metrics, NASA](https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/20100023445.pdf), [NASA PrognosticsMetricsLibrary](https://github.com/nasa/PrognosticsMetricsLibrary))

| Metric | Meaning |
|---|---|
| **Prognostic Horizon (PH)** | ✅ How far in advance of end-of-life the algorithm predicts RUL within desired α-bounds. **Longer is better** — this is the metric closest to operational value |
| **α-λ performance** | ✅ Binary at each time step: is the prediction within an α-band at fraction λ of the way through life? |
| **Relative Accuracy** | Accuracy relative to remaining life at the prediction time |
| **Convergence** | ✅ How quickly estimates settle. Faster convergence means higher confidence in maintaining a large prognostic horizon |

✅ These are reported to outperform traditional accuracy/precision metrics for assessing prognostic algorithms, and have been extended to incorporate probability-distribution information.

⬜ **We should report Prognostic Horizon.** "We detect and correctly bound the degradation 40 minutes before limit exceedance" is a statement an operator understands and values. "RMSE 12.4 cycles" is not.

---

## 9.9 A worked RUL example

⬜ **ILLUSTRATIVE** — constructed to show the reasoning chain end to end.

**Observations over a sortie:**

| Time | Oil temp residual | Vib band-3 energy | SFC residual | Health index |
|---|---|---|---|---|
| T+0:00 | +0.3 °C | 0.42 g | +0.1% | 98 |
| T+2:00 | +1.8 °C | 0.51 g | +0.8% | 94 |
| T+4:00 | +3.1 °C | 0.68 g | +1.9% | 88 |
| T+6:00 | +4.9 °C | 0.89 g | +3.1% | 81 |

**Step 1 — Is it real?** All three indicators move together, consistently, over hours. Rate of change is physically plausible. Neighbouring sensors are consistent. Lane A and B agree. → not a sensor fault.

**Step 2 — Fit the trend.** Health declines ≈2.8 units/hour, slightly accelerating. A linear fit over the last 4 hours gives slope −3.1 ± 0.4 units/hour.

**Step 3 — Extrapolate to threshold** (health = 50, our defined serviceability limit):

```
RUL = (81 − 50) / 3.1 ≈ 10.0 flight hours
```

**Step 4 — Uncertainty.** Propagating the slope uncertainty (±0.4):

```
Optimistic (slope 2.7): 11.5 h
Pessimistic (slope 3.5):  8.9 h
→ RUL = 10.0 h, 80% CI [8.9, 11.5] h
```

Note the interval is *narrow* because the trend is clean and the horizon is short. Early in degradation, with a noisy slope, it would be far wider — and reporting that honestly is the point.

**Step 5 — Operational decision.** Planned sortie remaining: 12 hours. RUL upper bound 11.5 h < 12 h.

> **Advisory: NO-GO for full sortie. Recommend return-to-base within 8 hours** (pessimistic bound with margin). **Probable cause: bearing wear — rising vibration band 3 with correlated oil temperature rise and efficiency loss. Recommend borescope inspection of the reduction gearbox.**

**This is the output that makes the system worth building.** Note how much of its value comes from the evidence trail and the interval, not from the point estimate.

---

## 9.10 What we can honestly do

| Capability | Feasible for us? | Why |
|---|---|---|
| Health index from residuals | ✅ Yes | Physics-based, no failure data needed |
| Degradation trend detection | ✅ Yes | Statistical, demonstrable |
| Trend extrapolation RUL + interval | ✅ Yes | Honest, transparent, defensible |
| Particle-filter RUL | ✅ Yes | Needs a degradation model, not failure data |
| LSTM RUL on simulated data | 🔶 Yes, with caveats | Must state that it is trained on simulation |
| LSTM RUL validated on real engine data | ❌ No | The data does not exist publicly |
| RUL on C-MAPSS as a method demonstration | ✅ Yes | Public, standard, comparable — but it is a **turbofan** |

⬜ **The honest framing for the presentation:** "We demonstrate the prognostic pipeline end to end, validated on simulated degradation and benchmarked on C-MAPSS. We do not claim validated RUL accuracy for a real Rotax 912 iS, because no public run-to-failure dataset for that engine exists. Acquiring one is the first item on our deployment roadmap."

That is a stronger answer than a fabricated accuracy figure, and a knowledgeable evaluator will recognise it as such.

---

**Next:** [Part X — The Digital Twin](10_digital_twin.md)
