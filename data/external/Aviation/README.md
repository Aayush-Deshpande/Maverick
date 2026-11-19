# Aviation — reference documentation

Not datasets. Public documentation used to ground the physics model, the parameter set, and the operating envelope.

---

## Rotax engine documentation

⬜ We use the Rotax 912 iS as our reference engine because it is publicly documented and representative of the class. This is **our assumption**, not a PS requirement — the PS names no engine.

| Document | URL | Use |
|---|---|---|
| **912 iS Operator's Manual** | https://avsport.org/acft/Rotax/912iS/912iS_operators_manual_d05875.pdf | Operating limits, normal ranges, parameter definitions |
| **912 Series Operator's Manual** | https://avsport.org/acft/Rotax/OM_912_Series_ED4_R0.pdf | General 912-series data |
| **EASA TCDS E.121** | https://www.easa.europa.eu/en/downloads/7633/en | Type certificate data sheet — certified limits |
| **Rotax engine specifications** | https://www.rotax-owner.com/en/support-topmenu/technical-information/rotax-engine-specifications | Published performance figures |

### What these give us

- Operating limits (CHT, EGT, oil pressure and temperature) for defining thresholds and health-index anchors
- Normal operating ranges for validating that our synthetic data is plausible
- RPM ranges — idle to maximum continuous
- The basis for an approximate performance map

### What they do not give us

- 🔒 Detailed performance maps (power/fuel flow vs RPM/MAP/altitude) at manufacturer fidelity
- 🔒 CAN message definitions — see [`../CAN_ECU/`](../CAN_ECU/README.md)
- 🔒 Failure mode data or degradation characteristics

---

## Publicly verified engine data interface facts

From equipment vendors who interface with the engine:

| Fact | Source |
|---|---|
| The 912 iS has **two ECU lanes (A and B)** using the **CAN Aerospace** format | https://aeroshop.eu/en/rdac-can-rotax-912is.html |
| Interface modules read both lanes and can fail over from A to B, or be locked "lane exclusive" | Same |
| **Parameters published over CAN:** RPM, manifold pressure, oil pressure, oil temperature, coolant temperature, **EGT for all four cylinders**, ECU voltage, engine hours | https://www.rs-flightsystems.com/product-page/emu-912xis |
| CAN bus diagnostic: ~60 Ω across CAN_H/CAN_L with engine off (two 120 Ω terminators in parallel) | https://aeroshop.eu/en/rdac-can-rotax-912is.html |
| EGT uses **K-type thermocouples**, typically 4 probes | https://www.rotax-owner.com/en/912-914-technical-questions/9485-engine-monitor-parameters |
| Oil pressure sensors: Honeywell/Keller types; VDO (pre-Sept 2008) or 4–20 mA | https://www.rotax-owner.com/en/912-914-technical-questions/7581-sensor-type-on-older-912-ul |
| The 914 has two air-pressure sensors — ambient and airbox | https://www.rotax-owner.com/pdf/UNDERSTANDING%20THE%20914%20ROTAX.pdf |

### The vibration gap

🔶 **Inference:** vibration is **not** in the published CAN parameter list. Vibration monitoring therefore requires added instrumentation — an accelerometer with its own high-rate acquisition path, separate from CAN.

This is a significant finding, because three of the eight PS fault targets depend on vibration. See [Part II §2.6](../../ANUMAAN/docs/study/02_engine_sensors.md).

---

## UAV platform references

### TAPAS-BH-201 (Rustom-II) — publicly reported

| Parameter | Value | Source |
|---|---|---|
| Range | ~250 km | https://en.wikipedia.org/wiki/TAPAS-BH-201 |
| Command range | up to ~1,000 km (satellite) | https://www.kodainya.com/blogs/tapas-bh-201-the-rustom2 |
| Endurance | 18–24 h | Multiple sources |
| Ceiling | ~28,000–30,000 ft | Multiple sources |
| Payload | up to 350 kg | Wikipedia |
| Wingspan | 20.6 m | Wikipedia |
| Max speed | ~225 km/h | Wikipedia |
| Datalink | Developed by DRDO's **DEAL** | https://www.airforce-technology.com/projects/rustom-ii-male-unmanned-aerial-vehicle-uav/ |
| BLOS demonstrated | June 2023, satellite-relayed | Multiple sources |
| Engines flown | Rotax 914, later Austro 180 hp; twin turboprop on some prototypes | https://en.wikipedia.org/wiki/TAPAS-BH-201 |

🔒 **Not public:** datalink waveform, frequencies, encryption, message set, onboard bus architecture, actual health-monitoring parameter list.

⚠️ Figures vary between sources. Cite the source when quoting, and do not present any of this as design input beyond establishing plausible scale.

---

## Standards

| Standard | Reference |
|---|---|
| **STANAG 4586** | https://publications.sto.nato.int/publications/STO%20Educational%20Notes/STO-EN-SCI-271/EN-SCI-271-03.pdf |
| **MAVLink** | https://mavlink.io/en/ |
| **CANaerospace** | https://en.wikipedia.org/wiki/CANaerospace |
| **SocketCAN** | https://docs.kernel.org/networking/can.html |

---

## Usage rule

Use these to ground the physics model and validate that synthetic data is plausible. **Never extrapolate beyond what a document states.** If our performance map is an approximation derived from published figures, say so — an approximate map is fine provided its error is smaller than the fault signatures we are detecting, and stating that condition is what makes it defensible.
