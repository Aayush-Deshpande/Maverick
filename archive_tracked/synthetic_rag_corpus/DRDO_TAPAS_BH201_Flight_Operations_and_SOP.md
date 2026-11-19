# DRDO MALE UAV (TAPAS-BH-201 / RUSTOM-II) FLIGHT MANUAL & EMERGENCY SOP
**Document Ref: DRDO-ADE-UAV-SOP-2026-V2**  
**Aeronautical Development Establishment (ADE) / Indian Defence Standards (DEF-STAN)**

---

## 1. MISSION THEATERS & REGIME PROFILES

### 1.1 Northern Sector (Ladakh High-Altitude Border Loiter)
* **Operating Altitude:** 18,000 - 24,000 ft MSL (Flight Level FL180 - FL240).
* **Base Station:** Leh Air Force Station (3,256 m MSL) / Nyoma Advanced Landing Ground.
* **Environmental Stress:** Ambient temperature -20 deg C to -32 deg C. High density altitude reduces air cooling mass flow by up to 48%, significantly increasing cylinder thermal runaway risk during extended loiter.
* **Standard Power Profile:** 72% TPS, 5,120 RPM, 90 KIAS, TAS 122 knots.

### 1.2 Western Sector (Thar Desert Extreme Heat Patrol)
* **Operating Altitude:** 3,000 - 8,000 ft MSL.
* **Environmental Stress:** Ambient temperature +42 deg C to +49 deg C. Airborne sand particulates accelerate injector nozzle wear and air filter dust loading. High ambient temperatures reduce oil cooler thermal dissipation margin.

---

## 2. DRDO CANONICAL FAILURE MODES & FAST SOP DIRECTIVES

### 2.1 Summary Matrix (PS-26054)

| Fault ID | Alert Title | Primary Indicator | Severity | SOP Emergency Action |
|---|---|---|---|---|
| **01** | Cylinder #2 CHT Overheat | CHT_2 > 135 deg C, Delta CHT > 25 deg C | CRITICAL | Enrich trim +12%, 4,600 RPM, descend 3,000 ft |
| **02** | Fuel Injector #1 Clog | Fuel Flow down 20%, EGT_1 > 880 deg C | CRITICAL | Switch FADEC Lane B, engage aux boost pump |
| **03** | Ignition Misfire (Lane A) | EGT_2 down 120 deg C, RPM Flutter | WARNING | Select Ignition Lane B, hold cruise power |
| **04** | Oil Pressure Decay | P_oil < 2.0 bar, T_oil elevated | CRITICAL | Reduce to 4,200 RPM, immediate RTB vector |
| **05** | Gearbox Vibration / Clutch | VIB > 3.2 mm/s, 3rd Harmonic | WARNING | Avoid 4,000-4,400 RPM resonance band |
| **06** | Exhaust EGT Imbalance | EGT_3 > 870 deg C, Delta EGT > 65 deg C | WARNING | Apply +6% individual fuel trim on Cyl #3 |
| **07** | Alternator Voltage Sag | V_bus < 12.8 V, I_bat < -10 A | WARNING | Shed ISR radar/payload, monitor battery SOC |
| **08** | Dual FADEC ECU Drift | Delta MAP > 8 kPa, Fuel Flow up | WARNING | Force Lane B arbitration, log post-flight |

---

## 3. MISSION READINESS (GO / NO-GO) CRITERIA

1. **GO Status:** All 27 telemetry parameters within nominal green bands. Autoencoder anomaly score < 0.35. RUL estimate > 12.0 hours.
2. **CAUTION Status:** Sub-threshold prognostic drift detected or non-critical advisory (e.g. minor EGT divergence or alternator voltage sag with adequate battery reserve). Mission may continue with enhanced telemetry monitoring.
3. **NO-GO Status:** Any CRITICAL fault (CHT overheat > 140 deg C, Oil pressure < 1.8 bar, Injector starvation with severe vibration). Autonomous return-to-base (RTB) or precautionary landing mandatory.
