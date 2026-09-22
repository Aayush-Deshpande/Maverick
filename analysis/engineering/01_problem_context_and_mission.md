# 🎯 Problem Context & Operational Mission
**DRDO / iDEX Problem Statement ID: 26054**  
*Rotax 912 iS Sport Propulsion System for Indian Defense MALE UAVs*

---

## 1. Defense Challenge & Operational Context

In modern defense and tactical surveillance, **Medium-Altitude Long-Endurance (MALE) Unmanned Aerial Vehicles (UAVs)**—such as India's **TAPAS-BH-201** and **Rustom-II**—are required to operate continuous 18-to-24 hour intelligence, surveillance, and reconnaissance (ISR) sorties across extreme operational theaters.

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                            INDIAN DEFENSE MALE UAV FLEET                                 │
│                                                                                          │
│           TAPAS-BH-201                                            Rustom-II              │
│   (Tactical Airborne Platform for                           (Medium-Altitude Long-       │
│    Aerial Surveillance-Beyond Horizon)                       Endurance Surveillance)     │
│                                                                                          │
│   Propulsion: Rotax 912 iS Sport                            Propulsion: Rotax 914 / 912  │
│   Endurance:  18–24 Hours                                   Endurance:  24 Hours         │
│   Ceiling:    20,000–26,000 ft AMSL                         Ceiling:    26,000 ft AMSL   │
└─────────────────────────────────────────────┬────────────────────────────────────────────┘
                                              │
                                Single Propulsion Core
                                              │
                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             CRITICAL STRATEGIC VULNERABILITY                             │
│                                                                                          │
│   • Single-engine propulsion: Loss of engine = Catastrophic aircraft hull loss          │
│   • Extreme geographic theaters: Ladakh (-22°C, 20,000 ft) vs. Thar Desert (+44°C)       │
│   • Sub-threshold thermodynamic drift cannot be detected by conventional static gauges   │
│   • Requirement: Real-time 3D Digital Twin with Prognostic AI & Physical Root-Cause XAI  │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### The Propulsion Core: Rotax 912 iS Sport
The Rotax 912 iS Sport is a 4-cylinder, 4-stroke liquid/air-cooled boxer engine equipped with dual electronic fuel injection (EFI), redundant Engine Control Units (Dual FADEC Lane A / Lane B), and an integrated propeller reduction gearbox (reduction ratio $i = 2.43$).

* **Displacement:** 1,352 cc
* **Compression Ratio:** 10.8 : 1
* **Takeoff Power:** 100 HP @ 5,800 RPM (5-minute limit)
* **Max Continuous Cruise:** 5,500 RPM (Loiter: 4,800–5,100 RPM)
* **Fuel Delivery:** Redundant electronic multi-point fuel injection (3.0 bar rail pressure)
* **Cooling Architecture:** Ram-air cooled cylinder heads with liquid-cooled cylinder liners

---

## 2. Extreme Geographic Theaters

The Digital Twin simulates and validates operations across India's most challenging tactical theaters:

```
                  ┌────────────────────────────────────────────────────────┐
                  │          TACTICAL OPERATIONAL THEATERS IN INDIA        │
                  └──────────────────────────┬─────────────────────────────┘
                                             │
               ┌─────────────────────────────┴─────────────────────────────┐
               ▼                                                           ▼
┌─────────────────────────────────────────┐     ┌─────────────────────────────────────────┐
│     NORTHERN HIGH-ALTITUDE THEATER      │     │      WESTERN EXTREME HEAT THEATER       │
│                (LADAKH)                 │     │              (THAR DESERT)              │
├─────────────────────────────────────────┤     ├─────────────────────────────────────────┤
│ • Altitude: 18,500 – 22,000 ft AMSL     │     │ • Altitude: 4,500 – 8,000 ft AMSL       │
│ • Ambient Temperature: -22°C to -35°C   │     │ • Ambient Temperature: +44°C to +50°C   │
│ • Air Density: 50% of Sea Level ($\rho$)│     │ • High ambient density altitude         │
│ • Low MAP (48–55 kPa naturally aspirated│     │ • Extreme thermal heat rejection strain │
│ • Severe cooling airflow thinness       │     │ • Oil viscosity breakdown & seal stress │
└─────────────────────────────────────────┘     └─────────────────────────────────────────┘
```

---

