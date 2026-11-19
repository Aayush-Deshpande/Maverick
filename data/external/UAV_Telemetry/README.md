# UAV_Telemetry — real UAV flight data with faults

Proxy tier. Real UAV flight dynamics, but **not** piston-engine degradation.

---

## ALFA — A Dataset for UAV Fault and Anomaly Detection

| Field | Value |
|---|---|
| **Source** | Carnegie Mellon Robotics Institute — Keipour, Mousaei, Scherer |
| **Paper** | https://arxiv.org/abs/1907.06268 |
| **Project page** | https://theairlab.org/alfa-dataset |
| **Published in** | International Journal of Robotics Research, 2021 |
| **Type** | Real fixed-wing UAV flight telemetry |
| **Relevance** | ★★★ UAV context · ★ engine PHM |

### Contents

- **47 autonomous flights** with processed data
- **23 sudden full engine failure scenarios**
- **24 scenarios across 7 other control-surface (actuator) fault types**
- 66 minutes of normal flight, 13 minutes post-fault
- Plus many hours of raw data from autonomous, autopilot-assisted and manual flights
- **Ground truth time and type of fault** for each scenario

### ⚠️ Read this before getting excited about "23 engine failure scenarios"

They are **sudden full engine failure** — the engine stops. That is a fundamentally different problem from PS-26054, which is about **gradual degradation detected before failure**.

| ALFA engine failures | PS-26054 |
|---|---|
| Sudden, complete | Gradual, progressive |
| Detection after the event | Prediction before the event |
| Flight-dynamics signature | Engine-health signature |
| No degradation trajectory | Degradation is the whole point |

ALFA does **not** give us piston-engine degradation data. It gives us something else that is still valuable.

### What it is genuinely good for

1. **Real flight telemetry with real sensor noise** — our synthetic data is clean by construction; this is not
2. **Fault-onset detection latency measurement** with genuine ground truth
3. **Testing anomaly detectors against real flight dynamics**, including manoeuvres and transients that could cause false alarms
4. **Realistic data gaps and dropouts**

### Use for ANUMAAN

Test the anomaly detection layer against real UAV telemetry to check that manoeuvres, mode changes and transients do not trigger false alarms. This is a genuine robustness test our synthetic data cannot provide.

**Split by flight**, never by row.

---

## UAV-SEAD — State Estimation Anomaly Dataset for UAVs

| Field | Value |
|---|---|
| **Source** | Identified via literature search |
| **Reference** | https://arxiv.org/pdf/2602.13900 |
| **Focus** | State-estimation anomalies |
| **Relevance** | ★★ — state estimation, not propulsion |

Worth evaluating. Focused on navigation/state-estimation anomalies rather than engine health, so likely secondary for us.

---

## What is not available

No public dataset was found containing:

- MALE UAV engine telemetry over a realistic datalink
- Piston-engine health parameters in flight
- Gradual engine degradation with UAV operating context
- Telemetry with realistic link impairments and ground-station reconstruction

This is why our simulation includes the link model ([`../Synthetic/`](../Synthetic/README.md)) — the bandwidth and loss behaviour is a first-class part of the problem, and no public dataset captures it.

---

## Citation

Keipour, A., Mousaei, M., & Scherer, S. (2021). *ALFA: A dataset for UAV fault and anomaly detection.* The International Journal of Robotics Research, 40(2-3).
