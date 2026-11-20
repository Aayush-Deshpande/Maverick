# ROTAX 912 iS / 912 iS SPORT LINE MAINTENANCE MANUAL (MML)
**Document Ref: MML-912iS-ED02-REV4**  
**Authoritative OEM Specification — BRP-Rotax GmbH & Co KG / DRDO Certified**  
**ATA 72-00 / ATA 73-10 / ATA 74-20 / ATA 76-00 / ATA 78-10 / ATA 79-00 / ATA 24-00**

---

## CHAPTER 00-00: GENERAL SPECIFICATIONS & ENVELOPE LIMITS

### 1.1 Engine Technical Data
* **Configuration:** 4-cylinder, 4-stroke horizontally opposed boxer engine with liquid-cooled cylinder heads and ram-air cooled cylinders.
* **Displacement:** 1352 cm3 (82.5 cu in).
* **Bore x Stroke:** 84.0 mm x 61.0 mm.
* **Compression Ratio:** 10.8 : 1.
* **Maximum Take-Off Power:** 73.5 kW (100 HP) at 5,800 RPM (max 5 minutes).
* **Maximum Continuous Power:** 69.0 kW (92.5 HP) at 5,500 RPM.
* **Idle Speed:** 1,800 +/- 100 RPM.
* **Propeller Reduction Ratio:** 1 : 2.4286 (integrated dog-clutch overload mechanism).

### 1.2 Operational Limits
* **Engine RPM:**
  * Maximum Redline: 5,800 RPM.
  * Maximum Continuous: 5,500 RPM.
  * Cruise Range: 4,800 - 5,200 RPM.
  * Economy Loiter: 4,300 - 4,600 RPM.
* **Cylinder Head Temperature (CHT):**
  * Nominal Range: 90 deg C - 115 deg C.
  * Maximum Continuous: 135 deg C (275 deg F).
  * Critical Alarm Threshold: > 140 deg C (Immediate descent / throttle reduction required).
* **Exhaust Gas Temperature (EGT):**
  * Nominal Cruise: 780 deg C - 820 deg C.
  * Maximum Continuous: 880 deg C (1,616 deg F).
  * Maximum Short Term (Take-Off): 950 deg C.
  * Maximum Allowable Cylinder-to-Cylinder Disparity (Delta EGT): 65 deg C.
* **Lubrication System (Oil Pressure & Temperature):**
  * Nominal Oil Pressure: 2.0 - 5.0 bar (29 - 73 psi).
  * Minimum Oil Pressure at Idle: 0.8 bar (12 psi).
  * Maximum Cold Start Oil Pressure: 7.0 bar (102 psi).
  * Nominal Oil Temperature: 90 deg C - 110 deg C.
  * Minimum Oil Temperature for Take-Off: 50 deg C (122 deg F).
  * Maximum Oil Temperature: 130 deg C (266 deg F).
* **Fuel Injection System:**
  * Fuel Rail Pressure: 3.0 +/- 0.2 bar (43.5 psi).
  * Fuel Flow at Cruise (5,000 RPM, Ladakh FL200): 14.5 - 17.5 L/h.
  * Fuel Flow at Economy Loiter: 11.0 - 13.5 L/h.
* **Electrical System:**
  * Nominal DC Bus Voltage: 14.1 +/- 0.3 V.
  * Warning Voltage Low: < 12.8 V (Battery assisting bus).
  * Critical Voltage Low: < 12.0 V (Immediate load shedding mandatory).

---

## CHAPTER 72-00: ENGINE CORE & AIRFLOW COOLING BAFFLES

### 2.1 Cylinder Head Cooling System
The Rotax 912 iS utilizes a hybrid cooling system: ram-air passes through specialized cowling baffles over the cylinder cooling fins, while an internal closed-loop water/glycol jacket cools the combustion chambers and valve seats.

