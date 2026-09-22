# Part XIX — Evaluation Metrics

*How to measure whether this actually works, and why the obvious metrics mislead.*

---

## 19.1 Three different questions

Detection, diagnosis and prognosis need different metrics. Reporting one number for "the system" hides the ones that matter.

| Task | Question | Metrics |
|---|---|---|
| **Anomaly detection** | Did we notice, and how often did we cry wolf? | False alarms/hour, detection latency, missed detection rate |
| **Fault classification** | Did we name it correctly? | Macro F1, per-class recall, confusion matrix |
| **RUL prognosis** | How wrong, and in which direction? | RMSE, asymmetric score, prognostic horizon, α-λ |

---

## 19.2 Regression metrics

### RMSE — Root Mean Square Error

```
RMSE = √( (1/n) Σ (ŷᵢ − yᵢ)² )
```

Squaring penalises large errors disproportionately. Units match the target, so "RMSE 12.4 cycles" is directly interpretable.

✅ RMSE is the standard loss and reporting metric for C-MAPSS RUL work.

### MAE — Mean Absolute Error

```
MAE = (1/n) Σ |ŷᵢ − yᵢ|
```

More robust to outliers than RMSE. **Report both:** RMSE ≫ MAE indicates a few large errors rather than uniform mediocrity, which is diagnostically useful — and in a safety context, a few large errors may matter more than the average.

### RUL error

```
error = RUL_predicted − RUL_true
```

**The sign is the whole point.** Positive means we predicted more life than existed — a late warning. Negative means early. See §19.5.

---

## 19.3 Classification metrics

| Metric | Formula | Meaning | When it matters |
|---|---|---|---|
| **Precision** | TP/(TP+FP) | Of alarms raised, how many were real | High precision ⇒ operators trust alerts |
| **Recall** | TP/(TP+FN) | Of real faults, how many we caught | **High recall ⇒ we do not lose aircraft** |
| **F1** | harmonic mean | Balance of the two | Single-number summary |
| **Macro F1** | unweighted mean across classes | Rare faults count equally | ✅ Our primary classification metric |
| **PR-AUC** | area under precision-recall | Threshold-independent under imbalance | Better than ROC-AUC when positives are rare |

**Why plain accuracy is disqualified:** with 99% healthy frames, predicting "healthy" always gives 99% accuracy and zero detections ([Part VIII §8.7](08_fault_diagnosis.md)).

**The precision/recall trade-off, stated operationally:**

```
High recall, low precision   → catches everything, alarms constantly
                             → operators disable the system → 0% effective recall
High precision, low recall   → alerts are trusted, but faults are missed
                             → an aircraft is lost
```

🔶 The first row is the subtler failure, and the more common one. A system that cries wolf is not merely annoying — it converges to being switched off, at which point its measured recall becomes irrelevant. **This is why false-alarm rate is a safety metric, not a convenience metric.**

---

## 19.4 Detection-specific metrics

### False alarms per flight hour

⬜ **This is the number that determines whether the system is deployable.** Report it in operational units, never as a per-sample rate.

```
At 20 Hz: 0.1% per-sample FPR  =  72 false alarms per hour   ← unusable
          0.001% per-sample    =  0.72 per hour              ← still poor
          Target: < 1 per 10 flight hours
                  ⇒ per-sample FPR < 1.4 × 10⁻⁶
```

🔶 That required per-sample rate is *demanding*, and seeing it written out is the point. It is why **persistence requirements** (N consecutive windows above threshold) are not a hack but a necessity: requiring 20 consecutive detections cuts the false-alarm rate by orders of magnitude at the cost of one second of latency ([Part VII §7.7](07_anomaly_detection.md)).

### Detection latency

Time from fault onset to alarm. Requires known onset times — which ⬜ our synthetic data provides by construction and ✅ ALFA provides via its ground-truth fault times.

```
detection_latency = t_alarm − t_fault_onset
```

Report the distribution, not just the mean. A method with 5 s median latency but a long tail is worse than one with 8 s median and a tight spread.

