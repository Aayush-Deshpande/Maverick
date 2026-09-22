# Part VIII — Fault Diagnosis and Classification

*Naming the fault, and why published benchmark accuracies will not transfer to our engine.*

---

## 8.1 The eight PS fault targets and their signatures

✅ **VERIFIED** — the official PS names these eight detection/prediction targets. The signature column is 🔶 **INFERENCE** from engine physics and the diagnostic reasoning in Parts II and VI.

| # | Fault | Primary signature | Supporting evidence | Best sensor |
|---|---|---|---|---|
| 1 | **Misfire** | 0.5-order vibration energy ↑↑; crank speed dip within a cycle | One cylinder's EGT ↓; RPM roughness ↑ | Vibration + crank-angle RPM |
| 2 | **Injector abnormality** | Commanded pulse width inconsistent with achieved fuel flow / EGT | One cylinder EGT deviates; fuel flow residual | EGT per cylinder + fuel flow |
| 3 | **Cooling degradation** | All CHT residuals rise together; slow, correlated | Coolant/oil temp ↑; worsens with altitude | CHT ×4 |
| 4 | **Lubrication issue** | Oil pressure residual falls at matched RPM/temp | Oil temp ↑; possibly bearing vibration ↑ | Oil P + T |
| 5 | **Sensor drift / failure** | Rate-of-change implausible; lane divergence; noise floor wrong | **Un**correlated with neighbours | Cross-sensor + dual lane |
| 6 | **Combustion instability** | Cycle-to-cycle variance ↑ in EGT and vibration | RPM jitter; irregular firing orders | EGT variance + vibration |
| 7 | **Overheating trend** | CHT/EGT residual trending up over tens of minutes | Still within limits — **this is the point** | CHT/EGT trend |
| 8 | **Abnormal vibration** | Energy at a specific order/bearing frequency ↑ | Envelope FFT line at BPFO/BPFI; kurtosis ↑ | Vibration spectrum |

**Read the "Best sensor" column carefully.** Faults 1, 6 and 8 — three of the eight — **cannot be reliably detected without proper high-rate vibration or crank-angle data**. This is the single most important design consequence in the whole diagnosis problem, and it is why [Part VI](06_vibration_analysis.md) matters more than the choice of classifier.

**Fault 7 is the PS's real ask.** "Overheating trend" is explicitly about detecting a rise *while values are still legal*. A threshold system cannot do this by construction. Trend detection is where the project justifies itself.

---

## 8.2 Feature-based classifiers

### Random Forest

**What it is.** Many decision trees, each trained on a bootstrap sample with a random feature subset at each split; the ensemble votes.

| Property | Assessment |
|---|---|
| Input | Engineered features / residuals |
| Training data | Hundreds to thousands of labelled examples per class |
| Inference cost | Very low — threshold comparisons down shallow paths |
| Handles | Mixed scales, nonlinearity, irrelevant features |
| Interpretability | Global feature importances built in; per-instance needs TreeSHAP |
| Weakness | Extrapolates poorly beyond training range; can overfit noisy labels |

**Why trees are strong here.** Small tabular datasets with engineered, physically meaningful features is precisely the regime where tree ensembles excel. They need no scaling, tolerate mixed units, and are extremely fast. For residual-vector classification they are a well-matched default, not a compromise.

### XGBoost / gradient boosting

Trees built sequentially, each correcting the previous ensemble's errors.

| vs Random Forest | |
|---|---|
| Accuracy | Usually somewhat better with tuning |
| Training | Sequential, so slower; more hyperparameters |
| Overfitting | More prone — needs regularisation and early stopping |
| Inference | Comparable, very fast |

⬜ **Practical recommendation:** start with Random Forest as the baseline (almost no tuning, robust), then try gradient boosting and keep it only if it measurably wins on a *properly split* validation set. Do not assume the more fashionable model is better on a dataset of a few thousand rows.

### SVM

Finds a maximum-margin separating boundary, nonlinear via kernels.

| Property | Assessment |
|---|---|
| Strength | Effective with limited data, strong theory |
| Weakness | O(n²–n³) training; needs careful scaling; multi-class is awkward (one-vs-rest/one-vs-one); probability estimates require extra calibration |