### 2.2 Baffle Seal Maintenance & Inspection Procedures
1. **Inspection Interval:** Every 50 flight hours or after severe turbulence / temperature transitions.
2. **Seal Integrity:** Inspect the flexible elastomeric cooling baffle seals between the engine air plenum shroud and Cylinder #2 / Cylinder #4 cylinder heads.
3. **Failure Mode (DRDO Fault 1):** If the baffle seal becomes dislodged or deformed, ram airflow separates from the cylinder fin boundary layer, resulting in rapid CHT rise on Cylinder #2 (> 138 deg C).
4. **Corrective Action:**
   * Step 1: Confirm CHT delta between Cyl #2 and Cyl #1 exceeds 25 deg C.
   * Step 2: Enrich fuel trim +12% via GCS to lower combustion chamber temperature.
   * Step 3: Reduce throttle to 4,600 RPM.
   * Step 4: Inspect baffle clip tension and replace torn silicone seals with OEM Part No. 965-021.

---

## CHAPTER 73-10: HIGH PRESSURE FUEL INJECTION (FADEC)

### 3.1 Dual Injector Architecture
Each cylinder runner is equipped with two electromagnetic high-pressure fuel injectors (Injector A and Injector B) controlled independently by FADEC Lane A and Lane B.

### 3.2 Fuel Injector Clog Diagnostics (DRDO Fault 2)
1. **Symptom Signature:** Total fuel flow rate drops by 15-25%, while Cylinder #1 EGT spikes above 880 deg C due to extreme lean-burn combustion.
2. **Kinematic Effect:** Unequal torque stroke distribution induces cyclic crankshaft deceleration, dropping engine RPM by 60-120 RPM and elevating reduction gearbox vibration (VIB > 1.2 mm/s).
3. **Emergency SOP:**
   * Force FADEC arbitration to Lane B auxiliary injection schedule.
   * Engage auxiliary electric fuel boost pump to ensure minimum 3.0 bar rail pressure.
   * If EGT remains divergent, land at nearest recovery airfield.
4. **Maintenance Action:** Disassemble fuel rail, remove Injector #1 (Part No. 874-320), and perform ultrasonic solvent backflush and flow rate calibration (nominal 185 cc/min at 3.0 bar).

---

## CHAPTER 74-20: DUAL IGNITION & SPARK PLUG SYSTEM

### 4.1 System Overview
Dual capacitive discharge ignition system with two spark plugs per cylinder (top and bottom). Driven by dual internal stator generators and FADEC ignition timing maps.

### 4.2 Ignition Misfire Diagnostics (DRDO Fault 3)
1. **Symptom Signature:** Unburnt fuel expelled into exhaust runner causes sharp EGT drop on affected cylinder (-90 to -135 deg C), accompanied by high-variance RPM flutter (+/- 150 RPM) and intense gearbox torsional shock vibration (VIB > 2.0 mm/s).
2. **Root Cause:** Primary ignition coil insulation breakdown or spark plug lead carbon track breakdown on Lane A circuit.
3. **Emergency Action:** Switch ignition arbitration from Lane A to Lane B via GCS control switch.
4. **Post-Flight Order:** Perform insulation resistance check on ignition lead (nominal 4.5 - 5.5 kOhm). Replace spark plug pack with OEM Part No. 897-257.

---

## CHAPTER 79-00: DRY-SUMP LUBRICATION SYSTEM

### 5.1 Hydraulic Circuit
Dry-sump system with integrated mechanical pressure pump, scavenge return lines, external oil reservoir (3.0 L capacity), and thermostat-controlled oil cooler.

### 5.2 Oil Pressure Loss & Bearing Failure (DRDO Fault 4)
1. **Symptom Signature:** Oil pressure collapses below 2.0 bar (typically falling to 1.6 - 1.8 bar). Hydrodynamic oil wedge breakdown causes severe bearing friction, resulting in rapid oil temperature climb (> 120 deg C), conduction heat rise on all 4 cylinder heads (+10 deg C), and parasitic RPM drag.
2. **Emergency Action:** Reduce throttle to 4,200 RPM immediately to minimize bearing shear stress. Initiate immediate precautionary landing / recovery vector.
3. **Maintenance Action:** Remove and inspect suction screen, magnetic drain plug (Part No. 941-895), and oil filter for bronze/steel metallic shavings.
