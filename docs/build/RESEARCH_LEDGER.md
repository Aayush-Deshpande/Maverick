# Research Ledger

*New here? Read [`MENTAL_MODEL.md`](MENTAL_MODEL.md) first, then [`SUPERSEDED_VS_CURRENT.md`](SUPERSEDED_VS_CURRENT.md).*

What has been researched for this project, in which direction, **how deep**, from which sources, with what confidence, and what has **not** been researched. Use it to decide whether a topic needs more research before building (usually it does not; see D26) and to find the document holding the detail.

## Depth scale

| Level | Meaning |
|---|---|
| **R0** | Not researched |
| **R1** | Surveyed: landscape known, key sources found |
| **R2** | Designed: method or architecture specified to implementable detail, with sources checked |
| **R3** | Implemented and verified **in simulation** (see [`../IMPLEMENTATION_LOG.md`](../IMPLEMENTATION_LOG.md)) |
| **R4** | Validated **on real data** |

**Evidence labels** used throughout `docs/`:

- ✅ verified against a source
- 🔶 engineering judgement or derived calculation
- ⬜ proposal or assumption
- 🔒 needs data we do not have

---

## 1. Timeline (how the knowledge accumulated)

| Date (2026) | Work | Output |
|---|---|---|
| Aug 30 – Sep 15 | Original system built: Blender engine twin, RAG copilot, ML/physics 20 Hz pipeline, telemetry generator, voice, Ladakh terrain canyon sim, mission reports, replay (per git history) | Code in `backend/`, `apps/`, `frontend/`; commits `9d69c66` … `9e366b7` |
| Sep 20 | PS audit and feature listing; pitch study of a benchmark team (usavionix); simulation review | `docs/00–03`, [`../fun_req.md`](../fun_req.md), [`../pitch/`](../pitch/) |
| Sep 21 | **Fly connectome** trend analysed for fault prediction: verdict "not a classifier replacement on 14 features; strong as novelty on high-dimensional input (waveforms/spectra)". Then a **global UAV/DRDO domain study** (sensors, signal types, comms, data processing) → the 23-part study course | [`../study/`](../study/) I–XXIII; [`../study/20_novelty_and_research.md`](../study/20_novelty_and_research.md); [`../study/proposal.md`](../study/proposal.md) |
| Sep 21–22 | Reality check on "threshold monitoring" and the IVHM gap; C-MAPSS relevance; edge vs ground split; **competitor audit** (23 repos found, 9 cloned); repository restructure; system guide | [`../audit/01–06`](../audit/README.md); [`../04_system_guide.md`](../04_system_guide.md); `competitors/` |
| Sep 22 | **Jev (TypeSafe) and OpenJev** assessed; **unoccupied-axes research** (engine class, standards, physics of failure, oil/SOAP, India environment, MAVLink/ArduPilot EFI, twin validity, security as physics, mission reliability, evaluation instruments) → F31–F68; engine-model search (AE300 = OM640; the 914 as the MALE standard); **NASA ACES** acquired | [`../audit/07`](../audit/07_unoccupied_axes_and_ground_up_plan.md); `docs/reference/` |
| Sep 22–23 | Implementation sessions 1–4: F01–F08, F12–F18, F31–F43, F46, F48, F50–F58, F60, F62–F63, F67–F68; plant/twin split; measured lead time | [`../IMPLEMENTATION_LOG.md`](../IMPLEMENTATION_LOG.md); commits `37acded` … `d71e1e7` |
| Sep 23 | Import-traced **audit against a deployable target**; **full-depth architecture** (51.2 kHz, combustion reconstruction, hierarchical estimator, active diagnosis); **red-team review** (PS line by line, DRDO reality, SIH format); **software-only design of every PS clause** incl. FL/edge/XAI/security/maintenance; **public datasets downloaded** and inspected; builder docs | [`../audit/08–12`](../audit/README.md); `docs/build/`; `Datasets/download_all.py` |

---

## 2. Coverage map

