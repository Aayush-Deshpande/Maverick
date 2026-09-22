# Part XXV — Misfire and Combustion Diagnostics

*Algorithms that consume `ω(θ)` from [Part XXIV](24_combustion_cycle_and_crank_dynamics.md). This is where PS faults #1 (misfire) and #6 (combustion instability) are actually solved.*

---

## 25.1 Why this is the highest-value detector we can build

[Part VIII §8.1](08_fault_diagnosis.md) already records that misfire's best sensor is "vibration + crank-angle RPM", and [§8.2](08_fault_diagnosis.md) states that faults 1, 6 and 8 "cannot be reliably detected without proper high-rate vibration or crank-angle data."

Our current classifier's **worst class is exactly this one** — FAULT_1 recall 0.8359 against precision 1.0 (`backend/ml/models/model_metrics.json`). It misses ~16% of misfires. That is not a tuning problem; it is an *information* problem. A 20 Hz averaged RPM channel does not contain the evidence.

🔶 **This part replaces a statistical guess with a direct measurement.** The output changes from "model thinks misfire, p=0.7" to "cylinder 3, 4.2% of cycles, onset 11 min ago."

---

## 25.2 Signal conditioning — before any detection

⚠️ Skipping this step is the most common cause of a misfire detector that works in simulation and fails on real data.

### Tach quantisation is the real constraint

A real crank sensor emits discrete edges. A 36-tooth wheel gives 10° resolution; 60-2 gives 6°. ✅ Angular velocity is computed between edges:

```
    ω_k = Δθ_tooth / Δt_k
```

⚠️ **Tooth-spacing manufacturing error is systematic, not random.** It repeats every revolution and will masquerade as a per-cylinder pattern — precisely the signal we are hunting.

⬜ **Mandatory correction:** learn a per-tooth correction factor during steady healthy operation and apply it thereafter.
```
    c_j = mean over revolutions of (ω_j / mean(ω))      # per tooth j
    ω_corrected[j] = ω_raw[j] / c_j
```
🔶 Without this, a manufacturing artifact produces a permanent phantom misfire on one cylinder.

### Remove the slow component

Throttle changes and prop-load dynamics move mean ω on a timescale far longer than one cycle. High-pass or subtract a per-cycle mean so we analyse *fluctuation*, not trend.

---

## 25.3 Method 1 — segmented torque deficit (primary)

**The workhorse.** Direct, explainable, needs no training data.

```
1. Segment each 720° cycle into 4 windows of 180°, one per firing event,
   phased by firing order 1-4-2-3.
2. For each window i, compute the angular-velocity gain:
       Δω_i = ω(end of window i) − ω(start of window i)
   Equivalently the mean angular acceleration over that cylinder's power stroke.
3. Normalise against the cycle to remove load/speed dependence:
       R_i = Δω_i / mean_j(Δω_j)
4. Healthy: R_i ≈ 1 for all i.
   Misfire on cylinder i: R_i collapses toward or below 0.
```