### Missed detection rate

Fraction of injected faults never detected before end-of-scenario. **Report per fault type** — an overall figure hides that (say) misfire detection is excellent while injector faults are being missed.

---

## 19.5 Asymmetric RUL scoring

✅ **VERIFIED** — this is built into the standard C-MAPSS evaluation: RMSE is symmetric, but the scoring function assigns more penalty when predicted RUL exceeds true RUL, because that delays the maintenance plan. ([Asymmetric-loss RUL](https://arxiv.org/pdf/2604.13459))

### The standard score

```
d = RUL_predicted − RUL_true

d < 0  (early):  s = exp(−d/13) − 1
d ≥ 0  (late):   s = exp( d/10) − 1

Total score = Σ sᵢ      (lower is better)
```

The different denominators (13 vs 10) make the late branch steeper.

```
Error   │ Early penalty │ Late penalty │ Ratio
  10 h  │      1.1      │     1.7      │ 1.5×
  20 h  │      3.6      │     6.4      │ 1.8×
  30 h  │     10.0      │    19.1      │ 1.9×
```

### Why late is worse, stated plainly

```
EARLY:  "RUL 10 h" but 15 h remained
        → maintenance performed 5 h early
        → cost: a serviceable component replaced, availability lost

LATE:   "RUL 15 h" but 10 h remained
        → aircraft dispatched on a 12 h sortie
        → engine fails at hour 10, over hostile terrain
        → cost: the aircraft, the mission, possibly the crew on the ground
```

These are not comparable, so the loss function must not treat them as comparable.

⬜ **Our practice:** train with an asymmetric loss, report RMSE *and* the asymmetric score, and — the operationally important part — **plan against the lower confidence bound, not the point estimate** ([Part XI §11.6](11_mission_simulation.md)).

---

## 19.6 Prognostic metrics

✅ **VERIFIED** — Saxena et al. defined four metrics now standard in PHM: Prognostic Horizon, α-λ performance, Relative Accuracy, and Convergence. NASA maintains a reference implementation. ([NASA NTRS](https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/20100023445.pdf), [PrognosticsMetricsLibrary](https://github.com/nasa/PrognosticsMetricsLibrary))

### Prognostic Horizon (PH)

✅ How far in advance of end-of-life the algorithm predicts RUL within desired α-bounds.

```
RUL
  │  ╲ true RUL
  │   ╲     ┌────── α-bounds (±20%)
  │    ╲   ╱
  │  ×  ╲ ╱   ← predictions enter the bounds HERE
  │      ╳
  │     ╱ ╲
  └────┴────────────────────── time
       ▲                    ▲
       └──────── PH ────────┘ EoL
```

**Longer is better.** ⬜ This is the metric closest to operational value, and the one to lead with: *"we bound the degradation within ±20% from 40 minutes before limit exceedance"* is a statement an operator can use. "RMSE 12.4" is not.

### α-λ performance

✅ Binary at each time step: is the prediction within the α-band at fraction λ through the component's life? Typically evaluated at λ = 0.5 (halfway to failure).

### Relative Accuracy

Accuracy normalised by the remaining life at prediction time — so a 2-hour error with 100 hours remaining is scored differently from a 2-hour error with 5 hours remaining, as it should be.

### Convergence

✅ How quickly estimates settle as more data arrives. Faster convergence means higher confidence in maintaining a large prognostic horizon.

---

## 19.7 System-level metrics

Beyond model quality, these decide whether the system works as a system.

| Metric | Target ⬜ | Why |
|---|---|---|
| **Inference latency (edge)** | <10 ms | Must keep up with 20 Hz |
| **Inference latency (GCS)** | <50 ms | Interactive feel |
| **End-to-end latency** | ✅ ~1.5 s, link-dominated | Sets operator expectation |
| **Bandwidth used** | <25 kbit/s | Fits the link budget ([Part XIII §13.5](13_edge_vs_ground_split.md)) |
| **Edge memory** | <100 MB | Fits a Pi-class board comfortably |
| **Availability under 20% loss** | >95% of twin updates | Graceful degradation |
| **Availability under total outage** | 100% edge function | ★ The architectural test |
| **Replay determinism** | Bit-identical | Investigation requires it |

🔶 The starred row is the one that distinguishes this architecture from a ground-only system, and it is a pass/fail rather than a percentage.

---

## 19.8 Evaluation protocol

⬜ The protocol we commit to, so results mean something:

### Splitting

> **Split by engine, flight or run. Never by row.** ([Part VIII §8.7](08_fault_diagnosis.md))

| Dataset | Split |
|---|---|
| Ours (synthetic) | By simulated airframe, with unseen degradation rates and environments in test |
| C-MAPSS | ✅ Use the provided train/test split |
| CWRU/Paderborn | By operating condition or by bearing unit |
| XJTU-SY/FEMTO | By bearing unit |
| ALFA | By flight |

### Fitting

Fit scalers, PCA and covariance matrices on **training data only**. Fitting on the full dataset leaks test statistics.

### Test-set discipline

Touch it once. Every re-tune against it converts it into a validation set and the reported number stops estimating generalisation.

### Reporting

Every result must state: dataset, split method, whether data is synthetic or real, class distribution, and the metric definition used.

⬜ **Template:**

> "Fault classification macro F1 = 0.89 (per-class recall 0.82–0.95) on 12 held-out simulated airframes with degradation rates and environments not present in training. Data is synthetic, generated by our own physics model, so this validates the pipeline rather than field accuracy. The same feature pipeline and classifier achieve [X] on the Paderborn bearing dataset, an independent public benchmark."

---

## 19.9 What we will and will not claim

| Claim | Can we? | Why |
|---|---|---|
| "Our pipeline detects all 8 PS fault types in simulation" | ✅ Yes | Demonstrable |
| "Macro F1 0.89 on held-out simulated airframes" | ✅ Yes, with the caveat stated | Honest and specific |
| "RUL RMSE X on C-MAPSS, comparable to published baselines" | ✅ Yes | Public benchmark, standard split |
| "Envelope analysis validated on CWRU" | ✅ Yes | Real vibration data |
| "97% accuracy on aero piston engine fault detection" | ❌ **No** | We have no real engine data |
| "Validated RUL for the Rotax 912 iS" | ❌ **No** | ✅ No public run-to-failure data exists |
| "Detects faults 40 minutes before limit exceedance" | 🔶 In simulation, stated as such | True of our scenarios; not a field claim |
| "Reduces bandwidth by ~4,000× vs raw vibration" | ✅ Yes | Arithmetic, verifiable |
| "Operates autonomously when the link is jammed" | ✅ Yes | Demonstrable by unplugging the cable |

🔶 The two ❌ rows are the tempting ones, and they are exactly what a domain-literate evaluator will probe. Declining to claim them, and explaining *why* the data does not exist, demonstrates more competence than asserting them.

---

## 19.10 Presenting results

⬜ A structure that survives hostile questioning:

1. **State the limitation first.** "No public piston-engine PHM dataset exists, so we validate the method on public benchmarks and the integration on physics-based simulation."
2. **Show benchmark results.** C-MAPSS for RUL, Paderborn/CWRU for vibration. Independent, comparable, real.
3. **Show simulation results.** With the split and the caveat in the same sentence.
4. **Show the system behaviour**, which does not depend on data realism at all: latency, bandwidth, link-loss autonomy, replay determinism, graceful degradation.
5. **Show the roadmap** to real validation: the instrumented test-cell campaign that would be needed ([Part XIV §14.8](14_datasets.md)).

🔶 Point 4 is undervalued. The architectural properties — 4,000× bandwidth reduction, full function under jamming, deterministic replay — are **demonstrably true regardless of how realistic our synthetic data is**, because they are properties of the system rather than of the models. They are the most defensible things we have, and they should be foregrounded rather than buried under accuracy figures we cannot fully support.

---

**Next:** [Part XX — Novelty and Research Opportunities](20_novelty_and_research.md)
