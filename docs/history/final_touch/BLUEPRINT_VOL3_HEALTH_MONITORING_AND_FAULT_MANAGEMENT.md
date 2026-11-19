# BLUEPRINT VOLUME 3: HEALTH MONITORING, SENSOR VALIDATION, AND FAULT MANAGEMENT PIPELINE

## 1. Sensor Validation & Analytical Redundancy Architecture

In an airborne propulsion system, false engine alarms caused by sensor drift or wiring degradation are as dangerous as undetected physical failures. A false in-flight abort over hostile territory or high-mountain terrain can result in aircraft hull loss. The first duty of the health monitoring system is rigorous **Sensor Validation via Analytical Redundancy**.

```
                           Raw Sensor Telemetry: y_raw(t)
                                         |
                                         v
                         +-------------------------------+
                         | Range & Rate Plausibility     | ---> Hard Out-of-Bounds Fault
                         | |dy/dt| > dy_max Limiters     |      (Sensor Disconnect / Open Circuit)
                         +-------------------------------+
                                         |
                                         v (Plausible Signals)
                         +-------------------------------+
                         | Parity Space Residual Engine  | <--- 0D/1D Analytical Predictions
                         | [Omega_parity] * y_meas       |
                         +-------------------------------+
                                         |
                       +-----------------+-----------------+
                       |                                   |
                       v                                   v
             [ SENSOR FAULT ISOLATED ]           [ VALIDATED SENSOR VECTOR ]
             - Freeze faulty sensor              y_valid(t) forwarded to
             - Switch to EKF Virtual Sensor      Digital Twin Observer & Residuals
             - Alert GCS: "SENSOR DEGRADED"
```

### 1.1 Sensor vs. Engine vs. Environmental Variation Discrimination
The system mathematically distinguishes four distinct sources of telemetry deviation:

```
+----------------------------------------------------------------------------------------------------+
|                        TELEMETRY DEVIATION DISCRIMINATION MATRIX                                   |
+----------------------------------------------------------------------------------------------------+
| Phenomenon             | Physics Signature                                   | Classification       |
+------------------------+-----------------------------------------------------+----------------------+
| Environmental Lapse    | All cylinders shift uniformly with altitude z;       | Normal Aerothermal   |
| (e.g., High-Hot Leh)   | MAP residual r_map ~ 0; EKF parameters constant.    | Operational Shift    |
+------------------------+-----------------------------------------------------+----------------------+
| Normal Throttle Step   | Transient lag in MAP and RPM matching engine inertia| Normal Dynamic       |
| (Combat Break / Climb) | J_eng; thermodynamic conservation satisfied.        | Operating Variation  |
+------------------------+-----------------------------------------------------+----------------------+
| Sensor Hardware Fault  | Single sensor jumps step-wise or drifts; analytical | Sensor Degradation   |
| (Thermocouple Break)   | parity residuals spike; thermodynamic residuals flat| (Isolate Sensor)     |
+------------------------+-----------------------------------------------------+----------------------+
| Real Engine Failure    | Multiple cross-correlated residuals violate limits; | Confirmed Engine     |
| (Piston Blow-by)       | Delta-P_crankcase > 0, Delta-T_oil > 0, Pmax drops. | Mechanical Fault     |
+----------------------------------------------------------------------------------------------------+
```

### 1.2 Parity Space Formulation
For sensor set $\mathbf{y}_s(t) = \mathbf{C}_s \mathbf{x}(t) + \mathbf{f}_s(t) + \mathbf{v}(t)$, the parity transformation matrix $\mathbf{V}_p$ is constructed such that $\mathbf{V}_p \mathbf{C}_s = \mathbf{0}$:
$$\mathbf{r}_p(t) = \mathbf{V}_p \cdot \mathbf{y}_s(t) = \mathbf{V}_p \cdot \mathbf{f}_s(t) + \mathbf{V}_p \cdot \mathbf{v}(t)$$
Under healthy sensors, $\mathbb{E}[\mathbf{r}_p(t)] = \mathbf{0}$. If sensor $j$ experiences a bias fault $f_{s,j}(t)$, the parity vector points along the dedicated column signature $\mathbf{v}_{p,j}$, isolating the exact faulty sensor in under $40\text{ ms}$.

---

