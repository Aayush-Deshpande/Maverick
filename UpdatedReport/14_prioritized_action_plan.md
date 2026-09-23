# REPORT 14: PRIORITIZED REMEDIATION ACTION PLAN

**DRDO Aero-Twin | SIH 26054 Technical Reconstruction**  
**Classification:** Engineering Roadmap & Codebase Remediation Specifications  
**Author:** DRDO Aero-Twin Engineering Reconstruction Team  
**Date:** March 2025  

---

## 1. REMEDIATION METHODOLOGY & PRIORITY TAXONOMY

This action plan translates the findings of Reports 01 through 13 into concrete, executable code modifications. Every identified gap is prioritized using the following engineering taxonomy:

* **[P0 — Critical]:** Fatal defects that cause runtime crashes, test suite failures, critical scientific circularity, or immediate disqualification during technical panel review.
* **[P1 — High]:** Major architectural discrepancies, core problem statement alignment gaps (the "Soul"), or broken communication pipelines between major subsystems.
* **[P2 — Medium]:** Important engineering enhancements that solidify defence airworthiness posture, improve algorithmic robustness, or optimize latency.
* **[P3 — Low]:** Code cleanup, dead file pruning, styling consistency, and documentation polish.

---

## 2. P0 (CRITICAL) REMEDIATION SPECIFICATIONS

---

