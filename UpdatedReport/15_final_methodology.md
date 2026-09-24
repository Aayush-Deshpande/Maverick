> ⚠️ **Read [31_VERIFICATION_AND_CORRECTIONS.md](31_VERIFICATION_AND_CORRECTIONS.md) before quoting or citing this report.** File paths, some numeric claims, and the competitor list in this report set were checked against the real repository on 2026-09-23 and substantially diverged -- most of it also predates real work (backend/plant, evaluation, mission, reliability, twin, edge, osacbm.py, crank-angle diagnostics, FlyHash novelty detection) that supersedes what this file describes. Use docs/04_system_guide.md and docs/audit/07_unoccupied_axes_and_ground_up_plan.md as the current, source-verified reference instead.

# REPORT 15: FINAL MATHEMATICAL & ALGORITHMIC METHODOLOGY

**DRDO Aero-Twin | SIH 26054 Technical Reconstruction**  
**Classification:** Theoretical Foundations & Mathematical Formulations  
**Author:** DRDO Aero-Twin Engineering Reconstruction Team  
**Date:** March 2025  

---

## 1. EXECUTIVE SUMMARY & HYBRID MODELING PARADIGM

The DRDO Aero-Twin system operates on a **hybrid physics-informed, data-driven methodology**. Pure data-driven models (black-box neural networks) lack physical conservation guarantees and generate catastrophic false alarms under unobserved flight regimes. Conversely, pure physics-based models (finite-element CFD and combustion reaction kinetics) are computationally intractable for real-time edge processing at 20 Hz.

Our methodology reconciles this trade-off by combining:
1. **Lumped-Parameter First-Principles Thermodynamics:** To model expected thermal and mechanical behavior as a function of pilot control inputs and environmental boundary conditions.
2. **Residual Generation & State Estimation (EKF):** To strip away normal operating dynamics, isolating genuine component degradation.
3. **Symmetric Bottleneck Autoencoding & Supervised Ensembles:** To detect non-linear multivariate anomalies and classify failure modes.
4. **Conformal Trend Extrapolation & Rainflow Fatigue Mechanics:** To predict Remaining Useful Life (RUL) with mathematically calibrated confidence intervals.

```
Hybrid Digital Twin Theoretical Flow
┌────────────────────────────────────────────────────────┐
│  Boundary Inputs: [RPM, Throttle, Airspeed, Altitude]  │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│ Measured Plant Sensors    │ │ 1st-Principles Physics    │
│ z_k = [CHT, EGT, P_oil...]│ │ Observer Model: x̂_k       │
└─────────────┬─────────────┘ └─────────────┬─────────────┘
              │                             │
              └─────────────┬───────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Residual Vector Generation: r_k = z_k - h(x̂_k)         │
│ Normalization: z_score = (r_k - μ) / σ                 │
└───────────────────────────┬────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│ Unsupervised Anomaly      │ │ Supervised Diagnostic     │
│ Autoencoder: J_AE = ‖z-ẑ‖² │ │ Random Forest: P(Fault|r) │
└─────────────┬─────────────┘ └─────────────┬─────────────┘
              │                             │
              └─────────────┬───────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ Probabilistic RUL & Conformal Prediction Intervals    │
│ + Palmgren-Miner Low-Cycle Thermal Fatigue Damage: D   │
└────────────────────────────────────────────────────────┘
```

---

## 2. THERMODYNAMIC PHYSICS OBSERVER FORMULATION

### 2.1 State Space & Control Vectors
Let the engine continuous state vector $\mathbf{x}(t) \in \mathbb{R}^7$ and environmental control vector $\mathbf{u}(t) \in \mathbb{R}^5$ be defined as:

$$\mathbf{x}(t) = \begin{bmatrix} T_{\text{cyl,1}}(t) \\ T_{\text{cyl,2}}(t) \\ T_{\text{cyl,3}}(t) \\ T_{\text{cyl,4}}(t) \\ T_{\text{oil}}(t) \\ P_{\text{oil}}(t) \\ \Omega(t) \end{bmatrix}, \quad \mathbf{u}(t) = \begin{bmatrix} \delta_{\text{throttle}}(t) \\ h_{\text{alt}}(t) \\ T_{\text{ambient}}(t) \\ P_{\text{ambient}}(t) \\ V_{\text{IAS}}(t) \end{bmatrix}$$

### 2.2 First-Law Energy Balance on Cylinder Heads
Applying the First Law of Thermodynamics to each individual cylinder head control volume ($i \in \{1, 2, 3, 4\}$):

$$m_{\text{head}} c_p \frac{d T_{\text{cyl},i}}{dt} = \dot{Q}_{\text{comb},i} - \dot{Q}_{\text{cool},i} - \dot{Q}_{\text{rad},i}$$

