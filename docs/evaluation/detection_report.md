# Detection evaluation - twin vs conventional threshold monitor

Both systems see the same frames from an independent plant
(`backend/plant/virtual_engine.py`), whose physics differs from the twin's
model and whose ground truth is reachable only through a separate call.
Positive lead time means the twin warned first.

Two detection channels are reported because they are complementary:
**thermal** residuals against a physics expectation, and **crank**
per-cylinder combustion from angular velocity. Neither alone finds
everything; the thermal channel cannot see a slow injector fault, and the
crank channel is silent on cooling and lubrication faults, which are not
combustion events.

## Summary

- Fault scenarios: **6**
- Detected by thermal residuals: **5**
- Detected by crank diagnostics: **2**
- Detected by **either channel**: **6**
- Detected by the conventional threshold baseline: **1**
- Found by the twin but invisible to the baseline: **4**
- Median detection lead time over the baseline: **7.92 min**
- False alarms per flight hour over 3.0 nominal hours: twin **0.0**, baseline **0.0**

## Per scenario

| Scenario | Thermal (s) | Crank (s) | Cyl | Baseline (s) | Lead (min) | Class | Notes |
|---|---|---|---|---|---|---|---|
| nominal_cruise_2h | - | - | - | - | - | - |  |
| nominal_hot_low | - | - | - | - | - | - |  |
| cooling_degradation | 1304.0 | - | - | - | - | ENGINE_FAULT | plant failed at t=1998s (CHT_OVERTEMP) |
| misfire_cyl3 | 765.0 | 660.0 | 3 | - | - | ENGINE_FAULT |  |
| injector_coking_cyl2 | - | 750.0 | 2 | - | - | - |  |
| oil_pressure_loss | 907.0 | - | - | 1382.0 | 7.92 | ENGINE_FAULT |  |
| turbo_bearing_wear | 2710.0 | - | - | - | - | ENGINE_FAULT |  |
| sensor_drift_cht1 | 2515.0 | - | - | - | - | SENSOR_FAULT | twin correctly classified SENSOR_FAULT |