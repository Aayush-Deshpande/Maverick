# BLUEPRINT VOLUME 4: PROGNOSTICS, RUL, AND MISSION RELIABILITY COUPLING

## 1. The Prognostics Reality: Addressing the Lack of Run-to-Failure Data

In academic data science competitions, models are frequently trained on datasets like NASA C-MAPSS (turbofans run to catastrophic failure on test stands). In actual military and commercial aviation:
1. **Engines are never permitted to operate to catastrophic in-flight destruction.** Components are pulled and overhauled at conservative Time-Between-Overhaul ($TBO$) intervals (e.g., $1,200\text{ to }2,000\text{ flight hours}$).
2. **True run-to-failure runout data for aero-piston engines (Rotax 914/915) does not exist in the public domain.**
3. **Any system claiming "99.8% precision RUL prediction" on uncalibrated synthetic data is technically invalid.**

The AP-CPDT resolves this dilemma by grounding prognostics on **hybrid physics damage kinetics**, stochastic Wiener drift, and **Conformal Prediction intervals** with mathematically proven finite-sample coverage:

```
+----------------------------------------------------------------------------------------------------+
|                         GROUNDED PROGNOSTICS METHODOLOGY                                           |
+----------------------------------------------------------------------------------------------------+
| Data Source               | Role in the System                                | Boundary & Claim   |
+---------------------------+---------------------------------------------------+--------------------+
| Physics Damage Kinetics   | Arrhenius, Paris-Erdogan, ISO 281 wear equations  | Deterministic      |
| (Thermodynamic Stressors) | provide causal rates of degradation.              | baseline rate      |
+---------------------------+---------------------------------------------------+--------------------+
| Fleet Maintenance Records | Historical overhaul intervals, oil spectrographic | Population prior   |
| (Airbase Depot)           | analyses, and teardown wear measurements.         | distribution       |
+---------------------------+---------------------------------------------------+--------------------+
| Test-Rig / HIL Synthetic  | Calibrated multi-failure simulation models to map | Anomaly signature  |
| Fault Injections          | non-linear cross-couplings and residual behavior. | validation only    |
+---------------------------+---------------------------------------------------+--------------------+
| In-Flight Telemetry       | Real-time observation of cumulative stress cycles | Drives individual  |
| (Physical Flight)         | and physics-residual drift rate beta(t).          | engine drift       |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Physics of Aero-Propulsion Degradation

Component degradation is driven by thermodynamic stressors computed directly by the Digital Twin:

```
                                  Thermodynamic Stressors
                               (T_oil, Pmax, CHT, RPM, TIT)
                                             |
         +--------------------+--------------+--------------+--------------------+
         |                    |                             |                    |
         v                    v                             v                    v
  [ Arrhenius Aging ]  [ Paris-Erdogan Fatigue ]     [ Archard Friction ]   [ ISO 281 Fatigue ]
  Lubricant thermal    Crankshaft & connecting rod   Piston ring pack &     Rolling element &
  breakdown & valve    cyclic mechanical fatigue     cylinder liner scuff   crankshaft main
  seat micro-welding   da/dN = C(Delta-K)^m          W = K * (F_N * s) / H  bearing fatigue
