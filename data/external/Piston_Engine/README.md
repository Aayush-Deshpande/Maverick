# Piston_Engine — the gap

**This folder is intentionally empty of datasets.**

---

## The finding

We searched for a public dataset containing aero piston engine sensor data with labelled faults or run-to-failure trajectories — the thing PS-26054 actually needs — and did not find one.

Specifically, nothing public was found with:

- Aero piston engine telemetry (CHT, EGT, oil, fuel flow, vibration)
- Labelled examples of the eight PS fault modes
- Run-to-failure trajectories for RUL
- UAV operating conditions

⚠️ **This is a negative result from our search, not proof of non-existence.** The honest phrasing is always "we did not find", never "does not exist."

---

## Why it probably does not exist publicly

Producing it would require deliberately damaging or destroying instrumented aero engines across multiple fault modes — expensive, hazardous, and for a defence platform almost certainly restricted. Manufacturers who hold such data treat it as proprietary.

---

## What this means for the project

This is the single most important constraint on our data strategy, and it should be stated openly rather than worked around quietly.

| Consequence | Response |
|---|---|
| No supervised training data for the 8 PS faults | Generate physics-based synthetic data ([`../Synthetic/`](../Synthetic/README.md)) |
| No real RUL validation for this engine class | Validate RUL *methods* on C-MAPSS and XJTU-SY |
| No real vibration signatures for a piston engine | Validate DSP on CWRU/Paderborn; synthesise with correct spectral structure |
| Cannot claim field accuracy | Never claim it. Report what was measured and on what |

---

## What would be needed to close the gap

For the deployment roadmap the PS asks for as a deliverable:

**1. Instrumented test cell.** A Rotax 912 iS-class engine with:
- Per-cylinder CHT and EGT
- Oil pressure and temperature
- Fuel flow
- **A dedicated vibration channel at ≥10 kHz with hardware anti-alias filtering and crank/tach synchronisation**
- Full CAN capture from both ECU lanes

**2. Baseline campaign.** Many hours of healthy operation across the full envelope — altitudes, temperatures, power settings — to establish normal residual distributions.

**3. Seeded-fault campaign.** Controlled introduction of each of the eight fault modes at several severities, with ground-truth onset times.

**4. Run-to-failure programme.** At least a few components run to serviceability limits, for genuine RUL data. This is the expensive part and the reason such data is rare.

**5. Flight validation.** Airborne data with real vibration environment, electrical noise, and altitude effects that a test cell cannot reproduce.

---

## Related

- Closest proxies: [`../Engine_PHM/`](../Engine_PHM/README.md) (turbofan RUL), [`../Bearing/`](../Bearing/README.md) (vibration), [`../UAV_Telemetry/`](../UAV_Telemetry/README.md) (flight context)
- Our substitute: [`../Synthetic/`](../Synthetic/README.md)
- Reasoning: [Part XIV §14.1](../../ANUMAAN/docs/study/14_datasets.md)

---

*If a suitable dataset is found later, document it here and update the top-level catalogue.*