| # | Topic | Depth | Main conclusions | Where | Key sources | Confidence |
|---|---|---|---|---|---|---|
| 1 | PS decomposition | R2 | 114 requirement rows (SYS/INT/CAP/DTC/HMS/FDP/AIM/SIM/VIS/DEL/OPT/INN/TEX); line-by-line coverage in 10 §1 | [`../fun_req.md`](../fun_req.md), [`../audit/10`](../audit/10_red_team_readiness_review.md) §1, [`../audit/11`](../audit/11_entire_ps_software_only.md) §2 | PS text ([`../00_official_problem_statement.md`](../00_official_problem_statement.md)) | High |
| 2 | Indian MALE platforms and engines | R2 | TAPAS BH-201 → **VRDE 2.2 L CRDi** (public facts only); Heron Mk I = Rotax 914; **Heron Mk II = Rotax 915 iS**; Archer-NG engine not public | [`DECISIONS.md`](DECISIONS.md) D01; 08 §0; 10 §2.7–2.8 | Indian Defence News / idrw (Aug 2025); Janes; IAI | High for the listed facts; **R0 for VRDE internals** |
| 3 | Engine sensors and signal types | R2 | Per-parameter sensor, signal, rate and fault map; vibration is a waveform, the rest are scalars | [`../study/02`](../study/02_engine_sensors.md) (**rates superseded by D08**) | Rotax manuals; benchmark datasets | High |
| 4 | Sampling physics | R2 | **51.2 kHz (20 kHz band)**, from Draper chamber modes 5.6–20 kHz; turbo 102.4 kHz; rail ≥ 30 kHz; crank edges ≤ 25 ns | [`../audit/09`](../audit/09_full_depth_architecture.md) §2 | Draper relation; rail-pressure sampling literature | High (first-order) |
| 5 | CAN / ECU / FADEC interfaces | R2 | J1939-style broadcast, UDS for diagnostics/routines, **XCP for internal variables**; MAVLink `EFI_STATUS` | [`../study/03`](../study/03_ecu_can_acquisition.md); 07 Part VII; 11 §4 | MAVLink docs; ArduPilot AP_EFI; ASAM XCP; ISO 14229 | Medium–high |
| 6 | **FADEC compensation functions** | R2 | Cylinder balancing and drift adaptation mask injector faults; **trims are a health signal** | 09 §4.4; D09 | Bosch zero-fuel calibration patent; injection-control patents | Medium (automotive CRDi; the VRDE FADEC is unknown 🔒) |
| 7 | Telemetry, datalinks, bandwidth | R2 | Raw vibration cannot be downlinked (12.6 Mbit/s against ~22 kbit/s spare); 29-byte health frame; full raw record to SSD | [`../study/04`](../study/04_telemetry_and_comms.md), [`05`](../study/05_edge_ai.md), [`13`](../study/13_edge_vs_ground_split.md); 09 §2.4 | STANAG 4586 overview; link budgets | Medium (**TAPAS link specifics 🔒**) |
| 8 | Combustion and crank dynamics | **R3 (SI)** / R2 (CI) | Wiebe → p(θ) → ω(θ) verified (order-2 dominant); **CI model specified** (ignition delay, double Wiebe, multi-injection) but not built | [`../study/24`](../study/24_combustion_cycle_and_crank_dynamics.md), [`25`](../study/25_misfire_and_combustion_diagnostics.md); 09 §5.2 | SAE 960039; Wiebe literature | High (SI), medium (CI) |
| 9 | Vibration DSP | R3 (order/envelope in simulation) / R2 (OFSC, kurtogram, gear CIs) | Angle-domain processing; cyclostationarity (OFSC); envelope order spectra; FM0/FM4/NA4 | [`../study/06`](../study/06_vibration_analysis.md), [`26`](../study/26_order_tracking_and_envelope.md); 09 §4.2 | Antoni; Abboud/Antoni (OFSC); Randall; HUMS CI literature | High |
| 10 | **Cylinder-pressure reconstruction** | R2 | Complementary fusion of crank speed and vibration; needs test-cell FRF calibration | 09 §4.3 | Randall/Gao; RBF reconstruction; *Sensors* 2024 fused-speed reconstruction | Medium–high |
| 11 | Injection diagnostics | R2 | Rail-pressure waves per injection; needle impacts; SOC − SOI = ignition delay | 09 §4.4 | CR injector diagnosis papers (rail pressure, vibration, VMD) | Medium |
| 12 | Anomaly detection | R3 | Residual-based; point-adjust inflation measured (0.049 vs 1.000 F1) | [`../study/07`](../study/07_anomaly_detection.md); IMPL_LOG F62 | AD evaluation literature | High |
| 13 | Fault diagnosis and classification | R2 | Classifiers are evidence; BN from FMECA; ambiguity groups; **active diagnosis** (cut-out etc.) | [`../study/08`](../study/08_fault_diagnosis.md); 09 §6 | Cylinder cut-out practice; FMECA | Medium–high |
| 14 | **Fly-inspired computing** | R2 (R3 residual-only) | FlyHash/FBF novelty on high-dimensional input; FlyNN for open-set/few-shot/federated; not novel as algorithms; test against a null | [`../study/20`](../study/20_novelty_and_research.md); 08 §4; 09 §6.3; D12 | Dasgupta *Science* 2017, *PNAS* 2018; Ram & Sinha AAAI 2022 / KDD 2021; Ryali ICML 2020 | High |
| 15 | Model Kombat / Jev lessons | R2 | Distillation; null (rewired) controls; strong simple baselines; efference copy; curriculum | 08 §4.3; `mk-jev-fly-brain/EXPERIMENTS.md` | The repo's own experiments | High (as method) |
| 16 | Jev / OpenJev | R1 | Closed hosted API excluded; community reproductions exist, unaudited | D13 | TypeSafe blog; GitHub repos | Medium |
| 17 | RUL and prognostics | R3 (metrics, conformal, damage in isolation) | Dual path; conformal (+ACI); PHM metrics waterfall | [`../study/09`](../study/09_rul_prognostics.md), [`27`](../study/27_conformal_prediction_for_rul.md); 09 §7 | Saxena/Goebel; NASA PrognosticsMetricsLibrary | High |
| 18 | Digital-twin theory and estimation | R2 | Twin = estimator (UKF/PF, differentiable); validity monitoring | [`../study/10`](../study/10_digital_twin.md); 09 §5; 11 §3.1 | Estimation theory; UDE/SINDy literature | High |
| 19 | Physics-informed and hybrid ML | R2 | Six hybrid patterns, each with a place; UDE and SINDy over naive PINNs for known ODE structure | 11 §3.1–3.2 | Brunton et al. (SINDy); Rackauckas et al. (UDE) | Medium–high |
| 20 | **Federated learning** | R2 | Hierarchical cross-silo; five shared objects; failure-masking poisoning + defences; federated conformal | 11 §3.4; D15 | arXiv 2608.04045; 2506.00499; FedCMAPSS; FCP (ICML 2023); FlyNN-FL; Flower/FLARE | Medium–high |
| 21 | Edge AI | R2 (R3 for budget arithmetic) | Capped process, mixed criticality, cascade, INT8, value-of-information telemetry | [`../study/05`](../study/05_edge_ai.md); 11 §3.3; `edge/compressor.py` | TinyML; ONNX Runtime | Medium–high |
| 22 | XAI and assurance | R2 | Explanations by audience; measured faithfulness; EASA Level 1 framing | 11 §3.5; D02 | EASA AI Concept Paper Issue 2 | Medium–high |
| 23 | Secure telemetry | R2 (R3 physics integrity in simulation) | Eight layers; signing ≠ encryption; PQC; hash-chained logs; CAN IDS + physics | 11 §3.6; 07 Part IX | mavlink.io signing; NIST FIPS 203/204; ROAD dataset paper | Medium–high |
| 24 | Reliability engineering | R3 | FMECA (MIL-STD-1629A), isolability, mission reliability, prescriptive | 07 Parts III–X; `reliability/`, `mission/` | MIL-STD-1629A (in repo); PHM literature | Medium (placeholder hazards) |
| 25 | Oil / SOAP / wear metals | R3 (simulation) | Element → source attribution | 07 Part V; `physics/oil_system.py` | SOAP literature | Medium |
| 26 | Indian environment effects | R3 (simulation) | Dust chain, cold/CFPP, hot-and-high; exposure accumulator | 07 Part VI | Desert-operations and fuel-waxing sources | Medium |
| 27 | Electrical system | R2 | **FADEC diesels quit without power**; ripple orders; start-impedance battery test; restart readiness | 10 §2.1 | PPRuNe; AAIB G-HAKA; GA News | Medium |
| 28 | Maintenance autonomy | R2 | L1–L4 with approval; CP-SAT; NFF KPI; fleet discrete-event simulation | 11 §3.7 | CBM/RCM practice | Medium |
| 29 | Standards | R2 | ISO 13374/OSA-CBM; MIL-STD-1629A; DO-178C; CEMILAC/IMTAR-21, IMTAR V2.0; ISA-18.2; EASA AI | 07 Part III; 10 | Official pages (CEMILAC, EASA) | Medium–high |
| 30 | Datasets | R2 (downloaded and inspected) | Triage and experiments E01–E15; engine-journal-bearings set is low value; 3500-DEFault is the fly-vs-RF test bed | [`../audit/12`](../audit/12_dataset_implementation.md); [`../../Datasets/`](../../Datasets/README.md) | Each dataset's landing page | High |
| 31 | Competitors | R2 | 23 repos; the field does residuals → IF/RF → dashboard; no real vibration processing anywhere | [`../audit/01`](../audit/01_competitive_audit.md), [`05`](../audit/05_expanded_survey.md), [`../COMPETITOR_ARCHITECTURE_BREAKDOWN.md`](../COMPETITOR_ARCHITECTURE_BREAKDOWN.md) | Cloned repos; demo videos | Medium (snapshot) |
| 32 | SIH format and judging | R1 | 36-hour finale; stable prototype preferred; criteria scored 1–20 → 100 | 10 §2.11 | SIH guides | Medium |
| 33 | Adoption and funding | R1 | Ground-first path; iDEX (≤ ₹1.5 Cr), TDF (≤ 90 %, ₹50 Cr cap) | 10 §2.10 | idex.gov.in; tdf.drdo.gov.in | Medium |
| 34 | Indigenous stack | R1 | No Chinese components (2025 Army cancellations); Indian LLMs (Sarvam, BharatGen); Indian RISC-V (VEGA DHRUV64, SHAKTI) | 10 §2.6; D14, D24 | News and official pages | Medium |
| 35 | Pitch and HMI benchmarks | R1 | A benchmark team's pitch structure; universal pitch principles | [`../pitch/`](../pitch/) | Demo videos | Medium |
| 36 | Fly-inspired open-source libraries and connectome simulators | R1 (surveyed, licences checked) | fbfc MIT; ffbf no licence; connectome sims are neuroscience tools; algorithm only useful on high-dim features - untested | [`DETECTOR_DECISION.md`](DETECTOR_DECISION.md) | GitHub pages/API; Dasgupta 2017/2018; Ram & Sinha 2021/2022 | Medium |
| 37 | Jev / OpenJev local variants | R1 | text/typed-decision LLMs; not for 20 Hz numeric detection | DETECTOR_DECISION s5 | community repos (27 B, ModernBERT-151 M, diffusion-LM server) | Low-medium (unaudited) |
| 38 | Universal vs per-engine detectors | **R3 (simulation, single seed set)** | calibration, not classifier, carries universality (E17) | DETECTOR_DECISION | `experiments/E17` | Medium (needs R6 + CIs) |
| 39 | Raspberry Pi 5 edge inference | R1 | 4x A76 @ 2.4 GHz; ONNX Runtime typically faster than TFLite; ms-scale RF/GBM; **our Pi timings are extrapolated, unmeasured** | MULTI_ENGINE_ARCHITECTURE s7 | web sources on Pi 5 ML benchmarks | Low (no hardware run) |
| 40 | Multi-engine concurrent runtime, levers | R2 | measured plant cost; L1-L4 layering | MULTI_ENGINE_ARCHITECTURE | timings, code audit | Medium-high |

