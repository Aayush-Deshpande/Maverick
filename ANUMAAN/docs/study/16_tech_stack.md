# Part XVI — Technology Stack

*Each choice argued both ways, then decided.*

---

## 16.1 How to read this

For each area: the candidates, the case for and against, and a decision with reasoning. The bias throughout is toward **boring, proven technology**, because the interesting part of this project is the PHM, not the infrastructure. Every hour spent fighting a fashionable database is an hour not spent on fault detection.

---

## 16.2 Backend framework

| Option | For | Against |
|---|---|---|
| **FastAPI** | Async, automatic OpenAPI docs, native WebSocket, Pydantic validation, excellent typing | Younger ecosystem than Flask/Django |
| Flask | Simple, ubiquitous | Sync by default; WebSockets need extensions |
| Django | Batteries included, admin UI | Heavyweight; ORM-centric, wrong shape for time series |
| Node/Express | Great WebSocket story | Splits the language — our ML is Python |

✅ **Decision: FastAPI.**

Reasoning: we need WebSocket streaming to the dashboard, and Pydantic gives us schema validation at the ingestion boundary for free — which directly implements the canonical-schema principle from [Part XV §15.6](15_system_architecture.md). Staying in one language keeps the twin, the ML, and the API in the same process space.

---

## 16.3 Machine learning

| Option | For | Against | Use for |
|---|---|---|---|
| **scikit-learn** | RF, IsoForest, PCA, SVM, scalers all present; stable API; trivially fast | No deep learning | ✅ Anomaly detection, classification, PCA |
| **PyTorch** | Flexible, best-in-class for sequence models, good quantisation tooling | Heavier; more code for simple tasks | ✅ Autoencoder, LSTM/GRU RUL |
| TensorFlow/Keras | TFLite is the strongest edge deployment path | Less pleasant for research iteration | 🔶 If we deploy to a microcontroller |
| XGBoost/LightGBM | Often best on tabular | Extra dependency; more tuning | 🔶 Compare against RF, keep if it wins |

✅ **Decision: scikit-learn as primary, PyTorch for neural components.**

Reasoning: most of our models are classical ([Part VII](07_anomaly_detection.md)), and scikit-learn does those better and faster than a deep-learning framework would. PyTorch handles the autoencoder and the RUL sequence models. 🔶 We should test gradient boosting against Random Forest but only adopt it if it wins on a *properly split* validation set ([Part VIII §8.7](08_fault_diagnosis.md)).

---

## 16.4 Signal processing

| Option | For | Against |
|---|---|---|
| **SciPy** | `signal` module has filters, Hilbert, STFT, windows; well tested | — |
| NumPy | FFT, array maths, the foundation | Lower level |
| librosa | Excellent spectrogram tooling | Audio-oriented; heavy dependency |
| PyWavelets | Wavelet analysis | Only if we pursue wavelets |

✅ **Decision: NumPy + SciPy.**

Reasoning: everything in [Part VI](06_vibration_analysis.md) — Hann windows, FFT, Hilbert envelope, Butterworth band-pass, resampling for order tracking — is directly available in SciPy. Angular resampling we write ourselves; it is interpolation onto an angle grid, perhaps twenty lines.

---

## 16.5 Time-series storage

| Option | For | Against |
|---|---|---|
| **TimescaleDB** | PostgreSQL extension — full SQL plus hypertables, compression, continuous aggregates | Needs a Postgres instance |
| InfluxDB | Purpose-built for time series | Separate query language; weaker relational joins |
| **Parquet on disk** | Columnar, compressed, perfect for batch analytics; no server | Not for live queries |
| SQLite | Zero setup | Poor for high-rate time series |

✅ **Decision: TimescaleDB for hot/warm, Parquet for cold.**

Reasoning: this matches the three-tier design in [Part XII §12.7](12_data_pipeline.md). Hypertables handle 20 Hz writes comfortably, continuous aggregates give us pre-computed trends for the dashboard, and SQL lets us join telemetry against mission and maintenance metadata — which a pure TSDB makes awkward. Parquet for cold storage because training reads whole columns.

🔶 **Pragmatic fallback:** if Postgres setup becomes a burden during the sprint, SQLite plus Parquet is adequate for a demo. Do not lose two days to database administration.

---

## 16.6 Streaming and messaging

| Option | For | Against |
|---|---|---|
| **WebSockets** | Native browser support; FastAPI built-in; low latency | Point-to-point |
| **UDP** | ✅ Realistic for a radio link — genuinely lossy and unordered | No delivery guarantee (which is the point) |
| MQTT | Designed for constrained/telemetry links; pub/sub | Needs a broker |
| Redis pub/sub | Fast, simple, also useful as a cache | Another service |
| Kafka | Durable, replayable, scales | ❌ Massive overkill here |