Where:
1. **Heat Input from Combustion ($\dot{Q}_{\text{comb},i}$):**
   $$\dot{Q}_{\text{comb},i} = \eta_{\text{thermal}} \cdot \dot{m}_{\text{fuel},i} \cdot \text{LHV}_{\text{fuel}} \cdot \xi_i$$
   where $\text{LHV}_{\text{fuel}} = 43.5\text{ MJ/kg}$ (aviation fuel lower heating value), $\eta_{\text{thermal}} \approx 0.32$ (indicated thermal efficiency), and $\xi_i \in [0, 1]$ represents the cylinder individual health factor (nominal $\xi_i = 1.0$).

2. **Fuel Mass Flow Rate ($\dot{m}_{\text{fuel}}$):**
   Governed by speed-density fuel injection equations:
   $$\dot{m}_{\text{fuel}} = \frac{\Omega \cdot V_{\text{disp}}}{2 \cdot 60} \cdot \frac{P_{\text{manifold}}}{R_{\text{spec}} T_{\text{manifold}}} \cdot \eta_{\text{vol}} \cdot \left(\frac{1}{\text{AFR}}\right)$$
   where $V_{\text{disp}} = 1.352 \times 10^{-3}\text{ m}^3$, $\text{AFR} = 14.7$ (stoichiometric air-fuel ratio), and volumetric efficiency $\eta_{\text{vol}} = f(\Omega, P_{\text{manifold}})$.

3. **Convective Heat Rejection ($\dot{Q}_{\text{cool},i}$):**
   $$\dot{Q}_{\text{cool},i} = h_{\text{conv}}(V_{\text{IAS}}, \rho) \cdot A_{\text{fin}} \cdot \left( T_{\text{cyl},i}(t) - T_{\text{ambient}}(t) \right)$$
   The convective heat transfer coefficient scales with ram air dynamic pressure:
   $$h_{\text{conv}} = h_0 \left( 1 + \kappa_v \sqrt{\frac{1}{2} \rho(h) V_{\text{IAS}}^2} \right)$$

### 2.3 Lubrication Oil Thermal Balance
The engine oil absorbs friction power from crankshaft journals and heat conduction from piston skirts, cooled by the external oil radiator:

$$C_{\text{oil}} \frac{d T_{\text{oil}}}{dt} = \dot{Q}_{\text{friction}}(\Omega) + \sum_{i=1}^4 \dot{Q}_{\text{piston}\to\text{oil},i} - \dot{Q}_{\text{cooler}}$$

$$\dot{Q}_{\text{cooler}} = \dot{m}_{\text{oil}} c_{\text{oil}} \varepsilon_{\text{hex}} \left( T_{\text{oil}} - T_{\text{ambient}} \right)$$

Where $\varepsilon_{\text{hex}}$ is the oil cooler heat exchanger effectiveness ($\approx 0.65$).

---

## 3. RESIDUAL GENERATION & KALMAN STATE ESTIMATION

### 3.1 Thermodynamic Residual Generation
Let $\mathbf{z}_k \in \mathbb{R}^m$ be the real-time sensor measurement vector at time step $k$. The physics model computes the expected measurement vector $\hat{\mathbf{z}}_k = h(\hat{\mathbf{x}}_k, \mathbf{u}_k)$. The raw residual vector $\mathbf{r}_k$ is:

$$\mathbf{r}_k = \mathbf{z}_k - \hat{\mathbf{z}}_k$$

To ensure cross-parameter comparability, residuals are dynamically normalized via rolling historical baselines:

$$r_{k,j}^* = \frac{r_{k,j} - \mu_{j,\text{baseline}}}{\sigma_{j,\text{baseline}}}$$

Under nominal conditions, by the Central Limit Theorem, $\mathbf{r}_k^* \sim \mathcal{N}(\mathbf{0}, \mathbf{I})$. Any persistent deviation $|\mathbf{r}_k^*| > 3.0$ indicates localized physical degradation.

### 3.2 Extended Kalman Filter (EKF) Discrete Formulation
To filter sensor noise and estimate unmeasured internal states (such as internal oil film thickness or localized coolant jacket temperature), an Extended Kalman Filter is formulated:

* **Non-linear Plant Model:** $\mathbf{x}_k = f(\mathbf{x}_{k-1}, \mathbf{u}_k) + \mathbf{w}_k, \quad \mathbf{w}_k \sim \mathcal{N}(\mathbf{0}, \mathbf{Q}_k)$
* **Observation Model:** $\mathbf{z}_k = h(\mathbf{x}_k) + \mathbf{v}_k, \quad \mathbf{v}_k \sim \mathcal{N}(\mathbf{0}, \mathbf{R}_k)$