### P0-1: Mutex Protection on MajorityVoteBuffer (Test Concurrency Race Fix)
* **Severity:** **P0 — Critical** (Causes intermittent `RuntimeError: deque mutated during iteration` during test execution).
* **Exact Module Affected:** [`backend/services/detection_pipeline.py`](file:///d:/Programming/PS054/backend/services/detection_pipeline.py)
* **Root Cause Analysis:** The `MajorityVoteBuffer` uses a Python `collections.deque` with `maxlen=N`. In multi-threaded testing (`tests/test_fun_req_compliance.py`), the background thread `EngineStateService._run_loop` appends items to the deque while the test thread calls `_tick()` and reads the buffer, mutating the deque during iteration.
* **Proposed Implementation Diff:**

```diff
--- a/backend/services/detection_pipeline.py
+++ b/backend/services/detection_pipeline.py
@@ -1,5 +1,6 @@
 import collections
+import threading
 from typing import List, Optional, Tuple
 
 class MajorityVoteBuffer:
     def __init__(self, window_size: int = 5):
         self.window_size = window_size
         self._buf = collections.deque(maxlen=window_size)
+        self._lock = threading.Lock()
 
     def add(self, fault_code: str) -> None:
-        self._buf.append(fault_code)
+        with self._lock:
+            self._buf.append(fault_code)
 
     def get_voted_fault(self) -> Tuple[str, float]:
-        if not self._buf:
-            return "NOMINAL", 1.0
-        counts = collections.Counter(self._buf)
-        most_common, count = counts.most_common(1)[0]
-        confidence = count / len(self._buf)
-        return most_common, confidence
+        with self._lock:
+            if not self._buf:
+                return "NOMINAL", 1.0
+            # Take a thread-safe snapshot list before counting
+            items = list(self._buf)
+        counts = collections.Counter(items)
+        most_common, count = counts.most_common(1)[0]
+        confidence = count / len(items)
+        return most_common, confidence
```
* **Dependencies:** Standard library `threading`.
* **Validation Method:** Execute `python -m pytest tests/test_fun_req_compliance.py` for 50 continuous iterations without a single concurrency failure.

---

### P0-2: Replace Brittle Deterministic RUL with Trend Extrapolation
* **Severity:** **P0 — Critical** (Eliminates the dangerous linear countdown in `rul_estimator.py` that undermines scientific defensibility).
* **Exact Module Affected:** [`backend/ml/rul_estimator.py`](file:///d:/Programming/PS054/backend/ml/rul_estimator.py), [`backend/services/engine_service.py`](file:///d:/Programming/PS054/backend/services/engine_service.py)
* **Root Cause Analysis:** `rul_estimator.py` uses a hardcoded decrementing counter (`self.rul = max(0.0, self.rul - dt)`). The actual statistical RUL engine implemented in `backend/ml/trend_analyser.py` (AIC polynomial fit + Monte Carlo perturbations) is currently bypassed by the main API response loop.
* **Proposed Implementation:** Wire `trend_analyser.py` directly into `EngineStateService._tick()` and expose the 90% confidence interval `(rul_p10, rul_p50, rul_p90)` in `backend/server/schemas.py`.

---

### P0-3: Fix Path Resolution in Standalone Batch Script
* **Severity:** **P0 — Critical** (Causes `launch_standalone_app.bat` to fail when launched from outside project root).
* **Exact File Affected:** [`launch_standalone_app.bat`](file:///d:/Programming/PS054/launch_standalone_app.bat)
* **Root Cause Analysis:** Line 50 points to `assets\blender\rotax_engine_twin.blend` using relative paths instead of resolving `%~dp0`.
* **Proposed Implementation Diff:**
```diff
-set BLENDER_FILE=assets\blender\rotax_engine_twin.blend
+set BLENDER_FILE=%~dp0assets\blender\rotax_engine_twin.blend
```

---

## 3. P1 (HIGH) REMEDIATION SPECIFICATIONS: THE "SOUL" UPGRADES

---

### P1-1: Indigenous DRDO / VRDE 2.2L Common-Rail Turbo-Diesel Engine Preset
* **Severity:** **P1 — High** (Directly addresses the DRDO MALE UAV indigenization mandate for TAPAS-BH201).
* **Exact Module Affected:** [`backend/physics/thermo_model.py`](file:///d:/Programming/PS054/backend/physics/thermo_model.py), [`backend/server/schemas.py`](file:///d:/Programming/PS054/backend/server/schemas.py)
* **Technical Specification:** Add an engine configuration selector supporting:
  1. `ROTAX_914_TURBO`: Displacement 1.352L, CR 9.0:1, 115 HP, Gasoline.
  2. `DRDO_VRDE_2_2L_DIESEL`: Displacement 2.179L, CR 17.5:1, 180 HP, Common-Rail Diesel (Jet-A1/F-34), Turbo boost $2.2\text{ bar}$, and VRDE's altitude derating schedule ($200\text{ HP @ SL} \to 200\text{ HP @ 10k ft} \to 150\text{ HP @ 20k ft} \to 110\text{ HP @ 30k ft}$).

---

### P1-2: 6-Subsystem Health Index Matrix Decomposition
* **Severity:** **P1 — High** (Fulfills DRDO Problem Statement 26054 §B requirement).
* **Exact Modules Affected:** [`backend/server/schemas.py`](file:///d:/Programming/PS054/backend/server/schemas.py), [`backend/server/engine_service.py`](file:///d:/Programming/PS054/backend/server/engine_service.py)
* **Technical Specification:** Decompose the single composite `health_index` into 6 discrete subsystem scores ($0.0 \to 1.0$):
  - `health_fuel_injection`: Based on fuel flow residual, rail pressure delta, and BSFC deviation.
  - `health_ignition_combustion`: Based on FADEC advance timing, lambda, and CHT-EGT correlation.
  - `health_electrical`: Based on bus voltage stability (14.1V ± 0.5V) and alternator current.
  - `health_lubrication`: Based on oil pressure ($2.0 - 5.0\text{ bar}$) and oil temperature ($80 - 110^\circ\text{C}$).
  - `health_cooling`: Based on cylinder head temperature balance ($\max |CHT_i - CHT_j| \le 12^\circ\text{C}$).
  - `health_mechanical_core`: Based on gearbox vibration RMS and ASTM E1049-85 Rainflow fatigue damage $D$.

---

### P1-3: Pre-Flight Mission Reliability Dispatch Gatekeeper (GO / CAUTION / NO-GO)
* **Severity:** **P1 — High** (Fulfills DRDO Problem Statement 26054 §E requirement).
* **Exact Module Affected:** [`backend/ml/trend_analyser.py`](file:///d:/Programming/PS054/backend/ml/trend_analyser.py), [`backend/server/engine_service.py`](file:///d:/Programming/PS054/backend/server/engine_service.py)
* **Technical Specification:** Fast-time 25-run Monte Carlo forward projection over planned mission sorties (*Endurance Loiter 10h*, *High Altitude Recon 22,000 ft*, *Hot Desert 45°C*).
  - Hard safety floors: $P_{\text{oil}} \ge 1.20\text{ bar}$, $CHT \le 135.0^\circ\text{C}$, $\text{Vibration} \le 2.80\text{ mm/s}$, $\Delta HI \le 15\%$.
  - Output formal clearance: `[GO]`, `[CAUTION]`, or `[NO-GO]` with the exact physical constraint cited.

---

### P1-4: Real Aerospace CAN Bus (`engine_can.dbc`) Ingestion via UDP Multicast
* **Severity:** **P1 — High** (Proves real-world avionics compatibility on Windows GCS).
* **Exact Modules Affected:** [`backend/telemetry/can_streamer.py`](file:///d:/Programming/PS054/backend/telemetry/can_streamer.py), new [`backend/telemetry/can/engine_can.dbc`](file:///d:/Programming/PS054/backend/telemetry/can/engine_can.dbc)
* **Technical Specification:** Use `cantools` and `python-can` with UDP multicast backend (`ff15:...`), broadcasting and receiving authentic CAN FD frames across processes without requiring Linux `vcan`.

---

### P1-5: Human-in-the-Loop Failsafe State Machine
* **Severity:** **P1 — High** (Standard defence C2 protocol compliance).
* **Exact Module Affected:** [`backend/server/engine_service.py`](file:///d:/Programming/PS054/backend/server/engine_service.py)
* **Technical Specification:** Enforce decoupled state transitions:
  $$\text{Engine: WARNING} \longrightarrow \text{AI: RTB\_RECOMMENDED} \longrightarrow \text{Operator: CONFIRMED} \longrightarrow \text{Autopilot: DIVERSION}$$
  Log all operator acknowledgments with UTC timestamps to `decision_events.csv`.

---

## 4. MASTER PRIORITIZED TASK TRACKER (P0 TO P3)

| Task ID | Priority | Subsystem | File / Component | Brief Description | Estimated Effort |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ACT-01** | **P0** | Backend / Testing | `detection_pipeline.py` | Add thread-safe lock around `MajorityVoteBuffer` deque | 1 hour |
| **ACT-02** | **P0** | ML / Prognostics | `rul_estimator.py` | Wire `trend_analyser.py` Monte Carlo RUL to API | 2 hours |
| **ACT-03** | **P0** | Automation | `launch_standalone_app.bat` | Fix `%~dp0` file path resolution | 15 mins |
| **ACT-04** | **P1** | Physics Core | `thermo_model.py` | Implement DRDO VRDE 2.2L Turbo-Diesel preset & derating | 3 hours |
| **ACT-05** | **P1** | Backend / API | `engine_service.py` | Decompose composite HI into 6-subsystem health matrix | 2 hours |
| **ACT-06** | **P1** | Mission Intel | `trend_analyser.py` | Implement Pre-Flight Dispatch Gatekeeper (GO/NO-GO) | 3 hours |
| **ACT-07** | **P1** | Telemetry Bus | `can_streamer.py` | Real CAN FD broadcast/receive via `cantools` & UDP multicast | 3 hours |
| **ACT-08** | **P1** | Decision Engine | `engine_service.py` | Human-in-the-Loop failsafe state machine & decision log | 2 hours |
| **ACT-09** | **P1** | 3D Visualization | `AeroPistonEngine3D.tsx` | Add Exploded View slider & projected SVG leader-lines | 3 hours |
| **ACT-10** | **P2** | Security | `backend/main.py` | Add TLS 1.3 (`wss://`) and JWT bearer token auth | 3 hours |
| **ACT-11** | **P2** | Signal Processing | `backend/dsp/` | Add C99 order-tracking module for 10 kHz vibration | 6 hours |
| **ACT-12** | **P3** | Documentation | `Report/` | Publish comprehensive engineering report folder | Complete |
| **ACT-13** | **P3** | Repository Clean | Root / scratch | Remove orphaned `.pyc` and temporary test files | 30 mins |
