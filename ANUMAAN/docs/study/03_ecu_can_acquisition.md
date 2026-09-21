# Part III — ECU, CAN Bus and Data Acquisition

*How an electrical signal becomes a number on a wire, and who actually owns that number.*

---

## 3.1 CAN from first principles

**Concept → Why it exists → How it works → Example → How we use it**

### Why CAN exists

By the 1980s a vehicle had dozens of electronic modules. Point-to-point wiring between every pair grows as O(n²) and becomes a wiring-loom nightmare, heavy and unreliable. Bosch designed **CAN (Controller Area Network)** to let every module share one pair of wires, with a scheme that guarantees the most urgent message always wins when two modules talk at once.

Two properties made it dominant in vehicles and then in aircraft:

1. **Message-oriented, not address-oriented.** A CAN frame is not addressed to a recipient. It is labelled with *what it contains*. Any node that cares can listen. Adding a listener requires changing nothing.
2. **Non-destructive arbitration.** When two nodes transmit simultaneously, one wins and the other backs off — and the winner's message is *not corrupted*. No retransmission, no collision penalty.

### The physical layer

✅ **VERIFIED** — CAN uses a twisted pair, CAN_H and CAN_L, terminated with 120 Ω resistors at both ends of the bus. Signalling is differential: during transmission CAN_H sits at a higher voltage than CAN_L, and the receiver reads the *difference*. ([Kvaser CAN tutorial](https://kvaser.com/can-protocol-tutorial/), [CAN physical layer](https://perspic.ca/blog/perspic-signals-1/can-bus-basics-2-understanding-the-physical-layer-3))

**Why differential signalling matters on an aircraft:** electrical noise from the ignition system, alternator, and radios couples into *both* wires nearly equally. Subtracting one from the other cancels the common-mode noise. This is why CAN survives in an environment that would corrupt a single-ended signal.

**A practical diagnostic:** ✅ with the engine off, measuring across the two CAN wires should read ~60 Ω — the two 120 Ω terminators in parallel. ([RDAC-CAN](https://aeroshop.eu/en/rdac-can-rotax-912is.html)) Reading 120 Ω means a terminator is missing; reading very high means an open bus.

### Dominant and recessive bits — the trick that makes arbitration work

CAN bits are not simply "high" and "low". They are:

- **Dominant (logical 0)** — actively driven. If any node drives dominant, the bus is dominant.
- **Recessive (logical 1)** — passive. The bus is recessive only if *every* node lets it be.

This is a wired-AND. It is the whole basis of arbitration.

### Arbitration, worked through

Every transmitter monitors the bus while it transmits. If it sends recessive but reads back dominant, it knows another node is transmitting a higher-priority message, and it immediately stops and becomes a receiver.

✅ **VERIFIED** — the arbitration field determines priority; the node with the **numerically lowest identifier wins** and continues transmitting without corruption. ([Kvaser: structure of a CAN frame](https://kvaser.com/lesson/structure-of-a-can-frame/), [Arbitration field](https://www.sciencedirect.com/topics/computer-science/arbitration-field))

```
Node A sends ID 0x100 →  0 0 0 1 0 0 0 0 0 0 0
Node B sends ID 0x120 →  0 0 0 1 0 0 1 0 0 0 0
                                      ↑
                         Bit 5: A sends dominant(0), B sends recessive(1).
                         Bus reads dominant. B sees mismatch, backs off.
                         A continues, message intact. Zero time lost.
```

**Design consequence for us:** lower CAN ID = higher priority. Safety-critical engine data should carry low IDs. ⬜ In our simulated bus we will follow this convention.

### Frame format

✅ **VERIFIED** — CAN 2.0A uses an 11-bit identifier; CAN 2.0B allows 29-bit extended identifiers, and standard and extended frames can coexist on the same bus. ([CAN 2.0B](https://acutena.com/en/protocols/can-2-0b/), [Kvaser tutorial](https://kvaser.com/can-protocol-tutorial/))

A classical CAN data frame:

| Field | Bits | Purpose |
|---|---|---|
| SOF | 1 | Start of frame, dominant |
| Identifier | 11 (or 29) | Message label **and** priority |
| RTR | 1 | Data frame vs remote request |
| Control / IDE / DLC | 6 | Includes DLC — how many data bytes follow (0–8) |
| **Data** | **0–64** | **The payload. At most 8 bytes.** |
| CRC | 15 + delim | Error detection |
| ACK | 2 | Any receiver that got it cleanly asserts dominant |
| EOF + IFS | 10 | End of frame, inter-frame space |

**The eight-byte limit is the defining constraint of CAN.** One frame cannot carry an entire engine state. It carries two to four values. This is why an engine ECU publishes *many* different frame IDs, each with a few parameters, at possibly different rates.

### Bit rate and what it buys you

✅ **VERIFIED** — 500 kbit/s is a common industrial configuration. ([Kvaser](https://kvaser.com/can-protocol-tutorial/), [J1939 network design](https://jcom1939.com/from-can-fundamentals-to-sae-j1939-network-design-for-industrial-and-diesel-engine-applications/))

🔶 **INFERENCE — bus load calculation.** A classical CAN frame with 8 data bytes costs roughly 110–130 bits including stuffing and overhead. At 500 kbit/s:

```
500,000 bits/s ÷ ~120 bits/frame ≈ 4,100 frames/s theoretical maximum
```

Suppose the engine publishes 10 distinct frame IDs at 50 Hz each:

```
10 × 50 = 500 frames/s  →  500 × 120 = 60,000 bits/s  =  12% bus load
```

Comfortable. Good practice keeps CAN bus load below ~50–70%. **The engine bus is not the bottleneck in our system — the radio link is.** That asymmetry is worth internalising: onboard you have bandwidth to spare; to the ground you have almost none.

---

## 3.2 SocketCAN — CAN on Linux

✅ **VERIFIED** — SocketCAN is a Linux kernel subsystem that exposes the CAN bus as a **standard network interface**, so applications use the ordinary Berkeley socket API. An application can receive all frames or filter by CAN ID. ([Linux kernel SocketCAN docs](https://docs.kernel.org/networking/can.html), [python-can SocketCAN](https://python-can.readthedocs.io/en/stable/interfaces/socketcan.html))

This is why the PS's mention of "SocketCAN" is a practical gift to us: **you do not need CAN hardware to develop.** Linux provides a virtual CAN interface.

```bash
# Create a virtual CAN interface — no hardware required
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Real hardware would instead be:
sudo ip link set can0 type can bitrate 500000
sudo ip link set up can0

# Observe traffic
candump vcan0

# Inject a frame by hand
cansend vcan0 123#DEADBEEF00112233
```

In Python:

```python
import can

bus = can.interface.Bus(channel='vcan0', bustype='socketcan')

for msg in bus:
    print(f"ID=0x{msg.arbitration_id:03X} DLC={msg.dlc} data={msg.data.hex()}")
```

⬜ **Our approach:** the telemetry simulator publishes onto `vcan0` using a documented, self-defined frame layout. The ingestion code then reads from a real socket, exactly as it would in flight. **Swapping the simulator for real hardware becomes a one-line interface change** — and being able to demonstrate that is worth a great deal in a judged prototype.

---

## 3.3 Decoding CAN payload bytes — illustrative only

⚠️ **The example below is ⬜ ILLUSTRATIVE. It is our own invented layout. It is NOT the Rotax mapping.** See §3.4 for why no real mapping appears in this document.

Suppose we define a frame carrying RPM, oil temperature, and oil pressure:

```
CAN ID: 0x120     DLC: 8
Data:   14 50 00 5B 01 A4 00 00
        └─┬─┘ └┬┘ └─┬─┘
```

| Bytes | Field | Encoding | Raw | Engineering value |
|---|---|---|---|---|
| 0–1 | RPM | uint16 big-endian, 1 RPM/bit | `0x1450` = 5200 | **5200 RPM** |
| 2 | Oil temp | uint8, offset −40, 1 °C/bit | `0x00`... see note | — |
| 3 | Oil temp | uint8, offset −40 | `0x5B` = 91 | **91 − 0 = 91 °C** ⬜ |
| 4–5 | Oil pressure | uint16, 0.01 bar/bit | `0x01A4` = 420 | **4.20 bar** |
| 6–7 | Reserved | — | — | — |

Decoder:

```python
import struct

def decode_0x120(data: bytes) -> dict:
    """ILLUSTRATIVE layout of our own definition. Not a Rotax mapping."""
    rpm       = struct.unpack_from('>H', data, 0)[0]          # 1 RPM/bit
    oil_temp  = data[3] - 0                                    # °C, our scaling
    oil_press = struct.unpack_from('>H', data, 4)[0] * 0.01    # bar
    return {"rpm": rpm, "oil_temp_c": oil_temp, "oil_press_bar": oil_press}
```

**The three things that always define a CAN signal** — and that you must document for every signal you define:

1. **Byte position and width** (which bytes, how many)
2. **Byte order** (big-endian/Motorola vs little-endian/Intel)
3. **Scale and offset** (`physical = raw × scale + offset`)

In industry these live in a **DBC file**, the standard CAN database format, readable by `cantools` in Python. ⬜ We will write our own DBC for our simulated bus. It is good practice and it demonstrates real engineering literacy.

---

## 3.4 The Rotax 912 iS reality — what is public and what is not

This section matters more for your credibility than almost anything else in this document.

### What is publicly verified ✅

- The 912 iS has **two ECU lanes (A and B)** using the **CAN Aerospace** data format. Interface modules such as the RDAC-CAN connect to both lanes. ([RDAC-CAN](https://aeroshop.eu/en/rdac-can-rotax-912is.html))
- **Failover behaviour:** the interface can continue providing data from lane B if lane A fails, configurable via DIP switches, or be locked "lane exclusive" to one lane. ([RDAC-CAN](https://aeroshop.eu/en/rdac-can-rotax-912is.html))
- **Parameters available from the 912/915 iS engine computers over CAN:** RPM, manifold pressure, oil pressure, oil temperature, coolant temperature, EGT for all four cylinders, ECU voltage, engine hours. ([RS Flight Systems EMU](https://www.rs-flightsystems.com/product-page/emu-912xis))
- **CANaerospace** itself is a documented higher-layer protocol over CAN, developed by Stock Flight Systems in 1998 for aeronautical use, with a 4-byte message header carrying node ID, data type, message code and service code. It is used as a UAV data bus. ([CANaerospace](https://en.wikipedia.org/wiki/CANaerospace))
- Rotax operator's manuals and EASA type certificate data sheets are publicly downloadable. ([OM-912 iS](https://avsport.org/acft/Rotax/912iS/912iS_operators_manual_d05875.pdf), [EASA TCDS E.121](https://www.easa.europa.eu/en/downloads/7633/en))

### What is NOT public 🔒

**The actual CAN ID-to-signal mapping for the Rotax 912 iS is not publicly documented.** Community discussions show owners and developers asking for exactly this and not finding it; the detail appears to be proprietary or available only through Rotax directly. ([Rotax owner forum: CANbus protocol](https://www.rotax-owner.com/en/915is-technical-questions/9007-canbus-protocol), [CAN bit definitions](https://www.rotax-owner.com/en/912is-technical-questions/8400-can-bit-definition-warning-lamps)) Connector pinout detail at the ECU end is also reported as not formally documented.

### The rule this creates

> **Never write a specific Rotax CAN ID or byte mapping in our documentation, code comments, or presentation.** If we need concrete frames, we define our own and label them clearly as our own.

Two reasons. First, fabricating it is simply wrong and a domain-expert judge may know it. Second, **we do not need it**: our architecture reads from a decoder layer, and swapping our simulated DBC for a real one later is a configuration change, not a redesign. Saying *"we designed against a documented interface abstraction because the vendor mapping is proprietary"* is a stronger engineering answer than a fabricated table.

---

## 3.5 Other aircraft buses, and where CAN sits among them

✅ **VERIFIED** comparison:

| Bus | Topology | Data rate | Frame | Typical domain |
|---|---|---|---|---|
| **CAN / CANaerospace** | Multi-master broadcast | commonly 500 kbit/s | ≤8 data bytes | Engine/ECU, small aircraft, UAV subsystems |
| **ARINC 429** | Point-to-point, one transmitter → many receivers | 12.5 or 100 kbit/s | 32-bit words, usually one word per message | Commercial transport avionics |
| **MIL-STD-1553** | Command/response, time-division multiplexed, bus controller | 1 Mbit/s fixed | Up to 32 × 16-bit words | Military platforms, fixed and rotary wing, spacecraft, unmanned aircraft |
| **SAE J1939** | CAN-based, 29-bit IDs, PGN/SPN naming | CAN rates | Always 8 data bytes | Heavy-duty ground vehicles, diesel engines |

([ARINC 429 vs MIL-STD-1553](https://kimdu.com/arinc-429-vs-mil-std-1553-a-comprehensive-comparison/), [CANaerospace](https://en.wikipedia.org/wiki/CANaerospace), [J1939](https://www.csselectronics.com/pages/j1939-explained-simple-intro-tutorial))

✅ Encoding differs too: ARINC 429 uses bipolar return-to-zero/bi-phase signalling, MIL-STD-1553 uses Manchester encoding.

✅ Note also that **CAN is not used for primary flight control** and is not a replacement for MIL-STD-1553.

🔒 **What bus DRDO's TAPAS uses internally is not public.** A reasonable 🔶 **INFERENCE** is that a military MALE platform would likely use 1553-class buses for mission-critical avionics and CAN-class buses for subsystem/engine data, because that is the general industry pattern — but we must never state it as fact, and nothing in our design should depend on it.

---

## 3.6 Data provenance — five categories you must keep separate

This taxonomy prevents a whole class of design errors. Every value in the system belongs to exactly one category, and they have different trust properties, rates, and failure modes.

| # | Category | Origin | Examples | Key property |
|---|---|---|---|---|
| 1 | **Raw sensor data** | Transducer output before digitisation | Thermocouple mV, accelerometer waveform | Analog, noisy, needs conditioning. Only exists onboard |
| 2 | **ECU-derived data** | Computed/measured inside the engine ECU | RPM, MAP, EGT ×4, oil P/T, ECU voltage, engine hours | Already calibrated. **We do not control its processing** |
| 3 | **Flight-controller data** | Autopilot / air data system | Altitude, airspeed, attitude, GPS, flight phase, throttle | Different clock domain — needs time alignment |
| 4 | **Telemetry data** | Whatever is selected and encoded for downlink | The subset that fits the link budget | Lossy, delayed, possibly out of order |
| 5 | **Ground-station data** | Reconstructed and augmented at the GCS | Residuals, health indices, RUL, advisories | Derived, not measured. Must be traceable back to (1)–(4) |

**Three errors this taxonomy prevents:**

- **Treating ECU-derived values as raw.** The ECU has already filtered and calibrated them. You cannot recover what it smoothed away — including, possibly, the exact transient that indicated a fault. If a fault signature needs raw dynamics, you need your own sensor, not the ECU's number.
- **Assuming telemetry equals onboard truth.** The downlink is a *lossy view*. Post-flight log analysis will legitimately show things the live view never did. Design the replay system knowing this ([Part XII](12_data_pipeline.md)).
- **Mixing clock domains.** Engine CAN, flight computer, and vibration DAQ each have their own timebase. Aligning them is a real engineering task, not an afterthought ([Part XII §12.4](12_data_pipeline.md)).

---

## 3.7 The complete acquisition chain

```
┌──────────────────────────────────────────────────────────────────────────┐
│ CATEGORY 1 — RAW SENSOR (analog domain, onboard only)                    │
│                                                                          │
│  Thermocouple ──mV──┐                                                    │
│  RTD ───────────Ω───┤                                                    │
│  Pressure ──4-20mA──┼──▶ [Signal conditioning: amplify, CJC, linearise] │
│  Hall pickup ─pulse─┤                          │                         │
│  Accelerometer ─AC──┘                          ▼                         │
│                                             [ ADC ]                      │
└────────────────────────────────────────────────┼─────────────────────────┘
                                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ CATEGORY 2 — ECU-DERIVED                    CATEGORY 1 (high-rate path)  │
│  ┌────────────────────────────┐             ┌─────────────────────────┐  │
│  │ ECU Lane A   ECU Lane B    │             │ Vibration DAQ @ 2–10kHz │  │
│  │  (dual, CAN Aerospace) ✅  │             │ SEPARATE from CAN       │  │
│  └─────────────┬──────────────┘             └───────────┬─────────────┘  │
│                │ CAN frames, 10–50 Hz                   │ waveform       │
└────────────────┼────────────────────────────────────────┼────────────────┘
                 ▼                                        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ ONBOARD COMPUTER  (Linux + SocketCAN)                                    │
│                                                                          │
│   [CAN decode / DBC]      [Flight computer: CATEGORY 3]                  │
│            │                          │                                  │
│            └──────────┬───────────────┘                                  │
│                       ▼                                                  │
│            [Time alignment + validity checks]                            │
│                       │                    [Vibration feature extraction]│
│                       │                     orders, RMS, kurtosis, bands │
│                       │                                │                 │
│                       └────────────┬───────────────────┘                 │
│                                    ▼                                     │
│                        [Edge analytics + health score]                   │
│                                    │                                     │
│                    ┌───────────────┴────────────────┐                    │
│                    ▼                                ▼                    │
│        [Onboard full-rate log]          [Telemetry encoder: CATEGORY 4]  │
│         stays with the aircraft                     │                    │
└─────────────────────────────────────────────────────┼────────────────────┘
                                                      ▼
                                              RF / SATCOM  →  GCS (CATEGORY 5)
```

**The two things to take from this diagram:**

1. **Vibration bypasses CAN entirely.** It needs its own acquisition path because CAN at 500 kbit/s with 8-byte frames is the wrong transport for a 10 kHz waveform, and because the ECU does not provide it.
2. **The log and the downlink diverge permanently.** The onboard log has everything. The downlink has a selected subset. Post-flight analysis is genuinely richer than live monitoring, and your replay architecture should reflect that rather than pretending they are the same stream.

---

**Next:** [Part IV — Telemetry and Communication](04_telemetry_and_comms.md)