## 2. Physics-Residual Generation

The foundational flaw of naive AI/ML health monitors is training deep neural networks directly on raw sensor values. When a UAV climbs from sea level ($101.3\text{ kPa}, 25^\circ\text{C}$) to $25,000\text{ ft}$ ($37.6\text{ kPa}, -34^\circ\text{C}$), raw sensor temperatures and pressures shift drastically, generating false anomaly alarms.

Our system solves this by computing **Normalized Physics Residuals**:
$$\mathbf{r}_{phys}(t) = \mathbf{y}_{valid}(t) - \mathbf{h}_{mvem}(\hat{\mathbf{x}}_{twin}(t), \mathbf{u}(t))$$

The normalized residual vector $\mathbf{r}^*(t) \in \mathbb{R}^7$ contains:
$$\mathbf{r}^*(t) = \begin{bmatrix}
\frac{EGT_{meas} - \widehat{EGT}_{mvem}}{\sigma_{egt}} & \text{Exhaust Gas Temperature Residual} \\[4pt]
\frac{CHT_{meas}^{max} - \widehat{CHT}_{mvem}^{max}}{\sigma_{cht}} & \text{Cylinder Head Temperature Residual} \\[4pt]
\frac{P_{oil,meas} - \widehat{P}_{oil,mvem}}{\sigma_{poil}} & \text{Oil Pressure Residual} \\[4pt]
\frac{T_{oil,meas} - \widehat{T}_{oil,mvem}}{\sigma_{toil}} & \text{Oil Sump Temperature Residual} \\[4pt]
\frac{MAP_{meas} - \widehat{MAP}_{mvem}}{\sigma_{map}} & \text{Manifold Absolute Pressure Residual} \\[4pt]
\frac{\dot{m}_{f,meas} - \widehat{\dot{m}}_{f,mvem}}{\sigma_{fuel}} & \text{Fuel Consumption Flow Residual} \\[4pt]
\frac{\Delta CHT_{cyl1-4}}{\sigma_{spread}} & \text{Inter-Cylinder Thermal Imbalance Residual}
\end{bmatrix}$$

Because the 0D/1D MVEM model explicitly accounts for altitude, ram-air velocity, ambient temperature, and throttle command, **these residuals remain strictly zero-mean Gaussian white noise under all healthy flight regimes**. Any deviation is guaranteed to represent true physical degradation.

---

## 3. Composite Health Indices (ISO 13374 / OSA-CBM Standards)

Following the ISO 13374 and MIMOSA OSA-CBM condition monitoring standards, the health of the propulsion system is aggregated into normalized indices $HI \in [0.0, 1.0]$, where $1.0$ represents pristine condition and $0.0$ represents functional failure:

```
                               +---------------------------------------+
                               | Overall Engine Health Index (HI_eng)  |
                               +---------------------------------------+
                                                   |
        +------------------+-----------------------+-----------------------+------------------+
        |                  |                       |                       |                  |
        v                  v                       v                       v                  v
+---------------+  +---------------+       +---------------+       +---------------+  +---------------+
| Combustion HI |  | Lubrication HI|       | Thermal HI    |       | Turbo HI      |  | Mechanical HI |
| (HI_comb)     |  | (HI_lub)      |       | (HI_therm)    |       | (HI_turbo)    |  | (HI_mech)     |
+---------------+  +---------------+       +---------------+       +---------------+  +---------------+
  - EGT balance      - Oil pressure          - CHT max               - Boost MAP vs     - Crankcase
  - Pmax variance    - Film thickness        - Coolant Delta-T         wastegate duty     blow-by
  - Specific fuel      h_min                 - Radiator thermal      - Compressor       - Bearing RMS
    consumption      - Oil temp margin         rejection               surge margin       vibration
```

### 3.1 Mathematical Formulations of Subsystem Health Indices
1. **Combustion Health Index ($HI_{comb}$):**
   $$HI_{comb}(t) = \exp\left( -w_1 \cdot \frac{|\Delta EGT_{cyl}^{spread}|}{\Delta EGT_{limit}} - w_2 \cdot \left(\frac{BSFC(t) - BSFC_{nominal}}{BSFC_{nominal}}\right)^2 \right)$$
