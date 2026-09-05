---
sortie_id: "SORTIE-2026-LADAKH-042"
uav_tail_number: "TAPAS-BH-201-AF04"
date: "2026-08-28"
theater: "LADAKH"
base: "Leh Air Force Station (3,256m MSL)"
flight_profile: "High-Altitude ISR Loiter"
duration_hours: 18.5
ambient_environment:
  oat_range_celsius: [-28.0, -12.0]
  density_altitude_ft: [11000, 24500]
  humidity_percent: 18
telemetry_log_path: "data/telemetry/sortie_2026_ladakh_042.parquet"
engine_health_index_start: 0.98
engine_health_index_end: 0.81
primary_events_logged: 2
---

# Mission Debrief: SORTIE-2026-LADAKH-042

## 1. Environmental & Operational Context
* **Mission Regime:** 18.5-hour high-altitude border loiter at 22,000 ft MSL in sub-zero ambient conditions (-22°C OAT).
* **Thermal Stress Profile:** Severe cooling baffle contraction due to extreme thermal gradient between combustion chambers (950°C) and external air (-22°C).

## 2. Chronological Timeline & Anomaly Events
* **T+00:00 to T+04:15:** Nominal climb to 22,000 ft. All parameters inside green band.
* **T+04:16:30 [ANOMALY DETECTED]:** Cylinder #2 CHT baseline began drifting upward at +0.38 deg C / min despite constant cruise throttle (5,100 RPM).
* **T+05:02:10 [FAULT 01 CONFIRMED]:** Fast ML classifier confirmed Cylinder #2 CHT Overheat (Score: 0.94).
* **T+05:03:00 [ACTION TAKEN]:** Operator executed AI prescriptive directive: Enriched fuel trim +12%, reduced throttle to 4,600 RPM, and descended to 18,000 ft. Thermal runaway arrested at 128.4°C.

## 3. Post-Flight Maintenance Directives
- [x] **Inspection Order #882:** Baffle seal elastomeric hardening inspection on Cylinder #2 shroud (`Covers_Theme_M_PlasticTheme_0`).
- [ ] **Component RUL Update:** Remaining Useful Life of Cyl #2 head reduced from 420 hrs to 385 hrs.