## 3. Not researched, or blocked (R0 / 🔒)

| Gap | Why it matters | How to close it |
|---|---|---|
| VRDE engine internals: bore/stroke/CR, rpm, rail pressure, injector type, **FADEC functions and data interface** | Every CI constant is an assumption | Ask VRDE; this is the "what we need from you" list |
| TAPAS datalink bandwidth and GCS architecture (ADE) | Link budget and integration | Ask ADE; meanwhile a parametric link emulator |
| IAF/Army maintenance data formats and levels (O/I/D) | Maintenance integration | Ask the users; ATA-like placeholders meanwhile |
| Government-approved crypto requirements | Layer 2 cipher choice | Pluggable crypto module (D17) |
| IMTAR specifics for advisory health-monitoring software | Certification path detail | Ask CEMILAC; the DO-178C low-DAL framing meanwhile |
| Cost figures (airframe, sorties, maintenance) | Impact model | Parametrised ranges (10 §2.9) |
| Real CI engine waveforms with in-cylinder pressure | Virtual pressure sensor calibration | Lab rig (roadmap) or VRDE test cell |
| **ACES `m_units` scale for EGT/CHT/engine-temp channels (°C vs °F vs raw)** | Blocks any sim-to-real EGT bias number (E01); binding itself is now fixed and confirmed (B0.3) | Obtain the ACES documentation PDF from NASA GHRC DAAC (`ghrc.nsstc.nasa.gov` was unreachable from this environment — TCP timeout, not auth, per session 1); until then report relative comparisons only |
| XJTU-SY bearing data | Optional | Google Drive / Baidu manual download |
| MIMII, ROAD, marine diesel downloads | Blocked by Zenodo rate filtering | Single-connection retry |
| Archer-NG engine | Config slot | Wait for public information |

