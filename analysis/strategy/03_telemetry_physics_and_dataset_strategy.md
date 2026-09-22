# Telemetry, Physics Modeling & Dataset Strategy
**DRDO / iDEX Problem Statement ID: 26054**  
*The 27-Parameter Master Dictionary, 1D Thermodynamic Physics Twin & Tri-Source Dataset Strategy*

---

## 📌 1. The 27-Parameter Master Data Dictionary

To ensure 100% compliance with DRDO PS-26054, the system defines **27 continuous telemetry, environmental, and machine learning fields**:

### A. Engine Kinematics & Operating Regimes

| # | Parameter Name | Signal Identifier | Unit | Nominal Flight Range | Critical Limit / Threshold | Sampling Rate | Description |
|---|---|---|---|---|---|---|---|
| **1** | **Crankshaft Speed** | `ENGINE_RPM` | RPM | 4,800 – 5,500 | Max: 5,800 (5 min takeoff limit) | 10–50 Hz | Primary engine rotational speed |
| **2** | **Propeller Speed** | `PROP_RPM` | RPM | 1,975 – 2,263 | Propeller shaft speed ($i=2.43$) | 10–50 Hz | Output speed after reduction gearbox |
| **3** | **Throttle Position** | `TPS` | % | 45.0% – 75.0% (Cruise) | 100.0% (Takeoff) | 10–50 Hz | Pilot/Autopilot throttle command |

### B. Thermal Management State (Cylinders & Exhausts)

| # | Parameter Name | Signal Identifier | Unit | Nominal Flight Range | Critical Limit / Threshold | Sampling Rate | Description |
|---|---|---|---|---|---|---|---|
| **4** | **Cylinder #1 Head Temp** | `CHT_1` | °C | 85.0 – 110.0 | $> 135.0^\circ\text{C}$ (Overheat) | 1–10 Hz | Thermocouple on Cylinder #1 Head |
| **5** | **Cylinder #2 Head Temp** | `CHT_2` | °C | 85.0 – 110.0 | $> 135.0^\circ\text{C}$ (Overheat) | 1–10 Hz | Thermocouple on Cylinder #2 Head |
| **6** | **Cylinder #3 Head Temp** | `CHT_3` | °C | 85.0 – 110.0 | $> 135.0^\circ\text{C}$ (Overheat) | 1–10 Hz | Thermocouple on Cylinder #3 Head |
| **7** | **Cylinder #4 Head Temp** | `CHT_4` | °C | 85.0 – 110.0 | $> 135.0^\circ\text{C}$ (Overheat) | 1–10 Hz | Thermocouple on Cylinder #4 Head |
| **8** | **Exhaust Gas Temp 1** | `EGT_1` | °C | 740.0 – 820.0 | $> 880.0^\circ\text{C}$ / $\Delta > 65^\circ\text{C}$ | 5–10 Hz | Runner #1 exhaust thermocouple |
| **9** | **Exhaust Gas Temp 2** | `EGT_2` | °C | 740.0 – 820.0 | $> 880.0^\circ\text{C}$ / $\Delta > 65^\circ\text{C}$ | 5–10 Hz | Runner #2 exhaust thermocouple |
| **10**| **Exhaust Gas Temp 3** | `EGT_3` | °C | 740.0 – 820.0 | $> 880.0^\circ\text{C}$ / $\Delta > 65^\circ\text{C}$ | 5–10 Hz | Runner #3 exhaust thermocouple |
| **11**| **Exhaust Gas Temp 4** | `EGT_4` | °C | 740.0 – 820.0 | $> 880.0^\circ\text{C}$ / $\Delta > 65^\circ\text{C}$ | 5–10 Hz | Runner #4 exhaust thermocouple |

### C. Lubrication, Fuel & Induction State

| # | Parameter Name | Signal Identifier | Unit | Nominal Flight Range | Critical Limit / Threshold | Sampling Rate | Description |
|---|---|---|---|---|---|---|---|
| **12**| **Oil Pressure** | `OIL_PRESS` | bar | 2.0 – 5.0 bar | $< 2.0\text{ bar}$ (Critical Loss) | 5–10 Hz | Dry-sump main oil gallery pressure |
| **13**| **Oil Temperature** | `OIL_TEMP` | °C | 75.0 – 110.0 | $> 130.0^\circ\text{C}$ | 1–5 Hz | Oil reservoir return temperature |
| **14**| **Fuel Flow Rate** | `FUEL_FLOW` | L/hr | 14.0 – 25.0 | Anomaly: $\pm 20\%$ deviation | 5–10 Hz | Instantaneous fuel consumption rate |
| **15**| **Fuel Rail Pressure** | `FUEL_RAIL_P` | bar | 2.8 – 3.2 bar | $< 2.5\text{ bar}$ | 5–10 Hz | Delivery pressure at injection manifold |
| **16**| **Manifold Absolute Press**| `MAP` | kPa | 80.0 – 100.0 | Cross-Lane Delta $> 8\text{ kPa}$ | 10–20 Hz | Intake manifold induction pressure |

### D. Mechanical Vibration, Electrical & FADEC Dual-Lane State

| # | Parameter Name | Signal Identifier | Unit | Nominal Flight Range | Critical Limit / Threshold | Sampling Rate | Description |
|---|---|---|---|---|---|---|---|
| **17**| **Gearbox Vibration RMS** | `VIB_GEARBOX_RMS`| mm/s | 0.20 – 1.50 | $> 1.80\text{ mm/s}$ (3rd harmonic) | 50–1000 Hz | Accelerometer RMS on reduction box |
| **18**| **Main DC Bus Voltage** | `BUS_VOLTAGE` | Volts | 13.8 – 14.2 | $< 12.8\text{ V}$ (Voltage Sag) | 5–10 Hz | Alternator regulator output voltage |
| **19**| **Battery Current Draw** | `BATTERY_CURRENT`| Amps | +2.0 to +10.0 (Charge)| Negative (Discharging under load) | 5–10 Hz | Battery net current flow |
| **20**| **Active FADEC Lane** | `FADEC_ACTIVE_LANE`| Enum | `LANE_A` (Primary) | Auto-arbitration to `LANE_B` | 1–5 Hz | Engine Control Unit lane status |