🔶 SVM appears constantly in the vibration literature partly for historical reasons. ✅ It remains in use — for example combined with shift-invariant sparse features for bearing diagnosis. ([Shift-invariant sparse features + optimised SVM](https://doi.org/10.3390/machines9050098)) For our tabular residual problem, trees are usually the more practical choice.

---

## 8.3 Deep learning on vibration

### 1D CNN on raw waveform

Convolutional filters slide along the raw time series, learning their own filters rather than using hand-designed ones.

```
raw window (2048 samples) → conv+pool ×N → dense → fault class
```

**Why it works:** early layers learn band-pass-like filters, deeper layers learn combinations. The network effectively learns its own signal-processing front end.

✅ **VERIFIED results** — a 1D CNN framework achieved average testing accuracies of **97.63% on CWRU** and **95.63% on the Paderborn (PU) dataset** using only raw vibration data without manual feature extraction. The CWRU result is noted as near-perfect because of its controlled laboratory environment, while PU is described as more complex. ([1D CNN bearing fault detection](https://arxiv.org/pdf/2602.09699))

### 2D CNN on spectrograms

Convert the signal to a time-frequency image, then apply image-classification architectures.

✅ **VERIFIED** — studies have used raw signals, envelope spectra and spectrograms as distinct inputs to 2D CNNs; combining hand-crafted discriminative features with deep features from audio spectrograms achieved **98.95% on CWRU and 100% on PU**. ([Deep-shallow feature fusion](https://www.nature.com/articles/s41598-025-93133-y))

### Raw versus spectrogram — how to choose

| | 1D CNN on raw | 2D CNN on spectrogram |
|---|---|---|
| Preprocessing | Minimal | STFT required |
| Learns | Its own filters | Spatial patterns in time-frequency |
| Data needed | More | Less (the transform injects prior knowledge) |
| Compute | Lower | Higher |
| Transfer learning | Limited | ✅ Can use ImageNet-pretrained backbones |
| Interpretability | Poor | Moderate — you can visualise which regions activate |

🔶 **INFERENCE for us:** the spectrogram route is better suited, because our data will be scarce, and the STFT encodes physics we already know rather than forcing the network to rediscover it. But see §8.6 before assuming either will reach the published numbers.

---

## 8.4 A deliberately important warning about those benchmark numbers

The 97.6% / 95.6% / 98.95% / 100% figures above are real and correctly cited. **They will not transfer to our problem.** Five independent reasons:

**1. Different machine physics.** CWRU and Paderborn are *bearing test rigs* — a motor, a shaft, a bearing, at essentially constant speed. Our target is a 4-cylinder 4-stroke aero engine: cyclic, impulsive, with combustion events, valve impacts and a reduction gearbox. ✅ The piston-engine review states explicitly that piston engines' cyclic pressure/volume variation makes them behave unlike steady-state rotating equipment and introduces unique fault-detection challenges. ([Piston engine diagnostics review](https://link.springer.com/article/10.1007/s10973-025-14728-1))

**2. Different fault set.** Those datasets contain seeded bearing defects. The PS's eight targets are mostly *not* bearing faults — misfire, injector faults, cooling degradation, lubrication, sensor drift, combustion instability.

**3. Laboratory versus flight conditions.** ✅ CWRU is explicitly described as yielding near-perfect results *because of* its controlled laboratory environment. An airborne engine has varying speed and load, changing altitude and temperature, airframe vibration, and electrical noise.

**4. Seeded versus natural faults.** Benchmark faults are usually machined into the component — a clean, large, well-defined defect. Real faults develop gradually and heterogeneously, and the early stages are far subtler than a seeded notch.

**5. Evaluation protocol.** Many published results split randomly across windows drawn from the *same* recording, so windows in the test set are near-duplicates of training windows. Accuracy then measures memorisation of a recording, not generalisation to a new machine. Splitting by machine/run, not by window, typically drops reported accuracy substantially.

> ⚠️ **Rule for our project: never cite a benchmark accuracy as an expectation for our system.** Cite it as evidence that a *method class* works on *its* problem. Our numbers must come from our own evaluation, on our own splits, with our own honesty about what the data is.

This is also, practically, a credibility matter. A judge who knows PHM will be more impressed by "we report 84% on a held-out engine, and here is why that is harder than the 97% you have seen on CWRU" than by an unqualified 99%.

---

## 8.5 Sparse coding and dictionary learning — an established family worth knowing

This section matters because it is directly relevant to the "bio-inspired" idea assessed in [Part XX](20_novelty_and_research.md).

✅ **VERIFIED** — sparse coding is an established feature-extraction technique for machinery fault diagnosis, with a substantial literature:

- Adaptive feature extraction using sparse coding for machinery fault diagnosis. ([Mechanical Systems and Signal Processing](https://www.sciencedirect.com/science/article/abs/pii/S0888327010002554))
- Liu et al. were **the first to apply dictionary learning to bearing vibration signals**, training dictionaries of waveforms per bearing condition and using them to classify fault types.
- **Adaptive online dictionary learning** for bearing fault diagnosis — i.e. the online-adaptation idea already exists in this field. ([Online dictionary learning](https://pmc.ncbi.nlm.nih.gov/articles/PMC6556119/))
- Shift-invariant sparse coding, convolutional sparse representation, shift-invariant K-SVD. ([Shift-invariant sparse features](https://doi.org/10.3390/machines9050098))
- Convolutional sparse dictionaries for **variable speed** conditions. ([Deep convolutional sparse dictionary learning](https://www.sciencedirect.com/science/article/abs/pii/S0016003224008135))
- Deep discriminative sparse representation learning. ([DDSRL](https://www.sciencedirect.com/science/article/abs/pii/S0952197624009941))
- Multi-layer convolutional dictionary learning for **explainable** rolling bearing fault diagnosis. ([Explainable CDL](https://www.sciencedirect.com/science/article/abs/pii/S0019057824000363))
- Dictionary learning for wind turbine drivetrain bearing monitoring. ([arXiv](https://arxiv.org/pdf/1902.01426))

**What this means for us.** Sparse representation of vibration is a *mature* approach with known strengths: it is naturally explainable (which atoms activated), it handles impulsive signals well, and online variants exist. It is a legitimate technique to build on. It is **not** an unexplored research gap, and we must not present it as one. [Part XX](20_novelty_and_research.md) works through the honest positioning.

---

## 8.6 The hybrid approach — what the field actually recommends

✅ **VERIFIED** — the piston-engine diagnostics review categorises fault detection into **knowledge-based, model-based, data-driven, and hybrid** frameworks. ([Review](https://link.springer.com/article/10.1007/s10973-025-14728-1))

| Approach | Basis | Strengths | Weaknesses |
|---|---|---|---|
| **Knowledge-based** | Expert rules, FMEA, fault trees | Transparent, needs no training data, certifiable | Only covers anticipated faults; brittle |
| **Model-based** | Physics equations, state observers | Works without failure data; extrapolates; physically meaningful residuals | Needs accurate parameters; model error looks like a fault |
| **Data-driven** | ML on historical data | Finds patterns nobody encoded; improves with data | Needs labelled faults; poor extrapolation; opaque |
| **Hybrid** | Combination | Complementary failure modes | More complex to build and validate |

✅ Hybrid is the current trend, and specifically: hybrid digital twins combining physics-based simulation, Kalman filtering, and ML models for fault diagnosis and RUL estimation. ([UAV piston engine PHM sources](https://link.springer.com/article/10.1007/s10973-025-14728-1))

### Our hybrid design

⬜ Each component placed where its strengths apply:

```
                     TELEMETRY + VIBRATION FEATURES
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌───────────────┐     ┌───────────────────────┐   ┌──────────────────┐
│ KNOWLEDGE     │     │ MODEL-BASED           │   │ DATA-DRIVEN      │
│ Physical      │     │ Thermodynamic twin    │   │ RF/GBM on        │
│ limits, FMEA  │     │ → RESIDUALS           │   │ residuals +      │
│ rules, sensor │     │ (regime-independent)  │   │ vibration feats  │
│ plausibility  │     │                       │   │                  │
│               │     │ Feeds BOTH neighbours │   │ + anomaly models │
└───────┬───────┘     └───────────┬───────────┘   └────────┬─────────┘
        │                         │                        │
        │  hard safety net        │  physical truth        │  learned patterns
        └─────────────────────────┼────────────────────────┘
                                  ▼
                    ┌──────────────────────────────┐
                    │  FUSION + ARBITRATION        │
                    │  · Knowledge layer can VETO  │
                    │    (sensor invalid → ignore) │
                    │  · Agreement raises severity │
                    │  · Disagreement → flag for   │
                    │    human review, don't guess │
                    └──────────────┬───────────────┘
                                   ▼
                    Fault label + confidence + evidence trail
```

**Why the physics block sits in the middle.** It is not one of three parallel opinions — it *transforms the data* that the data-driven block consumes. Classifying residuals is a fundamentally easier and better-posed problem than classifying raw values, because the regime dependence has already been removed. ✅ This is exactly what "physics-informed AI" (a PS-named innovation area) means operationally.

**Why the knowledge layer has veto power.** If sensor validation says a thermocouple is open-circuit, no downstream model should be allowed to interpret its reading. Hard-coded physical impossibility beats a confident model output every time.

---

## 8.7 Class imbalance and evaluation

Real fault data is extremely imbalanced — healthy operation vastly outnumbers faults, and among faults some modes are far rarer than others.

**Why accuracy is a useless metric here.** If 99% of frames are healthy, a model that outputs "healthy" always scores 99% accuracy and detects nothing.

Use instead:

| Metric | What it tells you |
|---|---|
| **Per-class precision/recall/F1** | Performance on each fault individually |
| **Macro F1** | Unweighted mean across classes — rare faults count as much as common ones |
| **Confusion matrix** | *Which* faults get confused with which — diagnostically informative |
| **PR-AUC** | Better than ROC-AUC under heavy imbalance |

**Handling imbalance:** class weights in the loss, resampling (SMOTE with care on time series — naive interpolation between windows can create physically impossible samples), or threshold adjustment per class.

### The splitting rule — the most common way to fool yourself

> **Split by engine, flight or run. Never by row or window.**

Consecutive samples from one flight are near-identical. A random row split puts near-duplicates in both train and test, and reports an accuracy that reflects memorisation, not generalisation. The number will look wonderful and mean nothing.

🔶 The same trap applies to synthetic data: if the simulator that generated the training data also generated the test data, the model is being evaluated on its ability to invert one generator, not to diagnose an engine. Any synthetic-data result must be reported with that caveat explicit, and ideally validated against a *different* data source ([Part XIV](14_datasets.md), [Part XVII](17_simulation_design.md)).

---

## 8.8 Explainability

✅ Explainable AI for fault diagnosis is a named PS innovation area, and it is an operational necessity: a maintainer will not pull an engine on the word of an unexplained number.

| Method | How it works | Cost | Output |
|---|---|---|---|
| **Feature importance (global)** | Built into tree models | Free | Which features matter overall |
| **TreeSHAP (per-instance)** | Exact Shapley values for tree ensembles, polynomial time | Extra computation per explanation | Per-feature contribution for this prediction |
| **PCA contribution** | Decompose reconstruction error by sensor | Free — same computation | Which sensor drove the anomaly |
| **Sparse-code activation** | Which dictionary atoms/units fired | Free — part of the forward pass | Which learned patterns are present |
| **Physics evidence trail** ⬜ | Report the residuals that triggered the decision | Free | "CHT₂ residual +34 °C while CHT₁ +1 °C" |

⬜ **Our approach: lead with the physics evidence trail.** "Cylinder 2 CHT is 34 °C above its physics-expected value while cylinders 1, 3, 4 are within 2 °C, and 0.5-order vibration energy rose 18×" is an explanation a propulsion engineer can *act on*. SHAP values over abstract feature names are a weaker communication, even though they are mathematically principled.

🔶 An important practical note on cost: TreeSHAP for a 100-tree, depth-12 forest at 20 Hz is a real per-frame expense. The standard solution is to compute explanations **only for flagged events**, not every frame — which removes the cost concern entirely and is what operational systems do.

---

## 8.9 Summary

| Question | Answer |
|---|---|
| Which classifier for residuals? | ⬜ Random Forest baseline; gradient boosting only if it wins on a proper split |
| Which for vibration? | ⬜ Engineered order/envelope features + a small model. CNN only if data justifies it |
| Will we reach 97%? | 🔶 Almost certainly not, and claiming it would be a red flag. See §8.4 |
| How do we split data? | By engine/flight/run. Never by row |
| What metric? | Macro F1 + per-class recall + confusion matrix. Never plain accuracy |
| How do we explain decisions? | Physics evidence trail first; SHAP on flagged events only |
| Is sparse coding novel here? | ❌ No — it is an established family. See §8.5 and [Part XX](20_novelty_and_research.md) |

---

**Next:** [Part IX — RUL and Prognostics](09_rul_prognostics.md)
