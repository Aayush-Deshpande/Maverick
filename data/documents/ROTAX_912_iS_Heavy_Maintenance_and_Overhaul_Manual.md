# ROTAX 912 iS HEAVY MAINTENANCE & OVERHAUL MANUAL (MMH)
**Document Ref: MMH-912iS-ED01-REV3**  
**Authoritative Overhaul Specifications — ATA 72-10 / ATA 76-00 / ATA 24-00**

---

## CHAPTER 72-10: PROPELLER REDUCTION GEARBOX OVERHAUL

### 1.1 Gearbox Architecture & Dog-Clutch Mechanism
The propeller reduction gearbox utilizes helical spur gears with an integrated dog-clutch torsion shock absorber. The dog-clutch mechanism consists of two face-cam dog rings preloaded by a spring pack to dampen propeller vibration harmonics.

### 1.2 Dog-Clutch Micro-Pitting & Backlash Degradation (DRDO Fault 5)
* **Symptom:** Elevated 3rd harmonic spectral peak (3x RPM / 60) producing RMS vibration > 3.2 mm/s.
* **Mechanism:** Surface fatigue and micro-pitting on the dog-clutch contact facets increase rotational backlash beyond allowable limit (0.05 mm).
* **Causal Propagation:** Dynamic cyclic chatter between output shaft and propeller creates mechanical parasitic drag, sagging engine RPM by 40-90 RPM and increasing front casing temperature (OIL_TEMP +8 deg C).
* **Maintenance Limits:**
  * Maximum allowable dog-clutch backlash: 0.05 mm (0.0020 in).
  * Friction torque slippage limit: 600 - 800 Nm.
  * Overhaul Action: Disassemble gearbox housing (Part No. 911-382), replace dog clutch mating rings (Part No. 881-280) and preloaded disk springs.

---

## CHAPTER 76-00: FADEC ENGINE CONTROL & SENSOR PLAUSIBILITY

### 2.1 Dual ECU Speed-Density Computation
The FADEC computes injected fuel mass according to the speed-density formula based on manifold absolute pressure (MAP), engine RPM, air charge temperature, and target air-fuel ratio.

### 2.2 Manifold Absolute Pressure (MAP) Sensor Drift (DRDO Fault 8)
* **Symptom:** Lane A MAP sensor calibration drifts positive by +8.0 to +12.0 kPa.
* **Causal Effect:** FADEC over-estimates cylinder air charge mass, commanding excessive injector pulse width. Fuel flow rises (+3.0 L/h), causing rich quench across all 4 cylinders: all EGTs drop (-45 deg C), combustion becomes sub-optimal, and engine RPM sags.
* **ECU Arbitration:** The FADEC plausibility monitor flags a cross-channel disparity when |MAP_A - MAP_B| > 7.0 kPa for > 3.0 seconds.
* **Action:** Force FADEC control to Lane B and perform sensor recalibration via BRP BUDS-Aircraft diagnostic tool.

---

## CHAPTER 24-00: ELECTRICAL POWER GENERATION & ALTERNATOR

### 3.1 Dual Alternator Stator Specifications
* **Generator A (Internal Stator):** Dedicated power for FADEC, ignition coils, and fuel injection pumps.
* **Generator B (External Alternator):** 14V 30A (420W) supplying aircraft avionics, SAR radar, optical gimbal payload, and battery float charging.

### 3.2 Alternator Voltage Sag Diagnostics (DRDO Fault 7)
* **Symptom:** DC bus voltage drops from nominal 14.1 V down to 12.1 - 12.4 V. Battery current swings from +4.0 A (charging) to -15.0 A (heavy discharge).
* **Causal Effect:** Stator winding thermal insulation breakdown or serpentine belt micro-slip under high payload current demand.
* **Emergency Procedure:** Shed non-critical ISR surveillance radar and payload optical sensor heaters. Confirm bus voltage recovers above 13.5 V.
* **Maintenance Procedure:** Test stator phase-to-phase resistance (nominal 0.35 +/- 0.05 Ohm) and check belt tension deflection (5.0 mm at 50 N).