### E. Environmental & Mission Operational Context

| # | Parameter Name | Signal Identifier | Unit | Operational Range | Description |
|---|---|---|---|---|---|
| **21**| **Barometric Altitude** | `ALTITUDE_FT` | Feet | Sea Level to 25,000 ft MSL | Pressure altitude of UAV airframe |
| **22**| **Outside Air Temp (OAT)**| `OAT_C` | °C | $-30.0^\circ\text{C}$ to $+50.0^\circ\text{C}$ | Ambient temperature in flight zone |
| **23**| **True Airspeed (TAS)** | `TAS_KNOTS` | Knots | 65.0 – 120.0 kts | Airframe speed relative to air mass |
| **24**| **Flight Phase** | `FLIGHT_PHASE` | Enum | `TAXI`, `TAKEOFF`, `CLIMB`, `LOITER`, `DESCENT` | Current flight phase of sortie |

### F. Machine Learning Labels & Ground Truth Targets

| # | Target Field | Signal Identifier | Type / Range | Description |
|---|---|---|---|---|
| **25**| **Health Index** | `HEALTH_INDEX` | Float ($0.0 \rightarrow 1.0$) | 1.0 = Nominal new engine, 0.0 = Critical failure |
| **26**| **Fault State ID** | `FAULT_ID` | Integer (`0` to `8`) | `0` = Healthy, `1..8` = 8 DRDO failure modes |
| **27**| **Remaining Useful Life**| `RUL_HOURS` | Float (Hours) | Hours remaining before component reaches critical limit |

---

## 2. 1D Thermodynamic Physics Baseline & Residual Principles

The Virtual Physics Shadow continuously solves thermodynamic cycle equations to establish what every parameter **should** be given ambient context and throttle:

$$\text{Residual}(t) = \text{Actual Sensor Reading}(t) - \text{Physics Model Prediction}(t)$$

### Rotax 912 iS Geometric Constants
* **Displacement:** $1,352\text{ cm}^3$
* **Bore / Stroke:** $84\text{ mm} \times 61\text{ mm}$
* **Compression Ratio:** $10.8:1$
* **Max Continuous Power:** $69\text{ kW} @ 5,500\text{ RPM}$

```
                                  ┌───────────────────────────────────────────────┐
                                  │   AMBIENT FLIGHT INPUTS (Alt, OAT, TAS, TPS)  │
                                  └──────────────────────┬────────────────────────┘
                                                         │
                                                         ▼
                                  ┌───────────────────────────────────────────────┐
                                  │       1D THERMODYNAMIC CYCLE SOLVER           │
                                  │  • Otto cycle indicated work & heat rejection │
                                  │  • Air density derating: ρ = P_amb / (R * T)  │
                                  │  • Look-up: TPS x RPM x OAT ──► Expected CHT  │
                                  └──────────────────────┬────────────────────────┘
                                                         │
                                                         ▼
                                  ┌───────────────────────────────────────────────┐
                                  │            RESIDUAL VECTOR GENERATOR          │
                                  │   ΔCHT = CHT_act - CHT_exp                    │
                                  │   ΔEGT = EGT_act - EGT_exp                    │
                                  │   ΔOilP = OilP_act - OilP_exp                 │
                                  └───────────────────────────────────────────────┘
```

---

## 3. High-Frequency Gearbox Vibration & Harmonics

* **Reduction Gearbox ($i = 2.43$):** Operates with an overload dog clutch mechanism.
* **Failure Signature:** Mechanical micro-pitting and backlash produce negligible thermal change early on, but manifest as distinct energy spikes at the **3rd harmonic** of the propeller reduction shaft ($3 \times \text{Propeller RPM}$).
* **Signal Processing:** FFT / Wavelet Packet Transform monitors energy in the $100\text{ Hz} – 5\text{ kHz}$ band to isolate gear wear before structural failure.

---

## 4. Tri-Source Dataset Acquisition Strategy

```
                                  ┌───────────────────────────────────────────────┐
                                  │      TRI-SOURCE DATASET ARCHITECTURE          │
                                  └──────────────────────┬────────────────────────┘
                                                         │
               ┌─────────────────────────────────────────┼────────────────────────────────────────┐
               ▼                                         ▼                                        ▼
    ┌─────────────────────────┐               ┌─────────────────────────┐              ┌─────────────────────────┐
    │ 1. Real Aviation Logs   │               │ 2. NASA Benchmarks      │              │ 3. Physics Simulator    │
    │ (Garmin G1000 / Savvy)  │               │ (C-MAPSS & CWRU)        │              │ (DRDO 1D Otto Generator)│
    ├─────────────────────────┤               ├─────────────────────────┤              ├─────────────────────────┤
    │ • Real piston noise     │               │ • Run-to-failure curves │              │ • 8 DRDO fault modes    │
    │ • Thermocouple jitter   │               │ • Bearing micro-pitting │              │ • Ladakh (-28°C / 22k ft│
    │ • Real pilot throttle   │               │ • Long-term degradation │              │ • Thar (+48°C desert)   │
    │ • Covers Params 1–16,21 │               │ • Covers Params 17,25,27│              │ • 100% labeled metadata │
    └─────────────────────────┘               └─────────────────────────┘              └─────────────────────────┘
```
