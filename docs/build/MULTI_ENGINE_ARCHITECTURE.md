# Multi-Engine Runtime Architecture — Simulators, Fault Injectors, Detectors, Levers, Waveform Edge

*Design record, 24 September 2026. Answers: how do simulators, fault injectors and detectors fit together for several engines at once; is a "lever" that changes readings a good idea; how does the dropdown switch instantly; where do recorded waveforms and the Raspberry Pi 5 edge node fit. Decisions D29, D30, D34 in [`DECISIONS.md`](DECISIONS.md); backlog tiers E13/E14 in [`BACKLOG.md`](BACKLOG.md); detector choice in [`DETECTOR_DECISION.md`](DETECTOR_DECISION.md); profile mechanism in [`UNIVERSALITY_AUDIT.md`](UNIVERSALITY_AUDIT.md). Nothing here is built yet unless stated.*

---

## 1. The mental model in one picture

```
                         ┌────────────────────────── RuntimeHub (one process) ─────────────────────────┐
  dropdown ───────────►  │  EngineRuntime[rotax_912is]  EngineRuntime[rotax_914]  EngineRuntime[rotax_915is] │
  (selects which stream  │  EngineRuntime[austro_ae300] EngineRuntime[vrde_crdi] ...   ← ALL run, always     │
   the UI subscribes to) │                                                                                  │
                         │   each EngineRuntime =                                                           │
                         │     Simulator(profile)  ──► Frame @ 20 Hz ─┬─► ring buffer (last N min)          │
                         │        ▲        ▲                          ├─► ScalarDetectorBank(profile)       │
                         │        │        └── FaultInjector hooks    │        └─► Evidence ─► Diagnosis    │
                         │   levers (throttle, alt, OAT, dust)        ├─► EdgeNode(profile)  ◄─ waveforms   │
                         │   fault levers (mode×loc×severity)         │        └─► HealthFrame (scalars)    │
                         │   sensor levers (bias/stuck/spoof)         └─► TruthRecord (evaluation only)     │
                         └──────────────┬───────────────────────────────────────────────────────────────────┘
                                        │ REST /api/engines/{id}/…   WS /ws/engines/{id}   WS /ws/fleet
                                        ▼
                                 React GCS · Blender viewport (asset variant per profile)
```

**Principle (D29):** *all engines simulate continuously; the dropdown only changes which one you are looking at.* Nothing restarts, nothing reloads — which is why it is instantaneous — and a **fleet view** can show every engine's health at once.

## 2. Is it affordable to run everything at once? (measured)

| Quantity | Measured 24 Sep |
|---|---|
| Plant `step()` time, all 5 engine configs | **0.12–0.15 ms** |
| 5 engines × 20 Hz | 100 steps/s ≈ **12–15 ms of CPU per second (~1.2 % of one core)** |
| Calibrated-residual detector | 344 µs features + 7 µs Mahalanobis per frame |
| 5 engines × 20 Hz detectors | ≈ 35 ms/s (3.5 % of a core) |
| sklearn RF, one row | **11.5 ms** ⇒ only on flagged frames, batched (`DETECTOR_DECISION` §3C) |

Conclusion: a laptop runs dozens of engines; concurrency is **not** the constraint. The constraint is engineering discipline (per-engine state isolation, deterministic seeds, no global singletons).

## 3. Today vs target (audit of the current runtime)