## 4. Corrections made along the way (do not repeat the wrong versions)

| Wrong claim | Correct version | Where corrected |
|---|---|---|
| "Bio-inspired sparse coding for engine PHM is our novel algorithm" | Established family; our contribution is the application and integration | study/20 §20.1 |
| "FlyHash is cheaper than the RF" (at 14 features) | Not at 14 features; the advantage appears on high-dimensional input | 21 Sep conversation; D12 |
| "Switch to the AE300 as the primary engine" | VRDE CRDi is the DRDO target; 914 for ACES; 915 iS for Heron Mk II; AE300 is a public proxy | D01 |
| "VRDE 2.2 L figures are unsourced" (UpdatedReport 31 §2.2) | 2.2 L, inline-4, turbo CRDi, FADEC, 180 hp at 11,000 ft, 32,000 ft are public; other numbers are not | D01 |
| `vrde_jayem_2_2l.json` "specification" | Mostly assumed values; needs per-field provenance | B0.4 ✅ |
| "ENGINE_THERMO_2 (1035°C) is the more likely true EGT" (session 4, 2026-09-23) | Right instinct, wrong specific fix: the real cause is a name-matrix start-of-string binding bug, not a wrong channel choice — fixed, EGT_1/2/3/4 and CHT now bind correctly (independently corroborated against a competitor's ACES decode); the *scale* (°C vs °F) is still unconfirmed | B0.3 ✅; IMPL_LOG S5 |
| Vibration at 2–10 kHz | 51.2 kHz (20 kHz band) | D08 |
| "No VRDE config exists" (08 §5.C, 10 §2.8) | It exists; its provenance is the problem | This ledger; B0.4 |
| Heron uses the Rotax 914 | Heron Mk I does; **Heron Mk II uses the 915 iS** | 10 §2.8 |
| "Median lead time 7.92 min" as a general result | A single scenario; n = 1 | 08 §5.F |
| "0 false alarms per hour" | Over 3 h, the 95 % upper bound is 1.0/h | 08 §5.F |
| OpenJev = "DiffusionGemma 3B-A4B, Apache-2.0" (from an SEO guide site) | Several community reproductions with differing bases; verify each | 08 §0 |
| "Engine class as configuration (F31) makes the twin engine-independent" (IMPLEMENTATION_LOG F31 headline) | Only the plant/turbo side consumes configs; the twin, live pipeline, limits, fault list, RUL model and UI are hardcoded to a 4-cylinder Rotax 912 iS, with no engine-selection path | UNIVERSALITY_AUDIT; D27 |
| "The independent plant is engine-independent" (IMPLEMENTATION_LOG G01 framing) | Independent of the *twin*, but Rotax-shaped internally: shared rpm map and SI-style EGT formula | FINDINGS F21 |
| "Live operator levers change the physics" (implied by the API) | They only overwrite displayed fields (gap G02, still open) | FINDINGS F23 |
| Engine Journal Bearings = raw IC-engine vibration | Test-report documents and chart images; low value | 12 §2 |
| UpdatedReport 00–30 file paths (`backend/services/…`, `d:/Programming/PS054/…`) | Do not exist | UpdatedReport/31 §2 |

## 5. Canonical source list (the ones the design actually rests on)

- **PS:** [`../00_official_problem_statement.md`](../00_official_problem_statement.md) · requirements [`../fun_req.md`](../fun_req.md)
- **Engines:** Rotax 914 installation/operator manuals (`docs/reference/`) · Indian Defence News and idrw (TAPAS/VRDE engine, Aug 2025) · Janes (Heron Mk II / 915 iS)
- **Standards:** MIL-STD-1629A (`docs/reference/`) · ISO 13374 / MIMOSA OSA-CBM · DO-178C · CEMILAC / IMTAR-21 · ISA-18.2 · EASA AI Concept Paper Issue 2 · NIST FIPS 203/204 · MAVLink 2 signing spec
- **Methods:**
  - Saxena & Goebel PHM metrics; NASA PrognosticsMetricsLibrary (`vendor/`)
  - Antoni (cyclostationarity); Abboud/Antoni (order-frequency spectral correlation)
  - Randall & Gao (cylinder-pressure reconstruction)
  - Dasgupta et al. 2017/2018 (FlyHash, Fly Bloom Filter); Ram & Sinha 2022 (FlyNN-FL)
  - Federated aircraft-engine prognostics (arXiv 2608.04045, 2506.00499); FedCMAPSS; federated conformal prediction (ICML 2023)
  - SAE 960039 (crank-speed misfire)
- **Data:** NASA ACES · NASA PCoE (C-MAPSS, N-CMAPSS, IMS, FEMTO, battery) · CWRU · Paderborn · 3500-DEFault · Marine Engine Fault (Zenodo) · ALFA · ROAD · SynCAN · SKAB · MIMII DG/DUE

The full URL lists are in the "Sources" section at the end of each audit document (07–12) and in each study part.

## Fly / connectome / Jev additions (24 Sep 2026)
- PMC12109256 Drosophila connectome as reservoir; ESA ACT fly-connectome reservoir; arXiv 2606.17745 (larval frozen rate operator); bioRxiv 2025.10.29.685101 (cross-species reservoir capacity); conn2res (Nat. Commun. 2024); github aditya1212singh/fly-connectome-forecasting; rithram/fbfc (MIT); dataplayer12/Fly-LSH; cauldr0nx/flyPaper; arXiv 2006.03741, 2206.09222, 2104.04121.
- Local measurement: maleCNS 12k circuit, 941,464 synapses, 8,149 E / 3,851 I. 100 approaches: `FLY_100_WAYS.md`. Result: E19.
- Licences: TabPFN 2.5+ non-commercial; Moirai CC BY-NC; TimesFM/Chronos Apache-2.0; `ffbf` no licence (excluded).
