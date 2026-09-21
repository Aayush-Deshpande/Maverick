# Part XVIII — Implementation Roadmap

*Ten phases, each with a deliverable, a dataset, a model, a metric, and a clear definition of done.*

---

## 18.1 Sequencing principle

Each phase must produce something **demonstrable on its own**. No phase may depend on a later one. The order follows the data: you cannot detect anomalies before you have telemetry, and you cannot predict RUL before you can measure health.

✅ Cross-check against the PS's required deliverables: functional prototype, digital twin architecture design, engine simulation model, AI/ML anomaly detection module, visualisation dashboard, demonstration on simulated or real datasets, technical documentation and deployment roadmap.

---

## Phase 1 — Telemetry pipeline

| | |
|---|---|
| **Build** | Synthetic generator (environment + healthy physics), CAN framing over `vcan0`, MAVLink-style downlink over UDP with configurable impairments, GCS ingestion, storage |
| **Dataset** | Ours, healthy only |
| **Model** | None |
| **Output** | Live telemetry flowing source → CAN → link → GCS → database |
| **Metric** | End-to-end latency; zero data loss on a clean link; correct gap marking at 5% loss |
| **Needs** | Python, python-can, pymavlink, FastAPI, TimescaleDB, Linux `vcan` |
| **Simulated** | Everything |
| **Done when** | You can plot a live 20 Hz channel in a browser, then induce 20% packet loss and see gaps marked rather than interpolated silently |

🔶 This phase is unglamorous and is the foundation of everything. Do not shortcut the impairment simulator — it is what forces the rest of the system to be honest.

---

## Phase 2 — Engine health monitoring

| | |
|---|---|
| **Build** | Full physics model (all cylinders, oil, fuel), residual computation, per-subsystem health indices, trend computation, basic dashboard |
| **Dataset** | Ours, healthy, all flight phases and environments |
| **Model** | Physics only — no ML yet |
| **Output** | Live health indices with residuals near zero across the whole envelope |
| **Metric** | **Healthy residual mean ≈ 0 and variance bounded in every regime** |
| **Needs** | SciPy, Rotax public operating data |
| **Done when** | Flying `LADAKH_HIGH_COLD` and `THAR_HOT` both give near-zero residuals on a healthy engine |

**This phase's metric is the single most important gate in the roadmap.** If healthy residuals are biased or noisy, every downstream detector inherits the problem and you will spend later phases tuning models to compensate for a physics error ([Part X §10.4](10_digital_twin.md)).

---

## Phase 3 — Vibration analytics

| | |
|---|---|
| **Build** | Vibration synthesis, high-rate channel, windowing + FFT, order tracking with tach sync, envelope analysis, time-domain statistics, feature vector |
| **Dataset** | Ours + ✅ CWRU and Paderborn for method validation |
| **Model** | Signal processing only |
| **Output** | ~40 features/s from a kHz waveform — the 4,000× reduction |
| **Metric** | Correct order lines at known RPM; **envelope analysis detects an injected bearing fault**; validated on ✅ CWRU |
| **Needs** | NumPy/SciPy; CWRU and Paderborn downloads |
| **Done when** | An injected bearing fault appears as a clear BPFO line in the envelope spectrum, and the same pipeline reproduces a sensible result on real CWRU data |

🔶 Validating on CWRU here is worth the extra effort: it proves the signal-processing chain works on *real* vibration, which nothing else in the project can claim.

---

## Phase 4 — Anomaly detection

| | |
|---|---|
| **Build** | Sensor validity layer, EWMA control charts, Mahalanobis, PCA residuals, Isolation Forest, small autoencoder, fusion, threshold policy with persistence |
| **Dataset** | Ours (healthy for training, faults for testing) + ✅ SKAB for method validation |
| **Model** | The layered stack from [Part VII §7.6](07_anomaly_detection.md) |
| **Output** | Live anomaly score with per-sensor attribution |
| **Metric** | **False alarms per flight hour** on healthy data; detection latency on injected faults; ROC/PR curves |
| **Needs** | scikit-learn, PyTorch |
| **Done when** | <1 false alarm per 10 flight hours on healthy data, while detecting all eight injected faults |

**Report false alarms per flight hour, not per sample** ([Part VII §7.7](07_anomaly_detection.md)). A 0.1% per-sample rate at 20 Hz is 72 alarms/hour — which is why the per-sample number is misleading and the per-hour number is the one that decides usability.