| Aspect | Today (verified) | Target |
|---|---|---|
| Runtime | `EngineStateService` **singleton**, one worker thread, one `TelemetryStreamer`, `/ws/telemetry` has **no engine parameter** | `RuntimeHub` holding one `EngineRuntime` per profile |
| Simulator | Circular streamer (twin equations + fault deltas) live; independent `VirtualEngine` only via opt-in adapter | `PlantSource(profile)` for every engine (D04, S01) |
| **Levers** | `SET_THROTTLE/ALTITUDE/OAT` **overwrite displayed fields after the frame is generated** (gap G02, still open) — cosmetic. Only `SET_REGIME` affects physics | Levers feed the plant's *inputs*; it already responds physically (`VirtualEngine.step(throttle_pct, altitude_ft, oat_c, dust)` — used with 7 operating points in E17) |
| Fault injection | `SET_FAULT` with legacy fault IDs 0–8 (cylinder-pinned) | Registry keyed by FMECA mode × location, filtered by the selected profile's `applicable_fault_modes()` |
| Detection | One pipeline, one RF/AE trained on Rotax 912 iS | Per-profile calibration + universal detector bank (D31) |
| Assets | One Rotax blend | Profile → asset variant map (§8) |
| Plant physics | Rotax-shaped internally (F21) | Config-driven rpm map / thermal targets (R6) |

## 4. Fault injection and "levers" — the answer

You asked whether a direct input that lets the user change readings via levers is a good idea. **Yes — but as three layers with one forbidden shortcut**, and every layer writes to the truth log.