```

### 2.1 Lubricant Thermal Oxidation & Valve Aging (Arrhenius Kinetics)
Thermal breakdown of engine lubricating oil and exhaust valve seat thermal erosion follow Arrhenius reaction kinetics:
$$k_{ox}(T) = A_{ox} \cdot \exp\left( -\frac{E_a}{R_{gas} \cdot T_{oil}} \right)$$
The cumulative thermal degradation dosage $D_{therm}(t)$ accumulated over flight duration $t$:
$$D_{therm}(t) = \int_0^t \exp\left( \frac{E_a}{R_{gas}} \cdot \left[ \frac{1}{T_{ref}} - \frac{1}{T_{oil}(\tau)} \right] \right) d\tau$$
When oil temperature exceeds nominal ($T_{oil} > 115^\circ\text{C}$), degradation accelerates exponentially, rapidly degrading hydrodynamic film thickness $h_{min}$.

### 2.2 Crankshaft & Connecting Rod High-Cycle Fatigue (Paris-Erdogan Law)
For mechanical components subjected to cyclic peak cylinder pressures $P_{max}$, micro-crack growth rate per engine revolution $N_{rev}$:
$$\frac{da}{dN_{rev}} = C \cdot \left( \Delta K(P_{max}, a) \right)^m, \quad \Delta K = Y \cdot \Delta \sigma(P_{max}) \cdot \sqrt{\pi a}$$
Where $m \approx 3.2$ for high-strength forged steel connecting rods, and $\Delta \sigma$ is directly proportional to peak indicated combustion pressure estimated by the Digital Twin virtual sensor.

### 2.3 Piston Ring Pack & Cylinder Liner Wear (Archard Adhesive Law)
Piston ring wear volume $V_{wear}$ across sliding distance $s$:
$$V_{wear} = K_{archard} \cdot \frac{F_{radial}(P_{im}, P_{max}) \cdot s}{H_{liner}}$$
As the ring pack wears, the blow-by clearance increases, elevating crankcase pressure and directly feeding back into the EKF parameter $\theta_{blowby}(t)$.

---

## 3. Stochastic Wiener Degradation Process with Drift

The progression of the component Health Index $HI(t)$ is modeled as a continuous-time stochastic Wiener process with state-dependent drift:
$$X(t) = X(0) + \int_0^t \mu(\mathbf{u}(\tau), \mathbf{x}_{twin}(\tau)) d\tau + \sigma_B \cdot B(t)$$
Where $X(t) = 1.0 - HI(t)$ is the cumulative degradation measure, $\mu(\cdot)$ is the physical drift rate driven by engine load and temperature, and $B(t)$ is standard Brownian motion capturing turbulent flight vibrations and operating noise.

### 3.1 First Hitting Time & Remaining Useful Life (RUL)
The failure threshold is defined as $D_{crit} = 1.0 - HI_{abort}$ (typically $HI_{abort} = 0.30$). The Remaining Useful Life $T_{RUL} = \inf\{ t > 0 : X(t_0 + t) \ge D_{crit} \}$ follows the **Inverse Gaussian Distribution**:
$$f_{RUL}(t | X(t_0)) = \frac{D_{crit} - X(t_0)}{\sqrt{2\pi \sigma_B^2 t^3}} \cdot \exp\left( -\frac{\left( D_{crit} - X(t_0) - \bar{\mu} \cdot t \right)^2}{2 \sigma_B^2 t} \right)$$

---

## 4. Conformal Prediction RUL Intervals (Zero Fake Claims)

To provide aerospace-grade statistical guarantees without uncalibrated point estimates, the system implements **Split Conformal Prediction**.

```
Calibration Set: {(x_cal, y_cal)_i} from Historical Flight Records / Engine Overhauls
                                      |
                                      v
Non-Conformity Scores: alpha_i = |y_cal,i - RUL_hat(x_cal,i)| / sigma_hat(x_cal,i)
                                      |
                                      v
Compute (1 - alpha) Empirical Quantile: q_hat = Quantile(alpha, (1 - alpha)(1 + 1/n))
                                      |
                                      v
