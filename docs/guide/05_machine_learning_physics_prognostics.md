# 🧪 Physics Twin, Machine Learning & Prognostics
**DRDO / iDEX Problem Statement ID: 26054**  
*Thermodynamic Virtual Shadow, 14 Residuals, 9-Stage Detection Pipeline & RUL Engine*

---

## 1. 1D Thermodynamic Virtual Physics Shadow

Rather than relying on black-box neural networks alone, the Digital Twin uses a **Physics-Informed Virtual Shadow** (`RotaxThermoModel`) that executes in < 0.5ms on every tick.

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                         1D THERMODYNAMIC VIRTUAL PHYSICS SHADOW                          │
└────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                             │
                       Inputs: Altitude, OAT, RPM, TPS, TAS, Phase
                                             │
                                             ▼
  1. ISA Barometric Atmosphere & Density Derating
     • Altitude lapse: $P_{\text{amb}} = 101.325 \times (1 - 0.0065 \cdot h_{\text{m}} / 288.15)^{5.25588}\text{ kPa}$
     • Air Density: $\rho_{\text{amb}} = (P_{\text{amb}} \cdot 1000) / (287.05 \cdot T_{\text{kelvin}})\text{ kg/m}^3$
     • Density Ratio: $\sigma = \rho_{\text{amb}} / 1.225$
                                             │
                                             ▼
  2. Volumetric Efficiency & Mass Flow Rate
     • $\eta_v = 0.82 + 0.08 \times (\text{TPS}/100)^{0.5}$
     • $\dot{m}_{\text{air}} = V_{\text{disp}} \times (\text{RPM}/120) \times \rho_{\text{amb}} \times \eta_v \times 3600\text{ [kg/hr]}$
                                             │
                                             ▼
  3. Air-Fuel Ratio (AFR) & Expected Fuel Flow
     • $\text{Target AFR} = 14.7 - 1.9 \times (\text{TPS}/100)^2$
     • $\text{Fuel Mass Flow} = \dot{m}_{\text{air}} / \text{Target AFR}\text{ [kg/hr]}$
     • $\text{Fuel Flow}_{\text{exp}} = \text{Fuel Mass Flow} / 0.74\text{ [L/hr]}$
                                             │
                                             ▼
  4. Cylinder Head & Exhaust Gas Temperatures (CHT / EGT)
     • Heat generation: $\dot{Q}_{\text{in}} \propto (\text{Fuel Flow} / 18.5) \times (\text{RPM}/5000)^{1.1}$
     • Heat dissipation factor: $K_{\text{cool}} = 0.75 \times \sigma \times (\text{TAS}/85) + 0.25$
     • $\text{Base CHT} = \text{OAT} + 75.0 + (35.0 \cdot \dot{Q}_{\text{in}} / K_{\text{cool}})\text{ [}^\circ\text{C]}$
     • Individual cylinder thermal offset: Cyl #2 (+1.5°C), Cyl #4 (+1.0°C)
                                             │
                                             ▼
  5. Lubrication & Manifold Pressure
     • $\text{Oil Temp}_{\text{exp}} = \text{OAT} + 60.0 + (28.0 \cdot \dot{Q}_{\text{in}} / K_{\text{cool}})\text{ [}^\circ\text{C]}$
     • $\text{Oil Press}_{\text{exp}} = 2.2 + 2.3 \times (\text{RPM}/5000) - 0.015 \times (\text{Oil Temp} - 80)\text{ [bar]}$
     • $\text{MAP}_{\text{exp}} = 35.0 + (P_{\text{amb}} - 38.0) \times (\text{TPS}/100)^{0.85}\text{ [kPa]}$
