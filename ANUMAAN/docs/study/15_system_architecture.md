# Part XV — System Architecture

*The layered design we should actually build.*

---

## 15.1 Design principles

Seven principles, each traceable to something established earlier in this course.

| # | Principle | Source |
|---|---|---|
| 1 | **The twin is the residual, not the display.** Everything else consumes twin state | [Part X](10_digital_twin.md) |
| 2 | **Adapters at every boundary.** No component knows its neighbour's wire format | [Part IV §4.6](04_telemetry_and_comms.md) |
| 3 | **Edge earns its place.** Onboard only if it fails the data, deadline or availability test | [Part XIII](13_edge_vs_ground_split.md) |
| 4 | **Physics before learning.** Compute residuals first; models operate on them | [Part VII §7.4](07_anomaly_detection.md) |
| 5 | **Degrade visibly.** Never show stale data as live | [Part XII §12.5](12_data_pipeline.md) |
| 6 | **Layered detection.** Statistical baseline always on; learned layers on top | [Part VII §7.6](07_anomaly_detection.md) |
| 7 | **Label every claim.** Verified, inference, assumption, proprietary | [README](README.md) |

---

## 15.2 The eight layers

```
╔══════════════════════════════════════════════════════════════════════════╗
║ LAYER 8 — GCS / PRESENTATION                                             ║
║  Dashboard · 3D view · alerts · advisory · replay UI · reports           ║
║  Consumes twin state. Contains ZERO detection logic                      ║
╚════════════════════════════════════╤═════════════════════════════════════╝
╔════════════════════════════════════╧═════════════════════════════════════╗
║ LAYER 7 — MISSION SIMULATION                                             ║
║  What-if trajectories · go/no-go · replay engine                         ║
║  Uses the SAME physics model as Layer 5                                  ║
╚════════════════════════════════════╤═════════════════════════════════════╝
╔════════════════════════════════════╧═════════════════════════════════════╗
║ LAYER 6 — PHM / ANALYTICS                                                ║
║  Anomaly ensemble · fault classifier · health indices · RUL + interval   ║
║  Operates on RESIDUALS, not raw values                                   ║
╚════════════════════════════════════╤═════════════════════════════════════╝
╔════════════════════════════════════╧═════════════════════════════════════╗
║ LAYER 5 — DIGITAL TWIN CORE                                              ║
║  Physics model · residuals · state estimator · degradation history       ║
║  ★ THE AUTHORITATIVE STATE OBJECT ★                                      ║
╚════════════════════════════════════╤═════════════════════════════════════╝
╔════════════════════════════════════╧═════════════════════════════════════╗
║ LAYER 4 — DATA / INGESTION                                               ║
║  Adapters · validation · time alignment · gap marking · storage          ║
╚════════════════════════════════════╤═════════════════════════════════════╝
╔════════════════════════════════════╧═════════════════════════════════════╗
║ LAYER 3 — COMMUNICATION (simulated link)                                 ║
║  Framing · sequence numbers · configurable latency, loss, bandwidth      ║
╚════════════════════════════════════╤═════════════════════════════════════╝
╔════════════════════════════════════╧═════════════════════════════════════╗
║ LAYER 2 — EDGE AI                                                        ║
║  Vibration features · residuals · lightweight anomaly · events · log     ║
║  MUST RUN WITH LAYER 3 DEAD                                              ║
╚════════════════════════════════════╤═════════════════════════════════════╝
╔════════════════════════════════════╧═════════════════════════════════════╗
║ LAYER 1 — DATA SOURCE                                                    ║
║  ⬜ Synthetic generator  │  🔶 CAN replay  │  ❌ Real engine (roadmap)    ║
║  All behind ONE interface                                                ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 15.3 Layer 1 — Data source

⬜ Three interchangeable implementations behind one interface:

```python
class TelemetrySource(Protocol):
    def frames(self) -> Iterator[RawFrame]: ...
    def describe(self) -> SourceInfo: ...   # what this source is, honestly
