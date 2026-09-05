---
sortie_id: "SORTIE-2026-THAR-089"
uav_tail_number: "TAPAS-BH-201-AF02"
date: "2026-08-14"
theater: "THAR_DESERT"
base: "Jaisalmer Air Force Station"
flight_profile: "Low-Altitude Desert Border Surveillance"
duration_hours: 12.0
ambient_environment:
  oat_range_celsius: [38.0, 48.5]
  density_altitude_ft: [4000, 9500]
  humidity_percent: 12
telemetry_log_path: "data/telemetry/sortie_2026_thar_089.parquet"
engine_health_index_start: 0.96
engine_health_index_end: 0.74
primary_events_logged: 1
---

# Mission Debrief: SORTIE-2026-THAR-089

## 1. Environmental & Operational Context
* **Mission Regime:** 12.0-hour desert patrol in extreme ambient heat (+46°C OAT) with airborne sand particulates.
* **Thermal Stress Profile:** Elevated oil reservoir operating temperature due to limited radiator delta T.

## 2. Chronological Timeline & Anomaly Events
* **T+06:45:00 [ANOMALY DETECTED]:** Oil pressure gradually decayed from 3.85 bar down to 1.72 bar while oil temperature surged to 124.5°C.
* **T+06:58:20 [FAULT 04 CONFIRMED]:** Fast ML classifier confirmed Oil Pressure Loss & Cavitation (Score: 0.98).
* **T+06:59:00 [ACTION TAKEN]:** Throttle reduced to 4,200 RPM, immediate RTB vector initiated. UAV recovered safely.

## 3. Post-Flight Maintenance Directives
- [x] **Inspection Order #904:** Oil suction screen flushed, oil filter element replaced (metallic particle count: normal).
- [x] **Relief Valve Overhaul:** Oil pressure relief valve spring replaced under Service Bulletin SB-912iS-019.