```

---

## 2. 14-Dimensional Normalized Residual Vector

Every frame, the system compares incoming sensor telemetry with the theoretical physics baseline to produce a **14-dimensional residual vector** ($\Delta = \text{Actual} - \text{Expected}$):

$$\vec{\Delta} = \begin{bmatrix}
\Delta CHT_1 & \Delta CHT_2 & \Delta CHT_3 & \Delta CHT_4 \\
\Delta EGT_1 & \Delta EGT_2 & \Delta EGT_3 & \Delta EGT_4 \\
\Delta OIL\_PRESS & \Delta OIL\_TEMP & \Delta FUEL\_FLOW & \Delta MAP \\
\Delta VIB\_RMS & \Delta BUS\_VOLTAGE
\end{bmatrix}$$

### Z-Score Normalization & Anomaly Score
Each channel is normalized by its empirical standard deviation $\sigma_i$:
* $z_{\text{CHT}} = |\Delta CHT_i| / 4.0^\circ\text{C}$
* $z_{\text{EGT}} = |\Delta EGT_i| / 15.0^\circ\text{C}$
* $z_{\text{OIL\_P}} = |\Delta OIL\_PRESS| / 0.3\text{ bar}$
* $z_{\text{VIB}} = |\Delta VIB\_RMS| / 0.25\text{ mm/s}$

The composite anomaly score combines maximum deviation with root-mean-square spread:
$$\text{Composite } Z = 0.65 \times \max(z_i) + 0.35 \times \sqrt{\frac{1}{N}\sum_{i=1}^{14} z_i^2}$$
$$\text{Anomaly Score} = 1.0 - e^{-0.45 \cdot \text{Composite } Z} \in [0.0, 1.0]$$

---

## 3. Sensor Sanity & Plausibility Validation

Before telemetry is passed to machine learning models, `SensorSanityValidator` verifies hardware plausibility to prevent false emergency alarms caused by wiring defects:

```
┌────────────────────────────────────────┬────────────────────────────────────────┐
│     PHYSICAL THERMODYNAMIC RAMP        │      ELECTRICAL SENSOR ARTIFACT        │
├────────────────────────────────────────┼────────────────────────────────────────┤
│ • $dT/dt \le 1.5^\circ\text{C/s}$      │ • $dT/dt > 10.0^\circ\text{C}$ in 50ms │
│ • Thermal conduction to oil/adjacent cyl│ • Isolated single-channel jump         │
│ • Natural analog jitter $\pm 0.15^\circ$C│ • Zero variance $\rightarrow$ Frozen ADC│
└────────────────────────────────────────┴────────────────────────────────────────┘
```

---

## 4. The 9-Stage Real-Time Detection Pipeline

The `DetectionPipeline` runs in $< 20\text{ms}$ at 20/50 Hz through 9 deterministic stages:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             9-STAGE ML DETECTION PIPELINE                                │
├──────────┬──────────────────────┬─────────────┬──────────────────────────────────────────┤
│ Stage    │ Operation            │ Latency     │ Description                              │
├──────────┼──────────────────────┼─────────────┼──────────────────────────────────────────┤
│ **1**    │ Sensor Sanity Check  │ < 0.1 ms    │ Validates rate-of-change and variance    │
│ **2**    │ Physics Residuals    │ < 0.5 ms    │ Computes 14-channel $\vec{\Delta}$ vector│
│ **3**    │ Autoencoder Scoring  │ < 2.0 ms    │ Computes L2 reconstruction loss          │
│ **4**    │ Gearbox FFT          │ < 2.0 ms    │ Monitors 3rd harmonic spectral peak      │
│ **5**    │ Score Buffer Write   │ < 0.1 ms    │ Writes scores to 60-min circular buffer  │
│ **6**    │ Fault Classification │ < 5.0 ms    │ Random Forest predicts Fault ID (1..8)   │
│ **7**    │ Majority Vote Buffer │ < 0.1 ms    │ Requires 8/10 frames agreement (500ms)   │
│ **8**    │ Prognostics Read     │ < 0.1 ms    │ Ingests latest background RUL report     │
│ **9**    │ JSON Event Emit      │ < 0.5 ms    │ Emits structured event with 30s holdoff  │
└──────────┴──────────────────────┴─────────────┴──────────────────────────────────────────┘
```

---

## 5. Gearbox 3rd Harmonic Spectral Analysis

Mechanical gear tooth micro-pitting produces negligible overall vibration RMS in its early stages, but creates a distinct spectral peak at the **3rd harmonic of the propeller reduction shaft**:

$$f_{\text{prop}} = \frac{\text{Engine RPM}}{60 \times 2.43} \approx 34.3\text{ Hz (at 5,000 RPM)}$$
$$f_{\text{target}} = 3 \times f_{\text{prop}} \approx 103.0\text{ Hz}$$

`GearboxSpectralAnalyser` tracks the ratio of current energy at $f_{\text{target}}$ against the initial 60-second baseline:
* **Harmonic Ratio < 3.0:** Nominal
* **Harmonic Ratio 3.0 – 5.9:** **WATCH** (Early micro-pitting detected)
* **Harmonic Ratio $\ge$ 6.0:** **FAULT** (Confirmed gearbox clutch wear / F05)

---

## 6. Degradation Trend Analysis & Probabilistic RUL Engine

Running in a dedicated background worker (`PrognosticsWorker`) every 10–20 seconds, the trend engine fits 3 candidate models to the rolling circular buffer (`ScoreBuffer`):

```
                  ┌────────────────────────────────────────┐
                  │    CANDIDATE DEGRADATION MODELS        │
                  └──────────────────┬─────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ 1. Linear Model  │       │ 2. Exponential   │       │ 3. Power-Law     │
│  $y = a + b \cdot t$│       │  $y = a \cdot e^{b t}$│       │  $y = a \cdot t^b$│
└──────────────────┘       └──────────────────┘       └──────────────────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     │
                                     ▼
                  Akaike Information Criterion (AIC) Selection
                  $\text{AIC} = n \ln(\text{RSS}/n) + 2k + \frac{2k(k+1)}{n - k - 1}$
                                     │
                                     ▼
                  Monte Carlo Projection to Threshold ($y = 0.85$)
                  $\rightarrow \text{RUL}_{P10} \text{ (10th percentile)}, \quad \text{RUL}_{P50} \text{ (Nominal)}$
```

### Mission Go / No-Go Decision Logic
$$\text{Go/No-Go Advisory} = \begin{cases}
\mathbf{GO} & \text{if } \text{RUL}_{P10} \ge 1.30 \times \text{Planned Sortie Hours} \\
\mathbf{CAUTION} & \text{if } 1.00 \times \text{Planned} \le \text{RUL}_{P10} < 1.30 \times \text{Planned} \\
\mathbf{NO-GO} & \text{if } \text{RUL}_{P10} < \text{Planned Sortie Hours}
\end{cases}$$