```

| Implementation | Status | Purpose |
|---|---|---|
| `SyntheticSource` | ⬜ We build it | Physics-based generation with fault injection ([Part XVII](17_simulation_design.md)) |
| `CANReplaySource` | ⬜ We build it | Replay a recorded CAN log through `vcan0` |
| `LiveCANSource` | 🔶 Roadmap | Real SocketCAN interface — a one-line change |

**Why `describe()` matters:** every output the system produces should be traceable to whether it came from simulation or real hardware. Making that explicit in the interface stops it from being quietly forgotten in a demo.

---

## 15.4 Layer 2 — Edge AI

⬜ Runs as a separate process from the GCS, with **no dependency on the link**.

```
┌─────────────────────────────────────────────────────────────┐
│  EDGE PROCESS                                               │
│                                                             │
│  CAN ingest (20 Hz) ──┐                                     │
│                       ├─▶ Validity checks ──▶ valid flags   │
│  Vibration (kHz) ─────┘         │                           │
│         │                       ▼                           │
│         │              Physics residuals                    │
│         ▼                       │                           │
│  Feature extraction ────────────┤                           │
│  (windows, FFT, orders,         │                           │
│   envelope, statistics)         ▼                           │
│         │              Lightweight anomaly                  │
│         │              (EWMA + Mahalanobis +                │
│         │               small quantised AE)                 │
│         │                       │                           │
│         └───────────┬───────────┘                           │
│                     ▼                                       │
│          ┌──────────────────────┐                           │
│          │  Event generator     │                           │
│          └──────────┬───────────┘                           │
│                     │                                       │
│     ┌───────────────┼───────────────┐                       │
│     ▼               ▼               ▼                       │
│  Full log      Telemetry       Local alert                  │
│  (always)      encoder         (autonomy)                   │
└─────────────────────────────────────────────────────────────┘
```

**The test that this layer is correct:** kill the link and the edge process must continue detecting, logging, and buffering with no error and no degradation in its own function. If it throws or stalls, the architecture is wrong.

---

## 15.5 Layer 3 — Communication

⬜ A deliberately *imperfect* simulated link. This is not a shortcut — a perfect link would let us build a system that fails in the field.

```python
@dataclass
class LinkProfile:
    bandwidth_kbps: float = 25.0
    latency_ms: float = 1200.0        # ✅ realistic for Ku SATCOM
    jitter_ms: float = 200.0
    packet_loss_pct: float = 2.0
    outage_schedule: list[tuple[float, float]] = field(default_factory=list)
```

⬜ Presets: `LOS_GOOD`, `SATCOM_NOMINAL`, `SATCOM_DEGRADED`, `JAMMED`.

🔶 Being able to switch to `JAMMED` live in a demo — and show the GCS correctly degrade while the edge keeps working — is one of the most convincing things the system can do, because it demonstrates the architecture rather than describing it.

---

## 15.6 Layer 4 — Data and ingestion

```
Frames ──▶ [Protocol adapter] ──▶ [Schema validation] ──▶ [Time align]
              MAVLink-style          version check          by onboard ts
              CAN                    range check                  │
              CSV/log                                             ▼
                                                        [Gap detection]
                                                         mark, don't fill
                                                               │
                                                  ┌────────────┴───────────┐
                                                  ▼                        ▼
                                          [Hot store: TSDB]       [Cold: Parquet]
```

⬜ **The canonical internal schema** — every adapter produces this, nothing downstream sees a wire format:

```python
@dataclass(frozen=True)
class TelemetryRecord:
    t_onboard: float              # acquisition time — order by THIS
    t_received: float             # arrival time
    values: dict[str, float]      # engineering units
    validity: dict[str, bool]     # per-channel
    source: SourceInfo            # synthetic / replay / live
    sequence: int                 # for loss detection
```

---

## 15.7 Layer 5 — Digital twin core

The authoritative state object, as specified in [Part X §10.6](10_digital_twin.md).

```python
@dataclass
class TwinState:
    t: float
    measured: dict[str, float]
    expected: dict[str, float]       # from the physics model
    residual: dict[str, float]       # measured − expected
    uncertainty: dict[str, float]    # from the state estimator
    validity: dict[str, bool]
    health: dict[str, float]         # per subsystem, 0–100
    staleness_s: float               # ★ how old is this, really
    degradation: DegradationHistory
```

**`staleness_s` is deliberately part of the state**, not a UI concern. Every consumer — dashboard, classifier, RUL — must be able to ask how current the data is and behave accordingly. This is principle 5 made structural rather than decorative.

⬜ The physics model is a **pure function**, so Layer 7 can call it on hypothetical inputs:

```python
def expected_state(inputs: EngineInputs, env: Environment,
                   engine: EngineParams) -> dict[str, float]: ...