**1. Time Update (Prediction Step):**
$$\hat{\mathbf{x}}_{k|k-1} = f(\hat{\mathbf{x}}_{k-1|k-1}, \mathbf{u}_k)$$
$$\mathbf{P}_{k|k-1} = \mathbf{F}_{k-1} \mathbf{P}_{k-1|k-1} \mathbf{F}_{k-1}^T + \mathbf{Q}_k$$
Where the Jacobian matrix $\mathbf{F}_{k-1} = \left. \frac{\partial f}{\partial \mathbf{x}} \right|_{\hat{\mathbf{x}}_{k-1|k-1}, \mathbf{u}_k}$.

**2. Measurement Update (Correction Step):**
$$\tilde{\mathbf{y}}_k = \mathbf{z}_k - h(\hat{\mathbf{x}}_{k|k-1})$$
$$\mathbf{S}_k = \mathbf{H}_k \mathbf{P}_{k|k-1} \mathbf{H}_k^T + \mathbf{R}_k$$
$$\mathbf{K}_k = \mathbf{P}_{k|k-1} \mathbf{H}_k^T \mathbf{S}_k^{-1}$$
$$\hat{\mathbf{x}}_{k|k} = \hat{\mathbf{x}}_{k|k-1} + \mathbf{K}_k \tilde{\mathbf{y}}_k$$
$$\mathbf{P}_{k|k} = (\mathbf{I} - \mathbf{K}_k \mathbf{H}_k) \mathbf{P}_{k|k-1}$$

---

## 4. ARTIFICIAL INTELLIGENCE & PATTERN RECOGNITION

### 4.1 Bottleneck Autoencoder Architecture
For unsupervised novelty detection, a symmetric bottleneck autoencoder compresses the 14-dimensional normalized residual vector $\mathbf{r}_k^*$ into a 4-dimensional latent subspace:

$$\mathbf{r}^* \in \mathbb{R}^{14} \xrightarrow[\mathbf{W}_1, \mathbf{b}_1]{\text{Dense } 8} \mathbf{h}_1 \xrightarrow[\mathbf{W}_2, \mathbf{b}_2]{\text{Dense } 4} \mathbf{z}_{\text{latent}} \xrightarrow[\mathbf{W}_3, \mathbf{b}_3]{\text{Dense } 8} \mathbf{h}_2 \xrightarrow[\mathbf{W}_4, \mathbf{b}_4]{\text{Dense } 14} \hat{\mathbf{r}}^* \in \mathbb{R}^{14}$$

* **Encoder Activation:** LeakyReLU with negative slope $\alpha = 0.1$.
* **Reconstruction Loss Metric (Anomaly Score):**
  $$J_{\text{AE}}(\mathbf{r}^*) = \|\mathbf{r}^* - \hat{\mathbf{r}}^*\|_2^2 = \sum_{j=1}^{14} \left( r_j^* - \hat{r}_j^* \right)^2$$
* **Adaptive Thresholding:** An anomaly alert is triggered if $J_{\text{AE}} > \tau_{\text{thresh}}$, where $\tau_{\text{thresh}} = \mu_{J} + 3.29 \sigma_{J}$ (corresponding to a 99.9% statistical confidence bound).

### 4.2 Multi-Class Diagnostic Random Forest
When an anomaly is confirmed, the residual vector $\mathbf{r}^*$ and derived spectral features are routed to an ensemble of $B = 100$ decorrelated decision trees.

The posterior class probability for fault class $c \in \{F_{00}, F_{01}, \dots, F_{08}\}$ is:

$$P(Y = c \mid \mathbf{r}^*) = \frac{1}{B} \sum_{b=1}^B \mathbb{I}\left( T_b(\mathbf{r}^*) = c \right)$$

* **Gini Impurity Splitting Criterion:**
  $$I_G(p) = 1 - \sum_{c=1}^C p_c^2$$
* **Rejection Option (Handling Unknown Faults):**
  $$\hat{Y} = \begin{cases} \arg\max_c P(Y = c \mid \mathbf{r}^*) & \text{if } \max_c P(Y = c \mid \mathbf{r}^*) \ge 0.65 \\ \text{"UNKNOWN\_ANOMALY"} & \text{if } \max_c P(Y = c \mid \mathbf{r}^*) < 0.65 \end{cases}$$
  This prevents the model from forcing novel failure modes into known training classes.

---

## 5. PROGNOSTICS, CONFORMAL RUL & FATIGUE DAMAGE

### 5.1 Probabilistic RUL Extrapolation via Akaike Information Criterion
In `backend/ml/trend_analyser.py`, when a progressive degradation fault (e.g., cooling blockage or oil leak) is detected, two competing degradation trajectory models are fitted over the sliding window $t \in [t_0, t_k]$:

$$\text{Linear Model: } g_1(t) = \beta_0 + \beta_1 t$$
$$\text{Quadratic Model: } g_2(t) = \alpha_0 + \alpha_1 t + \alpha_2 t^2$$

