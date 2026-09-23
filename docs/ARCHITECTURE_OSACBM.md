# ANUMAAN architecture — ISO 13374 / MIMOSA OSA-CBM mapping

The problem statement's structure — ingestion, processing, abnormal-condition
detection, health indices, RUL and degradation, maintenance advisory — is an
unlabelled restatement of ISO 13374. This document maps every module onto the
standard's six functional blocks, and is generated from
`backend/osacbm.py` so it cannot drift from the code.

## DA — Data Acquisition

*Access installed sensors and collect data*

4/4 modules implemented. PS requirements served: CAP-10, CAP-15, DEL-06, DTC-06, HMS-11, INT-01, INT-06, SIM-03

| Module | Purpose | Reads | Status |
|---|---|---|---|
| `backend.telemetry.mavlink_efi` | Ingest MAVLink EFI_STATUS (#225) from autopilot, SITL or recorded tlog | — | implemented |
| `backend.telemetry.can_streamer` | Engine frame generation and transport (to be split into a separate plant, G01) | — | implemented |
| `backend.telemetry.aces_loader` | Real Rotax 914 flight telemetry from NASA ACES for physics validation | — | implemented |
| `backend.telemetry.replay_engine` | Historical mission replay through the live ingestion path | — | implemented |

## DM — Data Manipulation

*Single and multi-channel signal transforms and feature extraction*

5/6 modules implemented. PS requirements served: CAP-11, FDP-03, FDP-09, HMS-09, HMS-11, INT-02, INT-03, INT-04, INT-07, SIM-04, SIM-05

| Module | Purpose | Reads | Status |
|---|---|---|---|
| `backend.physics.thermo_model` | Thermodynamic expected-state model and residual vector | DA | implemented |
| `backend.physics.turbo_model` | Boosted induction: wastegate authority, lag, surge margin, charge temperature | DA | implemented |
| `backend.physics.induction` | Air filter restriction and dust-ingestion wear chain | DA | implemented |
| `backend.physics.fuel_thermal` | Fuel temperature, cloud point / CFPP margin, cold-soak delivery | DA | implemented |
| `backend.physics.injector_faults` | Per-cylinder injector condition and torque contribution | DA | implemented |
| `backend.ml.spectral_analyser` | Vibration spectral features (dormant until the kHz channel exists, F04) | DA | **pending** |

## SD — State Detection

*Compare features against expected values or limits; produce condition indicators*

4/4 modules implemented. PS requirements served: AIM-04, CAP-03, CAP-12, FDP-01, FDP-06, INN-07

| Module | Purpose | Reads | Status |
|---|---|---|---|
| `backend.physics.sensor_validator` | Sensor sanity: unphysical rate, spike, frozen channel | DM | implemented |
| `backend.twin.integrity` | Physics-constrained telemetry integrity and spoof detection | DM | implemented |
| `backend.evaluation.threshold_baseline` | Conventional limit monitor, retained as the measured baseline | DM | implemented |
| `backend.ml.anomaly_detector` | Unsupervised residual anomaly scoring | DM | implemented |

## HA — Health Assessment

*Assess current health of the monitored item and diagnose faults*

5/5 modules implemented. PS requirements served: CAP-02, CAP-11, DTC-03, FDP-01, FDP-02, FDP-03, FDP-04, FDP-05, FDP-07, FDP-08, HMS-01, HMS-02

| Module | Purpose | Reads | Status |
|---|---|---|---|
| `backend.ml.fault_classifier` | Fault classification over physics residuals | SD | implemented |
| `backend.ml.detection_pipeline` | Nine-stage real-time detection and health indices | SD, DM | implemented |
| `backend.physics.oil_system` | Wear-metal spectrum, debris and oil condition with source attribution | DM | implemented |
| `backend.twin.validity` | Twin self-assessment; model drift vs engine fault vs sensor fault | SD, DM | implemented |
| `backend.reliability.isolability` | Which fault modes are physically distinguishable with the fitted sensors | SD | implemented |

## PA — Prognostic Assessment

*Project health forward: remaining useful life and future risk*

6/6 modules implemented. PS requirements served: AIM-05, AIM-06, CAP-04, CAP-05, CAP-06, CAP-13, CAP-14, INT-08, SYS-01

| Module | Purpose | Reads | Status |
|---|---|---|---|
| `backend.evaluation.damage_accumulation` | Rainflow + Miner physics-of-failure life consumption | HA | implemented |
| `backend.ml.rul_estimator` | Monte Carlo RUL and component-level prognosis | HA | implemented |
| `backend.ml.trend_analyser` | Degradation trend fitting | HA | implemented |
| `backend.evaluation.conformal` | Distribution-free RUL intervals with reported empirical coverage | PA | implemented |
| `backend.physics.exposure` | Environmental exposure accumulation and wear acceleration factors | HA | implemented |
| `backend.mission.reliability` | Mission completion probability with limiting-component attribution | PA, HA | implemented |

## AG — Advisory Generation

*Generate recommended actions for operators and maintainers*

3/3 modules implemented. PS requirements served: AIM-03, AIM-07, CAP-09, INT-08, VIS-08, VIS-09

| Module | Purpose | Reads | Status |
|---|---|---|---|
| `backend.mission.prescriptive` | Derate ladder and mission re-planning against a reliability requirement | PA | implemented |
| `backend.reports` | Mission debriefs and mission-wise health reports | PA, HA | implemented |
| `backend.graph` | Fleet knowledge graph, work orders and maintenance history | PA, HA | implemented |

## Layering check

No layering violations: every module reads only from its own layer or below.