2. **Lubrication Health Index ($HI_{lub}$):**
   $$HI_{lub}(t) = \min\left( 1.0, \; \max\left( 0.0, \; \frac{P_{oil}(t) - P_{oil,critical}}{P_{oil,nominal} - P_{oil,critical}} \right) \right) \cdot \Phi\left( \frac{h_{min}(t) - h_{crit}}{\sigma_h} \right)$$
3. **Turbocharging Health Index ($HI_{turbo}$):**
   $$HI_{turbo}(t) = 1.0 - \min\left(1.0, \; \frac{|MAP_{meas}(t) - \widehat{MAP}_{mvem}(t)|}{MAP_{threshold}} + \Delta u_{wg}^{leak}(t)\right)$$
4. **Overall Engine Health Index ($HI_{eng}$):**
   $$HI_{eng}(t) = \min\Big( HI_{comb}(t), \; HI_{lub}(t), \; HI_{therm}(t), \; HI_{turbo}(t), \; HI_{mech}(t) \Big)^{0.4} \cdot \left( \prod_{k=1}^5 HI_k(t) \right)^{\frac{0.6}{5}}$$
   *(The blended min-geometric product ensures that severe failure of a single critical subsystem immediately drops overall engine health while avoiding numeric cliffing).*

---

## 4. Anomaly Detection: Deep VAE + Extreme Value Theory (EVT)

Traditional thresholding ($3\sigma$) fails in non-linear aerospace systems due to fat-tailed transient noise, generating either excessive false alarms or missed early detections. We implement a hybrid **Deep Variational Autoencoder (VAE) + Extreme Value Theory (EVT) Peaks-Over-Threshold (POT)** anomaly detection engine.

```
Physics Residuals r*(t) ---> [ VAE Encoder: q_phi(z|r) ] ---> Latent Space z ~ N(mu_z, sigma_z^2)
                                                                      |
Reconstructed Residual r_hat <--- [ VAE Decoder: p_theta(r|z) ] <-----+
            |
            v
Reconstruction Anomaly Metric: s(t) = ||r*(t) - r_hat(t)||_W^2
            |
            v
[ Extreme Value Theory POT Engine ] ---> Fits Generalized Pareto Distribution (GPD)
                                         Computes Dynamic Threshold Th_alpha (p < 10^-4)
                                         Zero Manual Heuristic Tuning
```

### 4.1 Extreme Value Theory Peaks-Over-Threshold (POT) Formulation
The reconstruction error metric $s(t) = \sum_{j=1}^7 w_j \cdot (r_j^*(t) - \hat{r}_j^*(t))^2$ is evaluated against an extreme value threshold. According to the Pickands-Balkema-de Haan theorem, exceedances $Y = (s - u)$ over a sufficiently high initial threshold $u$ converge to the **Generalized Pareto Distribution (GPD)**:
$$G_{\xi, \sigma}(y) = 1 - \left( 1 + \frac{\xi \cdot y}{\sigma} \right)^{-\frac{1}{\xi}}, \quad y > 0, \; 1 + \frac{\xi y}{\sigma} > 0$$
Where $\xi$ is the extreme value shape parameter and $\sigma$ is the scale parameter, fitted via Maximum Likelihood Estimation (MLE).
For a targeted False Alarm Rate $\alpha = 10^{-4}$ ($1$ false alarm per $2.77$ flight hours at $10\text{ Hz}$), the mathematically exact anomaly threshold $z_q$ is:
$$z_q = u + \frac{\sigma}{\xi} \cdot \left[ \left( \frac{N_{total}}{N_u} \cdot \alpha \right)^{-\xi} - 1 \right]$$
**This provides mathematically guaranteed false-alarm rates without arbitrary user-chosen heuristics.**

---

## 5. The Complete 10-Stage Fault Management Pipeline

When an anomaly is detected, the system executes an automated, deterministic 10-stage fault resolution protocol:

