# Part IV — Telemetry and Communication

*How data crosses 250 km of air, what the standards are, and why the link's limits dictate our architecture.*

---

## 4.1 Line of sight and beyond line of sight

### LOS — Line of Sight

A direct radio path between the ground antenna and the aircraft. Radio at these frequencies travels essentially in straight lines, so the Earth's curvature sets a hard geometric limit.

🔶 **INFERENCE — the radio horizon calculation.** The standard approximation, accounting for atmospheric refraction (the 4/3-Earth model):

```
d (km) ≈ 4.12 × √(h in metres)
```

For an aircraft at 28,000 ft ≈ 8,534 m:

```
d ≈ 4.12 × √8534 ≈ 4.12 × 92.4 ≈ 381 km
```

Plus a small contribution from the ground antenna's own height. So a TAPAS-class UAV at its ceiling has roughly **380 km of geometric line of sight**.

✅ TAPAS-BH-201's reported mission range is ~250 km. ([TAPAS-BH-201](https://en.wikipedia.org/wiki/TAPAS-BH-201)) 🔶 **INFERENCE** — that 250 km sits comfortably inside the ~380 km geometric horizon, which is consistent with a LOS-limited mission radius. The practical limit is set by the link budget (transmit power, antenna gain, receiver sensitivity), not by geometry alone.

### BLOS — Beyond Line of Sight

