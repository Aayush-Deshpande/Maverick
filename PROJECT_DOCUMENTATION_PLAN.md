# ANUMAAN Documentation Website — Project Documentation Plan

**Purpose of this document**: a verified article hierarchy for the ANUMAAN (SIH PS-26054, Team Midnight Ciphers) documentation website, produced from a full read of the repository — code, tests, prior audits, evaluation artifacts, git history, and verification screenshots — not from assumption. This is a planning document. No website content has been written yet.

**Status note on what already exists in-repo**: `ANUMAAN_documentation_content_v1/` is a *style and structure scaffold* (writing rules, evidence discipline, diagram specs, section skeletons) produced earlier — it is not filled-in content. `docs/`, `docs/study/`, `docs/audit/`, `docs/build/`, and `REPORT/` contain the actual verified engineering substance. This plan reconciles the scaffold's structure with what the repository actually contains today (verified 2026-09-29), and corrects a few places where the scaffold's placeholders undersell or don't yet reflect recently landed work (mission planning went from "not implemented" to shipped between 2026-09-24 and 2026-09-28; FlyHash runs live per-tick in the modern runtime, not just as a tested-but-dormant module).

---

## 0. Ground truth this plan is built on

- **Two live backend pipelines coexist**, not one: a modern multi-engine `RuntimeHub` path (5 engine profiles, tier-0 residual detection with FlyHash running every tick, tier-1 reservoir classifier on the selected engine) and a legacy Rotax-912-iS-only `EngineStateService` path (richer diagnosis/RUL/agent/voice/replay, kept alive as "Legacy GCS", never to be labeled "legacy" in the UI). These are architecturally parallel, not layered — the documentation must not imply one supersedes the other yet.
- **A large fraction of the repository is real, tested, research-grade engineering that is not wired into the live demo path**: security/CAN-IDS, federated learning, waveform/high-rate DSP (order tracking, envelope analysis, crank-angle reconstruction), prognostics/RUL. This is not padding — competitively, it is the project's strongest differentiator (see §5) — but it must be labeled by actual reachability, not folder presence. Not everything in this category is equally disconnected: direct code inspection shows `backend/diagnose/bn.py` (Bayesian diagnosis) is in fact heavily wired into the modern RuntimeHub path (`engine_runtime.py`, `evidence_adapter.py`, `explain.py`, `maintenance/work_package.py`) and FlyHash runs live, per-tick, in both the legacy and modern pipelines — the documentation must verify reachability per-module at publish time rather than trust any single older snapshot, including this one.
- **Dataset adapters synthesize data**; they do not parse the real public files they are named after (confirmed directly in `aces.py`, `cmapss.py`, `cwru.py`). This must never be presented as external validation.
- **Mission planning is newly real**, not aspirational: `MissionExecutive`, kinematics, reliability (Monte Carlo hazard-rate `R(t)`), prescriptive advisory, and a 3-tab Planner/Simulation/Debrief UI landed 2026-09-24→28, with Playwright-verified screenshots. It is cleanly RuntimeHub-only — `backend/server/mission_api.py` calls `get_hub()` directly, with no legacy fork — which is architecturally simpler to document than the split elsewhere in the system.
- **The 3D/physics multi-engine story has a real, self-documented gap worth stating precisely, not softening**: `backend/runtime/registry.py` and `configs/engines/` support 5 engines end-to-end at the runtime/config level, and all 5 have Draco GLBs and Blender scenes — but the core thermodynamic model (`backend/physics/thermo_model.py`) is an Otto-cycle model scoped to the Rotax 912 iS, and `docs/assets/00_asset_program_overview.md` states outright that its 3D asset program (a 7-airframe, 6-engine target matrix including diesels and turbo units the current physics can't honestly drive) is "specification only, no modelling has started." So: 5 engines are *selectable*, roughly 1 of 5 is *fully physics-and-fault-wired*. This single fact should be stated once, precisely, and cross-referenced rather than repeated inconsistently across articles.
- **The team already runs an unusually rigorous self-audit discipline**: a 4-tier evidence label convention (✅ VERIFIED / 🔶 INFERENCE / ⬜ ASSUMPTION / 🔒 PROPRIETARY), a competitive audit against 15 other SIH teams that revises its own claims when wrong, and a "Digital Shadow vs Digital Twin" honesty framing (STANAG 4586 LOI 2) prepared for judge cross-examination. This culture is itself worth documenting, not just borrowing its discipline.

This plan follows the same evidence-label convention and the same maturity labels defined in the v1 scaffold (LIVE / IMPLEMENTED / PARTIAL / SIMULATED / ROADMAP), and requires them on every technical article.

---

## 1. Project map

```
PROBLEM (SIH PS-26054: predictive DT for MALE UAV aero piston engines)
   ↓
REQUIREMENTS (6 expected-solution components A–F; 8 fault/anomaly targets)
   ↓
ENGINEERING APPROACH (physics-residual core; detection → diagnosis → prognosis → mission
                       consequence as four distinct problems, not one model)
   ↓
SYSTEM ARCHITECTURE (two coexisting backend pipelines; edge/ground compute split;
                      OSA-CBM six-layer mapping)
   ↓
SUBSYSTEMS
   ├─ Digital twin & physics core        (thermo model, crank/combustion, sensor validation)
   ├─ AI/ML stack                        (FlyHash novelty, Bayesian diagnosis, RUL/prognostics)
   ├─ Mission planning & reliability     (executive, kinematics, Monte Carlo R(t))
   ├─ 3D digital twin & visualization    (Three.js, Blender, canyon flight sim)
   ├─ Operator GCS (frontend)            (modern console + legacy workspace + voice copilot)
   └─ Security, edge & fleet layer       (CAN-IDS, link emulation, federation, edge compression)
   ↓
DATA (real Rotax/engine spec constants; synthetic plant/telemetry; proxy PHM datasets;
       FMECA taxonomy; recorded mission/replay bundles)
   ↓
MODELS (physics-first residuals; sparse novelty coding; reservoir classifier; Bayesian net;
         Weibull/conformal prognostics; Monte Carlo mission-hazard model)
   ↓
SIMULATION (independent plant model; synthetic telemetry generator; canyon flight; replay engine)
   ↓
MISSION (profile/phase model; engine-aware kinematics; reliability propagation; prescriptive advisory)
   ↓
VALIDATION (evidence-label discipline; pytest suite; characterization tests; competitive audit;
             Playwright UI verification)
   ↓
DEMONSTRATION (fault-injection demo chain; mission sortie; judge Q&A; SIH journey)
```

---

## 2. Proposed site information architecture

Two top-level sections, as specified in the v1 scaffold and confirmed appropriate:

1. **Technical Documentation** — how the system works, what's real, what's evidenced.
2. **Our SIH Journey** — the engineering chronicle, evidence-backed.

Below is the full article hierarchy. Each article lists: **what it must establish**, **primary source material already in-repo**, and a **maturity/evidence note** the writer must resolve before publishing (per the four-label and five-maturity-tag conventions already established in this repo).

---

## 3. Technical Documentation — article hierarchy

### 3.1 Orientation
| # | Article | Establishes | Primary sources |
|---|---|---|---|
| 1.1 | **What ANUMAAN Is** (home/overview) | The one-sentence problem, the one-sentence approach, reader promise (4 questions every subsystem page answers) | `docs/00_official_problem_statement.md`, `README.md`, v1 `00_HOME.md`/`01_TECHNICAL_OVERVIEW.md` |
| 1.2 | **The Problem: SIH PS-26054, in Our Own Words** | Official PS text verbatim + our engineering interpretation; requirement-to-component traceability table | `docs/00_official_problem_statement.md`, `01_problem_statement_breakdown.md`, `fun_req.md` |
| 1.3 | **Digital Shadow or Digital Twin? A Precise Answer** | Honest classification under AIAA S-119 / ISO 23247 / STANAG 4586 LOI framing — leads with the project's strongest credibility move rather than burying it in a judge-defense doc | `UpdatedReport/13_judge_question_bank.md` Q1, `docs/study/10_digital_twin.md` |

### 3.2 System architecture
| # | Article | Establishes | Primary sources |
|---|---|---|---|
| 2.1 | **System Architecture Overview** | Seven-layer conceptual stack; runtime data path diagram; repo-to-architecture mapping | v1 `02_SYSTEM_ARCHITECTURE.md` (fill placeholders with real paths), `docs/study/15_system_architecture.md`, `docs/ARCHITECTURE_OSACBM.md` |
| 2.2 | **Two Runtimes, One Shell: Modern vs. Legacy GCS** | Why two backend pipelines coexist (`RuntimeHub`/modern vs `EngineStateService`/legacy), what each owns, why they aren't interchangeable, migration status | `docs/build/MENTAL_MODEL.md` §2, `docs/build/CURRENT_STATE.md` |
| 2.3 | **Edge/Ground Compute Split** | Deterministic low-latency path vs. cognitive/asynchronous path; bandwidth argument (~160 kbit/s raw vs ~122 kbit/s link) as the concrete engineering driver | `docs/study/05_edge_ai.md`, `13_edge_vs_ground_split.md`, `backend/edge/` |
| 2.4 | **OSA-CBM: Mapping Six Standard Layers Onto ANUMAAN** | ISO 13374 layer mapping as an architecture-legitimacy anchor | `backend/osacbm.py`, `docs/ARCHITECTURE_OSACBM.md` |

### 3.3 Digital twin & physics core
| # | Article | Establishes | Primary sources |
|---|---|---|---|
| 3.1 | **The Physics Core: What "Expected Behavior" Means** | Residual = observed − expected as the central interface; state vector/measurement model; what's manufacturer-sourced vs. fitted vs. assumed | v1 `03_DIGITAL_TWIN_AND_PHYSICS.md`, `backend/physics/`, `docs/study/01_big_picture.md`, `10_digital_twin.md` |
| 3.2 | **Engine Sensors, from First Principles** | Every monitored parameter, its sensor type, rate, and which faults it reveals | `docs/study/02_engine_sensors.md` |
| 3.3 | **Sensor Integrity: Telling a Broken Gauge from a Broken Engine** | Plausibility checks, residual shielding, why this distinction is safety-critical | `backend/physics/sensor_validator.py`, `backend/twin/` |
| 3.4 | **Crank-Angle Combustion Diagnostics** (flagship technical article) | Slider-crank kinematics → Wiebe heat release → cylinder pressure → ω(θ); why this replaces "asserted" synthetic misfire signatures with physics-derived ones; per-cylinder torque-deficit misfire detection | `docs/study/24_combustion_cycle_and_crank_dynamics.md`, `25_misfire_and_combustion_diagnostics.md`, `backend/ml/crank_diagnostics.py`, git commit `fd77805` |
| 3.5 | **The Independent Plant Model (G01)** | Why a second, physically independent simulator exists so residuals reflect real model mismatch, not a generator checking itself; the `ANUMAAN_USE_INDEPENDENT_PLANT` scope boundary | `backend/plant/`, `README.md` §"The independent plant" |
| 3.6 | **The DRDO 8-Fault Matrix** | The 8 canonical fault modes, sensor triggers, 3D target parts, and how they trace to the 20-mode FMECA taxonomy underneath | `README.md` fault table, `docs/reliability/FMECA.md`, `backend/reliability/` |
| 3.7 | **Order Tracking and Envelope Analysis** (flagship / competitive differentiator) | Angular resampling for varying RPM, Hilbert envelope demodulation, why fixed-frequency "2X harmonic" bins smear on a UAV that constantly changes power — and why this is genuinely rare among comparable SIH projects | `docs/study/26_order_tracking_and_envelope.md`, `docs/audit/05_expanded_survey.md` §2 |
| 3.8 | **One Physics Model, Five Engines: The Generalization Gap** | States plainly that `thermo_model.py` is an Otto-cycle model scoped to the Rotax 912 iS while `engine_config.py`/`registry.py` already support 5 engine profiles at the runtime level, and that `docs/assets/` independently documents the same gap on the 3D-asset side (diesel/turbo engines in the target matrix that current physics can't yet honestly drive). One honest article here prevents an inconsistent claim from surfacing in five different places | `backend/physics/thermo_model.py`, `backend/physics/engine_config.py`, `configs/engines/*.json`, `docs/assets/00_asset_program_overview.md` |

### 3.4 AI/ML stack
| # | Article | Establishes | Primary sources |
|---|---|---|---|
| 4.1 | **AI Is Not One Model: The Four-Layer Reasoning Stack** | Novelty detection vs. diagnosis vs. prognosis vs. advisory as four different questions requiring different models/data/metrics | v1 `04_AI_ML_AND_FLY_BRAIN.md`, `docs/study/07_anomaly_detection.md`–`09_rul_prognostics.md` |
| 4.2 | **Bio-Inspired Sparse Novelty Coding (FlyHash), Honestly Positioned** | What it is (expand-and-sparsify, FlyHash-style random projection), that it runs live per-tick in tier-0 today (not dormant), and — critically — the team's own literature-search correction that this technique is a decade-old established family, not a novel algorithm; what the actual (narrower, defensible) contribution is | `docs/study/20_novelty_and_research.md` (full honesty framing), `backend/runtime/engine_runtime.py`, `backend/ml/flyhash_novelty.py`, git commit `ed38c2d` |
| 4.3 | **Bayesian Fault Diagnosis** | The ATA-chapter deterministic diagnostic agent (rule-based, no LLM) plus `backend/diagnose/bn.py`'s exact Bayesian network over FMECA failure modes and isolability signatures — confirmed genuinely wired into the modern RuntimeHub path (`engine_runtime.py`, `evidence_adapter.py`, `explain.py`, `maintenance/work_package.py`), not merely research-tested | `backend/agent/diagnostic_agent.py`, `backend/diagnose/bn.py`, `docs/study/08_fault_diagnosis.md` |
| 4.4 | **Degradation, RUL, and Conformal Prediction** | Damage accumulation (rainflow/Miner), Weibull degradation, split conformal calibration for a one-sided lower RUL bound — and why an interval must ship with a coverage number, not be presented as certainty | `docs/study/09_rul_prognostics.md`, `27_conformal_prediction_for_rul.md`, `backend/evaluation/conformal*.py`, `backend/prognose/rul.py` |
| 4.5 | **What's Trained, What's Fixed, What's Calibrated** | A component-by-component table distinguishing conventional training, calibration, and fixed analytical models — prevents the single most common judge misreading | v1 `04_AI_ML_AND_FLY_BRAIN.md` §6 |
| 4.6 | **The Voice Copilot: Local Whisper.cpp + Kokoro, with an Honest Fallback** | Real local STT/TTS pipeline (VAD, barge-in), browser `SpeechRecognition` fallback with a visible status chip when local engines are unavailable, and the team's own scope note that this sits outside the literal PS | `backend/voice/`, `frontend/src/components/VoiceCopilot.tsx`, `docs/audit/02_self_audit.md` |
| 4.7 | **Offline RAG Knowledge Assistant** | PDF/manual-grounded retrieval for maintenance Q&A over 21 Rotax/DRDO manuals; what's indexed, what grounds an answer vs. what the LLM improvises | `backend/knowledge/`, `backend/agent/copilot.py` |
| 4.8 | **Why the Default LLM Is Disabled** | The local LLM provider defaults to `none`; a Chinese-origin model (Qwen) was deliberately removed as the default over a documented supply-chain concern, with a deterministic fallback covering the copilot when no LLM is enabled — a short, concrete example of a defence-context engineering decision | `backend/agent/llm_engine.py`, decision D14 in `docs/build/DECISIONS.md` |

### 3.5 Mission planning & reliability
| # | Article | Establishes | Primary sources |
|---|---|---|---|
| 5.1 | **From Engine Health to Mission Consequence** | Why mission reliability is a defined computable quantity — R = P(sortie completes without propulsion-induced abort) — not a health-index badge; why hazard rates compose correctly and thresholds don't | `backend/mission/reliability.py` docstring (excellent as-is source), v1 `05_MISSION_PLANNING_AND_SIMULATION.md` |
| 5.2 | **The Mission Executive: One Authoritative State Machine** | 20 Hz kinematics (WGS84/ENU), ISA atmosphere, phase model (taxi→takeoff→climb→cruise→loiter→dash→descent→landing), how levers drive the selected engine's physics | `backend/mission/executive.py`, `kinematics.py`, `phase_engine.py`, `REPORT/mission_planning_implementation_final.md` |
| 5.3 | **Monte Carlo Mission Reliability and the Limiting Component** | The hazard-model Monte Carlo method, confidence intervals, and — importantly, per the module's own docstring — the explicit labeling of base hazard rates as the weakest, most-assumption-dependent part of the system | `backend/mission/reliability.py`, `prescriptive.py` |
| 5.4 | **Mission Planner, Simulation, Debrief: The Operator Workflow** | The 3-tab web workflow: pre-flight planning → live simulation with fault injection → post-flight debrief/replay | `frontend/src/components/MissionOperationsPanel.tsx`, `.playwright-mcp/mission_sim/` screenshots |
| 5.5 | **Sortie Recording, Replay, and the Mission Knowledge Graph** | How completed sorties persist (CSV/JSON manifests), the replay engine's event-marker seek, and the graph-based mission/anomaly/maintenance store | `backend/reports/`, `data/graph_db/`, `backend/graph/`, `apps/mission_graph_viewer/` |

### 3.6 3D digital twin & simulation environment
| # | Article | Establishes | Primary sources |
|---|---|---|---|
| 6.1 | **Three Visualization Tracks, One Runtime State** | Three.js web twin, Blender master twin, canyon flight sim all consume the same authoritative runtime — none is an independent physics source | v1 `06_3D_TWIN_AND_FRONTEND.md` |
| 6.2 | **The Three.js Engine Twin: 5 Engines, Draco-Compressed** | GLB/Draco pipeline, component highlight/fault-target mapping, eased camera transitions, and — honestly — current wiring status per engine (verify against code at publish time rather than trusting older handoff notes) | `apps/threejs_twin/index.html`, `assets/models/draco/*.glb` |
| 6.3 | **Building the Blender Master Twin** | Per-engine `.blend` scenes (Rotax 912/914/915iS, Austro AE300, VRDE Jayem), showcase scenes, asset pipeline standards | `assets/blender/`, `docs/assets/00_asset_program_overview.md`–`05_deliverables_validation_acceptance.md`, `apps/blender_twin/` |
| 6.4 | **Ladakh Canyon Flight Simulation** | The standalone terrain/flight demo, its relationship (or lack of one) to the authoritative mission executive, desktop vs. web status | `apps/canyon_flight/`, `assets/models/ladakh_canyon_terrain.glb`, `launch_canyon_simulation.bat` |
| 6.5 | **Asset Pipeline: From CAD to Browser** | Modeling/QA standards, rigging/animation spec, GLB compression strategy, validation/acceptance criteria | `docs/assets/02_quality_and_modelling_standards.md`–`05_deliverables_validation_acceptance.md`, `rendering_guide.md` |

### 3.7 Operator GCS (frontend)
| # | Article | Establishes | Primary sources |
|---|---|---|---|
| 7.1 | **The Operator Console: Fleet, Engine, Evidence** | Default modern console: fleet tiles, tier-0/tier-1 evidence, profile-valid fault injection, levers — and the explicit `SIMULATION` evidence class shown to the user | `frontend/src/components/EngineRuntimeConsole.tsx` (or current equivalent), `docs/build/CURRENT_STATE.md` |
| 7.2 | **Legacy GCS: The Mature Six-Workspace Console** | Why this workspace is retained (not "legacy" in tone) — real 20 Hz telemetry, real fault injection, real Blender/3D control for Rotax 912 iS | `docs/build/MENTAL_MODEL.md` (terminology note), frontend legacy views |
| 7.3 | **Reading the Evidence: Health, Alarms, and What They Don't Mean Yet** | Maturity labeling discipline applied to the UI itself — what tier-0/tier-1 scores are and are not (not a certified airworthiness judgment, not a confirmed diagnosis) | `docs/build/MENTAL_MODEL.md` §2 "Limits that matter to the UI" |

### 3.8 Security, edge & fleet layer
| # | Article | Establishes | Primary sources |
|---|---|---|---|
| 8.1 | **Telemetry Integrity: Merkle Logging and CAN Intrusion Detection** | Tamper-evident logging, jitter-based CAN-IDS — clearly labeled research/tested, not wired to the live UI | `backend/security/merkle_log.py`, `can_ids.py` |
| 8.2 | **Resilient Datalink: Jamming, Signing, and Store-and-Forward** | Link emulator behavior under loss/jamming, message signing, priority queue draining | `backend/link/link_emulator.py` |
| 8.3 | **Federated Fleet Learning** | Colony aggregation design, canary evaluation — research status, why federation matters for a fleet of airframes that can't share raw data | `backend/federation/aggregator.py`, `colony.py` |
| 8.4 | **Edge Compression and the Bandwidth Budget** | Feature-frame packing, link-budget accounting, ties back to the edge/ground split argument | `backend/edge/compressor.py` |

### 3.9 Data strategy
| # | Article | Establishes | Primary sources |
|---|---|---|---|
| 9.1 | **The Dataset Landscape: What's Real, What's Proxy, What's Synthetic** | Honest inventory of `Datasets/` categories; the corrected finding that NASA ACES contains real Rotax-914 UAV telemetry (no fault labels) while ACES/C-MAPSS/CWRU/battery *adapters* in this repo currently synthesize rather than parse | `docs/study/14_datasets.md`, `docs/audit/05_expanded_survey.md` §3, `backend/datasets/*.py`, `backend/telemetry/aces_loader.py` |
| 9.2 | **FMECA: The Fault Taxonomy Underneath Everything** | MIL-STD-1629A-derived 20-mode table, RPN scoring, channel/detection-method mapping, explicit GAP marking discipline | `docs/reliability/FMECA.md`, `ISOLABILITY.md` |

### 3.10 Validation & evidence
| # | Article | Establishes | Primary sources |
|---|---|---|---|
| 10.1 | **Evidence-First Documentation: The Four Labels** | The ✅/🔶/⬜/🔒 convention itself, why it exists, and that this documentation site follows it | `docs/README.md` "Evidence labels", `docs/study/README.md` |
| 10.2 | **Test Coverage and Characterization** | pytest suite scope, characterization tests pinning headline numbers as regressions, the reachability audit tool | `docs/build/BACKLOG.md` E0 section, `tests/`, `scripts/tools/audit_reachability.py` |
| 10.3 | **The Competitive Audit: Where We Actually Stand** | 15-team competitive scoring, the "second, not first" finding, the two corrected claims — presented as intellectual honesty, not a weakness | `docs/audit/01_competitive_audit.md`, `05_expanded_survey.md`, `README.md` "three findings that matter" |
| 10.4 | **UI Verification: What the Screenshots Actually Show** | Dated Playwright-based verification (baseline, mission_sim 8-step sequence, phase1/2/5/10 matrices) as real evidence, not mockups | `.playwright-mcp/` |

### 3.11 Limitations & roadmap
| # | Article | Establishes | Primary sources |
|---|---|---|---|
| 11.1 | **What's Live, What's Simulated, What's Roadmap** | The five-tag maturity system applied across every subsystem in one master table | v1 `08_LIMITATIONS_AND_ROADMAP.md`, `docs/build/CURRENT_STATE.md` |
| 11.2 | **The Path to a Connected System** | Ordered roadmap: waveform pipeline connection, real dataset parsing, aircraft/CAN hardware adapter at the `Frame` boundary, unified runtime | `docs/build/MENTAL_MODEL.md` §5, `BACKLOG.md` |

### 3.12 Reference
| # | Article | Establishes |
|---|---|---|
| 12.1 | **Technology Stack** — argued, not a logo wall (v1 `11_TECH_STACK.md`) |
| 12.2 | **Glossary** (`docs/study/23_glossary.md`) |
| 12.3 | **Judge FAQ / Technical Q&A** — curated from `UpdatedReport/13_judge_question_bank.md` and `25_DRDO_TECHNICAL_QA.md`, re-verified against current code before publishing (the source file itself warns some of its claims predate current work) |

---

## 4. "Our SIH Journey" — article hierarchy

Following the v1 scaffold's chapter template (What happened / What did we build / What changed / What failed / Evidence), populated against real evidence found in-repo:

| # | Chapter | Evidence available |
|---|---|---|
| J1 | Why we picked PS 26054 | Team/problem-selection context (needs team interview — not derivable from repo) |
| J2 | Understanding the Digital Twin requirement | `docs/00_official_problem_statement.md`, `01_problem_statement_breakdown.md` |
| J3 | Research phase — building the 27-part study course | `docs/study/` I–XXIII, dated before the audit |
| J4 | First architecture, and the two-pipeline reality that emerged | Early commits (`a63c0f6` "full digital twin", `9962bf9` independent plant) |
| J5 | Building the physics/engine layer | Commits `37acded`, `7819c13`, `fd77805` (crank-angle chain), `2fc262d` |
| J6 | The competitive audit: finding out we were second, not first | `docs/audit/01_competitive_audit.md`, `05_expanded_survey.md` — genuinely strong material: shows real self-correction (0-of-11-do-vibration-DSP claim revised to 2-of-15, ACES dataset claim revised) |
| J7 | AI/ML experiments and the FlyHash honesty correction | `docs/study/20_novelty_and_research.md` §20.1 "A correction, stated up front" — rare and valuable material: the team publicly retracting their own novelty claim |
| J8 | Building the 3D twin: Three.js, Blender, and 5 engines | Commit history for `apps/threejs_twin/`, `assets/blender/`, `docs/assets/` |
| J9 | Mission planning: from "not implemented" to a working web loop in days | `REPORT/mission_planning_architecture.md` (2026-09) → `mission_planning_implementation_final.md` (2026-09-28) — a clean before/after pair with dates |
| J10 | Integration problems: two backends, one shell | `docs/build/MENTAL_MODEL.md`, `SUPERSEDED_VS_CURRENT.md` — the unresolved integration is itself honest material |
| J11 | Testing and evidence discipline | `docs/build/VERIFICATION_CHECKLIST.md`, `.playwright-mcp/`, pytest counts tracked in `BACKLOG.md` |
| J12 | Preparing for judges | `UpdatedReport/13_judge_question_bank.md`, `29_DEMO_METHODOLOGY.md`, `27_CLAIMS_AND_EVIDENCE.md` |
| J13 | What we would change next | `docs/build/BACKLOG.md` ordered remaining work, `08_LIMITATIONS_AND_ROADMAP.md` |

**Note**: J1 and parts of J13's "human side" (who owned which subsystem, how work was coordinated) are not derivable from the repository and require direct input from the team — flag this rather than fabricate it, per the v1 scaffold's explicit rule.

---

## 5. Standout material worth featuring prominently (not buried in subsystem pages)

1. **The FlyHash honesty correction** (`docs/study/20_novelty_and_research.md`) — a team publicly finding and correcting its own novelty overclaim, with full literature citations, is rare and highly credible to a technical judge panel.
2. **The competitive audit's self-corrections** (`docs/audit/05_expanded_survey.md`) — same pattern, applied to competitive positioning.
3. **Crank-angle combustion diagnostics + order tracking/envelope analysis** — per the audit, this is the field's actual open differentiator (0 of 15 surveyed teams do tach-synchronous order tracking or per-cylinder torque-deficit misfire detection).
4. **Mission reliability's hazard-rate argument** — the `reliability.py` docstring is already better-written than most documentation; it should be excerpted, not paraphrased.
5. **Digital Shadow vs. Digital Twin under STANAG 4586** — leads with precision instead of a vague "digital twin" claim a judge would probe first.
6. **The Playwright verification trail** — dated, real UI evidence rather than claimed evidence.
7. **The one-physics-model-five-engines gap, stated once and cross-referenced** — `docs/assets/00_asset_program_overview.md` already admits its 3D program is "specification only," and this lines up exactly with `thermo_model.py`'s Rotax-912iS scope. Stating this plainly in one place (article 3.8) is more credible than letting a judge discover the inconsistency between a "5-engine selector" screenshot and a 912iS-only physics model.
8. **The disabled-by-default LLM decision** — a small, concrete instance of defence-context engineering judgment (removing a Chinese-origin model as the default, documented as decision D14) that's easy to overlook but exactly the kind of detail a DRDO panel notices favorably.

---

## 6. Diagram plan

Reuse the v1 scaffold's diagram specification (`12_SITE_CONTENT_AND_DIAGRAM_SPEC.md`) as-is — it is well-specified (Mermaid only, monochrome, ≤10-12 nodes, dashed subgraph boundaries for layers). Diagrams A–H map directly onto articles 2.1, 2.3, 3.1, 4.1, 5.1, 6.1, 10.1, and the SIH Journey overview respectively.

---

## 7. What this plan deliberately does not do

Per your instruction, this is not a code audit. Every "PARTIAL / not wired / research-only" note above exists only where it is necessary to state honestly what a subsystem *is* for documentation purposes (the same discipline this repository already enforces on itself) — not to critique implementation choices, file layout, or completeness. The next step, if you approve this hierarchy, is content writing per article, not further repository restructuring.