```
[ Stage 1: Normal Behaviour ]
   | Physics residuals r*(t) conform to Gaussian white noise (s(t) < z_q).
   v
[ Stage 2: Deviation Inception ]
   | Latent reconstruction error s(t) exceeds EVT threshold z_q.
   v
[ Stage 3: Anomaly Detection Triggered ]
   | Anomaly score logged; temporal persistence timer initialized (t_start = t).
   v
[ Stage 4: Fault Confirmation (Temporal Persistence) ]
   | Condition must persist for T_persist >= 3.0 seconds (150 cycles at 50 Hz).
   | Discards transient electromagnetic interference and instantaneous sensor glitches.
   v
[ Stage 5: Fault Isolation (Parity Space & Residual Signatures) ]
   | Sensor parity checks confirm all sensors healthy; fault is internal engine mechanical.
   | Residual directional signature vector s_dir = sign(r*(t)) computed.
   v
[ Stage 6: Fault Classification (FMECA Multi-Class Classifier) ]
   | Multi-class residual classifier isolates exact failure mode:
   | (e.g., TURBO_WASTEGATE_STUCK_OPEN vs. INJECTOR_3_CLOGGED vs. PISTON_RING_BLOWBY).
   v
[ Stage 7: Severity Assessment ]
   | Fault severity graded: AMBER (Advisory / Mission Degraded) or RED (Critical / Abort).
   v
[ Stage 8: Degradation Trajectory Estimation ]
   | Active damage kinetics model engaged; drift parameter beta updated.
   v
[ Stage 9: Prognosis & Conformal RUL Prediction ]
   | Conformal predictor projects RUL confidence bounds [RUL_low, RUL_high] at 95% coverage.
   v
[ Stage 10: Mission Impact & Actionable Recommendation ]
   | Tactical flight envelope derated; glide polar reachability cone projected to GCS;
   | Pilot presented with 1-click divert advisory to nearest reachable airfield.
```

---

## 6. Aerothermal & Mechanical FMECA Classification Engine

The system embeds an aero-propulsion Failure Mode, Effects, and Criticality Analysis (FMECA) diagnostic knowledge base:

```
+----------------------------------------------------------------------------------------------------+
|                         AERO-PROPULSION FMECA CLASSIFICATION MATRIX                                |
+----------------------------------------------------------------------------------------------------+
| Failure Mode                   | Diagnostic Residual Signature Vector                 | Severity   |
+--------------------------------+------------------------------------------------------+------------+
| Turbocharger Wastegate Stuck   | Delta-MAP << 0, Delta-EGT > 0, N_tc << N_target,     | AMBER      |
| Open (High Altitude Derate)    | Throttle = 100% but MAP flat.                        | (Tactical) |
+--------------------------------+------------------------------------------------------+------------+
| Single-Cylinder Fuel Injector  | Delta-EGT_cyl3 << 0, Delta-CHT_cyl3 << 0,            | AMBER      |
| Partial Clogging (Lean / Cut)  | Inter-cylinder spread > 45 K, BSFC rises.            | (Monitor)  |
+--------------------------------+------------------------------------------------------+------------+
| Piston Ring Pack Blow-by       | Delta-P_crankcase >> 0, Delta-T_oil > 0,             | AMBER      |
| (Combustion Gas Leakage)       | Delta-P_max < 0, oil consumption rate rises.         | (Degrade)  |
+--------------------------------+------------------------------------------------------+------------+
| Cylinder Head Gasket Weep      | Coolant expansion tank pressure spikes, Delta-CHT >0,| RED        |
| (Coolant Cross-Contamination)  | White vapor exhaust signature, coolant level drops.  | (Land ASAP)|
+--------------------------------+------------------------------------------------------+------------+
| Oil Pump Pressure Regulator    | Delta-P_oil << 0 across all RPMs; T_oil rises;       | RED        |
| Jammed (Imminent Bearing Wipe) | Hydrodynamic film h_min collapses below 0.8 um.      | (Land Immed|
+--------------------------------+------------------------------------------------------+------------+
```

### 6.1 Explainable AI (XAI) Attribution
For every classified fault, the system outputs SHAP (Shapley Additive Explanations) feature attributions. When `TURBO_WASTEGATE_STUCK_OPEN` is signaled to the propulsion engineer, the console displays:
- $+44\%$ attribution from `MAP_Deficit_vs_Target`
- $+28\%$ attribution from `Elevated_EGT_Post_Turbine`
- $+19\%$ attribution from `Zero_Wastegate_PWM_Response`
- $+9\%$ attribution from `Barometric_Altitude_Lapse`
**This provides the propulsion engineer with transparent physical justification for the diagnosis.**