✅ **Decision: UDP for the simulated datalink, WebSockets for the GCS→UI path.**

Reasoning: UDP is the honest choice for the radio link — it loses and reorders packets naturally, which is exactly the behaviour we need to design against ([Part XII §12.5](12_data_pipeline.md)). Using TCP there would hide the very failure mode the architecture exists to handle. WebSockets for the browser because it is direct and well supported.

❌ **Explicitly rejecting Kafka.** It is the right tool for durable multi-consumer event streams at scale. We have one producer, one consumer, and a deadline. Adding it would consume days and demonstrate nothing about PHM.

---

## 16.7 Physics and simulation

| Option | For | Against |
|---|---|---|
| **NumPy/SciPy + our own model** | Full control, transparent, fast, explainable | We write the thermodynamics |
| SciPy `solve_ivp` | Proper ODE integration for thermal dynamics | Slower than a fixed-step update |
| CoolProp | Accurate thermodynamic properties | Heavy for our fidelity level |
| Simulink/GT-Power | Industry standard for engine modelling | ❌ Licensing, and not Python |

✅ **Decision: our own model in NumPy, with `solve_ivp` for the thermal ODEs.**

Reasoning: the model in [Part X §10.4](10_digital_twin.md) is a handful of equations. Writing it ourselves means we can explain every term — which matters both for the physics-informed AI claim and for a judge asking how it works. 🔶 A fixed-step Euler update at 20 Hz is likely sufficient for thermal states with time constants of tens of seconds; use `solve_ivp` if stability becomes an issue.

---

## 16.8 CAN tooling

| Option | For | Against |
|---|---|---|
| **python-can** | ✅ SocketCAN interface, standard library for this | — |
| **cantools** | DBC parsing and signal encode/decode | — |
| can-utils | `candump`, `cansend` for debugging | CLI only |

✅ **Decision: python-can + cantools + can-utils, over `vcan0`.**

Reasoning: this is the real toolchain. ✅ SocketCAN exposes CAN as a network interface, so our code is identical for virtual and real hardware ([Part III §3.2](03_ecu_can_acquisition.md)). ⬜ We write our own DBC and document it as ours — 🔒 never a fabricated Rotax mapping ([Part III §3.4](03_ecu_can_acquisition.md)).

---

## 16.9 Telemetry protocol

| Option | For | Against |
|---|---|---|
| **pymavlink** | ✅ Real MAVLink framing, sequence numbers, CRC | Custom fields need a dialect or `NAMED_VALUE_FLOAT` |
| Custom binary | Simple, exactly our fields | Less credible than a real standard |
| Protobuf | Schema evolution, compact | Another toolchain |
| JSON | Human readable | ❌ Far too verbose for a kbps link |

✅ **Decision: MAVLink-style framing via pymavlink.**

Reasoning: ✅ MAVLink's sequence numbers give us free packet-loss measurement, and CRC_EXTRA catches schema mismatches ([Part IV §4.5](04_telemetry_and_comms.md)). Using a real protocol is also more defensible than inventing one. ❌ JSON is disqualified by arithmetic: at ~25 kbit/s, verbose encoding wastes most of the budget.

---

## 16.10 Frontend

| Option | For | Against |
|---|---|---|
| **React + TypeScript** | Mature, typed, huge ecosystem | Build tooling |
| Vue | Gentler learning curve | Smaller ecosystem |
| Plain HTML + Chart.js | Minimal setup | Gets unwieldy for a complex dashboard |
| Streamlit/Dash | Very fast to build in Python | Limited layout control; awkward for real-time 3D |

✅ **Decision: React + TypeScript**, with **Recharts or uPlot** for charts and **Three.js** for the 3D view.

Reasoning: TypeScript catches schema mismatches between API and UI at compile time. 🔶 For 20 Hz streaming charts, uPlot is dramatically faster than most charting libraries — worth knowing before the dashboard stutters in a demo.

🔶 **Pragmatic note:** if frontend time is short, Streamlit gets a credible dashboard running in hours. The PS requires a dashboard, not a beautiful one, and ✅ the team's own breakdown warns against over-investing in visual polish before the required capabilities work.

---

## 16.11 3D visualisation

| Option | For | Against |
|---|---|---|
| **Three.js** (glTF from Blender) | Runs in the browser, integrates with the dashboard | Requires export pipeline |
| Blender + bpy live | Direct use of existing assets | ❌ Blender is not a runtime for a GCS |
| Babylon.js | Strong engine features | Smaller community |