---

## Phase 5 — Fault classification

| | |
|---|---|
| **Build** | Labelled dataset generation for all 8 faults, feature engineering, Random Forest baseline, gradient-boosting comparison, "unknown anomaly" handling, evidence trail |
| **Dataset** | Ours (all 8 faults, multiple severities and onsets) + ✅ Paderborn |
| **Model** | RF primary; GBM if it wins on a proper split |
| **Output** | Named fault + confidence + the residuals that drove it |
| **Metric** | **Macro F1 and per-class recall** on held-out simulated airframes. Never plain accuracy |
| **Needs** | scikit-learn |
| **Done when** | All 8 faults classified above a stated per-class recall, **sensor drift correctly separated from engine faults**, and genuinely novel inputs returning "UNKNOWN" |

**The sensor-drift row is the hard one and the valuable one.** ✅ It is a PS fault target, and misclassifying a failed thermocouple as engine destruction is precisely the error the system exists to prevent ([Part VII §7.5](07_anomaly_detection.md)).

---

## Phase 6 — RUL prediction

| | |
|---|---|
| **Build** | Health index construction, degradation trend fitting, linear/exponential extrapolation with prediction intervals, particle filter, optional GRU |
| **Dataset** | ✅ C-MAPSS (method validation) + ✅ XJTU-SY (vibration RUL) + ours (run-to-failure) |
| **Model** | Extrapolation baseline → particle filter → GRU only if it wins |
| **Output** | RUL in hours with a confidence interval and a visible trend line |
| **Metric** | RMSE, ✅ **asymmetric score**, ✅ **prognostic horizon** |
| **Needs** | scikit-learn, PyTorch, C-MAPSS and XJTU-SY downloads |
| **Done when** | RUL reported with intervals; C-MAPSS numbers comparable to published baselines; the dashboard shows the degradation trend underneath every RUL figure |

⚠️ **Build the extrapolation baseline first and keep it.** ✅ The team's own breakdown already notes that simple extrapolation is an honest starting point and that a number without a visible trend is not RUL. A neural model must beat the baseline on a proper split to justify itself.

---

## Phase 7 — Digital twin integration

| | |
|---|---|
| **Build** | Unified `TwinState`, Kalman/complementary state estimation, staleness tracking, degradation history, all consumers reading from twin state |
| **Dataset** | All previous |
| **Model** | Integration of Phases 2–6 |
| **Output** | One authoritative state object driving everything |
| **Metric** | **The deletion test** — remove the dashboard and detection still works; graceful degradation under link loss |
| **Done when** | Cutting the link shows STALE with widening uncertainty (never a frozen value), and disabling the 3D view changes nothing functional |

---

## Phase 8 — Mission simulation and replay

| | |
|---|---|
| **Build** | Physics model as a pure function on hypothetical inputs, mission profile definition, trajectory prediction, go/no-go logic, replay engine with seek-to-event |
| **Dataset** | Stored flights from earlier phases |
| **Model** | Reuses the Phase 2 physics |
| **Output** | What-if trajectories, go/no-go verdicts, scrubable replay |
| **Metric** | **Identical degradation under two environments gives different verdicts**; replay is bit-for-bit deterministic |
| **Done when** | The `LADAKH` / `THAR` paired scenario produces different go/no-go outcomes from identical engine state, and replaying a flight twice gives identical twin states |

🔶 That paired scenario is the strongest single demonstration in the project, because it proves the simulation is physics-driven rather than scripted ([Part XI §11.4](11_mission_simulation.md)).

---

## Phase 9 — Edge deployment

| | |
|---|---|
| **Build** | Split the edge process onto separate hardware, quantise the edge model, event-driven telemetry, "on request" detail tier, onboard logging and backfill |
| **Dataset** | Live from the generator |
| **Model** | Quantised versions of Phase 4 models |
| **Output** | A physically separate edge unit that survives link loss |
| **Metric** | Edge inference latency and memory; **full function with the link severed**; bandwidth actually used vs budget |
| **Needs** | Raspberry Pi class ⬜ ([Part XVI §16.12](16_tech_stack.md)) |
| **Done when** | Unplugging the network cable leaves the edge detecting and logging, and reconnecting backfills the gap |

---

## Phase 10 — Integrated demonstration

