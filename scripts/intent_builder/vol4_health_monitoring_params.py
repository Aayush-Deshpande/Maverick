"""
Volume 4: Health Monitoring Parameters, Cross-Correlation & Diagnostic Spectrum
Reverse-engineering the engineering intent behind DRDO Problem Statement 26054.
"""

CONTENT = r"""# Volume IV: Health Monitoring Parameters, Cross-Correlation & Diagnostic Spectrum
**Exhaustive Sensor Analysis, Multi-Dimensional Correlation & The Diagnostic Hierarchy**

---

## 1. Deep Analysis of the Mandated Sensor Parameters

DRDO Problem Statement 26054 explicitly mandates the continuous monitoring of **nine distinct parameter classes**. DRDO did not choose these parameters at random; together, they span the entire thermodynamic, fluidic, electrical, and structural observability subspace of an aero-piston engine.

```mermaid
graph TD
    subgraph ObservabilitySubspace["The 9-Parameter Observability Architecture"]
        Rot["1. RPM & Crank Angle<br/>(Rotational Kinetics & Torque Balance)"]
        ThermHead["2. CHT 1-4<br/>(Combustion Heat & Coolant Heat Flux)"]
        ThermExh["3. EGT 1-4<br/>(Chemical Combustion & AFR Balance)"]
        Lube["4. Oil Pressure & Temp<br/>(Journal Bearing Hydrodynamics)"]
        Fuel["5. Fuel Flow<br/>(Volumetric Delivery & BSFC)"]
        Vib["6. Vibration Signatures<br/>(Elastodynamics & Harmonic Orders)"]
        Elec["7. Battery & Alternator<br/>(FADEC Power & Electrical Bus)"]
        Timing["8. Injection Timing<br/>(ECU Phasing & Solenoid Status)"]
        Boost["9. Manifold Pressure (MAP)<br/>(Turbocharger & Air Induction)"]

        Rot & ThermHead & ThermExh & Lube & Fuel & Vib & Elec & Timing & Boost --> DT_Core["Digital Twin Central State Observer"]
    end
```

---

## 2. Parameter-by-Parameter Diagnostic & Prognostic Deep Dive

### 1. Engine Speed (RPM) & Crankshaft Phasing
* **Physical Meaning**: Rotational angular velocity ($\omega = 2\pi N / 60$) and angular acceleration ($\alpha = d\omega/dt$) of the engine output shaft.
* **Subsystem**: Reciprocating mechanical assembly and propeller reduction gearbox.
* **Observable Failure Modes**: Single-cylinder misfire, torsional vibration resonance, propeller governor hunt, mechanical seizure onset.
* **Healthy Envelope**: 1,800–2,200 RPM (ground idle); 5,000–5,500 RPM (economy cruise); 5,800 RPM (max continuous takeoff power, limited to 5 minutes). Speed jitter under steady cruise $\le \pm 15 \text{ RPM}$.
* **Abnormal Signatures**: Cyclic RPM ripple ($\Delta N > \pm 35 \text{ RPM}$) at half-engine order ($0.5\times$), sudden speed sag under constant throttle, high-frequency torsional oscillations.
* **Diagnostic vs. Prognostic Value**: High diagnostic value for instantaneous misfire and governor failures; moderate prognostic value (gradual friction rise indicates bearing wear).
* **Sampling Rate & Conditioning**: 50 Hz CAN bus average; raw 60-2 Hall-effect sensor trigger pulses sampled at $\ge 10 \text{ kHz}$ on onboard edge processor.

### 2. Cylinder Head Temperature (CHT 1–4)
* **Physical Meaning**: Metal temperature of the aluminum cylinder heads, reflecting the balance between combustion heat release and liquid-coolant heat rejection.
* **Subsystem**: Cylinder head combustion chamber and liquid-cooling jacket.
* **Observable Failure Modes**: Localized coolant boiling, water pump cavitation, radiator matrix fouling, pre-ignition, detonation.
* **Healthy Envelope**: $80^\circ\text{C}$ to $115^\circ\text{C}$ during standard cruise; maximum allowable limit $135^\circ\text{C}$ (continuous); absolute redline $150^\circ\text{C}$. Multi-cylinder spread $\Delta CHT \le 12^\circ\text{C}$.
* **Abnormal Signatures**: Monotonic CHT creep across all heads during climb; single-head divergence ($\Delta CHT > 25^\circ\text{C}$); rapid temperature derivative ($\frac{dT}{dt} > 1.5^\circ\text{C/s}$).
* **Diagnostic vs. Prognostic Value**: Very high prognostic value for cooling system decay and progressive thermal runaway; moderate diagnostic value for detonation due to thermal probe lag ($\tau \approx 3\text{--}8 \text{ s}$).
* **Sampling Rate & Conditioning**: 1 Hz to 5 Hz; cold-junction compensated Type-J or RTD resistance elements.

### 3. Exhaust Gas Temperature (EGT 1–4)
* **Physical Meaning**: Sensible enthalpy of burned exhaust gas exiting the exhaust ports, serving as the direct proxy for the cylinder air-fuel ratio ($\lambda$).
* **Subsystem**: Combustion chamber and exhaust runners.
* **Observable Failure Modes**: Injector partial clogging (lean shift), injector dripping (rich shift), ignition spark failure (misfire), exhaust valve leakage.
* **Healthy Envelope**: $780^\circ\text{C}$ to $850^\circ\text{C}$ at cruise; peak allowable limit $880^\circ\text{C}$; absolute redline $920^\circ\text{C}$. Multi-cylinder balance spread $\Delta EGT \le 35^\circ\text{C}$.
* **Abnormal Signatures**: Sudden drop of $> 150^\circ\text{C}$ within 2 seconds (misfire); steady upward divergence of one cylinder toward $900^\circ\text{C}$ (lean burn from clogged injector); erratic EGT jumping (intermittent spark).
* **Diagnostic vs. Prognostic Value**: Highest diagnostic value for individual cylinder combustion faults due to low thermal probe inertia ($\tau \approx 0.5\text{--}1.0 \text{ s}$); high prognostic value for injector varnishing.
* **Sampling Rate & Conditioning**: 5 Hz to 10 Hz; Inconel-sheathed fast-response Type-K thermocouples.

### 4. Oil Pressure & Oil Temperature
* **Physical Meaning**: Fluid dynamic pressure in the main crankcase gallery and bulk thermal energy in the dry-sump reservoir.
* **Subsystem**: Forced dry-sump lubrication and hydrodynamic journal bearings.
* **Observable Failure Modes**: Hydrodynamic oil film collapse, journal bearing spalling, relief valve sticking open/closed, oil dilution from unburned fuel, scavenge pump aeration.
* **Healthy Envelope**: Oil Pressure: 2.0 to 5.0 bar (cruise), minimum 0.8 bar (idle), maximum 7.0 bar (cold start). Oil Temperature: $80^\circ\text{C}$ to $110^\circ\text{C}$, minimum $50^\circ\text{C}$ for takeoff, maximum redline $130^\circ\text{C}$ (synthetic oil).
* **Abnormal Signatures**: Oil pressure decaying below 1.5 bar while oil temperature is $< 100^\circ\text{C}$; oil pressure collapsing suddenly to zero (relief valve failure); oil temperature creeping past $135^\circ\text{C}$.
* **Diagnostic vs. Prognostic Value**: Highest criticality in the propulsion system; sudden pressure loss is instantly fatal to the engine (mechanical seizure in $< 60$ seconds); oil pressure decay at normalized temperature provides 5 to 20 flight hours prognostic horizon for bearing fatigue.
* **Sampling Rate & Conditioning**: Pressure at 10 Hz to 20 Hz; Temperature at 1 Hz to 5 Hz.

### 5. Fuel Flow Rate
* **Physical Meaning**: Mass/volumetric rate of liquid fuel delivered to the engine fuel rail ($\dot{m}_f$).
* **Subsystem**: Fuel delivery system (pumps, regulator, injectors, lines).
* **Observable Failure Modes**: Fuel line vapor lock in high-altitude hot conditions, auxiliary pump failure, fuel filter blockage, systemic fuel leakage.
* **Healthy Envelope**: 12 to 18 Liters/hr (economy loiter); 25 to 35 Liters/hr (maximum continuous climb). Specific fuel consumption matching calibrated BSFC map within $\pm 4\%$.
* **Abnormal Signatures**: Fuel flow dropping while MAP and RPM are commanded high; uncommanded fuel flow spike without corresponding power increase (fuel line leak).
* **Diagnostic vs. Prognostic Value**: Essential for mission endurance estimation, reserve fuel planning, and thermodynamic thermal efficiency monitoring.
* **Sampling Rate & Conditioning**: 5 Hz to 10 Hz; Pelton turbine flowmeter with digital pulse counter.

### 6. Structural Vibration Signatures
* **Physical Meaning**: High-frequency elastodynamic mechanical acceleration ($g$) generated by combustion shock, reciprocating masses, and rotating gears.
* **Subsystem**: Structural crankcase, propeller reduction gearbox, crankshaft assembly, engine mounts.
* **Observable Failure Modes**: Propeller track-and-balance unbalance ($1\times$ RPM), piston slap ($2\times$ RPM), gearbox gear tooth spalling, crankshaft bearing fatigue.
* **Healthy Envelope**: Overall RMS vibration $\le 1.8 \text{ g}$ across 10 Hz to 2 kHz band; spectral peaks at rotational harmonics bounded by calibrated baseline templates.
* **Abnormal Signatures**: Emergence of high-amplitude peak at propeller shaft frequency ($1\times$ PSRU speed); high spectral kurtosis ($K > 4.5$) in the 2 kHz to 8 kHz band (bearing spalling); low-frequency half-order flutter ($0.5\times$ engine speed).
* **Diagnostic vs. Prognostic Value**: Superior prognostic capability for mechanical components; detects bearing fatigue and gear micro-pitting tens of flight hours before thermodynamic sensors show any disturbance.
* **Sampling Rate & Conditioning**: 5 kHz to 20 kHz; tri-axial piezoelectric accelerometers; onboard edge FFT and spectral kurtosis extraction.

### 7. Battery Voltage & Alternator Current
* **Physical Meaning**: DC electrical bus voltage stability and net current flow into/out of the aircraft primary battery.
* **Subsystem**: Engine electrical generation and FADEC power bus.
* **Observable Failure Modes**: Alternator diode rectifier failure, internal battery cell short, electrical bus undervoltage.
* **Healthy Envelope**: $27.8 \text{ V}$ to $28.6 \text{ V}$ DC bus voltage; alternator output current $+10 \text{ A}$ to $+35 \text{ A}$ (positive charging current); battery temperature $\le 45^\circ\text{C}$.
* **Abnormal Signatures**: Bus voltage dropping below $24.0 \text{ V}$; alternator current dropping to negative (battery discharging in flight); high ripple voltage on DC line ($> 1.2 \text{ V}_{\text{RMS}}$).
* **Diagnostic vs. Prognostic Value**: Critical safety monitoring; FADEC and electronic ignition fail completely if bus voltage drops below $18 \text{ V}$, resulting in immediate total engine flameout.
* **Sampling Rate & Conditioning**: 10 Hz to 20 Hz; Hall-effect current shunt and precision resistor divider.

### 8. Injection Timing Parameters
* **Physical Meaning**: The crank angle phasing and electrical pulse duration commanded by the FADEC to the fuel injectors and ignition coils.
* **Subsystem**: Electronic engine control (FADEC / ECU / TCU).
* **Observable Failure Modes**: Cam/crank sensor phase slip, ECU driver circuit degradation, knock-induced timing retardation limits.
* **Healthy Envelope**: Injection Start Angle: $280^\circ$ to $320^\circ$ BTDC; Spark Advance: $18^\circ$ to $28^\circ$ BTDC (varying dynamically with RPM and MAP).
* **Abnormal Signatures**: FADEC retarding ignition timing by $> 8^\circ$ continuously (indicating severe active knock suppression); pulse width diverging between left and right cylinder banks.
* **Diagnostic vs. Prognostic Value**: Direct indicator of ECU internal control states; explains thermodynamic anomalies.
* **Sampling Rate & Conditioning**: 10 Hz; digital diagnostic broadcast over CAN bus.

---

## 3. The Multi-Dimensional Cross-Parameter Correlation Matrix

A core failure of legacy monitoring systems is evaluating sensors in isolation. An engine fault manifests as a **coupled multi-sensor disturbance pattern**:

| Engine Operating Condition / Fault Mode | RPM | CHT (1–4) | EGT (1–4) | Oil Pressure | Oil Temp | Fuel Flow | Vibration | Battery / Alt | Primary Cross-Sensor Signature |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Normal High-Power Climb** | $\uparrow\uparrow$ | $\uparrow\uparrow$ (Balanced) | $\uparrow\uparrow$ (Balanced) | $\uparrow$ (3.5–4.5 bar) | $\uparrow$ (95–105°C) | $\uparrow\uparrow$ | Normal | Normal | All parameters rise proportionally with commanded throttle. |
| **Normal Economy Cruise** | Steady | Steady (90–105°C) | Steady (800–840°C)| Steady (3.2 bar) | Steady (90°C) | Steady | Minimal | Charging | Complete multi-sensor stability; residuals $\approx 0$. |
| **Single-Cylinder Misfire (Cyl 3)** | Jitter ($\pm 35$) | Drop on Cyl 3 | **Plunge on Cyl 3 ($> -200^\circ\text{C}$)** | Normal | Normal | Normal | **Spike at $0.5\times$ RPM** | Normal | **EGT3 plunges + 0.5x vibration spike + RPM ripple.** |
| **Injector Partial Clog (Cyl 2)** | Normal | Slow rise on Cyl 2 | **Rise on Cyl 2 ($+50\text{--}80^\circ\text{C}$)**| Normal | Normal | Slight drop | Slight rise | Normal | **EGT2 diverges upward (lean peak) + Cyl 2 CHT creep.** |
| **Water Pump Cavitation (High Alt)** | Normal | **All CHTs Rise ($> 135^\circ\text{C}$)** | Normal | Normal | Slow rise | Normal | Normal | Normal | **All 4 CHTs climb simultaneously while EGT remains normal.** |
| **Bearing Spalling (Big-End Journal)** | Normal | Normal | Normal | **Decays ($-0.8 \text{ bar}$)** | **Creeps ($> 125^\circ\text{C}$)**| Normal | **High Kurtosis (2–8 kHz)**| Normal | **Oil pressure drops + oil temp climbs + high-frequency vibration.** |
| **Combustion Knock / Pre-ignition** | Normal | **Steep Rise ($\frac{dT}{dt} > 2^\circ\text{C/s}$)** | Drops slightly | Normal | Normal | Normal | **High 5–8 kHz acoustic** | Normal | **Rapid CHT spike + acoustic resonance + FADEC retards timing.** |
| **Sensor Oxidation (CHT 4 Drift)** | Normal | **Cyl 4 reads $+30^\circ\text{C}$** | Normal | Normal | Normal | Normal | Normal | Normal | **Violates Parity Space: CHT 4 rises, but coolant and oil are steady!** |

---

## 4. Clarification of the Diagnostic & Prognostic Spectrum

Problem Statement 26054 combines several terms that are often conflated in literature:

```mermaid
graph LR
    D1["1. Fault Detection<br/>'Is something abnormal?'<br/>Time: Milliseconds"] --> D2["2. Fault Diagnosis<br/>'What & where has failed?'<br/>Time: Seconds"]
    D2 --> D3["3. Fault Prediction<br/>'Will a failure occur soon?'<br/>Time: Minutes to Hours"]
    D3 --> D4["4. Prognostics & RUL<br/>'How much life remains?'<br/>Time: Hours to Sorties"]
    D4 --> D5["5. Tactical Mitigation<br/>'What action should we take?'<br/>Time: Mission Horizon"]
```

1. **Fault Detection**: Identifying that the current operational vector $\mathbf{z}(t)$ deviates statistically from nominal healthy operation ($e > \tau_{\text{threshold}}$).
2. **Fault Diagnosis (Isolation & Classification)**: Pinpointing the exact physical sub-assembly and failure mechanism (e.g. mapping the residual vector to "Category: Injector 2 Orifice Restriction").
3. **Fault Prediction**: Anticipating a fault *before* functional failure or parameter redline breach occurs (e.g. predicting that Cylinder 3 CHT will cross the critical $135^\circ\text{C}$ limit in 12 minutes based on current climb angle).
4. **Prognostics (RUL Estimation)**: Modeling the irreversible wear kinetics of degrading components (bearing Babbitt wear, spark plug gap erosion) and estimating remaining operational hours until functional retirement.
5. **Tactical Mitigation (Prescriptive Decision Support)**: Recommending optimal flight actions (throttle derating, altitude modification, return-to-base) to prevent in-flight engine shutdown and enhance mission reliability.
"""