Past the horizon, you need a relay. In practice that means a satellite. ✅ DRDO demonstrated satellite-relayed beyond-line-of-sight control of TAPAS-BH-201 in June 2023, and a command range of ~1,000 km is reported. ([TAPAS decoded](https://www.kodainya.com/blogs/tapas-bh-201-the-rustom2), [Rustom-II](https://www.airforce-technology.com/projects/rustom-ii-male-unmanned-aerial-vehicle-uav/))

```
            LOS                                    BLOS
                                                        ☉ satellite
                                                     ╱     ╲
      ✈ ─────────────────── 📡          ✈ ─────────╱       ╲───────── 📡
      aircraft   direct     GCS          aircraft              GCS
                 path                        (two ~36,000 km hops)

   Latency: milliseconds                Latency: ~1–1.5 s round trip ✅
   Range:   to the horizon (~380 km)    Range: effectively global
```

---

## 4.2 Frequency bands

✅ **VERIFIED** — medium-endurance UAS operating LOS typically use lower-frequency **C-band**. BLOS deployments generally operate between **UHF (300 MHz) and Ku-band (15 GHz)**, with **Ku downlink at 11.7–12.7 GHz and uplink at 14–14.5 GHz**. UAV sensor data over satellite may use C-, X-, Ku- or Ka-band. ([Data Links chapter](https://kstatelibraries.pressbooks.pub/unmannedaircraftsystems/chapter/chapter-13-data-links-functions-attributes-and-latency/), [broadband links for UAV data](https://www.researchgate.net/publication/261727128_ADVANCED_BROADBAND_LINKS_FOR_TIER_III_UAV_DATA_COMMUNICATION))

### The physics that explains the choices

**Higher frequency gives more bandwidth but less robustness.** Bandwidth scales with carrier frequency, so Ku-band can carry video where UHF cannot. But higher frequencies suffer more rain attenuation (a real problem in Indian monsoon conditions) and demand tighter antenna pointing.

**Higher frequency also means smaller antennas for the same gain.** Antenna gain depends on aperture measured in wavelengths. At Ku-band the wavelength is ~2 cm, so a high-gain directional antenna is physically small enough to fit in a UAV nose radome. At UHF the wavelength is ~1 m, so you get an essentially omnidirectional low-gain antenna — robust, poor in throughput.

**This is why real systems carry several links at once.** 🔶 **INFERENCE** on the general pattern:

| Link | Typical band | Carries | Loss consequence |
|---|---|---|---|
| Command & control (C2) | UHF / C-band / Ku | Commands up, telemetry down | **Mission-critical** |
| Payload / video | Ku / Ka | Sensor imagery | Mission degraded, aircraft safe |
| Backup / emergency | UHF, low rate | Minimal telemetry, recovery commands | Last resort |

**Uplink** = ground → aircraft (commands). **Downlink** = aircraft → ground (telemetry, video). Uplink needs very little bandwidth but the highest reliability; downlink carries far more data.

**Our engine telemetry rides the C2 downlink**, sharing it with navigation and system status — which is exactly why the budget is so tight.

---

## 4.3 Bandwidth, latency, and why they dominate our design

✅ **VERIFIED** — Ku-band SATCOM is the most commonly used on UAVs today. Reported figures: data rates of **approximately 122 kbps or less** with latency of **approximately 1 to 1.5 seconds** between command and feedback. ([Data Links chapter](https://kstatelibraries.pressbooks.pub/unmannedaircraftsystems/chapter/chapter-13-data-links-functions-attributes-and-latency/))

✅ For context, 3GPP reliability targets for command and control links are >99.99% with 50–100 ms latency — which SATCOM cannot meet, and this is acknowledged as a limitation of satellite links for real-time control.

✅ There is active research specifically on customising MAVLink to fit low-data-rate SATCOM links. ([MAVLink over low data rate SATCOM, IEEE](https://ieeexplore.ieee.org/document/10958424/))

### The budget, made concrete

```
AVAILABLE (Ku-band C2 downlink, order of magnitude) ✅   ~122 kbit/s
   shared with navigation, system status, commands...

OUR ENGINE TELEMETRY BUDGET ⬜                            ~25–30 kbit/s

WHAT FITS:
   30 scalar channels × 4 B × 20 Hz                       ≈ 19 kbit/s  ✅ fits
   vibration FEATURES (≈40 floats/s)                      ≈  1.3 kbit/s ✅ fits
   event messages (sporadic)                              ≈ negligible ✅ fits

WHAT DOES NOT FIT:
   ONE raw accelerometer @10 kHz, 16-bit                  ≈ 160 kbit/s ❌
                                                   exceeds the ENTIRE link
```

### Four consequences for the architecture

1. **High-rate analysis must be onboard.** Not a preference — arithmetic.
2. **~1.5 s latency means the ground cannot close a fast control loop.** Any protective reaction that must happen in under a second has to be onboard and autonomous.
3. **Links can be jammed, and weather degrades them.** ✅ STANAG 4586 point-to-point links "can suffer from severe bandwidth degradation in certain environments due to weather, geography, and/or enemy jamming." ([STANAG 4586 interoperability](https://corvusintell.com/blog/interoperability/stanag-4586-uav-interoperability/)) **The system must keep working with the link dead.**
4. **Packet loss is normal, not exceptional.** The GCS pipeline must handle gaps, reordering, and duplicates as routine.

---

## 4.4 STANAG 4586 — the military GCS standard

### What it is and why it exists

✅ **VERIFIED** — STANAG 4586 is the NATO standard for **Standard Interfaces of UAV Control System (UCS) for NATO UAV Interoperability**. It specifies the interfaces required to achieve a required Level of Interoperability between different UAV systems. ([NATO STO publication](https://publications.sto.nato.int/publications/STO%20Educational%20Notes/STO-EN-SCI-271/EN-SCI-271-03.pdf), [Kutta](https://kuttatech.com/stanag-4586-interoperability/))

**The problem it solves:** without a standard, every UAV needs its own bespoke ground station. A coalition operation with five nations' aircraft would need five incompatible control rooms. STANAG 4586 makes one compliant GCS able to work with many compliant aircraft.

### The architecture

✅ **VERIFIED** components: Air Vehicle (AV), **Vehicle Specific Module (VSM)**, **Data Link Interface (DLI)**, **Core UCS (CUCS)**, Command and Control Interface (CCI), Human Computer Interface (HCI), and **Command and Control Interface Specific Module (CCISM)**.

```
   ✈ Air Vehicle
   │   (vendor-specific autopilot, payload, proprietary messages)
   ▼
┌──────────────────────────────────────────────────────────┐
│  VSM — Vehicle Specific Module                           │
│  ✅ Converts a UAS's NON-compliant autopilot and payload │
│     interfaces into STANAG-compliant messages            │
│  ── this is the ADAPTER. One per aircraft type.          │
└────────────────────────┬─────────────────────────────────┘
                         │  DLI — Data Link Interface
                         │  ✅ standard messages and formats between
                         │     VSM and CUCS
                         ▼
┌──────────────────────────────────────────────────────────┐
│  CUCS — Core UCS                                         │
│  The standardised control station core.                  │
│  Speaks only DLI messages. Aircraft-agnostic.            │
└────────────┬──────────────────────────┬──────────────────┘
             │ HCI                      │ CCI
             ▼                          ▼
        Operator displays         CCISM → legacy C4I systems
                                  ✅ for systems not directly
                                     STANAG-compatible
```

**The pattern to steal:** the VSM is an adapter that isolates vendor-specific details behind a standard interface. ⬜ **Our design does exactly this** — a decoder/adapter layer between the telemetry source and the digital twin core, so the twin never knows whether it is fed by a simulator, a CAN log, or a real aircraft. See [Part XV](15_system_architecture.md).

### The five Levels of Interoperability (LOI)

✅ **VERIFIED** ([UAV Navigation](https://www.uavnavigation.com/company/blog/interoperability-and-stanag-4586-flight-control-systems-uav-navigation-grupo-oesia), [corvus](https://corvusintell.com/blog/interoperability/stanag-4586-uav-interoperability/)):

| LOI | Capability |
|---|---|
| **1** | Indirect receipt/sending of UAV telemetry data |
| **2** | Direct reception of telemetry from the UAV |
| **3** | Control and monitoring of the UAV **payloads** |
| **4** | Control and monitoring of the **UAV**, excluding take-off and landing |
| **5** | Full control and monitoring, including launch and recovery |

⬜ **Where our system sits: LOI 2.** We consume telemetry directly; we never command the aircraft. This is honest and it is also the right scope — a health-monitoring system should be advisory. Being able to say "our system is a LOI-2 consumer in STANAG terms" is precise, correct, and shows domain literacy.

---

## 4.5 MAVLink — the lightweight alternative

### What it is

✅ **VERIFIED** — MAVLink is a communication protocol for unmanned systems specifying a comprehensive set of messages exchanged between unmanned systems and ground stations. ([MAVLink overview](https://mavlink.io/en/about/overview.html))

It is dominant on smaller UAVs because it is open, extremely compact, and supported by the whole open-source autopilot ecosystem (PX4, ArduPilot, QGroundControl, MAVProxy).

### Packet structure

✅ **VERIFIED — MAVLink v2 frame** ([Packet serialization](https://mavlink.io/en/guide/serialization.html), [MAVLink 2](https://mavlink.io/en/guide/mavlink_2.html)):

| Field | Bytes | Purpose |
|---|---|---|
| Magic / start-of-frame | 1 | **0xFD** for v2 (0xFE for v1) |
| Payload length | 1 | Length of payload data |
| Incompatibility flags | 1 | Frames that must be handled specially |
| Compatibility flags | 1 | Allows backwards-compatible evolution |
| Packet sequence | 1 | Counts up — **enables packet-loss detection** |
| System ID | 1 | Which vehicle |
| Component ID | 1 | Which component on it |
| **Message ID** | **3** | Defines what the payload *means* and how to decode it |
| Payload | 0–255 | The data |
| CRC | 2 | CRC-16/MCRF4XX, plus a CRC_EXTRA byte |
| Signature | 13 | Optional, for authentication |

✅ Minimum packet ≈ **12 bytes**; maximum ≈ **280 bytes** signed. ✅ Trailing zero bytes in the payload are truncated before sending — a deliberate bandwidth optimisation that matters on a constrained link.

### Why the design choices matter to us

- **CRC_EXTRA** is a checksum over the message *definition*, not just the data. If sender and receiver were built from different versions of the message spec, the CRC fails. This catches a whole class of silent version-mismatch bugs. Worth imitating: version your telemetry schema and check it.
- **The sequence number** gives you free packet-loss measurement. ⬜ Our GCS should track it and display link quality — it is cheap and it looks credible in a demo.
- **Zero-truncation** shows the mindset: on these links, every byte is worth optimising.

### Relevant message families

🔶 **INFERENCE** on which matter for us: `HEARTBEAT` (liveness and mode — its absence is how you detect link loss), `SYS_STATUS`, `GLOBAL_POSITION_INT`, `ATTITUDE`, `VFR_HUD`, and `NAMED_VALUE_FLOAT` / `DEBUG_VECT`, which are the pragmatic way to carry custom values such as engine parameters without defining a new dialect.

⬜ **Our approach:** use MAVLink-style framing over UDP for the simulated link, carrying engine telemetry in a custom message or as named values. This gives realistic framing, sequence numbers, and loss detection without needing real hardware.

---

## 4.6 Bridging MAVLink and STANAG 4586

✅ **VERIFIED** — the two have complementary strengths and there is an active research literature on bridging them, including algorithms for MAVLink→STANAG 4586 conversion for interoperability and secure communication. ([Analysis and improvement of STANAG 4586 / MAVLink](https://www.researchgate.net/publication/347425323_A_Study_on_the_Analysis_and_Improvement_of_STANAG_4586_MAVLink_Protocol_for_Interoperability_Improvement_of_UAS), [Proposing an algorithm for UAV interoperability](https://link.springer.com/chapter/10.1007/978-981-16-3153-5_44))

**"Bridging" means** a translation layer that receives messages in one protocol and re-emits equivalent messages in the other — functionally a VSM, in STANAG's own terms.

```
   PX4/ArduPilot ──MAVLink──▶ [ BRIDGE / VSM ] ──DLI messages──▶ STANAG CUCS
                              maps message IDs,
                              units, coordinate frames,
                              rates
```

✅ A noted challenge: STANAG 4586's large message set can be inefficient to transmit on bandwidth-limited links, whereas MAVLink is compact.

**The design principle for us:** ⬜ do not couple the digital twin to any wire protocol. Define an internal canonical telemetry schema, and put thin adapters in front of it (MAVLink adapter, CAN adapter, CSV/log adapter, STANAG adapter). This is the single most valuable structural decision in the comms layer, and it costs almost nothing to do from the start.

---

## 4.7 What the standards do not solve

✅ **VERIFIED and important:** STANAG 4586 "specifies message formats and semantics, **not latency requirements**". Latency on satellite-relayed links is described as a structural constraint the standard cannot resolve. ([corvus](https://corvusintell.com/blog/interoperability/stanag-4586-uav-interoperability/))

The lesson: **a protocol standard guarantees that two systems understand each other. It guarantees nothing about whether the data arrives in time, or at all.** Our system must be built to tolerate:

| Condition | Required behaviour |
|---|---|
| Latency ~1.5 s | No ground-side function may assume real-time control authority |
| Packet loss | Interpolate, mark gaps explicitly, never silently fabricate |
| Reordering | Sort by embedded timestamp, not arrival order |
| Total link loss | Onboard keeps monitoring and logging autonomously; GCS shows "stale, last update T−x", **never a frozen value that looks live** |
| Link restored | Backfill from onboard buffer if bandwidth allows; reconcile the timeline |

⬜ That last row is a genuinely good demo moment: cut the link, show the GCS correctly degrade to "STALE" rather than lying, show the onboard detector still running, then restore and backfill.

---

## 4.8 DRDO specifics — verified versus unknown

### ✅ Verified public information

- The Rustom-II/TAPAS data link was **developed by DRDO's Defence Electronics Application Laboratory (DEAL)**, to transmit ISR data, imagery and video to the ground control station in real time. ([Rustom-II, Airforce Technology](https://www.airforce-technology.com/projects/rustom-ii-male-unmanned-aerial-vehicle-uav/))
- Satellite-based communication and BLOS control were demonstrated in June 2023. ([TAPAS-BH-201](https://en.wikipedia.org/wiki/TAPAS-BH-201))
- Range ~250 km, command range up to ~1,000 km, endurance 18–24 h, ceiling ~28,000–30,000 ft.

### 🔒 Not public

Waveform, modulation, exact frequencies, encryption, frame format, message set, anti-jam techniques, achievable data rate, and the onboard bus architecture.

### The rule

> When presenting, say: *"DRDO's DEAL developed the TAPAS datalink; its technical details are not public, so we designed against open standards — MAVLink for the prototype, STANAG 4586 LOI-2 semantics for the architecture — with an adapter layer so a real datalink could be substituted without redesigning the twin."*

That answer is accurate, demonstrates you know the landscape, and is far stronger than a confident-sounding fabrication.

---

## 4.9 Summary — the five numbers that shape everything

| Quantity | Value | Consequence |
|---|---|---|
| Downlink capacity ✅ | ~122 kbit/s or less (Ku C2) | Raw vibration cannot be sent |
| Round-trip latency ✅ | ~1–1.5 s (SATCOM) | No ground-side fast control loop |
| Radio horizon 🔶 | ~380 km at 28,000 ft | Explains why BLOS/SATCOM exists |
| Our telemetry budget ⬜ | ~25–30 kbit/s | ~30 scalars at 20 Hz + features fits |
| One raw accelerometer 🔶 | ~160 kbit/s | Exceeds the whole link, by itself |

---

**Next:** [Part V — Edge AI and the Compute Split](05_edge_ai.md)