✅ **Decision: model in Blender, export glTF, render with Three.js.**

Reasoning: the GCS is a web dashboard; the 3D view must live inside it. ⬜ Critically, per [Part X §10.9](10_digital_twin.md), the 3D view is a *consumer* of twin state and contains no logic. Blender remains the authoring tool, not the runtime.

---

## 16.12 Edge hardware

| Option | Power ✅ | For | Against |
|---|---|---|---|
| **Raspberry Pi 5 / CM4** | ~3–5 W | Linux + SocketCAN natively; ample for FFT + small models | ✅ No ML-oriented GPU |
| Jetson Orin Nano | ✅ ~5 W idle, 8–12 W inference, ~25 W peak | ✅ Up to 40 TOPS INT8 | Overkill for our workload; more power |
| STM32/ESP32 | mW | ✅ Proven for FFT + int8 MLP | Would require rewriting in C |

✅ **Decision: Raspberry Pi class for the prototype.**

Reasoning: honest sizing from [Part V §5.6](05_edge_ai.md) — our edge workload is a few FFTs and a sub-100 kB model per second, a few percent of one core. 🔶 Specifying a Jetson would be over-specification we could not justify if asked. The correct answer to "why not a Jetson?" is *"because our workload does not need one; we would move to it only if we pushed CNN inference onboard."* That answer demonstrates engineering judgment; the reverse does not.

---

## 16.13 RAG and advisory

| Option | For | Against |
|---|---|---|
| **sentence-transformers + FAISS/Chroma** | Local, offline, small | Quality depends on the corpus |
| Local LLM (Qwen/Llama class) | ✅ Fully offline — matches the air-gapped requirement | Memory and latency cost |
| Cloud LLM API | Best quality | ❌ Defeats air-gapped operation |

✅ **Decision: local embeddings + local vector store + a small local LLM.**

Reasoning: ✅ the team's own architecture document already specifies 100% air-gapped local operation, which is the right call for a defence context. ❌ A cloud API would contradict it. 🔶 The corpus should be publicly available Rotax operator's manuals and general maintenance documentation — not fabricated "DRDO procedures".

**Scope discipline:** the RAG layer explains and advises. It must never *compute* a detection or an RUL. ✅ The team's own breakdown correctly identifies "a chatbot that talks about failures without actually computing anything" as a misinterpretation of the PS.

---

## 16.14 Testing

| Tool | Purpose |
|---|---|
| **pytest** | Unit and integration tests |
| **hypothesis** | Property-based testing — excellent for signal processing invariants |
| **pytest-benchmark** | Latency budgets ([Part XII §12.9](12_data_pipeline.md)) |

🔶 Property-based testing deserves a mention because it fits signal processing unusually well: *"for any sine wave at frequency f below Nyquist, the FFT peak must be at f"* is a property that catches a whole class of indexing and scaling bugs that example-based tests miss.

⬜ **Tests that matter most for this project:**
1. Physics model gives sane values across the whole flight envelope
2. Residuals are near zero for synthetic healthy data in every regime
3. Each injected fault produces its expected signature
4. The pipeline handles gaps, reordering and duplicates without crashing
5. **Edge process survives link loss** — the architectural test from [Part XV §15.4](15_system_architecture.md)
6. Replay is deterministic — same input, same twin state

---

## 16.15 The stack

```
┌──────────────────────────────────────────────────────────────┐
│  UI          React + TypeScript · uPlot · Three.js           │
├──────────────────────────────────────────────────────────────┤
│  API         FastAPI · WebSockets · Pydantic                 │
├──────────────────────────────────────────────────────────────┤
│  PHM         scikit-learn · PyTorch · NumPy/SciPy            │
├──────────────────────────────────────────────────────────────┤
│  Twin        NumPy · SciPy solve_ivp (our physics model)     │
├──────────────────────────────────────────────────────────────┤
│  Storage     TimescaleDB (hot/warm) · Parquet (cold)         │
├──────────────────────────────────────────────────────────────┤
│  Comms       pymavlink over UDP · impairment simulator       │
├──────────────────────────────────────────────────────────────┤
│  Edge        Python on Pi-class · python-can · SocketCAN     │
├──────────────────────────────────────────────────────────────┤
│  Source      Our generator · vcan0 · (live CAN — roadmap)    │
└──────────────────────────────────────────────────────────────┘
```

🔶 Every element is either standard in its field or something we deliberately wrote ourselves for transparency. Nothing here is chosen to sound impressive, and that is intentional — the novelty in this project should live in the PHM, not the plumbing.

---

**Next:** [Part XVII — Realistic Simulation Design](17_simulation_design.md)