Live Flight Prediction: RUL_pred(t) +/- q_hat * sigma_hat(t)
===> Guaranteed 95% Coverage: P(RUL_true in [RUL_low, RUL_high]) >= 0.95
```

### 4.1 Formal Guarantees
For any significance level $\alpha = 0.05$ ($95\%$ confidence), the prediction interval $\mathcal{C}_{1-\alpha}(\mathbf{x})$ satisfies:
$$\mathbb{P}\Big( RUL_{true} \in \mathcal{C}_{1-\alpha}(\mathbf{x}) \Big) \ge 1 - \alpha$$
On the operator GCS console, prognostics are strictly rendered as:
$$\mathbf{RUL} = [142\text{ hrs}, \; 186\text{ hrs}] \quad (95\%\text{ Confidence Interval, } \hat{\mu} = 164\text{ hrs})$$
**The system never issues false exact scalars like "164.21 hrs", respecting airworthiness honesty.**

---

## 5. Mission Layer: Tactical Flight Envelope Derating

The health of an aero-engine must directly govern the operational capabilities of the aircraft. When component degradation or an amber fault is confirmed, the system computes **Dynamic Envelope Derating**:

```
+----------------------------------------------------------------------------------------------------+
|                         TACTICAL ENVELOPE DERATING MECHANICS                                       |
+----------------------------------------------------------------------------------------------------+
| Engine Health State            | Aerodynamic / Tactical Derating Impact        | Operational Limit |
+--------------------------------+-----------------------------------------------+-------------------+
| Pristine Condition             | Full flight envelope: 30,000 ft AMSL ceiling; | Unrestricted      |
| (HI_eng > 0.85)                | 115% boost climb rating available.            | Combat Sortie     |
+--------------------------------+-----------------------------------------------+-------------------+
| Turbocharger Wastegate Stuck   | Altitude ceiling derated:                     | High-Altitude     |
| (MAP Deficit Delta-MAP = 18 kPa| z_ceiling = 17,200 ft AMSL (Loss of boost);   | Reconnaissance    |
| HI_turbo = 0.54)               | Max continuous power derated to 82%.          | Prohibited        |
+--------------------------------+-----------------------------------------------+-------------------+
| Elevated Oil Sump Temp         | Cruise throttle capped at 75% MCP;            | Abort to Orbit;   |
| (T_oil = 128 C, HI_lub = 0.42) | High-speed dash (> 110 kts) inhibited to      | RTB (Return to    |
|                                | prevent hydrodynamic film collapse.           | Base) Advisory    |
+--------------------------------+-----------------------------------------------+-------------------+
| Cylinder Compression Loss      | Climb rate limited to Vy <= 350 ft/min;       | Immediate Land    |
| (HI_comb = 0.28, Severe Blowby)| Thermal runaway predicted in 18 minutes.      | at Nearest Base   |
+--------------------------------+-----------------------------------------------+-------------------+
```

### 5.1 Remaining Mission Endurance (RME) Formulation
The system computes Remaining Mission Endurance $RME(t)$ by solving the constrained fuel-power-health optimization:
$$RME(t) = \min \left( \frac{M_{fuel,rem}(t)}{\dot{m}_{f,cruise}(t)}, \; \inf\{ \tau > 0 : HI_{critical}(t + \tau) \le HI_{limit} \} \right)$$

---

## 6. Aerodynamic Coupling: Glide Polar Reachability Cone Engine

If propulsion health degrades to critical levels ($HI_{eng} < 0.20$ or impending loss of power), the system instantly transitions from passive monitoring to active **Aircraft Reachability Decision Support**.

```
                             Aircraft at Altitude z_alt, Position (x0, y0)
                                                  |
                         +------------------------+------------------------+
                         |                                                 |
                         v                                                 v
           [ Power-Off Glide Polar: L/D ]                     [ Local Wind Vector: W(z) ]
           V_glide = sqrt(2*W / (rho*S*C_L_opt))              Magnitude & Heading
                         |                                                 |
                         +------------------------+------------------------+
                                                  |
                                                  v
                              +---------------------------------------+
                              | Dynamic 3D Reachability Glide Cone    |
                              | R_reach(psi) = z_alt * (L/D)_glide... |
                              +---------------------------------------+
                                                  |
                                                  v
                              +---------------------------------------+
                              | Airfield Reachability Ranking & HUD   |
                              | 1. Airbase Alpha: Reachable (+4200 ft)|
                              | 2. FOB Bravo: Reachable (+1100 ft)    |
                              | 3. Highway Strip: Out of Range (-800) |
                              +---------------------------------------+
```

### 6.1 Unpowered Aerodynamic Glide Equations
For a fixed-wing MALE UAV (e.g., Tapas-BH-201 wing area $S$, aspect ratio $AR$, zero-lift drag coefficient $C_{D0}$):
$$C_L = \frac{2 \cdot W_{uav}}{\rho_0(z) \cdot v_{tas}^2 \cdot S}$$
$$C_D = C_{D0} + \frac{C_L^2}{\pi \cdot AR \cdot e}$$
Optimal glide ratio:
$$\left(\frac{L}{D}\right)_{max} = \frac{1}{2 \cdot \sqrt{C_{D0} \cdot \frac{1}{\pi \cdot AR \cdot e}}}$$
Under ambient wind vector $\mathbf{W} = [W_x, W_y]^T$, the maximum glide range along bearing $\psi$ is:
$$R_{glide}(\psi) = z_{alt} \cdot \left(\frac{L}{D}\right)_{max} \cdot \left( 1 + \frac{W_x \cos\psi + W_y \sin\psi}{V_{best-glide}} \right)$$

### 6.2 Emergency Airfield Reachability Ranking
The engine evaluates all designated airbases, forward operating strips, and prepared emergency zones within $150\text{ km}$:
$$\text{Arrival Altitude Above Threshold: } \Delta z_{margin,i} = z_{alt} - \frac{d_i}{\left(\frac{L}{D}\right)_{eff}(\psi_i)} - z_{runway,i}$$
Airfields with $\Delta z_{margin,i} > 500\text{ m}$ ($1,640\text{ ft}$) are highlighted in bright green on the UAV pilot's tactical HUD, presenting an instantaneous 1-click divert routing vector.