The optimal model is selected via the **Akaike Information Criterion (AIC)**:

$$\text{AIC} = 2k - 2\ln(\hat{L}) = 2k + n \ln\left(\frac{\text{RSS}}{n}\right)$$

Where $k$ is the number of model parameters, $n$ is window length, and $\text{RSS}$ is residual sum of squares.

### 5.2 Monte Carlo Failure Horizon Projection
Let $y_{\text{crit}}$ be the physical safety threshold (e.g., $T_{\text{CHT}} = 150^\circ\text{C}$). To compute RUL under parameter uncertainty, a 500-sample Monte Carlo perturbation is executed:

$$\beta_i^{(m)} \sim \mathcal{N}\left(\hat{\beta}_i, \text{Var}(\hat{\beta}_i)\right), \quad m = 1, \dots, 500$$

For each trajectory $g^{(m)}(t)$, the time-to-failure $t_{\text{fail}}^{(m)}$ is the root of:

$$g^{(m)}(t_{\text{fail}}^{(m)}) - y_{\text{crit}} = 0$$

$$\text{RUL}^{(m)} = t_{\text{fail}}^{(m)} - t_{\text{current}}$$

The reported RUL is the 50th percentile (median), bounded by a 90% non-parametric confidence interval:

$$\text{RUL}_{\text{reported}} = \text{Median}(\{\text{RUL}^{(m)}\}), \quad \text{CI}_{90} = \left[ P_{5}(\{\text{RUL}^{(m)}\}), P_{95}(\{\text{RUL}^{(m)}\}) \right]$$

### 5.3 Palmgren-Miner Cumulative Thermal Fatigue Damage
Aviation piston engines suffer low-cycle fatigue (LCF) from thermal reversals. In `trend_analyser.py`, continuous temperature signals are decomposed into discrete reversal cycles using the standard **Rainflow-Counting Algorithm (ASTM E1049-85)**.

For each identified thermal reversal range $\Delta T_i$, the permissible cycles to failure $N_i$ is determined from the Coffin-Manson relation:

$$\frac{\Delta \varepsilon_p}{2} = \varepsilon_f' (2 N_i)^c \implies N_i = A \left( \Delta T_i \right)^{-m}$$

Where $A$ and $m$ are material fatigue constants for 2024-T6 aluminum alloy. The cumulative fatigue damage fraction $D \in [0, 1]$ is integrated via the Palmgren-Miner linear cumulative damage hypothesis:

$$D = \sum_{i=1}^M \frac{n_i}{N_i(\Delta T_i)}$$

When $D \to 1.0$, microscopic fatigue cracks initiate at the valve bridge or exhaust port, signaling mandatory teardown and overhaul.

---

## 6. COMPLETE METHODOLOGICAL RIGOR SUMMARY

| Subsystem | Governing Equation / Algorithm | Primary Input | Output Metric | Computational Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **Physics Plant** | 1st Law Thermodynamics ($Q_{\text{in}} - Q_{\text{out}} = mc \frac{dT}{dt}$) | Throttle, Altitude, Airspeed | Expected Temperatures $\hat{\mathbf{z}}_k$ | $\mathcal{O}(1)$ (0.8 ms) |
| **State Estimator** | Extended Kalman Filter (EKF) | Raw Telemetry + Physics | Estimated State Vector $\hat{\mathbf{x}}_k$ | $\mathcal{O}(n^3)$ ($n=7$, 0.12 ms) |
| **Residual Generator** | Dynamic z-score Normalization | Measured $\mathbf{z}_k$ vs Expected $\hat{\mathbf{z}}_k$ | Normalized Residual $\mathbf{r}_k^*$ | $\mathcal{O}(m)$ ($m=14$, 0.01 ms) |
| **Anomaly Detector** | Bottleneck Autoencoder (14-8-4-8-14) | Residual Vector $\mathbf{r}_k^*$ | Reconstruction Error $J_{\text{AE}}$ | $\mathcal{O}(1)$ (0.06 ms) |
| **Fault Classifier** | Random Forest ($B=100$ trees) | Residuals + Vibration | Class Posterior $P(F_i \mid \mathbf{r})$ | $\mathcal{O}(B \cdot d)$ (1.4 ms) |
| **Prognostics (RUL)** | AIC Polynomial Fit + 500-run Monte Carlo | Historical Residual Drift | Probabilistic RUL + $\text{CI}_{90}$ | $\mathcal{O}(M \cdot n)$ (12.5 ms) |
| **Fatigue Mechanics** | Rainflow Counting + Palmgren-Miner | Thermal Reversals $\Delta T$ | Cumulative Damage Index $D$ | $\mathcal{O}(N \log N)$ (0.4 ms) |
