---
sortie_id: "SORTIE-2026-LADAKH-104"
uav_tail_number: "TAPAS-BH-201-AF05"
date: "2026-08-22"
theater: "LADAKH"
base: "Leh Air Force Station"
flight_profile: "Stratospheric Border Loiter FL230"
duration_hours: 16.0
ambient_environment:
  oat_range_celsius: [-31.0, -18.0]
  density_altitude_ft: [15000, 26000]
  humidity_percent: 15
telemetry_log_path: "data/telemetry/sortie_2026_ladakh_104.parquet"
engine_health_index_start: 0.99
engine_health_index_end: 0.88
primary_events_logged: 1
---

# Mission Debrief: SORTIE-2026-LADAKH-104

## 1. Environmental & Operational Context
* **Mission Regime:** 16-hour long-endurance ISR patrol at 23,000 ft MSL.

## 2. Chronological Timeline & Anomaly Events
* **T+08:12:00 [ANOMALY DETECTED]:** Gearbox vibration RMS elevated from 0.52 mm/s to 3.45 mm/s (dominant 3rd harmonic).
* **T+08:15:30 [FAULT 05 CONFIRMED]:** ML diagnostic pipeline confirmed Dog-Clutch Micro-Pitting & Backlash Resonance (Score: 0.96).
* **T+08:16:00 [ACTION TAKEN]:** Cruise RPM adjusted from 4,200 RPM to 4,800 RPM to escape torsional resonance window. Vibration stabilized at 1.4 mm/s.

## 3. Post-Flight Maintenance Directives
- [ ] **Inspection Order #931:** Propeller reduction gearbox dog-clutch backlash measurement (max allowable: 0.05 mm).