| Layer | Lever | Acts on | Why it is legitimate | Exists today? |
|---|---|---|---|---|
| **L1 Operating** | throttle, altitude, OAT, dust, mission regime | plant *inputs* | This is how an operator really changes readings: through the physics, with lags and transients | Plant: ✅. Live service: ❌ cosmetic (G02) |
| **L2 Fault** | mode × location × severity × ramp (from the profile's applicable modes) | plant *physical parameters* via `inject_fault` | Faults must be causes, never edited outputs (PS-derived rule, doc 17 §17.1) | Plant: ✅ 12 fault names. Registry/UI: ❌ |
| **L3 Sensor** | bias, drift, stuck-at, noise, dropout, spoof | `SensorModel` (between physics and frame) | Sensor faults are a named PS target (FDP-06); this is where *sensor-vs-engine* discrimination is tested | Plant: ✅ `SENSOR_BIAS_DRIFT`, `SENSOR_STUCK`. Others ❌ |
| **L4 Direct reading override** | "set CHT₂ = 180" | the frame, bypassing plant and sensor model | ⚠️ **Not a normal path.** It creates physically inconsistent frames. Allowed *only* in an explicit **detector test-bench** mode, e.g. to demonstrate the physics-integrity/spoof detector | ❌ (build as test-bench only) |

**Rules that make levers safe (D30):**
1. Every injection is recorded in the `TruthRecord` with `origin ∈ {SCENARIO, MANUAL_LEVER, TESTBENCH_OVERRIDE}`. Runs containing `MANUAL_LEVER` or `TESTBENCH_OVERRIDE` are **excluded from accuracy/false-alarm KPIs** (otherwise the demo silently pollutes the evidence).
2. The UI shows only faults valid for the selected engine (a diesel has no spark misfire; an NA engine has no wastegate).
3. Sliders are rate-limited and go through the plant's first-order dynamics — a throttle step gives a transient, not an instant jump (the acceptance test from G02).
4. The detectors never see levers or truth — only `Frame`s (`tests/test_no_truth_leak.py` already enforces the inference side).
5. **Hooks/triggers:** injectors register themselves — `register_fault(mode, applies_to=lambda profile: …, apply=lambda plant, params: …, clear=…)`. The UI, the API schema and the FMECA all read from this registry; adding a fault is one registration, not edits in five files.

**Why this is also the best demo feature:** a judge moves a slider, and *lead time* becomes visible — the twin flags cooling degradation minutes before the conventional redline monitor, live, on any engine.

## 5. Detector bank per engine

Per `EngineRuntime`, in order of cost (all engine-agnostic code; only the calibration is per-engine):

| Tier | Component | Cost | Runs |
|---|---|---|---|
| 0 | Sensor sanity / integrity gate (`sensor_validator`, `twin/integrity`) | µs | every frame |
| 1 | **Calibrated-residual detector**: per-tail regression on the commanded operating point → z-residuals → Mahalanobis + max\|z\|, conformal thresholds | ~350 µs | every frame |
| 2 | **Classifier registry**: universal RF/GBM (+ engine-class flags), per-engine override if present; batched | ms | only when tier 1 flags, or every k-th frame |
| 3 | Diagnostic Bayesian network over evidence, ambiguity groups (D11) | ms | on new evidence |
| W | **Waveform / edge channel** (§7): per-cylinder and spectral evidence for what scalars cannot see | see §7 | per engine cycle |

Calibration lives with the tail: `{engine_serial: {ridge coefficients, sigma, calibration window, date, git commit}}` (a D28 sidecar), regenerated after maintenance events.

## 6. API (proposed)

`GET /api/engines` · `GET /api/engines/{id}/schema` (channels, units, limits, applicable faults, levers, asset variant) · `GET /api/engines/{id}/state` · `WS /ws/engines/{id}` (engine stream; replaces `/ws/telemetry`) · `WS /ws/fleet` (one summary row per engine at 1 Hz) · `POST /api/engines/{id}/levers` (L1/L3) · `POST /api/engines/{id}/faults` / `DELETE …` (L2) · `POST /api/engines/{id}/testbench/override` (L4, guarded). The old single-engine routes stay as aliases to the *selected default engine* during migration.

## 7. Waveforms and the Raspberry Pi 5 edge node

**The idea (yours, kept):** an onboard edge computer watches the raw waveforms; **only if an anomaly persists** does it engineer features and send *scalars* to the ground. That is the right split — and the probe in `DETECTOR_DECISION` §4 shows why it is necessary: injector and rail faults exist *only* in the waveform.

```
 WaveformSource ──► EdgeNode (Pi-5-class: 4 cores @ 2.4 GHz, memory-capped, emulated in software)
  • plant crank/rail signal (now)        tier 0  always-on cheap gate  ── compact spectral features (order bins, kurtosis, RMS)
  • synthesised 51.2 kHz (E2)                     Mahalanobis on ~30 numbers   [or FlyHash-FBF if it wins W5]
  • dataset replay: CWRU 12/48 kHz,       persist  M-of-N over K cycles + hysteresis  (one noisy cycle ≠ alarm)
    Paderborn 64 kHz, (3500-DEFault)      tier 1  ONLY on persistence: engineer features
  • recorded .npz + manifest                       per-cylinder torque deficit, order features, envelope indices, kurtosis, trims
                                          out     HealthFrame v2 (≤ 64 bytes of scalars) + optional raw snippet on request
                                                       │ link emulator (1–20 kbit/s, loss, jamming, store-and-forward)
                                                       ▼
                                          Ground ScalarDetectors + Bayesian network (same code as §5)
```

- **Recorded waveforms are a first-class asset.** A `WaveformRecorder` writes `.npz` + manifest (engine profile, fault truth incl. `origin`, rate, seed, git commit, SHA-256). Recorded runs make experiments repeatable and let the edge pipeline be regression-tested bit-exactly.
- **The Pi is emulated in software first (D23/D34):** a resource-capped process/container (4 cores, memory cap, optional per-core slowdown factor) so latency and memory are measured under constraint; a **real Pi 5 benchmark is a roadmap item (TRL)**, not a claim. Estimated Pi speed relative to this laptop: ~3–6× slower for Python — 🔶 unmeasured.
- **What runs at tier 0 is undecided by design:** Mahalanobis (proven on tabular) vs FlyHash-FBF (unproven, potentially cheaper and better on spectra) — decided by W5, not by preference.
- **"Sends scalars":** exactly the compact frame already prototyped in `backend/edge/compressor.py` (29 bytes for 4 cylinders), extended in `INTERFACES.md` §5 (HealthFrame v2).

## 8. Assets: what "blender-ready" really means today

| Engine profile | Asset | Reality (verified 24 Sep) |
|---|---|---|
| `rotax_912is`, `rotax_914`, `rotax_915is` | **one file**, `assets/blender/rotax_912_is_sport.blend` (78 MB) | Contains **one 912i base** plus *fitting sets* `Fittings_*Rotax914_*`, `External_Alternator_*Rotax914_Extras`, `Fittings_*Rotax915_*` (31 matching objects, 112 total). **No turbo/intercooler/wastegate mesh.** ⇒ the three Rotax "versions" are **variants (show/hide object sets), not three files.** |
| `austro_ae300` | `assets/models/engines/austro_ae330.blend` (821 KB, real) | AE330 ≠ AE300; use as a **proxy, labelled**. Small file — verify it is a usable mesh before relying on it |
| `vrde_jayem_2_2l` | none | needs an asset or a generic CRDi stand-in |
| `tei_pd170`, TB3 airframe, the Rotax STEP CAD folder | **Git-LFS pointer stubs (131–133 bytes) — not real files** (39 stubs) | `git lfs pull` or drop the references |

**Profile→asset map** (in each profile): `{blend, variant_objects_visible, hidden, sensor→mesh, component→mesh, camera_poses}`; switching engine toggles object visibility and re-binds faults to component meshes (replacing the hardcoded 912 iS mesh names in `DRDO_FAULT_DEFINITIONS`). The Blender client subscribes to `WS /ws/engines/{id}`.

## 9. Acceptance criteria (how we will know it works)

1. Five engines run concurrently at 20 Hz for one hour; CPU < 10 % of one core (excl. UI); no cross-engine state leakage (test: a fault on engine A never alters engine B's frames).
2. Switching the dropdown changes the visible stream within one frame period (50 ms) with no reload; `/ws/fleet` shows all five.
3. Selecting a diesel shows no spark faults; selecting an NA engine hides turbo faults (registry filter test).
4. A throttle step produces a transient with a visible time constant (G02 done-when list) — asserted by test.
5. Same seed + same lever/fault script ⇒ bit-identical `Frame` and `TruthRecord` streams.
6. A run containing a manual lever is excluded from KPIs (test on the evaluation loader).
7. Injector coking is detected through the waveform channel while every scalar detector stays quiet (the F22 demonstration).
8. Edge emulation: tier-0 gate holds its deadline under a CPU cap; only persistent anomalies produce a HealthFrame; bytes/hour within the link budget.

## 10. Risks and open questions

| Risk | Mitigation |
|---|---|
| The plant is Rotax-shaped (F21): diesels look wrong (EGT ~1,150 °C, rpm above rated) | R6 (config-driven plant) **before** any cross-engine claim leaves the lab; write characterization tests first (B0.9) |
| Per-engine state leaks through module-level globals (`can_streamer`, `thermo_model` constants, singletons) | Runtime built only from `PlantSource`/`Frame`; ratchet test keeps globals from growing |
| CPython GIL limits true parallelism | Not needed at this load; a single scheduler thread stepping all engines deterministically is simpler and reproducible |
| Sensor-layer spoofing confuses evaluation | `origin` flag + KPI exclusion (§4 rule 1) |
| Pi timings are extrapolated | Say "emulated / estimated"; real-board benchmark on the roadmap |
| Assets missing (LFS stubs, no VRDE mesh) | Show a generic 2D schematic fallback; fetch LFS objects |

## 11. Build order (backlog tier E13, then E14)

R1 `EngineRuntime`/`RuntimeHub` → R2 fault/lever registry + `TruthRecord.origin` → R3 levers drive plant inputs (close G02) → R4 engine API + per-engine WS + fleet WS + dropdown → R5 asset variant map → R6 config-driven plant (after B0.9) → R7 sensor-layer levers → R8 load test; in parallel W1–W4 (detector bank, classifier registry, `WaveformSource`, edge emulation) → W5 bake-off decides the tier-0 detector.

## Amendment 24 Sep 2026 — heavy inference is selected-engine only (D29/D36/D37)

All engines run simulators, injectors and tier-0/1 detectors (FlyHash, Mahalanobis, reservoir readout) concurrently. Heavy models (tier-2: large reservoir, TabPFN, TimesFM/Chronos, Jev-style text model) run only for the dropdown-selected engine, or when tier-0 escalates another engine. Ground infra is assumed DRDO-class GPU. Switching warms the selected engine's cached state so the switch stays instantaneous.