| | |
|---|---|
| **Build** | End-to-end scenario, advisory generation, RAG over public manuals, mission reports, presentation narrative |
| **Dataset** | Full scenario library |
| **Model** | Everything integrated |
| **Output** | The complete demonstration in [Part XXI](21_end_to_end_scenario.md) |
| **Metric** | ✅ Every PS requirement visibly demonstrated, per the team's own judge-expectation table |
| **Done when** | The full narrative — normal → degradation → detection → diagnosis → prediction → advisory → replay — runs unassisted |

---

## 18.2 Dependencies

```
 P1 Telemetry
     │
     ▼
 P2 Health monitoring  ◀──── the critical gate: residuals must be clean
     │
     ├──────────────┬──────────────┐
     ▼              ▼              │
 P3 Vibration   P4 Anomaly         │
     │              │              │
     └──────┬───────┘              │
            ▼                      │
     P5 Classification             │
            │                      │
            ▼                      │
        P6 RUL ◀───────────────────┘
            │
            ▼
   P7 Twin integration
            │
      ┌─────┴─────┐
      ▼           ▼
 P8 Mission   P9 Edge
      └─────┬─────┘
            ▼
   P10 Integrated demo
```

🔶 Phases 3 and 4 can run in parallel. Phases 8 and 9 can run in parallel. Everything else is sequential, and **Phase 2 gates everything** — its residual-quality metric is the one that determines whether later phases are building on sand.

---

## 18.3 Priority under time pressure

⬜ If time runs short, this is the order in which to sacrifice things — derived from ✅ the team's own mandatory/optional table.

**Must have — cannot present without these:**

| Item | PS requirement |
|---|---|
| Telemetry pipeline (P1) | "Real-time data ingestion capability" ✅ |
| Physics twin with residuals (P2) | "Virtual engine model synchronized with live data" ✅ |
| Anomaly detection (P4) | "Anomaly detection algorithms" ✅ |
| Fault classification for all 8 (P5) | The 8 named fault targets ✅ |
| RUL with trend and interval (P6) | "Remaining Useful Life estimation" ✅ |
| Dashboard (part of P1/P7) | "Visualization Dashboard" ✅ |
| Mission simulation (P8) | "Simulating engine behavior under different conditions" ✅ |
| Replay (P8) | "Replay of historical mission data" ✅ |

**Strongly differentiating — build if at all possible:**

| Item | Why |
|---|---|
| Vibration analytics (P3) | 🔶 3 of 8 faults depend on it; most teams will skip it |
| Edge deployment (P9) | ✅ PS innovation area; demonstrates the bandwidth argument |
| Link-loss demonstration | 🔶 Proves the architecture, not just the models |
| Public benchmark validation | 🔶 Independent evidence nobody else will have |

**Cut first:**

| Item | Why |
|---|---|
| 3D visual polish | ✅ Explicitly cosmetic; the team's own doc flags it as scope creep |
| Photorealistic terrain | ✅ Same |
| Voice interface polish | ✅ Same |
| Transformer/GNN RUL | 🔶 Data-starved; no demonstrable gain ([Part IX](09_rul_prognostics.md)) |
| Onboard classification | 🔶 Optional per [Part XIII](13_edge_vs_ground_split.md) |

---

## 18.4 Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Physics model inaccurate → biased residuals | **High** — poisons everything downstream | Phase 2 gate; calibrate on healthy data; monitor residual bias |
| Synthetic data too easy → inflated metrics | **High** — credibility collapse under questioning | Unseen parameters in test; ✅ cross-validate on public benchmarks |
| Vibration synthesis unrealistic | Medium | ✅ Validate the pipeline on CWRU/Paderborn |
| Over-investment in 3D | Medium | Hard time-box; PS requirements first |
| Database/infra time sink | Medium | ⬜ Fall back to SQLite + Parquet |
| Claiming accuracy we cannot support | **High** — a domain judge will find it | Evidence labels throughout; state limitations first |
| Scope creep into autonomy/control | Medium | ⬜ We are STANAG LOI-2: advisory only |

🔶 The last-but-one deserves emphasis. The failure mode that would most damage this project in front of a DRDO evaluator is not an unimpressive number — it is an impressive number that cannot be defended. Every metric we present should come with the split, the dataset, and the caveat already stated.

---

**Next:** [Part XIX — Evaluation](19_evaluation.md)