## 3. The 4 Operational Pillars of Reliability (DRDO PS-26054)

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                               THE 4 OPERATIONAL PILLARS                                  │
├──────────────────────────┬──────────────────────────┬────────────────────────────────────┤
│ 1. REAL-TIME 3D TWIN     │ 2. PROGNOSTIC DRIFT & RUL│ 3. COGNITIVE AI REASONING          │
│ Live 20/50 Hz Telemetry  │ Sub-threshold drift      │ Causal propagation chains,         │
│ synchronized with 109-   │ detection, AIC curve     │ ATA chapter citations, and safety- │
│ component raytraced CAD, │ fitting, Monte Carlo     │ guardrailed technical manual RAG.  │
│ visual fault glow, X-Ray │ RUL estimation, and Pre- │                                    │
│ ghosting & camera framing│ Flight Go/No-Go analysis.│                                    │
├──────────────────────────┴──────────────────────────┴────────────────────────────────────┤
│ 4. FLEET-WIDE CONDITION-BASED MAINTENANCE (CBM)                                          │
│ Air-gapped property graph tracking multi-sortie stress histories, degradation trends,    │
│ open work orders, and generating automated post-flight debriefs (`MISSION_xxx.md`).      │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. The 8 Canonical DRDO Fault Scenarios Matrix

The system implements high-fidelity physical modeling, real-time detection, causal isolation, and visual highlighting for the **8 canonical failure modes** defined in DRDO PS-26054:

| # | Fault Name | Primary Physical Trigger | 3D CAD Target Mesh Component | Physical Causal Chain | Prescriptive Action |
|---|---|---|---|---|---|
| **01** | **Cylinder #2 CHT Overheat** | CHT_2 > 135°C | `Covers_Theme_M_PlasticTheme_0` | Baffle seal degradation $\rightarrow$ cooling restriction on Cyl #2 $\rightarrow$ CHT_2 surges $\rightarrow$ conductive heat to oil $\rightarrow$ EGT_2 climbs $\rightarrow$ health degrades. | Enrich fuel trim +12%, throttle back 15%, initiate immediate RTB vector. |
| **02** | **Fuel Injector #1 Clog** | Fuel Flow drop (-22%) + EGT_1 surge | `Rotax_912i_Base_M_PlasticGreen_0` | Electromagnetic nozzle deposit $\rightarrow$ fuel starvation on Cyl #1 $\rightarrow$ lean burn spikes EGT_1 $\rightarrow$ torque asymmetry drops RPM $\rightarrow$ vibration rises. | Switch to Lane B ECU backup map, activate auxiliary boost pump. |
| **03** | **Ignition Misfire** | RPM Jitter (±180 RPM) + EGT_2 drop | `Wiring_Harness_M_Copper_0` | Secondary ignition lead insulation breakdown $\rightarrow$ spark dropout $\rightarrow$ unburnt fuel drops EGT_2 $\rightarrow$ power pulsation causes high RPM flutter and vibration shock. | Force FADEC arbitration to redundant Lane B ignition coil set. |
| **04** | **Oil Pressure Loss** | Oil Press < 2.0 bar + Oil Temp rise | `Oil_Tank_M_Steel_0` | Scavenge line cavitation / relief valve spring fatigue $\rightarrow$ oil pressure collapses $\rightarrow$ bearing friction surges $\rightarrow$ oil temp escalates $\rightarrow$ all CHTs climb. | Immediate throttle reduction to 4,200 RPM, initiate precautionary descent. |
| **05** | **Gearbox Vibration** | 3rd Harmonic FFT spike / VIB_RMS > 1.8 | `Gearbox_Type_2_M_Steel_0` | Propeller reduction dog-clutch tooth micro-pitting $\rightarrow$ 3rd harmonic resonance ($3 \times \text{Prop RPM}$) $\rightarrow$ mechanical drag sags RPM $\rightarrow$ frictional heat in gearbox. | Limit rapid throttle transients, schedule post-flight clutch overhaul. |
| **06** | **Exhaust EGT Imbalance** | EGT_3 > 850°C / Delta > 65°C | `Exhaust_System_M_SteelDark_0` | Runner #3 mixture divergence $\rightarrow$ high exhaust gas temperature on runner #3 $\rightarrow$ cylinder head thermal transfer $\rightarrow$ asymmetric scavenging. | Adjust individual cylinder fuel trim on Cylinder #3. |
| **07** | **Alternator Voltage Sag** | Bus Voltage < 12.8V + Battery drain | `External_Alternator_M_Steel_0` | Stator winding thermal sag / serpentine belt micro-slip $\rightarrow$ bus voltage collapses $\rightarrow$ battery current swings to net discharge (-15A). | Shed non-essential ISR payload, engage backup avionics battery bus. |
| **08** | **Dual FADEC ECU Drift** | MAP Lane A/B Delta > 8 kPa | `ECU_M_PlasticBlack_0` | Lane A MAP transducer drifts positive $\rightarrow$ speed-density over-fueling $\rightarrow$ fuel flow rises $\rightarrow$ over-rich mixture cools all EGTs $\rightarrow$ power sags. | Force FADEC to Lane B, flag Lane A MAP sensor for recalibration. |
