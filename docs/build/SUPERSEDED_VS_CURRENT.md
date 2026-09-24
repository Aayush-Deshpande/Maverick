# Superseded vs Current — What to Wire, What to Retire

*Read this before wiring, extending, or "fixing" anything. Companion to `MENTAL_MODEL.md` §7 (traps). Each of the eight entries below is a confirmed pair — verified by reading both files and tracing every importer, not guessed — where an old implementation and a new/better one coexist, and only one should end up wired into the live system.*

**Verdict legend:**
- **WIRE** — this is the current, correct implementation. Point live callers at it.
- **RETIRE** — this is the old implementation. Stop extending it; remove it once nothing depends on it.
- **BUILD** — neither existing implementation is the target; the real target doesn't exist in code yet.

---

## S01 — Sensor data source: the plant/twin circularity

| | Old | New |
|---|---|---|
| File | `backend/telemetry/can_streamer.py` (`TelemetryStreamer`) | `backend/plant/virtual_engine.py` (`VirtualEngine`) |
| Status today | **LIVE** — `engine_service.py` imports it directly | **HARNESS + opt-in** — used by `evaluation/harness.py`; reachable in the live service only via `backend/plant/adapter.py`, gated by env var `ANUMAAN_USE_INDEPENDENT_PLANT` (default `"0"`, i.e. off) |
| The problem | Generates "actual" sensor readings **from the same equations the twin uses as its expectation**, plus injected fault deltas. Every accuracy/detection number computed against it measures self-agreement with the generator, not diagnosis of anything. This is documented in the module's own history — see `IMPLEMENTATION_LOG.md` "G01". | Genuinely independent: its own crank/turbo/induction/fuel/injector/oil physics, build-to-build variation, and a sensor model (bias, lag, noise, quantisation) the twin has no access to. `truth()` is a separate method from the sensor-frame output, so wiring ground truth into a detector by accident is structurally harder. |
| Verdict | **RETIRE** (but not yet — faults 5–8 aren't modelled in `VirtualEngine` yet, see below) | **WIRE**, but the wiring is currently a stopgap, not the target state |
| **Why the adapter is off by default (deliberate)** | `plant/adapter.py`'s own docstring: enabling it changes the residual distribution the RF was trained on, silently invalidating the published 0.9751 accuracy with no replacement number. Do not flip it without retraining and re-publishing both figures. | — |
| **New, additive route (B1.1/B1.2)** | `backend/sources/plant_source.py` emits `(Frame, TruthRecord)` straight from `VirtualEngine`, bypassing both the legacy streamer and the adapter. Not on the live path yet; it is what B1.3/B1.4 will consume. | — |
| What "wiring it" currently means | `plant/adapter.py` bridges `VirtualEngine` into the live service for **nominal flight and faults 1–4 only**; faults 5–8 and channels other than core thermal/pressure/RPM still pass through the old streamer untouched. | — |
| Also depend on the old streamer | `backend/telemetry/dataset_fusion_engine.py` (TEST-only, imports `TelemetryStreamer` directly) and `backend/telemetry/rotax_dataset_generator.py` (the RF's training-data generator — meaning **the live RF classifier's 97.5% accuracy figure was measured against this same circular source and is not a trustworthy number**, per `IMPLEMENTATION_LOG.md`) | — |
| The real target (backlog) | Not "flip the adapter's env var default to 1" as a quick fix — that's a stopgap improvement, still leaving faults 5-8 circular. The actual target is **B1.5**: extend `VirtualEngine` to cover the *full* FMECA fault library (see S02), taxonomised as mode × location rather than 8 hardcoded classes, then make it the *only* source, deleting `TelemetryStreamer` and its two dependents entirely. | |

## S02 — Fault taxonomy: 8 hardcoded classes vs 20 MIL-STD-1629A modes

| | Old | New |
|---|---|---|
| File | `backend/telemetry/can_streamer.py` — `DRDO_FAULT_DEFINITIONS` dict (8 entries, IDs 0–8) | `docs/reliability/fmeca.json` + `backend/reliability/fmeca.py` (20 failure modes, MIL-STD-1629A derived) + `docs/reliability/isolability.json` |
| Status today | **LIVE** — this is the fault-ID space every live component uses: `DetectionPipeline`'s majority-vote buffer, `RotaxFaultClassifier`, the RF model's training classes, the Blender client's `target_mesh` mapping | **DOC-only** — produces the FMECA document and isolability matrix; nothing in the live path reads from it |
| The problem | Faults are *chosen* (someone picked 8 things to simulate), each is hardcoded to a specific cylinder (e.g. fault 1 is *always* "CYLINDER_2_CHT_OVERHEAT" — an overheat on cylinder 3 isn't a representable class at all), and there's no traceability to why these 8 and not others. | Faults are *derived* from a systematic failure-mode analysis, each with severity, occurrence, detectability, an isolability signature, and — critically — the isolability matrix proves which fault *pairs* are indistinguishable on the current sensor set (e.g. misfire ≡ injector needle stick on today's channels). |
| Verdict | **RETIRE** | **WIRE** (via B5.3's diagnostic Bayesian network, generated from the FMECA + isolability files) |
| The trap | Don't just add FMECA-derived fault names as *more entries* in `DRDO_FAULT_DEFINITIONS` — that keeps the "one fault ID = one hardcoded location" design flaw. The FMECA's own structure (mode × location as separate fields) is the fix; the taxonomy needs replacing, not extending. | |

## S03 — Prognostics/decision: two unrelated RUL and Go/No-Go systems

| | Old | New |
|---|---|---|
| File | `backend/ml/rul_estimator.py` — `RULEstimator` (hardcoded component lifetimes × stress multipliers) and `MissionGoNoGoAdvisory` (a simple margin-check: planned hours vs estimated RUL hours → GO/CAUTION/NO_GO) | Three separate pieces, all built independently: `backend/evaluation/damage_accumulation.py` (rainflow + Miner's rule physics-of-failure damage), `backend/evaluation/conformal.py` (split conformal prediction intervals + ACI), `backend/evaluation/prognostic_metrics.py` (PH/α-λ/RA/convergence, NASA library port); and separately `backend/mission/reliability.py` — `MissionReliabilityEngine` (Monte Carlo mission reliability with a Wilson score interval, GO/MARGINAL/NO-GO) + `backend/mission/prescriptive.py` (derate ladder) |
| Status today | **LIVE** — this is literally the RUL number and Go/No-Go verdict shown in the demo today | **ALL ORPHAN, and UNTESTED** — none of the new-side files is imported by anything live, and (verified 24 Sep) **none has any pytest coverage**: their "verified" results in `IMPLEMENTATION_LOG.md` came from ad-hoc runs at the time, not committed regression tests |
| The problem | `RULEstimator`'s component lifetimes (`Cylinder_Head_Assembly: 450.0` hours, etc.) are made-up starting points with a stress multiplier — not a physics-of-failure model, not validated against anything, and not the same "RUL" concept the new pieces implement at all. `MissionGoNoGoAdvisory`'s margin check has no uncertainty quantification and no notion of *which component* is limiting beyond whatever `RULEstimator` reports. | The new pieces were each built and checked (see `IMPLEMENTATION_LOG.md` session entries for each — by ad-hoc runs, not committed tests), but **were never assembled into one estimator** — nobody wrote the code that (a) calls damage_accumulation to get a physics-based RUL, (b) calls a data-driven RUL path, (c) wraps both in conformal intervals, (d) checks them against each other (the "dual-path disagreement alarm," D18), and (e) feeds the result into `MissionReliabilityEngine`. |
| Verdict | **RETIRE** `RULEstimator` and `MissionGoNoGoAdvisory` entirely | **WIRE + FINISH BUILDING** — the pieces exist but the assembly (backlog **B6.1**, **B6.2**) does not |
| The trap | This is the clearest "half-done, not obviously so" case in the repo. Someone skimming file names might think RUL/prognostics is "done" (4 real files, real algorithms, real tests) when in fact **there is no single RUL estimator that combines them**, and the one that's live is the crude placeholder. Don't wire `damage_accumulation.py` output directly into the live UI as-is either — it still needs the dual-path assembly and conformal wrapping first, per D18. | |

## S04 — Fault classification logic: a dead duplicate

| | Old/dead duplicate | Live version |
|---|---|---|
| File | `backend/ml/fault_classifier.py` — `RotaxFaultClassifier.classify()` | `backend/ml/detection_pipeline.py` — `DetectionPipeline._classify()` (inline, same file) |
| Status today | Exported from `backend/ml/__init__.py`, exercised **only by `tests/test_ml_classifier.py` and `tests/test_rotax_dataset.py`** — never instantiated by `engine_service.py` or anywhere else in the live path | **LIVE** |
| The problem | Both files independently implement **the identical 8-fault physics-boundary sigmoid scoring logic** — same magic-number thresholds (`d_CHT_2 > 12.0`, `actual.CHT_2 > 125.0`, the same sigmoid formula), copy-pasted rather than shared. `detection_pipeline.py`'s own comment even says "Physics boundary fallback (same logic as RotaxFaultClassifier)" — acknowledging the duplication in a comment rather than removing it. | — |
| The real risk | If someone "fixes a threshold" in one file during a future session (plausible — the thresholds are placeholders per S02's taxonomy problem), the other file silently keeps the old, now-wrong value, and nobody notices because they never run side by side. | — |
| Verdict | **RETIRE** `fault_classifier.py`'s duplicated rule logic entirely | Keep the inline version **only until B5.3** (the diagnostic Bayesian network) replaces both — this hardcoded-threshold rule engine is *itself* a placeholder for the FMECA-derived taxonomy in S02, not a long-term design |
| Note | `RotaxFaultClassifier.DiagnosticResult` dataclass shape may still be useful as a reference for API design when building the real diagnosis output (`Hypothesis` in `INTERFACES.md` §7) — don't delete the whole file blindly, but don't wire its `classify()` method into anything live either. | |

## S05 — Vibration analysis: RMS-scalar DFT vs the (unbuilt) 51.2 kHz DSP core

| | Old | Target (not built) |
|---|---|---|
| File | `backend/ml/spectral_analyser.py` — `GearboxSpectralAnalyser` | `backend/dsp/` package per `docs/audit/09` §4.2 (order tracking, envelope analysis, order-frequency spectral correlation) — **does not exist yet** |
| Status today | **LIVE** — Stage 4 of `detection_pipeline.py`, running on the 20 Hz `VIB_GEARBOX_RMS` scalar | **BUILD** — this is 0% implemented, tracked as backlog **B3.3–B3.4** |
| The problem | Its own module docstring is explicit about the limitation: "at 20 Hz the Nyquist frequency is 10 Hz, while the engine's actual vibration harmonics (~103 Hz at 5000 RPM) are far above that." The module has a documented, deliberate RMS-threshold fallback for exactly this reason — it is not broken code, it's a correct implementation of a design that was already known to be inadequate when it was written. | Per `docs/audit/09` §2, real diagnostic content (combustion resonance, injector/valve impacts, bearing envelope carriers) lives in the 5.6–20 kHz band, requiring 51.2 kHz sampling — a completely different acquisition chain, not a parameter tweak to the existing one. |
| Verdict | **RETIRE once the new DSP core covers its one real function** (the 3rd-harmonic gearbox early-warning check) — until then, leave it running as the best available approximation | **BUILD** (this is new-build work, not a wiring task — there is no "new version sitting unwired" to point to here, unlike S01–S04) |
| The trap | Don't try to "fix" this by bumping `sample_rate_hz=20.0` to a higher number without also (a) actually producing higher-rate synthetic vibration data from the plant (backlog **B2.3**), and (b) rebuilding the feature extraction around angle-domain resampling rather than a fixed-window FFT. A parameter change alone would silently produce meaningless numbers on data that still doesn't contain the target frequencies. | |

## S06 — Engine model: hardcoded constants vs the config system

| | Old | New |
|---|---|---|
| File | `backend/physics/thermo_model.py` — `RotaxThermoModel`, with Rotax 912 iS constants defined at module level | `backend/physics/engine_config.py` + `configs/engines/*.json` (5 engines, per-field provenance as of B0.4) |
| Status today | **LIVE** — this is the twin's "expected state" calculation in the live pipeline | **TEST-only-ish** — `turbo_model.py` and `plant/virtual_engine.py` consume it; `thermo_model.py` does not |
| The problem | The whole point of `engine_config.py` (F31, "engine class as configuration") is that switching the engine the twin models should be a config change, not a code change. `thermo_model.py` was never updated to read from it, so the "5 engine configs" capability is real for the *plant* side but not for the *twin* side — the twin can only ever model a Rotax 912 iS regardless of which config is loaded. | — |
| Verdict | **RETIRE** the hardcoded constants | **WIRE**, and this is exactly the job of backlog **B4.1** (the differentiable/dynamic thermofluid model), which replaces `thermo_model.py`'s algebraic expectation with a config-driven dynamic model anyway — so this isn't a small patch, it's subsumed by a bigger rebuild already on the backlog. |

---

## S07 — "Conformal" RUL intervals: a fake in the live path, the real one orphaned

| | Old (fake) | New (real) |
|---|---|---|
| File | `backend/ml/rul_estimator.py` — `RULEstimator.get_conformal_rul()` | `backend/evaluation/conformal.py` — split conformal (finite-sample `ceil((n+1)(1-a))/n` quantile), normalised scores, `AdaptiveConformal` (ACI), `empirical_coverage()` |
| Status today | **LIVE** — `engine_service.py:595` puts its output in the state the UI shows | **ORPHAN**, no pytest coverage |
| The problem | The docstring said "split-conformal... guarantees 1-alpha coverage" and it emitted `coverage_guarantee: "90% Conformal Calibration"`. The code is a fixed 12 % margin + 18 % x anomaly score: no calibration set, no non-conformity scores, `significance_level` does not change the bounds. Coverage was never measured. A reviewer asking "how was this calibrated?" would find nothing. The test (`test_conformal_rul_prediction_intervals`) only checked `p10 <= p50 <= p90`, so it gave false assurance. | Correct method; measured 0.902 coverage vs 0.900 nominal on synthetic data (ad-hoc run, IMPLEMENTATION_LOG F12). Not yet run against a real estimator or under distribution shift. |
| Verdict | **Label corrected 24 Sep**: now `calibrated: False`, `coverage_guarantee: "None -- uncalibrated heuristic margin (not conformal)"`, docstring rewritten, test pins it. Numbers unchanged. **RETIRE** together with `RULEstimator` (B6.1). | **WIRE** in B6.1 (wrap both RUL paths) and B5.2 (detector thresholds) -- after characterization tests exist (B0.9) |
| The trap | Do not "restore" the old label because the UI text looks nicer. And do not assume the name of a method or a test tells you what it does -- this one had both wrong. | |

## S08 - Detector strategy: one Rotax-trained RF vs the calibrated-residual detector bank

| | Old | New |
|---|---|---|
| Where | `ml/detection_pipeline.py` Stage 3/6 (autoencoder 14-8-4-8-14, RF trained on the circular 912 iS generator) | `backend/detect/` (W1/W2, to be built; prototype in `experiments/E17`) |
| Problem | Trained on one engine's generator (2 Sep); 4-cylinder feature names; accuracy is self-agreement | Per-tail calibration + universal Mahalanobis/max\|z\|; classifier registry (universal default, per-engine override) |
| Verdict | **RETIRE** after W1/W2 | **BUILD** (evidence: `DETECTOR_DECISION.md`) |
| Trap | Do not "retrain the RF on the plant" and call it universal - the features and channel names are 4-cylinder Rotax; build the n_cyl-agnostic features first | |

## Summary table

| ID | Old (retire) | New (wire) | Currently wired? | Backlog item that finishes it |
|---|---|---|---|---|
| S01 | `can_streamer.TelemetryStreamer` | `plant.virtual_engine.VirtualEngine` | Partially (faults 1-4 only, opt-in flag) | B1.5 |
| S02 | `can_streamer.DRDO_FAULT_DEFINITIONS` (8 hardcoded) | `reliability/fmeca.py` (20 modes) | No | B5.3 |
| S03 | `ml/rul_estimator.py` (both classes) | `evaluation/{damage_accumulation,conformal,prognostic_metrics}.py` + `mission/reliability.py` | No — pieces exist unassembled | B6.1, B6.2 |
| S04 | `ml/fault_classifier.RotaxFaultClassifier` | (dead duplicate of live inline logic — no "new" side yet) | N/A — delete the duplicate | B5.3 (both sides get replaced) |
| S05 | `ml/spectral_analyser.py` | `backend/dsp/` (doesn't exist) | N/A — nothing to wire, must be built | B3.3, B3.4 |
| S06 | `physics/thermo_model.py` constants | `physics/engine_config.py` | No | B4.1 |
| S07 | `RULEstimator.get_conformal_rul` (fixed-margin heuristic, was mislabelled conformal) | `evaluation/conformal.py` (real) | No (label corrected 24 Sep) | B6.1, B5.2 |
| S08 | Rotax-trained RF + autoencoder in the live pipeline | `backend/detect/` calibrated-residual detector bank (unbuilt) | No | W1, W2 |

**Rule of thumb going forward:** before extending any file in the "Old" column above, check this table. If your task is in the "Backlog item" column, that's the real scope — it's usually bigger than just "wire A to B," because the new side is often incomplete on its own (S02, S03) or doesn't exist yet (S05).
