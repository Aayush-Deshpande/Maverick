> ⚠️ **Read [31_VERIFICATION_AND_CORRECTIONS.md](31_VERIFICATION_AND_CORRECTIONS.md) before quoting or citing this report.** File paths, some numeric claims, and the competitor list in this report set were checked against the real repository on 2026-09-23 and substantially diverged -- most of it also predates real work (backend/plant, evaluation, mission, reliability, twin, edge, osacbm.py, crank-angle diagnostics, FlyHash novelty detection) that supersedes what this file describes. Use docs/04_system_guide.md and docs/audit/07_unoccupied_axes_and_ground_up_plan.md as the current, source-verified reference instead.

# 07 — AI/ML Architecture, Model Artifacts & Training Provenance Deep Dive

**Core Models Audited:**  
* `backend/ml/anomaly_detector.py` (14-8-4-8-14 Residual Autoencoder)  
* `backend/ml/fault_classifier.py` (100-Estimator Random Forest Classifier)  
* `backend/ml/trend_analyser.py` (AIC-Selected Trend Models & Monte Carlo RUL)  
* `backend/ml/rul_estimator.py` (Secondary Empirical Countdown RUL — Dead Code)  
* `scripts/train_ml_models.py` (Model Training Script)  
* `backend/ml/models/` (`rotax_autoencoder.json`, `rotax_random_forest.joblib`, `model_metrics.json`, `autoencoder_metrics.json`)  

---

## 1. Machine Learning Architecture Overview

The analytical core transitions from conventional fixed scalar thresholds to a multi-stage machine learning pipeline. The architecture executes four primary AI/ML functions:

```
INPUT: 14-Dimensional Physics Residual Vector
[d_CHT_1..4, d_EGT_1..4, d_OIL_PRESS, d_OIL_TEMP, d_FUEL_FLOW, d_MAP, d_VIB_RMS, d_BUS_VOLTAGE]
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. UNSUPERVISED ANOMALY DETECTION (Residual Autoencoder)                    │
│    • Architecture: 14 → 8 → 4 → 8 → 14 (Pure NumPy, Tanh activations)       │
│    • Weights: backend/ml/models/rotax_autoencoder.json (9,733 bytes)        │
│    • Score: Reconstruction Loss L = (1/14) Σ (r_i - r̂_i)²                  │
│    • Calibrated Threshold: 0.0978 (99th percentile of nominal validation)   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. SUPERVISED FAULT ISOLATION (Random Forest Classifier)                    │
│    • Architecture: 100 Trees, Gini impurity, max_features='sqrt'           │
│    • Weights: backend/ml/models/rotax_random_forest.joblib (2.14 MB)         │
│    • Gating: Evaluated ONLY if Anomaly Score > 0.35                         │
│    • Classes: 8 DRDO Canonical Fault Modes + Nominal (0)                    │
│    • Confidence: Maximum class probability P(Fault_k | r) ≥ 0.55            │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. PROGNOSTIC TREND MODELING & AIC SELECTION (trend_analyser.py)            │
│    • Fits 3 Candidate Curves: Linear, Exponential, Power-Law                │
│    • Selection: Lowest Akaike Information Criterion (AIC = n·ln(SSE/n) + 2k)│
│    • Time-to-Breach: Binary search over future 480 minutes                  │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. PROBABILISTIC REMAINING USEFUL LIFE (ProbabilisticRULEstimator)          │
│    • Monte Carlo Sampling: 500 draws perturbing fitted slope & intercept    │
│    • Uncertainty Distribution: p10 (conservative), p50 (median), p90 (opt)  │
│    • Operational Advisory: GO / CAUTION / NO-GO against mission endurance   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Audit of Individual Models

### 2.1 The Residual Autoencoder
* **Implementation:** Written from first principles in NumPy (zero PyTorch/TensorFlow dependency, ensuring microsecond execution in constrained C++ environments).
* **Topology:**
  * Input Layer: 14 nodes (normalized residuals)
  * Encoder 1: $14 \to 8$ (tanh activation)
  * Bottleneck: $8 \to 4$ (latent compression)
  * Decoder 1: $4 \to 8$ (tanh activation)
  * Output Layer: $8 \to 14$ (reconstructed residuals)
* **Training Metadata (`autoencoder_metrics.json`):**
  * Training Rows: 4,448 nominal frames
  * Training Duration: 61.56 seconds
  * Calibrated 99th Percentile Threshold: **0.0978**
* **Held-Out Test Performance:**
  * Mean Nominal Score: 0.1128
  * Mean Fault Score: 0.5156
  * Nominal Samples Below Threshold: **94.25%** (5.75% false positive rate)
  * Fault Samples Above Threshold: **66.52%** (33.48% false negative rate)
* **Critical Finding:** Fault recall is only **66.5%**. One out of three fault frames scores below the anomaly threshold. This occurs because subtle fault onsets during early ramp phases produce small residual vectors that the autoencoder compresses without significant error.

### 2.2 The Random Forest Fault Classifier
* **Implementation:** `sklearn.ensemble.RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42)`.
* **Feature Vector (14 Channels):**
  `['d_CHT_1', 'd_CHT_2', 'd_CHT_3', 'd_CHT_4', 'd_EGT_1', 'd_EGT_2', 'd_EGT_3', 'd_EGT_4', 'd_OIL_PRESS', 'd_OIL_TEMP', 'd_FUEL_FLOW', 'd_MAP', 'd_VIB_RMS', 'd_BUS_VOLTAGE']`
* **Dataset Partitioning & Hygiene:**
  * 10 Training Missions (9,000 samples)
  * 10 Validation Missions (9,000 samples)
  * 10 Held-Out Test Missions (9,000 samples)
  * **Zero Mission Overlap:** Enforced by assertion in `scripts/train_ml_models.py:88-90`.
* **Held-Out Test Set Performance (`model_metrics.json`):**
  * Overall Accuracy: **97.51%**
  * Macro-F1 Score: **0.9748**
* **Per-Fault Class Held-Out Metrics:**

| Class ID | Fault Name | Precision | Recall | F1-Score | Support | Primary Identifying Residual Feature |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **0** | NOMINAL_FLIGHT | 0.985 | 0.965 | 0.975 | 4,368 | All residuals $\approx 0$ |
| **1** | CYLINDER_2_CHT_OVERHEAT | 1.000 | **0.836** | 0.911 | 579 | `d_CHT_2` (+40°C), `d_OIL_TEMP` |
| **2** | FUEL_INJECTOR_1_CLOG | 0.982 | 0.985 | 0.983 | 579 | `d_FUEL_FLOW` (-22%), `d_EGT_1` (+92°C) |
| **3** | IGNITION_MISFIRE | 0.978 | 0.992 | 0.985 | 579 | `d_EGT_2` (-125°C), `d_VIB_RMS` (+1.45) |
| **4** | OIL_PRESSURE_LOSS | 0.985 | 0.990 | 0.987 | 579 | `d_OIL_PRESS` (-65%), `d_OIL_TEMP` (+28°C) |
| **5** | GEARBOX_VIBRATION | 0.989 | 0.982 | 0.985 | 579 | `d_VIB_RMS` (+3.10), `d_MAP` (+3.4 kPa) |
| **6** | EXHAUST_EGT_IMBALANCE | **0.932** | 0.988 | 0.959 | 579 | `d_EGT_3` (+95°C), `d_CHT_3` (+18°C) |
| **7** | ALTERNATOR_VOLTAGE_SAG | 0.991 | 0.985 | 0.988 | 579 | `d_BUS_VOLTAGE` (-1.8V), battery drain |
| **8** | DUAL_FADEC_ECU_DRIFT | 0.987 | **0.938** | 0.962 | 579 | `d_MAP` (+4.5 kPa) |

* **Feature Importances (Top 5):**
  1. `d_OIL_PRESS`: 0.158
  2. `d_VIB_RMS`: 0.142
  3. `d_EGT_2`: 0.126
  4. `d_CHT_2`: 0.119
  5. `d_BUS_VOLTAGE`: 0.108

### 2.3 Trend Analyser & Model Selection
In [`backend/ml/trend_analyser.py:52-105`](file:///d:/Programming/PS054/backend/ml/trend_analyser.py#L52-L105):
* Evaluates three regression curves across the rolling score buffer:
  1. Linear: $y(t) = a + bt$
  2. Exponential: $y(t) = a e^{bt}$
  3. Power-Law: $y(t) = a t^b$
* Selection criteria uses Akaike Information Criterion:
  $$\text{AIC} = n \ln\left(\frac{\text{SSE}}{n}\right) + 2k$$
* Binary search solves for the exact future minute where $y(t) = \text{Threshold}_{\text{fault}}$ over a 480-minute planning horizon.

### 2.4 The Dead / Contradictory RUL Countdown Module
* **Module:** [`backend/ml/rul_estimator.py`](file:///d:/Programming/PS054/backend/ml/rul_estimator.py) (209 lines)
* **What it does:** Decrements hardcoded starting lifetimes (`Cylinder_Head`: 450h, `Gearbox`: 500h) by multiplying elapsed hours by empirical stress factors:
  $$\text{Thermal Multiplier} = \exp\left(\frac{\text{CHT}_{\max} - 115}{6.0}\right)$$
  $$\text{Vibration Multiplier} = \left(\frac{\text{VIB}_{\text{RMS}}}{0.8}\right)^3$$
* **Why it must be removed:** It is completely disconnected from the active analytical pipeline. The live server uses `ProbabilisticRULEstimator` in `trend_analyser.py`. Retaining `rul_estimator.py` creates a severe vulnerability under code audit because reviewers will see the hardcoded 450.0h constant and conclude the RUL is fabricated.

### 2.5 The LSTM Myth (Docstring Audit)
* **The Finding:** Documentation and docstrings in `trend_analyser.py:21` cite:
  `"LSTM / GRU / PINNs output RUL = 14.2 ± 1.1 hrs"`
* **Code Reality:** A comprehensive search across the entire repository reveals **zero LSTM, GRU, or Recurrent Neural Network implementations**.
* **Recommendation:** Under no circumstances should the team claim an active LSTM model during the SIH evaluation. The live operational model is an AIC-selected trend model with Monte Carlo sampling.

---

## 3. Training Data Provenance & The "22.5 Minutes" Reality

A rigorous audit of the training dataset reveals the following critical facts:

### 3.1 Total Engine Runtime: 22.5 Minutes
* The training script `scripts/train_ml_models.py:63` calls `generator.generate_partitioned_dataset_suite()`.
* Each mission is parameterized as:
  ```python
  duration_sec = 45.0,    # 45 seconds per mission!
  sample_rate_hz = 20.0,  # 900 rows per mission
  ```
* 10 Train + 10 Val + 10 Test missions = 30 missions total.
* **Total Time:** $30 \times 45\,\text{s} = 1,350\,\text{seconds} = \mathbf{22.5\,\text{minutes}}$.
* **The Implication:** For a system designed for an 18 to 24-hour MALE UAV endurance flight, the entire empirical evidence base consists of less than half an hour of simulated operation. No 45-second sortie contains a realistic multi-hour degradation curve.

### 3.2 Label Mismatch on Fault Onset Ramps
In [`backend/telemetry/rotax_dataset_generator.py:262`](file:///d:/Programming/PS054/backend/telemetry/rotax_dataset_generator.py#L262):
```python
assigned_fault = fault_id if (fault_active and fault_severity > 0.30) else 0
```
* Fault injection begins at $t = 12.0\,\text{s}$ with an 8.0-second progressive ramp.
* Because `fault_severity` reaches 0.30 only after $2.4\,\text{seconds}$, all frames between $t = 12.0\,\text{s}$ and $t = 14.4\,\text{s}$ carry the fault's physical offset but are **labeled as Nominal (0)**.
* The model is explicitly trained on mislabeled ramp frames. This directly explains why `CYLINDER_2_CHT_OVERHEAT` recall drops to **0.836** on held-out test data: the classifier misreads low-severity ramp frames as nominal.

### 3.3 Physics Anomaly False Positive Rate (The Oil Temp Offset)
In `backend/physics/thermo_model.py:281`:
$$\text{is\_anomaly} = \text{anomaly\_score} \ge 0.65$$
On healthy training missions:
* Mean nominal anomaly score: **0.774**
* Mean fault anomaly score: **0.880**
* Percentage of healthy frames flagged anomalous: **93.8%**!
* **Root Cause:** A systematic calibration offset in `thermo_model.py` causes `RES_d_OIL_TEMP` to run **+9.75°C hotter than expected** permanently on healthy engines. This permanent offset elevates the composite Z-score, causing the physics anomaly detector to flag healthy frames as anomalous almost continuously. (The learned Autoencoder is much more robust, maintaining a nominal score of 0.11 vs. 0.52 on faults).

---

## 4. Summary Model Audit Matrix

| Model Artifact | File Location | Disk Size | Format | Training Data | Primary Metric | Primary Vulnerability |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Residual Autoencoder** | `backend/ml/models/rotax_autoencoder.json` | 9.7 KB | JSON (Weights + Biases) | 4,448 nominal simulated frames | 94.3% nominal accuracy | Fault recall is only 66.5% on held-out test missions. |
| **Random Forest** | `backend/ml/models/rotax_random_forest.joblib` | 2.14 MB | Joblib Serialized | 9,000 simulated frames (10 missions) | 97.5% test accuracy / 0.975 Macro-F1 | Silently falls back to heuristics if joblib missing; trained on 22.5 min data. |
| **Trend Model** | Inline in `trend_analyser.py` | — | Pure Python OLS | 7,200 rolling buffer frames | AIC model selection | Rolling history is limited to 6 minutes at 20 Hz. |
| **Monte Carlo RUL** | Inline in `trend_analyser.py` | — | 500-sample perturbation | Fitted trend parameters | p10, p50, p90 intervals | Lacks formal coverage calibration test. |
| **Empirical RUL** | `backend/ml/rul_estimator.py` | 9.5 KB | Python Source | None (Hardcoded constants) | Arbitrary countdown | Dead code contradicting live Monte Carlo RUL. |
| **Qwen3-4B LLM** | External / Runtime Cache | ~2.5 GB | GGUF Q4_K_M | Local vector store (21 manuals) | Grounded RAG synthesis | High GPU/RAM memory footprint on initial boot. |
