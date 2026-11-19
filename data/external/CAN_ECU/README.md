# CAN_ECU — bus data, tooling, and our own DBC

---

## The central fact

> 🔒 **The Rotax 912 iS CAN ID-to-signal mapping is not publicly documented.**

Community discussions show owners and developers asking for exactly this and not finding it. The detail appears to be proprietary or available only through Rotax directly. Connector pinout detail at the ECU end is also reported as not formally documented.

- https://www.rotax-owner.com/en/915is-technical-questions/9007-canbus-protocol
- https://www.rotax-owner.com/en/912is-technical-questions/8400-can-bit-definition-warning-lamps

### The rule this creates

**Never write a specific Rotax CAN ID or byte mapping in our documentation, code, or presentation.**

Two reasons:

1. Fabricating it is wrong, and a domain-expert evaluator may know it.
2. **We do not need it.** Our architecture reads through a decoder layer. Swapping our DBC for a real one later is a configuration change, not a redesign.

The strong answer when asked: *"the vendor mapping is proprietary, so we designed against a documented interface abstraction — our own DBC for the prototype, replaceable with the real one on integration."*

---

## What IS publicly verified

| Fact | Source |
|---|---|
| Dual ECU lanes (A and B) using **CAN Aerospace** format | https://aeroshop.eu/en/rdac-can-rotax-912is.html |
| Lane failover: continue from lane B if A fails; configurable lane-exclusive mode | Same |
| **Parameter list** over CAN: RPM, manifold pressure, oil pressure, oil temperature, coolant temperature, EGT ×4, ECU voltage, engine hours | https://www.rs-flightsystems.com/product-page/emu-912xis |
| ~60 Ω across CAN_H/CAN_L, engine off | https://aeroshop.eu/en/rdac-can-rotax-912is.html |
| CANaerospace: 4-byte header with node ID, data type, message code, service code | https://en.wikipedia.org/wiki/CANaerospace |

---

## CAN fundamentals

Full tutorial in [Part III](../../ANUMAAN/docs/study/03_ecu_can_acquisition.md).

| Property | Value |
|---|---|
| Identifier | 11-bit (CAN 2.0A) or 29-bit (CAN 2.0B); both can coexist |
| Data payload | **Maximum 8 bytes** — the defining constraint |
| Bit rate | Commonly 500 kbit/s |
| Physical | Twisted pair CAN_H/CAN_L, 120 Ω at each end, differential |
| Arbitration | Lowest ID wins, non-destructively |
| Bit states | Dominant (0) actively driven; recessive (1) passive — a wired-AND |

---

## Tooling

### SocketCAN — no hardware needed

Linux exposes CAN as a standard network interface, so identical code works for virtual and real buses.

```bash
# Virtual CAN — development without hardware
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Real hardware
sudo ip link set can0 type can bitrate 500000
sudo ip link set up can0

# Observe / inject
candump vcan0
cansend vcan0 123#DEADBEEF00112233
```

### Python

```python
import can

bus = can.interface.Bus(channel='vcan0', bustype='socketcan')
for msg in bus:
    print(f"ID=0x{msg.arbitration_id:03X} DLC={msg.dlc} data={msg.data.hex()}")
```

| Package | Purpose |
|---|---|
| `python-can` | SocketCAN interface |
| `cantools` | DBC parsing, signal encode/decode |
| `can-utils` | `candump`, `cansend` for debugging |

References: https://docs.kernel.org/networking/can.html · https://python-can.readthedocs.io/

---

## Our DBC

⬜ We define our own CAN database for the simulated bus. **It is ours, documented as ours, and is not a Rotax mapping.**

Every CAN signal needs exactly three things defined:

1. **Byte position and width**
2. **Byte order** (big-endian/Motorola or little-endian/Intel)
3. **Scale and offset** — `physical = raw × scale + offset`

⬜ **Illustrative example — our own layout, not Rotax:**

```
CAN ID: 0x120     DLC: 8
Data:   14 50 00 5B 01 A4 00 00

bytes 0–1  RPM          uint16 BE, 1 RPM/bit      0x1450 = 5200 RPM
byte  3    Oil temp     uint8, 1 °C/bit           0x5B   = 91 °C
bytes 4–5  Oil pressure uint16 BE, 0.01 bar/bit   0x01A4 = 4.20 bar
bytes 6–7  reserved
```

⬜ **Convention:** lower CAN ID = higher priority, so safety-critical engine data gets low IDs — mirroring real CAN practice.

Store the DBC file here as `anumaan_engine.dbc` when written, with a header comment stating clearly that it is our own definition.

---

## Bus load

🔶 A classical CAN frame with 8 data bytes costs roughly 110–130 bits including stuffing and overhead.

```
10 frame IDs × 50 Hz = 500 frames/s
500 × 120 bits       = 60,000 bit/s
60,000 / 500,000     = 12% bus load
```

Comfortable; good practice keeps load below ~50–70%.

**The engine bus is not our bottleneck — the radio link is.** Onboard you have bandwidth to spare; to the ground you have almost none. That asymmetry drives the whole architecture.

---

## Other buses

| Bus | Rate | Frame | Domain |
|---|---|---|---|
| CAN / CANaerospace | ~500 kbit/s | ≤8 data bytes | Engine, UAV subsystems |
| ARINC 429 | 12.5 / 100 kbit/s | 32-bit words | Commercial avionics |
| MIL-STD-1553 | 1 Mbit/s | ≤32 × 16-bit words | Military platforms |
| SAE J1939 | CAN rates | Always 8 bytes, PGN-addressed | Heavy-duty ground vehicles |

CAN is **not** used for primary flight control and does not replace MIL-STD-1553.

🔒 What bus DRDO uses internally on TAPAS is not public. Do not assert it.