```

No hidden state, no live-data dependency. This one constraint is what makes mission simulation possible without a second model.

---

## 15.8 Layer 6 — PHM analytics

```
TwinState (residuals, features, health)
    │
    ├──▶ [Anomaly ensemble]  EWMA · Mahalanobis · PCA · IsoForest · AE
    │         │                             │
    │         ▼                             ▼
    │    fused score                 per-sensor attribution
    │         │
    │    [if above threshold + persistence]
    │         ▼
    ├──▶ [Fault classifier] ──▶ label + confidence + evidence trail
    │                              │
    │                              └─▶ "UNKNOWN ANOMALY" is a valid output
    │
    ├──▶ [Health index] ──▶ per-subsystem 0–100, decomposable
    │
    └──▶ [RUL] ──▶ hours + confidence interval + trend line
```

⬜ Every output carries its **evidence trail** — the residuals and features that drove it — so the dashboard can always answer "why?" without a separate explainability system ([Part VIII §8.8](08_fault_diagnosis.md)).

---

## 15.9 Layers 7 and 8

**Layer 7 — Mission simulation and replay.** Calls the same pure physics function on hypothetical inputs ([Part XI](11_mission_simulation.md)). Replay re-feeds stored telemetry through Layers 4–6 deterministically.

**Layer 8 — Presentation.** Dashboard, 3D view, alerts, advisory, reports. ✅ The PS requires a visualisation dashboard showing health status, fault alerts, efficiency trends, maintenance advisory and mission-wise reports.

**The deletion test:** remove Layer 8 entirely and the system must still detect, classify, and predict — observable through logs and an API. If it cannot, logic has leaked into the presentation layer, which is a structural bug ([Part X §10.9](10_digital_twin.md)).

---

## 15.10 Process and deployment view

⬜ Three processes, mirroring the physical deployment:

```
┌───────────────────────────────┐     ┌──────────────────────────────────┐
│  EDGE PROCESS                 │     │  GCS PROCESS                     │
│  (would run on the aircraft)  │     │  (ground station)                │
│                               │     │                                  │
│  Layer 1: source              │     │  Layer 4: ingestion              │
│  Layer 2: edge AI             │     │  Layer 5: twin core              │
│                               │     │  Layer 6: PHM                    │
│  ├─ full log (local)          │     │  Layer 7: simulation, replay     │
│  └─ telemetry out ────────────┼────▶│  ├─ storage                      │
│                               │ L3  │  └─ API / WebSocket ─────────┐   │
└───────────────────────────────┘     └──────────────────────────────┼───┘
                                                                     ▼
                                                      ┌──────────────────────┐
                                                      │  UI PROCESS          │
                                                      │  Layer 8: dashboard, │
                                                      │  3D, alerts, replay  │
                                                      └──────────────────────┘
```

🔶 Running the edge as a genuinely separate process — ideally on a separate machine or a Raspberry Pi — is worth the small extra effort. It makes the link-loss demonstration real rather than simulated-within-one-process, and it forces the interfaces to be honest.

---

## 15.11 What is real, simulated, and assumed

| Component | Status |
|---|---|
| CAN decode via SocketCAN | ✅ **Real** — genuine kernel interface, `vcan0` |
| CAN frame content | ⬜ **Our own** DBC, documented as ours. 🔒 Rotax mapping is proprietary |
| Engine physics model | ⬜ **Approximate**, from public Rotax data |
| Telemetry framing | ✅ Real MAVLink-style framing over UDP |
| Link impairments | ⬜ **Simulated**, using ✅ realistic parameters |
| Vibration signals | ⬜ **Synthesised** with correct spectral structure |
| Anomaly / classification methods | ✅ **Real**, standard algorithms |
| Accuracy numbers | ⬜ On synthetic data + ✅ public benchmarks. **Never claimed for a real engine** |
| RUL method | ✅ Real method, ⬜ validated on simulation + ✅ C-MAPSS |
| Dashboard, 3D, replay | ✅ Real software |
| DRDO datalink specifics | 🔒 **Unknown** — never asserted |

---

**Next:** [Part XVI — Technology Stack](16_tech_stack.md)