**Threshold:** ⬜ `R_i < 0.4` flags a misfire on that cycle. Tune against the generator, then verify the false-alarm rate on healthy data — [§25.7](#257-evaluation).

**Why it is attributable:** the deficit appears in the misfiring cylinder's *own* angular window. Cylinder identity comes from crank phase, not from a model's guess.

⚠️ **Boxer caveat:** at 180° firing spacing on a 4-cylinder, adjacent power strokes overlap slightly through rod/inertia coupling, so a misfire on cylinder 4 bleeds a little into cylinder 2's window. Use the *maximum* deficit to attribute, and expect ~10–20% crosstalk. Validate attribution with a confusion matrix over which cylinder was actually killed.

---

## 25.4 Method 2 — order-domain (confirmatory)

A 4-cylinder 4-stroke fires at **order 2**. One dead cylinder makes the pattern repeat once per *cycle* (720°) instead of once per 180°, injecting energy at **half-orders**.

```
    Healthy:   dominant order 2, weak 0.5 / 1 / 1.5
    Misfire:   order 0.5 and 1 rise sharply; order 2 falls
    Detector:  E_0.5 / E_2   — a dimensionless ratio, speed-invariant
```

🔶 **Use this as corroboration, not as the primary.** It tells you *a* cylinder is misfiring but not *which* — phase information is needed for that, which is what §25.3 provides. Two independent methods agreeing is what makes the diagnosis defensible.

⚠️ Requires **tach-synchronous order tracking** ([Part VI §6.6](06_vibration_analysis.md), [Part XXVI](26_order_tracking_and_envelope.md)). Plain FFT on a varying-RPM sortie smears these lines into uselessness.

---

## 25.5 Misfire rate, not misfire flag

⬜ A single missed combustion event is not a fault — it happens occasionally in healthy engines. **The diagnosis is a rate.**

```
    misfire_rate_i = (misfiring cycles for cyl i) / (total cycles)   over a sliding window
```

| Rate | Interpretation | Action |
|---|---|---|
| < 0.5% | Normal cyclic variability | none |
| 0.5 – 2% | Early degradation — plug, injector, or lead | advisory, monitor trend |
| 2 – 10% | Established fault | warning; EGT on that cylinder confirms |
| > 10% | Severe — thermal and catalyst-equivalent damage risk | immediate |

⬜ Window: 500–1000 cycles (~12–24 s at 5,000 RPM). Long enough to be statistically meaningful, short enough to be responsive.

**Report the trend, not just the level:** `+0.3%/min` is the number that supports a prognosis; `4.2%` alone is a snapshot.

---

## 25.6 Combustion instability — PS fault #6

Distinct from misfire: combustion *occurs* every cycle but varies excessively cycle-to-cycle. Rising instability commonly **precedes** misfire, making it the earlier warning.

✅ The standard metric is **COV of IMEP**:
```
    IMEP = (1/V_d) ∮ p dV                     per cylinder, per cycle
    COV_IMEP = σ(IMEP) / mean(IMEP) × 100%
```

✅ **VERIFIED thresholds** — COV_IMEP > 10% is the widely adopted boundary for unacceptable combustion stability and poor driveability; ~3% is used as a strict target in advanced combustion control; ~5% is typical of a marginal operating point. ([two-stroke idle cyclic-variation study](https://www.nature.com/articles/s41598-026-56635-x), [combustion stability control](https://www.sciencedirect.com/science/article/pii/S2405896316313908), [cyclic variation of IMEP at idle, *JMST*](https://link.springer.com/article/10.1007/BF03184801))

| COV_IMEP | State |
|---|---|
| < 3% | Stable |
| 3 – 5% | Acceptable; watch |
| 5 – 10% | Degrading — PS fault #6 territory |
| > 10% | Unstable ✅ |

⚠️ **We have no cylinder-pressure sensor.** Real aero engines do not carry one. So IMEP must be *inferred* from ω(θ):

⬜ **Torque-proxy COV** — use per-cylinder `Δω_i` as an IMEP surrogate:
```
    COV_torque,i = σ(Δω_i) / mean(Δω_i) × 100%     over the sliding window
```
🔶 This is a proxy, and must be labelled as one. It correlates with COV_IMEP but is not equal to it — inertia and load filter the relationship. ⬜ Calibrate the mapping against the [Part XXIV](24_combustion_cycle_and_crank_dynamics.md) model, where true IMEP *is* computable, and publish the correlation. That calibration is itself a creditable piece of work.

---

## 25.7 Evaluation

⬜ Metrics that matter. Accuracy is the wrong one — misfires are rare, so a detector that never fires scores well.

| Metric | Target | Why |
|---|---|---|
| **Cylinder attribution accuracy** | > 95% | Confusion matrix over *which* cylinder. The claim we are actually making |
| **False-alarm rate on healthy data** | < 1 per flight hour | ⚠️ The metric nobody reports. A jumpy detector is unusable |
| **Minimum detectable misfire rate** | ≤ 1% | Sensitivity floor |
| **Detection latency** | < 30 s from onset | Operational relevance |
| **Robustness to tach quantisation** | hold at 36 and 60-2 teeth | Transfers to hardware |
| **Robustness across RPM/load** | 2,000–5,800 RPM, 30–100% load | Must not be tuned to one operating point |

⬜ **Comparison baseline (F13):** run our 20 Hz RandomForest (FAULT_1 recall 0.8359) on the same scenarios. Expected headline: *"recall 0.84 → >0.98, with cylinder identification the baseline cannot provide at all."*

---

## 25.8 Cross-domain corroboration — what makes it a diagnosis

🔶 A misfire is not a single-signal event. Physics says it must appear in several places at once, and checking that is what separates a diagnosis from a classification.

| Channel | Expected on a real misfire | Timescale |
|---|---|---|
| ω(θ) torque deficit | Immediate, that cylinder's window | Same cycle |
| Order 0.5 / 1 energy | Rises | Seconds |
| **EGT on that cylinder** | **Falls** (no combustion) | 5–20 s (thermal lag) |
| CHT on that cylinder | Falls slightly | 30–60 s |
| Fuel flow | Unchanged (fuel still injected unless it is a fuel fault) | — |
| Vibration RMS | Small rise | Seconds |

⬜ **This table is the fault-isolation logic.** If ω(θ) shows a deficit on cylinder 3 **and** EGT#3 falls with correct thermal lag → real misfire. If ω(θ) shows a deficit but **all EGTs are unchanged** → suspect the crank sensor or the detector, not the engine.

⚠️ That second row is the same reasoning our sensor validator uses ([Part VII](07_anomaly_detection.md)) applied to a new signal — and it is why [Part XXIV §24.10](24_combustion_cycle_and_crank_dynamics.md) check 7 (misfire ⇒ EGT drop) matters so much. If the generator does not couple combustion to thermal state, this entire corroboration chain is untestable.

---

## 25.9 Output format

⬜ What the operator and the dashboard should receive:

```json
{
  "fault": "MISFIRE",
  "cylinder": 3,
  "misfire_rate_pct": 4.2,
  "trend_pct_per_min": 0.3,
  "onset_utc": "2026-09-22T11:14:07Z",
  "confidence": 0.94,
  "evidence": {
    "torque_deficit_ratio": 0.31,
    "order_0p5_to_2_ratio": 2.7,
    "egt_3_residual_c": -48,
    "egt_others_residual_c": [2, -1, 3]
  },
  "ruled_out": [
    "sensor_fault: EGT#3 corroborates the torque deficit",
    "fuel_starvation: fuel flow nominal, other cylinders unaffected"
  ],
  "advisory": "Cylinder 3 ignition or injector. Expect ~2% power loss.
               Monitor EGT#3. Inspect plug and lead post-flight."
}
```

🔶 The `ruled_out` field is the difference between a diagnostic system and a classifier, and it is cheap to produce once §25.8's table is implemented.

---

## 25.10 Implementation order

```
1. ω(θ) from Part XXIV                      ← prerequisite
2. Tach model + per-tooth correction (§25.2) ← skip this and everything after is unreliable
3. Segmented torque deficit (§25.3)          ← primary detector
4. Misfire rate + trend (§25.5)
5. Order-domain confirmation (§25.4)         ← needs Part XXVI
6. COV proxy for instability (§25.6)
7. Cross-domain corroboration (§25.8)
8. Evaluation vs 20 Hz baseline (§25.7)
```

---

*Depends on: [Part XXIV](24_combustion_cycle_and_crank_dynamics.md) · [Part XXVI](26_order_tracking_and_envelope.md). Implements features F02, F03 of the [feature spec](../audit/04_feature_spec.md).*
