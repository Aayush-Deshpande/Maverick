# DRDO MALE UAV PROPULSION FMECA REPORT (PS-26054)
**Failure Mode, Effects, and Criticality Analysis — Rotax 912 iS Sport Aero-Engine**

---

## 1. FMECA SUMMARY & RISK PRIORITY NUMBERS (RPN)

| Fault ID | Component | Failure Mode | Severity (S) | Occurrence (O) | Detection (D) | RPN | Primary Causal Pathway |
|---|---|---|---|---|---|---|---|
| **01** | Shroud Baffle | Seal Degradation / Leak | 8 | 4 | 2 | **64** | Baffle leak -> Cyl 2 cooling air deficit -> CHT2 surge -> Oil heating -> Radiant heat to Cyl 4 |
| **02** | Injector #1 | Nozzle Clog / Cavitation | 9 | 3 | 2 | **54** | Nozzle restriction -> Lean burn Cyl 1 -> EGT1 spike -> Torque ripple -> RPM sag & vibration |
| **03** | Lane A Coil | Spark Lead Breakdown | 7 | 4 | 2 | **56** | Spark loss -> Unburnt fuel -> EGT2 drop -> Cyclic misfire -> RPM flutter & gearbox shock |
| **04** | Oil System | Scavenge Cavitation / Relief | 9 | 3 | 2 | **54** | Pressure drop -> Bearing friction surge -> Oil temp spike -> Block heat to all heads -> RPM drag |
| **05** | Gearbox | Dog-Clutch Micro-Pitting | 7 | 4 | 2 | **56** | Tooth pitting -> 3rd harmonic resonance -> Parasitic drag -> RPM sag -> MAP rise & oil heating |
| **06** | Exhaust #3 | Mixture Disparity / Gasket | 6 | 4 | 2 | **48** | Mixture lean out -> EGT3 spike -> CHT3 warming -> Asymmetric exhaust pulse & mild vibration |
| **07** | Alternator | Stator Thermal Sag / Slip | 6 | 4 | 2 | **48** | Generation deficit -> Bus voltage sag -> Battery discharge -> Weak coil dwell & RPM sag |
| **08** | FADEC ECU | MAP Transducer Drift | 7 | 3 | 2 | **42** | MAP drift high -> Speed-density overfueling -> Fuel flow rise -> Rich quench all EGTs cool |

---

## 2. CROSS-SUBSYSTEM COUPLING LAWS
1. **Thermal-Mechanical Coupling:** Hydrodynamic bearing starvation directly converts mechanical torque loss into oil thermal energy ($\Delta T_{\text{oil}} \propto \text{RPM} \times \Delta P_{\text{oil}}^{-1}$).
2. **Combustion-Kinematic Coupling:** Uneven single-cylinder torque stroke production creates crankshaft rotational velocity fluctuation ($\Delta \text{RPM}_{\text{flutter}} \propto |\Delta EGT_i|$).
3. **FADEC Closed-Loop Dynamics:** In speed-density injection, any unmeasured pressure drift directly biases fuel air-charge delivery ($m_f \propto \text{MAP}_{\text{reported}}$), altering all downstream exhaust temperatures.
