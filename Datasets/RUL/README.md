# RUL — run-to-failure data index

Cross-reference of every source in this catalogue that contains **complete degradation trajectories** — the data type RUL modelling requires and which is genuinely scarce.

---

## Why this folder is an index rather than a store

RUL needs run-to-failure trajectories: a component operated, instrumented, until it actually fails. This is expensive and destructive, which is why the field has so few such datasets and why C-MAPSS — a *simulator* — became the standard benchmark.

The literature states the problem directly: limited run-to-failure samples is the major challenge in developing prognostics, and it is the main motivation for federated approaches that pool learning across operators without sharing data.

---

## Available run-to-failure sources

| Dataset | Machine | Signal | Trajectories | Folder |
|---|---|---|---|---|
| **C-MAPSS** | Turbofan (simulated) | 21 sensors + 3 settings | 100–260 per subset | [`../Engine_PHM/`](../Engine_PHM/README.md) |
| **N-CMAPSS** | Turbofan (simulated) | Higher fidelity | — | [`../Engine_PHM/`](../Engine_PHM/README.md) |
| **XJTU-SY** | Bearing | Vibration 25.6 kHz | 15 bearings | [`../Bearing/`](../Bearing/README.md) |
| **FEMTO / PRONOSTIA** | Bearing | Vibration 25.6 kHz | 17 bearings | [`../Bearing/`](../Bearing/README.md) |
| **IMS** | Bearing | Vibration | 3 test-to-failure runs | [`../Bearing/`](../Bearing/README.md) |
| **Ours (synthetic)** | **Piston engine** | All 8 PS faults + vibration | Unlimited | [`../Synthetic/`](../Synthetic/README.md) |

**Nothing in that table is an aero piston engine except our own synthetic data.** See [`../Piston_Engine/`](../Piston_Engine/README.md).

---

## The complementary pair

| | C-MAPSS | XJTU-SY / FEMTO |
|---|---|---|
| Engine-like sensors | ✅ | ❌ |
| Multiple operating conditions | ✅ | ❌ |
| Vibration | ❌ | ✅ |
| Large published baseline | ✅ | ✅ |

**Use both.** C-MAPSS validates RUL from multivariate scalar sensors under varying conditions — our residual path. XJTU-SY validates RUL from vibration — our mechanical path. Our system needs both, and neither dataset alone covers it.

---

## Evaluation metrics

See [Part XIX](../../ANUMAAN/docs/study/19_evaluation.md) for full treatment.

### Asymmetric score (C-MAPSS convention)

```
d = RUL_predicted − RUL_true

d < 0 (early):  s = exp(−d/13) − 1
d ≥ 0 (late):   s = exp( d/10) − 1

Total = Σ sᵢ       (lower is better)
```

Late predictions are penalised more steeply, because a late prediction means an aircraft was dispatched on a sortie longer than its remaining life.

### Prognostic metrics (Saxena et al.)

| Metric | Meaning |
|---|---|
| **Prognostic Horizon** | How far before end-of-life predictions stay within α-bounds. **Longer is better** — the metric closest to operational value |
| **α-λ performance** | Is the prediction within an α-band at fraction λ of life? |
| **Relative Accuracy** | Accuracy normalised by remaining life at prediction time |
| **Convergence** | How fast estimates settle |

Reference implementation: https://github.com/nasa/PrognosticsMetricsLibrary

---

## Practices

| Practice | Reason |
|---|---|
| **Split by unit** (engine/bearing), never by cycle | Adjacent cycles are near-duplicates |
| **Cap the RUL target** (C-MAPSS convention: 125) | Early-life RUL is unpredictable; a piecewise-linear target reflects that |
| **Report intervals, not point estimates** | A bare RUL number is operationally unsafe |
| **Report prognostic horizon** | It is what an operator can act on |
| **Build the extrapolation baseline first** | A neural model must beat it on a proper split to justify itself |

---

## What we can honestly claim

| Claim | Feasible |
|---|---|
| "RUL method validated on C-MAPSS, comparable to published baselines" | ✅ Yes |
| "Vibration-based RUL validated on XJTU-SY" | ✅ Yes |
| "Full prognostic pipeline demonstrated on piston-engine simulation" | ✅ Yes, stated as simulation |
| "Validated RUL for a real Rotax 912 iS" | ❌ **No** — the data does not exist publicly |
