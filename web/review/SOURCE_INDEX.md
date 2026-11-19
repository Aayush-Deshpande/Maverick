# Source index

Structural index only. Deep review evidence is in PROJECT_REVIEW.md.

## backend/__init__.py (1 lines)





## backend/ml_runtime_lock.py (45 lines)

Process-Wide First-Import Lock for `transformers`-Dependent Engines.
DRDO / iDEX Problem Statement ID: 26054



## backend/osacbm.py (287 lines)

OSA-CBM / ISO 13374 architecture mapping — F34.

Layer:39, ModuleRegistration:66, check_layering:210, coverage:227, architecture_markdown:246

## backend/agent/__init__.py (3 lines)





## backend/agent/copilot.py (1261 lines)

Agentic Mission Copilot & Tactical Flight Assistant.
DRDO / iDEX Problem Statement ID: 26054

_trim_to_complete_sentence:127, _strip_markdown_for_speech:148, MissionCopilot:193

## backend/agent/diagnostic_agent.py (343 lines)

Cognitive Diagnostic Agent & ATA Citation Reasoner — Plane 2
DRDO / iDEX Problem Statement ID: 26054

DiagnosticDirective:21, DiagnosticAgent:234

## backend/agent/flight_intent.py (149 lines)

Natural-Language Flight-Vector Intent Engine (PRD F10).
DRDO / iDEX Problem Statement ID: 26054

FlightIntent:60, parse_flight_intent:89, _repo_root:104, default_queue_path:109, write_flight_command:113, handle_flight_command_text:141

## backend/agent/llm_engine.py (491 lines)

Local LLM Reasoning Engine — served via Ollama (GGUF, GPU-offloaded)
DRDO / iDEX Problem Statement ID: 26054

LocalLLMEngine:122

## backend/alarms/rationalisation.py (148 lines)

ISA-18.2 Compliant Alarm Management and Flood Suppression (B6.3, VIS-06).

AlarmPriority:18, AlarmState:25, RationalisedAlarmSpec:33, ActiveAlarm:44, ISA18AlarmManager:92

## backend/core/__init__.py (9 lines)





## backend/core/channels.py (39 lines)

Channel registry (U2): the canonical channel list is DERIVED from the engine profile, never typed as CHT_1..4.

ChannelSpec:15, channel_specs:23, channel_names:38

## backend/core/cycle_block.py (48 lines)

CycleBlock (INTERFACES Sec 3): high-rate telemetry representation for one 720-degree engine cycle.

WaveformChannel:16, CycleBlock:24

## backend/core/frame.py (232 lines)

Canonical low-rate telemetry contract -- B1.1.

Frame:56, FaultTruth:151, TruthRecord:163, frame_from_plant:188, truth_from_plant:218

## backend/core/limits.py (43 lines)

Operating-limit (redline) evaluation from the engine profile (U3).  Cylinder-count agnostic.

Exceedance:16, check_limits:25

## backend/core/pipeline.py (83 lines)

OSA-CBM stage executor (B1.3, D05): one pipeline for live, replay and evaluation.

Stage:19, StageStats:28, FunctionStage:39, Pipeline:51

## backend/core/profile.py (169 lines)

EngineProfile (U1, D27): Unified profile joining physics config, asset manifest,
channels, applicable fault modes, and provenance summary.

EngineProfile:27, _compute_provenance_summary:129, _load_asset_manifest:137, load_profile:149, load_all_profiles:166

## backend/datasets/aces.py (86 lines)

Synthetic ACES-shaped scenario generator (not a NASA ACES file loader).

ACESLoader:18

## backend/datasets/alfa.py (87 lines)

Synthetic ALFA-shaped scenario generator (not an ALFA dataset file loader).

ALFALoader:19

## backend/datasets/base.py (70 lines)

Universal Dataset Abstraction and Metadata Contracts (B7.1, CAP-07, D19, D35).

EvidenceClass:20, DatasetManifest:28, DatasetRecord:42, BaseDatasetLoader:51

## backend/datasets/battery.py (88 lines)

Synthetic NASA PCoE-shaped scenario generator (not a NASA battery-file loader).

BatteryLoader:19

## backend/datasets/cmapss.py (103 lines)

Synthetic C-MAPSS-shaped scenario generator (not a NASA C-MAPSS file loader).

CMAPSSLoader:19

## backend/datasets/cwru.py (91 lines)

Synthetic CWRU-shaped scenario generator (not a CWRU signal-file loader).

CWRULoader:20

## backend/datasets/default_3500.py (116 lines)

Synthetic Multi-Engine 3500-Run Benchmark Dataset Loader (B7.7, BENCH-06, D19).

Default3500Loader:20

## backend/detect/__init__.py (10 lines)

Calibrated-residual detection stack (W1/W11): per-tail calibration, cheap scorers, conformal thresholds,
persistence gate, and the sparse reservoir tier. Consumes canonical ``Frame`` only.



## backend/detect/calibration.py (146 lines)

Per-tail calibration ("twin-lite") -- backlog W1, decision D31.

_design:30, _command:35, _measure:41, TailCalibration:53

## backend/detect/detector.py (120 lines)

ResidualDetector -- calibrated-residual detector with split-conformal thresholds and a persistence gate
(backlog W1, decisions D31/D36).

DetectionResult:31, PersistenceGate:57, ResidualDetector:74, conformal_threshold:115

## backend/detect/reservoir.py (111 lines)

Sparse reservoir tier (backlog W11, decision D36) -- temporal detector on calibrated features.

_scale:26, connectome_matrix:34, random_matrix:47, Reservoir:55

## backend/detect/scorers.py (68 lines)

Cheap anomaly scorers over calibrated feature vectors (backlog W1).

FlyBloomScorer:17, Mahalanobis:48, MaxAbsZ:61

## backend/diagnose/active.py (76 lines)

Active Diagnosis and Expected Information Gain Test Selection (B5.4, FDP-03, D11).

TestRequest:20, ActiveDiagnosticPlanner:31

## backend/diagnose/bn.py (128 lines)

Diagnostic Bayesian Network and Hypothesis Ranking (B5.3, FDP-02..09, AIM-02, D11).

Evidence:25, Hypothesis:36, DiagnosticBayesianNetwork:45

## backend/diagnose/explain.py (78 lines)

Audience-Tailored Explanation Generator and XAI Metrics (B5.5, INN-06, VIS-02..04).

ExplanationBundle:30, ExplanationGenerator:40

## backend/dsp/__init__.py (5 lines)

DSP Package -- Order Tracking and Vibration Signal Processing for Propulsion Digital Twin.



## backend/dsp/order_tracker.py (179 lines)

Order-Tracking Vibration Digital Signal Processing (DSP) Module (B2.4, HMS-09, PS-26054).

OrderSpectrumReport:20, OrderTracker:45

## backend/economics/impact.py (98 lines)

Fleet Economics, Mission Reliability, and Financial Impact Model (V7, INN-06).

CostModelParameters:16, FleetEconomicMetrics:25, FleetEconomicsModel:37

## backend/edge/__init__.py (3 lines)





## backend/edge/compressor.py (272 lines)

Edge feature compression, bandwidth and power accounting — F08 / F67 / F68.

LinkBudget:44, EdgeFeatureFrame:59, EdgeCompressor:115, PowerBudget:200, LatencyBudget:238

## backend/edge/node.py (88 lines)

EdgeNode -- persistence-gated scalar downlink with bandwidth, latency and power accounting (W4, D34).

EdgeProfile:28, EdgeNode:38

## backend/evaluation/__init__.py (55 lines)

ANUMAAN evaluation package.



## backend/evaluation/conformal.py (237 lines)

Conformal prediction for RUL intervals — F12 / F53.

Interval:44, _conformal_quantile:71, SplitConformalRUL:88, AdaptiveConformal:149, empirical_coverage:192, coverage_curve:218

## backend/evaluation/damage_accumulation.py (313 lines)

Physics-of-failure damage accumulation — F36 / F37.

Cycle:53, extract_turning_points:65, rainflow_cycles:92, CoffinManson:134, ShockCoolingLaw:166, ComponentDamage:195, DamageAccumulator:224, accumulate_from_series:302

## backend/evaluation/harness.py (422 lines)

Evaluation harness — closes G03, implements F18.

Scenario:44, ScenarioResult:64, EvaluationHarness:123

## backend/evaluation/prognostic_metrics.py (206 lines)

Standard PHM prognostic performance metrics — F60.

PrognosticSeries:48, _alpha_bounds:76, prognostic_horizon:82, alpha_lambda:104, relative_accuracy:124, convergence:139, evaluate:178

## backend/evaluation/threshold_baseline.py (217 lines)

Conventional threshold monitor, as a measured baseline — F13.

Limit:39, Alarm:57, ThresholdMonitor:97, compare_detection:161, false_alarm_rate:206

## backend/evaluation/validation.py (357 lines)

External validation, protocol correctness and novelty handling — F14/F16/F17/F62/F63.

ResidualShield:53, NoveltyGate:127, ad_scores:189, Sim2RealReport:248, validate_against_aces:276

## backend/fadec_emulator/emulator.py (122 lines)

FADEC Emulator with Cylinder Balancing, UDS Diagnostics, and XCP (B2.6, OPT-01/02, TEX-05, D09).

UDSResponse:24, FADECEmulator:32

## backend/federation/aggregator.py (110 lines)

Federated Aggregator with Differential Privacy and Canary Validation Gate (W7, INN-04, D28).

AggregationResult:19, FederatedAggregator:29

## backend/federation/colony.py (67 lines)

Federated Edge Colony Node and Local Update Extraction (W7, INN-04, D28).

ColonyModelDelta:15, ColonyNode:23

## backend/foundation/forecast_chronos.py (93 lines)

Probabilistic Time-Series Forecasting Interface (W8, INN-06, D35).

ForecastResult:18, TimeSeriesForecaster:28

## backend/foundation/tabpfn_wrapper.py (79 lines)

TabPFN In-Context Tabular Classifier Wrapper (W8, INN-06, D35).

TabularPrediction:18, InContextTabularClassifier:25

## backend/foundation/text_classifier.py (94 lines)

Zero-Shot Maintenance Log & PIREP Text Classifier (W10, INN-06, D35).

TextClassificationResult:17, MaintenanceTextClassifier:27

## backend/graph/__init__.py (11 lines)





## backend/graph/mission_graph.py (447 lines)

Mission Knowledge Graph & Fleet Intelligence Engine — Phase J
DRDO / iDEX Problem Statement ID: 26054

SortieNode:20, SubsystemNode:41, AnomalyEventNode:52, MaintenanceActionNode:70, MissionKnowledgeGraph:89

## backend/graph/mission_reporter.py (246 lines)

Post-Flight Mission Reporter — Phase J
DRDO / iDEX Problem Statement ID: 26054

_fmt_relative:47, MissionReporter:55

## backend/knowledge/loaders/__init__.py (34 lines)

Document Loaders and Ingestion Engine for Rotax 912 iS & UAV Manuals.
DRDO / iDEX Problem Statement ID: 26054

load_and_chunk_file:15

## backend/knowledge/loaders/chunker.py (78 lines)

Paragraph & Section Text Chunker for Aerospace Technical Documents.
DRDO / iDEX Problem Statement ID: 26054

chunk_document:12

## backend/knowledge/loaders/office_loader.py (74 lines)

Local Office (DOCX / PPTX) Document Loader for Engine Directives.
DRDO / iDEX Problem Statement ID: 26054

load_docx:13, load_pptx:48

## backend/knowledge/loaders/pdf_loader.py (57 lines)

Local PDF Document Loader for Aerospace & Engine Manuals.
DRDO / iDEX Problem Statement ID: 26054

load_pdf:13

## backend/knowledge/loaders/text_loader.py (26 lines)

Local Text / Markdown Loader for SOPs, Flight Manuals, and Directives.
DRDO / iDEX Problem Statement ID: 26054

load_text:10

## backend/knowledge/retrieval/__init__.py (7 lines)

Retrieval and Reranking Service for Rotax 912 iS & DRDO UAV Manuals.
DRDO / iDEX Problem Statement ID: 26054



## backend/knowledge/retrieval/embedding_index.py (99 lines)

Local Semantic Embedding Index for Aerospace Manuals.
DRDO / iDEX Problem Statement ID: 26054

_get_model:32, _corpus_fingerprint:59, semantic_rank:67

## backend/knowledge/retrieval/local_store.py (122 lines)

Local Technical Manual Knowledge Store.
DRDO / iDEX Problem Statement ID: 26054

LocalKnowledgeStore:31

## backend/knowledge/retrieval/reranker.py (85 lines)

Local Cross-Encoder Semantic Reranking Service for Aerospace Manuals.
DRDO / iDEX Problem Statement ID: 26054

_get_ranker:16, rerank_passages:28

## backend/link/link_emulator.py (113 lines)

Constrained Datalink Emulator and Priority Store-and-Forward (B2.7, INN-07, OPT-03).

QueuedPacket:23, DatalinkEmulator:30

## backend/maintenance/work_package.py (278 lines)

Automated Maintenance Work Package Generation and Opportunistic Scheduler (B10.1, B10.2, INN-06).

SparePart:21, MaintenanceTask:29, WorkPackage:43, WorkPackageGenerator:82

## backend/mission/__init__.py (10 lines)





## backend/mission/glide.py (226 lines)

MALE UAV Aerodynamic Glide Polar and Emergency Runway Reachability Module (PS-26054).

DiversionAirfield:19, AirfieldReachability:30, GlideAssessment:56, UAVGlidePolar:104

## backend/mission/prescriptive.py (264 lines)

Prescriptive advisory and mission re-planning — F57 / F58.

DerateOption:44, ReplanResult:81, PrescriptiveAdvisor:111

## backend/mission/profiles.py (107 lines)

MALE UAV Multi-Phase Mission Profiles (R10, B1.4, D16).

MissionPhase:17, MissionSegment:31, MissionProfile:42, create_standard_male_surveillance_mission:69, create_high_altitude_leh_mission:91

## backend/mission/reliability.py (391 lines)

Mission reliability — F56.

components_for_fault:80, MissionPhase:101, MissionProfile:129, ComponentHazard:181, DEFAULT_COMPONENTS:207, MissionReliabilityEngine:240, _wilson_interval:379

## backend/ml/__init__.py (6 lines)





## backend/ml/anomaly_detector.py (410 lines)

Residual Autoencoder — Unsupervised Anomaly Detector
DRDO / iDEX Problem Statement ID: 26054

_relu:32, _sigmoid_list:36, _matmul_bias:40, _mse:52, _he_init:56, _zeros:65, _normalise:94, AutoencoderWeights:108, ResidualAutoencoder:122

## backend/ml/crank_diagnostics.py (439 lines)

Per-cylinder combustion diagnostics from crank angular velocity — F02/F03/F04/F05/F06.

CylinderContribution:57, MisfireReport:79, CrankDiagnostics:119, angular_resample:311, order_spectrum:347, order_features:363, envelope_spectrum:398

## backend/ml/detection_pipeline.py (759 lines)

Integrated Real-Time Detection Pipeline — Plane 1
DRDO / iDEX Problem Statement ID: 26054

ThresholdBaselineReport:67, DiagnosticEvent:97, PipelineState:116, MajorityVoteBuffer:135, DetectionPipeline:181

## backend/ml/flyhash_novelty.py (237 lines)

FlyHash sparse coding for vibration/residual novelty detection.

residual_and_order_features:88, SparseRandomProjection:111, FlyHashEncoder:142, NoveltyReport:172, FlyNoveltyDetector:181

## backend/ml/rul_estimator.py (217 lines)

Rotax 912 iS Prognostics & Remaining Useful Life (RUL) Estimator
DRDO / iDEX Problem Statement ID: 26054

MissionGoNoGoAdvisory:15, RULEstimator:29

## backend/ml/spectral_analyser.py (279 lines)

Gearbox FFT Spectral Analyser
DRDO / iDEX Problem Statement ID: 26054

SpectralReport:33, GearboxSpectralAnalyser:60

## backend/ml/trend_analyser.py (755 lines)

Degradation Trend Analyser + Probabilistic RUL Engine
DRDO / iDEX Problem Statement ID: 26054

_linspace:45, _least_squares_linear:52, _fit_exponential:77, _fit_power_law:92, _aic:107, DegradationModel:115, ChannelTrendReport:126, RULEstimate:138, GoNoGoAdvisory:149, PrognosticsReport:159, ScoreBuffer:176, DegradationTrendAnalyser:249, ProbabilisticRULEstimator:447, PrognosticsWorker:616

## backend/performance/maps.py (144 lines)

Engine Performance Maps and Atmospheric Scaling (R9, B1.4, D16).

AtmosphericState:21, PerformanceMaps:29

## backend/physics/__init__.py (14 lines)





## backend/physics/combustion_ci.py (178 lines)

CI (Compression Ignition / CRDi) Combustion Physics Model (B2.1).

CICombustionParams:21, calc_ignition_delay_deg:34, double_wiebe_mass_burned:47, CICombustionModel:93

## backend/physics/crank_dynamics.py (364 lines)

Crank-angle-resolved engine dynamics — F01.

EngineGeometry:52, WiebeCombustion:125, CylinderState:149, CrankDynamicsModel:164

## backend/physics/engine_config.py (312 lines)

Engine class as configuration, not hardcoding — F31.

IgnitionMode:73, InductionType:78, CylinderLayout:84, TurbochargerSpec:110, EngineConfig:123, load_engine_config:296, available_engines:308

## backend/physics/exposure.py (229 lines)

Environmental exposure accumulator — F40.

ExposureRecord:41, ExposureAccumulator:72

## backend/physics/fuel_thermal.py (219 lines)

Fuel thermal management and cold-fuel risk — F42.

FuelProperties:41, FuelThermalState:76, FuelThermalModel:101

## backend/physics/induction.py (182 lines)

Induction path: air filter restriction and the dust-ingestion wear chain — F43.

DustEnvironment:40, InductionState:62, InductionModel:90

## backend/physics/injector_faults.py (274 lines)

Compression-ignition injector fault library — F41.

InjectorState:66, InjectorFault:88, InjectorBank:103

## backend/physics/oil_system.py (265 lines)

Oil system health: wear-metal spectrum, debris, blow-by — F39.

WearMetalLimits:63, OilState:85, OilSystemModel:114

## backend/physics/rail.py (110 lines)

Common-Rail Hydraulics and Injector Physics Model (B2.2, FDP-03).

RailConfig:21, CommonRailHydraulics:30

## backend/physics/sensor_validator.py (460 lines)

Sensor Sanity & Plausibility Validator
DRDO / iDEX Problem Statement ID: 26054

ChannelSanityStatus:67, SanityReport:79, SensorSanityValidator:101, apply_residual_shielding:409

## backend/physics/structure.py (143 lines)

Structural Dynamics and High-Rate Acoustic Waveform Physics (B2.3, B2.4, HMS-09, FDP-09).

BearingGeometry:23, StructuralAcoustics:54

## backend/physics/thermo_model.py (418 lines)

Rotax 912 iS Sport 1D Thermodynamic Physics Model & Residual Calculator
DRDO / iDEX Problem Statement ID: 26054

EnginePhysicalState:29, ResidualVector:87, RotaxThermoModel:117, lookup_performance_map:411

## backend/physics/turbo_model.py (254 lines)

Turbocharger / boosted induction model — F32.

isa_ambient:50, TurboState:65, TurboFaults:96, TurbochargerModel:105

## backend/plant/__init__.py (3 lines)





## backend/plant/adapter.py (187 lines)

Independent-plant adapter — bridges VirtualEngine into the twin's data path.

IndependentPlantAdapter:95

## backend/plant/sensors_hr.py (89 lines)

High-Rate Sensor Chain Emulation (B2.5, FDP-06).

TriggerWheelConfig:21, HighRateSensorChain:28

## backend/plant/virtual_engine.py (435 lines)

Independent virtual engine — the plant, not the twin. Closes G01.

EngineVariation:67, SensorChannel:97, SensorModel:130, VirtualEngine:164

## backend/prognose/rul.py (87 lines)

Dual-Path Remaining Useful Life (RUL) Prognostics (B6.1, CAP-06, AIM-05, D18).

RULEstimate:19, DualPathRULEstimator:32

## backend/reliability/__init__.py (4 lines)





## backend/reliability/fmeca.py (450 lines)

FMECA — failure mode, effects and criticality analysis — F33.

SeverityClass:36, FailureMode:48, FMECA:108, build_default_fmeca:220

## backend/reliability/isolability.py (292 lines)

Fault detectability and isolability analysis — F35.

IsolabilityReport:39, SignatureMatrix:77, canonical_signature:258, from_fmeca:276

## backend/reports/__init__.py (5 lines)





## backend/reports/mission_bundle.py (365 lines)

Mission Knowledge Graph -> Report Dump adapter — DRDO / iDEX PS-26054

build_and_write_mission_bundle:57, _build_health:139, _build_faults:177, _build_timeline:215, _build_predictions:294, _build_actions:328, _iso:364

## backend/reports/report_dump_writer.py (285 lines)

Post-Mission Report Dump Writer — DRDO / iDEX Problem Statement ID: 26054

default_report_root:73, worst_severity:78, format_elapsed:88, ReportDumpWriter:96, summarise_telemetry_csv:230

## backend/runtime/__init__.py (6 lines)





## backend/runtime/engine_runtime.py (754 lines)

EngineRuntime -- one engine profile's simulator + injectors + detector bank (R1/R2/R3/R7, D29, D05).

Tick:56, _first_cylinder_index:77, EngineRuntime:101

## backend/runtime/hub.py (90 lines)

RuntimeHub -- every engine profile runs concurrently; the dropdown selects which one gets the heavy tier
and the primary stream (R1, D29).  Deterministic: same seeds + same tick count => identical streams.

RuntimeHub:15

## backend/runtime/levers.py (46 lines)

Operating levers with first-order dynamics (R3, closes G02).

Levers:13

## backend/runtime/registry.py (51 lines)

Fault registry (R2, D30): which plant faults an engine profile accepts, and which of them the scalar
channels can actually see.  Faults are filtered per profile from the engine config, never hard-coded per engine.

FaultSpec:14, _all:23, _turbo:24, _ci:25, faults_for:46, thermal_visible_faults:50

## backend/runtime/sensor_levers.py (135 lines)

Sensor-layer fault levers (R7, D30): bias, drift, stuck, noise, dropout, and spoofing.

SensorFault:19, SensorLevers:27

## backend/security/can_ids.py (101 lines)

CAN Bus Intrusion Detection System (CAN IDS) (B9.1, INN-07, D17).

CANAlert:18, CANIntrusionDetector:26

## backend/security/merkle_log.py (85 lines)

Tamper-Evident Merkle-Sealed Flight Log (B9.1, INN-07, D17).

FlightLogEntry:18, MerkleFlightLog:26

## backend/server/__init__.py (4 lines)

Rotax 912 iS MALE UAV Digital Twin — Laptop Backend Server Package
DRDO / iDEX Problem Statement ID: 26054



## backend/server/engine_api.py (256 lines)

Engine API (R4): per-engine REST + WebSocket routes over the concurrent RuntimeHub (D29).

get_hub:32, _rt:47, SelectBody:54, FaultBody:58, LeverBody:67, list_engines:74, select_engine:79, engine_state:89, engine_history:97, engine_events:150, engine_schema:167, inject_fault:177, clear_faults:208, set_levers:214, ws_engine:219, ws_fleet:237

## backend/server/engine_service.py (1043 lines)

Authoritative Real-Time Engine & Analytics Service
Rotax 912 iS MALE UAV Digital Twin — Laptop Backend Server
DRDO / iDEX Problem Statement ID: 26054

EngineStateService:97

## backend/server/main.py (623 lines)

FastAPI Real-Time Telemetry & Control Server
Rotax 912 iS MALE UAV Digital Twin — Laptop Backend Server
DRDO / iDEX Problem Statement ID: 26054

AIAskRequest:67, VoiceResetRequest:71, MaintenanceSignoffRequest:75, FlightCommandRequest:79, lifespan:99, serve_threejs_twin:143, broadcast_telemetry_loop:174, root:212, get_health:240, get_current_state:255, post_control_command:262, export_cbm_debrief:272, get_fleet_cbm_summary:284, get_region_comparison:297, list_replay_manifests:309, get_replay_manifest:315, get_replay_frame:324, post_flight_command:333, list_maintenance_work_orders:351, signoff_maintenance_action:360, get_ai_status:385, warmup_ai_engine:392, ask_ai_copilot:401, get_voice_status:424, warmup_voice_engines:436, reset_voice_session:459, voice_converse:467, get_voice_thinking:540, websocket_telemetry_endpoint:557, websocket_blender_endpoint:589

## backend/server/schemas.py (180 lines)

Pydantic Data Schemas & API Contracts
Rotax 912 iS MALE UAV Digital Twin — Laptop Backend Server
DRDO / iDEX Problem Statement ID: 26054

EngineTelemetry:11, AnalyticsState:62, UnifiedTelemetryState:133, ControlCommand:144, VoiceConverseResponse:158, ServerHealthResponse:171

## backend/sources/__init__.py (1 lines)





## backend/sources/plant_source.py (56 lines)

PlantSource -- the current independent plant behind the canonical Frame contract (B1.2, part 1).

PlantSource:24

## backend/sources/recorder.py (60 lines)

Recorder + ReplaySource (W3, B1.2): record any Frame stream to .npz + manifest and replay it bit-exactly.

record:21, ReplaySource:38

## backend/sources/waveform.py (209 lines)

WaveformSource and WaveformRecorder (W3, SIM-03): High-rate CycleBlock acquisition and .npz recording/replay.

WaveformSource:26, WaveformRecorder:147

## backend/telemetry/__init__.py (3 lines)





## backend/telemetry/aces_loader.py (289 lines)

NASA ACES real-telemetry loader — F48.

_decode_name_matrix:165, ACESGranule:182, load_granule:271, list_granules:285

## backend/telemetry/can_streamer.py (512 lines)

Rotax 912 iS Telemetry Streamer & DRDO Fault Injector
DRDO / iDEX Problem Statement ID: 26054

TelemetryStreamer:75

## backend/telemetry/mavlink_efi.py (209 lines)

MAVLink EFI_STATUS ingestion — F46.

EFIFrame:82, efi_to_anumaan:98, MAVLinkEFISource:132, replay_tlog:192

## backend/telemetry/replay_engine.py (203 lines)

Historical Mission Replay Engine (PRD F12 / final_tasks/02_HISTORICAL_MISSION_REPLAY_AND_SCRUBBER.md).
DRDO / iDEX Problem Statement ID: 26054

_repo_root:23, default_report_dump_dir:27, _FrameIndex:32, ReplayEngine:45

## backend/telemetry/socketcan_bridge.py (182 lines)

SocketCAN & SAE J1939 Telemetry Ingestion Bridge
DRDO / iDEX Problem Statement ID: 26054 — Defence GCS Ready Ingestion

SocketCANBridge:28

## backend/twin/__init__.py (4 lines)





## backend/twin/degradation.py (136 lines)

Degradation Particle Filter and SINDy Law Identification (B4.4, CAP-05/13, INN-01).

SINDyIdentifier:17, DegradationParticleFilter:88

## backend/twin/history.py (107 lines)

Operational History and Severity Accumulator per Tail (R11, B4.6).

MaintenanceRecord:19, TailHistoryState:29, OperationalHistoryTracker:57

## backend/twin/integrity.py (301 lines)

Physics-constrained telemetry integrity — F54 / F55.

PhysicalConstraint:55, default_constraints:81, _expected_map:142, IntegrityVerdict:149, TelemetryIntegrityMonitor:172

## backend/twin/model.py (158 lines)

Dynamic Lumped-Parameter Thermofluid Twin Model (B4.1, B4.6, D03).

ThermofluidParams:21, DynamicThermofluidModel:34

## backend/twin/priors.py (64 lines)

Hierarchical Fleet Priors and Empirical Bayes Personalization (B4.5, SYS-09).

FleetPrior:15, TailPriorEngine:38

## backend/twin/residual_detector.py (243 lines)

Physics-residual detector with per-tail calibration — F50, and the detector the
evaluation harness actually needs.

ExpectationModel:48, DetectionVerdict:89, ResidualDetector:107

## backend/twin/ukf.py (195 lines)

UKF Joint State and Parameter Estimation Twin (B4.2, CAP-11, DTC-02/04).

ParameterEstimate:24, ThermofluidUKF:39

## backend/twin/validity.py (323 lines)

Twin validity monitoring — F51 / F52.

chi2_bounds:60, ValidityVerdict:84, TwinValidityMonitor:124

## backend/twin/virtual_sensors.py (89 lines)

Virtual Sensor Synthesis Module (B4.2, CAP-11, DRDO PS-26054).

VirtualSensorSynthesizer:20

## backend/voice/__init__.py (5 lines)

Voice Interaction Layer (Plane 2 extension) — Speech-to-Text, Text-to-Speech, and
multi-turn conversational orchestration for the Mission Copilot.
DRDO / iDEX Problem Statement ID: 26054



## backend/voice/conversation.py (50 lines)

Voice Conversation State Manager.
DRDO / iDEX Problem Statement ID: 26054

VoiceConversationManager:21

## backend/voice/stt_engine.py (192 lines)

Local Whisper.cpp Speech-to-Text Engine — ggml-tiny.en (CPU, offline).
DRDO / iDEX Problem Statement ID: 26054

_find_ffmpeg:55, LocalWhisperSTT:67

## backend/voice/thinking_stream.py (48 lines)

Live "Thinking" Preview Buffer for the Voice Copilot.
DRDO / iDEX Problem Statement ID: 26054

ThinkingStreamStore:24

## backend/voice/tts_engine.py (177 lines)

Local Kokoro-82M Text-to-Speech Engine (offline, GPU-accelerated when available).
DRDO / iDEX Problem Statement ID: 26054

LocalKokoroTTS:43

## experiments/E17_detector_bakeoff_plant.py (315 lines)

E17 -- Universal vs per-engine detectors, and fly-inspired novelty vs classical, on the
multi-engine plant.  (docs/build/DETECTOR_DECISION.md)

simulate_run:59, build:78, design:95, Calib:100, stack:133, FBF:141, Maha:165, MaxZ:176, IF:184, novelty_metrics:193, rf:207, macro_f1:211, main:215

## experiments/E19_connectome_reservoir.py (126 lines)

E19 - fly connectome as a reservoir (temporal detector) vs its own controls.
Evidence class: SIMULATION (plant data).  Pre-registered rule: docs/build/FLY_100_WAYS.md.
Contenders (same z-features, same ridge readout unless noted):
  connectome | shuffled (edge-target rewired) | random ESN (same N/nnz) | windowed RF | static RF

load_conn:31, scale:43, shuffled:51, random_esn:58, run_res:65, feats:74, mf1:78, windowed:82, main:87

## experiments/E20_runtime_end_to_end.py (77 lines)

E20 - end-to-end evidence through the PRODUCT code path (RuntimeHub / EngineRuntime), not an experiment script.

one:29, main:53

## experiments/E21_twin_estimation.py (120 lines)

Experiment E21: Dynamic Twin Joint State/Parameter Estimation & SINDy Law Recovery (B4.1, B4.2, B4.4).

run_experiment:30

## experiments/E22_diag_prognostics.py (98 lines)

Experiment E22: Diagnosis, Active Test Selection, Dual-Path Prognostics, and Alarm Management (B5.3, B5.4, B6.1, B6.3).

run_experiment:32

## experiments/E23_edgelink_security.py (243 lines)

E23: Datalink, FADEC Emulation, and Cybersecurity Benchmark (B2.6, B2.7, B9.1, OPT-01, OPT-02, OPT-03, INN-07, D17).

run_e23_benchmark:30

## experiments/E24_fleet_des.py (268 lines)

E24: 12-Tail 3-Base Discrete Event Simulation (DES) Fleet Reliability & Economics (B10.1, B10.2, V7, R9, R10, R11).

SimulatedTail:41, run_e24_fleet_simulation:55

## experiments/E25_foundation_bakeoff.py (193 lines)

E25: Foundation Model Bake-off: PIREP NLP, Chronos Forecasting, and In-Context Tabular (W8, W10, INN-06, D35).

run_e25_bakeoff:27

## frontend/src/App.tsx (344 lines)

Frontend source / stylesheet.



## frontend/src/index.css (328 lines)

Frontend source / stylesheet.



## frontend/src/main.tsx (10 lines)

Frontend source / stylesheet.



## frontend/src/vite-env.d.ts (1 lines)

Frontend source / stylesheet.



## frontend/src/components/AerospaceMarkdown.tsx (209 lines)

Frontend source / stylesheet.



## frontend/src/components/CalculationsPanel.tsx (193 lines)

Frontend source / stylesheet.



## frontend/src/components/ConnectionModal.tsx (210 lines)

Frontend source / stylesheet.



## frontend/src/components/DiagnosticCard.tsx (358 lines)

Frontend source / stylesheet.



## frontend/src/components/EngineControls.tsx (217 lines)

Frontend source / stylesheet.



## frontend/src/components/EngineRuntimeConsole.tsx (121 lines)

Frontend source / stylesheet.



## frontend/src/components/FaultMatrix.tsx (127 lines)

Frontend source / stylesheet.



## frontend/src/components/Header.tsx (193 lines)

Frontend source / stylesheet.



## frontend/src/components/MaintenanceDashboardPanel.tsx (475 lines)

Frontend source / stylesheet.



## frontend/src/components/MissionReadinessCard.tsx (199 lines)

Frontend source / stylesheet.



## frontend/src/components/MissionReplayScrubber.tsx (213 lines)

Frontend source / stylesheet.



## frontend/src/components/PanelErrorBoundary.tsx (62 lines)

Frontend source / stylesheet.



## frontend/src/components/PropulsionEngineerPanel.tsx (546 lines)

Frontend source / stylesheet.



## frontend/src/components/ReadingsPanel.tsx (226 lines)

Frontend source / stylesheet.



## frontend/src/components/SubsystemHealthCard.tsx (182 lines)

Frontend source / stylesheet.



## frontend/src/components/VoiceCopilot.tsx (894 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/AnumaanSplash.tsx (151 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/HudFrame.tsx (219 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingArchitecture.tsx (159 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingDetection.tsx (141 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingExploreCTA.tsx (193 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingFleetMap.tsx (271 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingFooter.tsx (47 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingGCSPreview.tsx (323 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingHero3D.tsx (582 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingMatrix.tsx (270 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingNav.tsx (69 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingPage.tsx (249 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingPillars.tsx (247 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingProblem.tsx (211 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingPrognosis.tsx (125 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingReliability.tsx (136 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingTheatres.tsx (138 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingTicker.tsx (81 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/LandingTwin.tsx (153 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/aeroLineup.ts (141 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/anumaan-splash.css (236 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/hud-frame.css (612 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/landing-editorial.css (1029 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/landing-investigation.css (916 lines)

Frontend source / stylesheet.



## frontend/src/components/landing/landing.css (127 lines)

Frontend source / stylesheet.



## frontend/src/hooks/useEngineRuntime.ts (129 lines)

Frontend source / stylesheet.



## frontend/src/hooks/useMissionReplay.ts (232 lines)

Frontend source / stylesheet.



## frontend/src/hooks/useTelemetrySocket.ts (287 lines)

Frontend source / stylesheet.



## frontend/src/types/telemetry.ts (192 lines)

Frontend source / stylesheet.



## scripts/audit_aero_dt_coverage.py (104 lines)

Audit script for Aero Piston Engine Digital Twin Knowledge Base (DRDO PS 26054).
Verifies 100% presence, distribution, and depth across all 36 prompt dimensions and PS requirements.



## scripts/audit_drdo_intent_coverage.py (91 lines)

Audit script for DRDO Intent & Expected Solution Knowledge Base (DRDO PS 26054).
Verifies 100% presence, distribution, and depth across all 31 prompt dimensions and requirements.



## scripts/audit_fl_coverage.py (59 lines)





## scripts/audit_ideal_blueprint_coverage.py (79 lines)

Coverage and Verification Audit for Ideal Project Blueprint Suite (DRDO PS 26054).
Verifies that all 32 required architectural sections, principles, formulas, and diagrams
are comprehensively covered across the 8 blueprint volumes and master portal in final_touch/.



## scripts/build_aero_dt_knowledge_base.py (82 lines)

Master Builder for Aero Piston Engine Digital Twin Knowledge Base (DRDO PS 26054).
Compiles 10 exhaustive, peer-reviewed, defense-grade markdown volumes covering:
1. PS Deconstruction & Traceability Matrix
2. Aero-Engine Physics, Thermodynamics & UAV Systems
3. Failure Modes, FMECA & Reliability Engineering
4. Digital Twin Theory, State Estimation & Simulation
5. AI/ML Prognostics, RUL & Uncertainty Quantification
6. Avionics Hardware, Edge AI & System Interfaces
7. GCS HMI, Mission Decision Support & Fleet Federated Learning
8. DRDO Ecosystem, Certification, Airworthiness & Supply Chain
9. Red-Team Review, Gaps, Benchmarking & Evidence Base
10. Master Conceptual Synthesis & Architectural Portal



## scripts/build_architecture_knowledge.py (731 lines)

Script to generate comprehensive Architecture Knowledge, Mental Models, Data Flows,
Mind Maps, and Feature Deep-Dives for Project ANUMAAN (DRDO / SIH PS-26054).
Outputs to final_touch/ and final touch/ directories.

main:706

## scripts/build_drdo_intent_knowledge_base.py (75 lines)

Master Builder for DRDO Intent & Expected Solution Knowledge Base (DRDO PS 26054).
Compiles 8 exhaustive research volumes reverse-engineering the engineering intent behind PS 26054:
1. DRDO_INTENT_PS_DECONSTRUCTION_AND_SEMANTICS.md
2. DRDO_INTENT_END_TO_END_SYSTEM_RECONSTRUCTION.md
3. DRDO_INTENT_PHYSICS_AND_AI_HYBRID_COUPLING.md
4. DRDO_INTENT_HEALTH_MONITORING_AND_PARAM_CORRELATION.md
5. DRDO_INTENT_MISSION_RELIABILITY_REPLAY_AND_GCS.md
6. DRDO_INTENT_DEFENCE_GRADE_CERTIFICATION_AND_EVIDENCE.md
7. DRDO_INTENT_CREDIBILITY_REDTEAM_AND_PROJECT_GAP_ANALYSIS.md
8. MASTER_DRDO_EXPECTED_SOLUTION_SYNTHESIS.md



## scripts/build_fl_knowledge_base.py (1153 lines)

Comprehensive Federated Learning Knowledge Base Builder (Version 3 - 100% Audited).
Extracted from FedNeMo papers, implementation code, PRDs, and design documents.
Outputs to final_touch/ and final touch/.



## scripts/build_ideal_project_blueprint.py (178 lines)

Master Builder for Ideal Project Blueprint (DRDO PS 26054).
Compiles 8 comprehensive, deeply reasoned, technically defensible engineering volumes
and an overarching Master Synthesis Portal into:
- e:/backup-llm/backup-no-llm/3d_engine/final_touch/
- e:/backup-llm/backup-no-llm/3d_engine/final touch/



## scripts/generate_analysis_md.py (602 lines)

Comprehensive File-by-File Repository Audit Generator
Target: final_touch/analysis.md and 'final touch/analysis.md'
Workspace: e:/backup-llm/backup-no-llm/3d_engine
DRDO / SIH Problem Statement ID: 26054 (ANUMAAN Digital Twin)

get_file_stats:25, analyze_python_file:40, infer_python_purpose:109, analyze_js_ts_file:195, analyze_markdown_file:247, analyze_json_yaml_file:293, analyze_batch_file:327, analyze_csv_data_file:356, analyze_binary_asset_file:376, audit_single_file:426, main:445

## scripts/generate_rotax_manifests.py (378 lines)

Generate asset manifests for the three Rotax engines from their shipped GLB geometry.

glb_node_names:57, group_of:67, cylinder_of:84, classify:133, resolve_thermal:141, build:297, main:359

## scripts/ingest_rag_docs.py (573 lines)

RAG Knowledge Ingestion & Document Downloader / Generator
DRDO / iDEX Problem Statement ID: 26054 — Rotax 912 iS Digital Twin

build_pdf_doc:441, build_docx_doc:496, ingest_knowledge:522

## scripts/inject_pixelcode_avionix.py (19 lines)





## scripts/populate_engine_references.py (50 lines)





## scripts/render_cad_rotax.py (127 lines)



setup_render_settings:5, clear_lights_cameras:14, add_studio_lighting:19, get_scene_bbox:44, render_multi_views:62

## scripts/run_15_step_verification_demo.py (251 lines)

ANUMAAN 15-STEP TECHNICAL VERIFICATION DEMONSTRATION SCRIPT
DRDO / iDEX Problem Statement ID: 26054

print_step:32, run_15_step_verification:39

## scripts/simulate_missions.py (153 lines)

Accelerated mission generator -> report_dump/
DRDO / iDEX Problem Statement ID: 26054

simulate_mission:47, _apply_simulated_timescale:91, _close_telemetry_log:121, main:130

## scripts/test_socketcan_mavlink_bridge.py (131 lines)

Test & Verification: SocketCAN, MAVLink EFI, and VRDE-Jayem Aero-Diesel Ingestion
DRDO / iDEX Problem Statement ID: 26054

test_socketcan:17, test_mavlink:57, test_engine_configurations:93

## scripts/verify_kinematics.py (65 lines)





## scripts/blueprint_builder/vol1_master_executive_and_requirements.py (190 lines)

Blueprint Volume 1: Master Executive Philosophy, Requirements Re-Derivation, and System Boundaries.
Defines the executive architecture, first principles, PS traceability matrix, master mental model, and system boundaries.



## scripts/blueprint_builder/vol2_physics_twin_and_state_estimation.py (205 lines)

Blueprint Volume 2: Physics Engine, Dynamic State Observer, and Digital Twin Core.
Defines the genuine digital twin definition, 0D/1D thermodynamic MVEM formulations,
Extended Kalman Filter (EKF), virtual sensors, state vector, and synchronization.



## scripts/blueprint_builder/vol3_health_monitoring_and_fault_management.py (230 lines)

Blueprint Volume 3: Health Monitoring, Sensor Validation, and Fault Management Pipeline.
Defines parity space sensor validation, thermodynamic residual generation, composite Health Indices,
Deep VAE + Extreme Value Theory anomaly detection, and the 10-stage FMECA fault management chain.



## scripts/blueprint_builder/vol4_prognostics_mission_reliability_and_flight_envelope.py (192 lines)

Blueprint Volume 4: Prognostics, RUL, and Mission Reliability Coupling.
Defines physics-informed degradation kinetics, Wiener drift processes, Conformal Prediction RUL intervals,
tactical flight envelope derating, and aircraft aerodynamic glide polar reachability cone.



## scripts/blueprint_builder/vol5_avionics_edge_and_gcs_hmi.py (162 lines)

Blueprint Volume 5: Avionics Ingestion, Edge Architecture, and Dual-Role GCS HMI.
Defines avionics bus protocols (SocketCAN, MAVLink, ARINC 429), edge FFT processing,
170ms latency budget, dual-role HMI (Pilot HUD vs Propulsion Console), and EEMUA 191 alarm rationalization.



## scripts/blueprint_builder/vol6_fleet_intelligence_and_federated_learning.py (158 lines)

Blueprint Volume 6: Fleet Intelligence, Cross-Engine Analytics, and Disciplined Federated Learning.
Defines the justification for FL in defence, hierarchical depot topology, Differential Privacy,
FedRand/StochasticLoRA parameter-efficient aggregation, non-IID handling, and fleet population benchmarking.



## scripts/blueprint_builder/vol7_verification_certification_and_security.py (195 lines)

Blueprint Volume 7: Verification & Validation Pyramid, Sim-to-Real, Aerospace Certification, and Security.
Defines the 10-level V&V pyramid, domain randomization sim-to-real transfer, CEMILAC DO-178C DAL-C roadmap,
ASTM F3269-17 Run-Time Verification Monitor, and multi-layer defence cybersecurity.



## scripts/blueprint_builder/vol8_gap_analysis_implementation_roadmap_and_review.py (456 lines)

Blueprint Volume 8: Codebase Gap Analysis, Technology Stack, Repository Structure, and Engineering Roadmap.
Defines tech stack justification, 3d_engine gap analysis (Keep/Refactor/Replace/Remove/Add/Defer/Investigate),
repository structure, data flow schemas, 5 user journeys, 15-step demo script, honesty manifesto, 13-phase roadmap, and 12-point review.



## scripts/dt_builder/vol10_master_portal.py (101 lines)

Volume 10: Master Conceptual Synthesis & Architectural Navigation Portal
For DRDO Problem Statement 26054: Aero Piston Engine Digital Twin for MALE UAVs



## scripts/dt_builder/vol1_ps_deconstruction.py (189 lines)

Volume 1: Problem Statement Deconstruction & Master Traceability Matrix
For DRDO Problem Statement 26054: Aero Piston Engine Digital Twin for MALE UAVs



## scripts/dt_builder/vol2_engine_physics.py (252 lines)

Volume 2: Aero-Engine Physics, Thermodynamics & UAV Propulsion Systems
For DRDO Problem Statement 26054: Aero Piston Engine Digital Twin for MALE UAVs



## scripts/dt_builder/vol3_failure_modes_fmeca.py (146 lines)

Volume 3: Failure Modes, FMECA & Reliability Engineering
For DRDO Problem Statement 26054: Aero Piston Engine Digital Twin for MALE UAVs



## scripts/dt_builder/vol4_digital_twin_theory.py (200 lines)

Volume 4: Digital Twin Theory, State Estimation & Simulation
For DRDO Problem Statement 26054: Aero Piston Engine Digital Twin for MALE UAVs



## scripts/dt_builder/vol5_ai_ml_prognostics.py (212 lines)

Volume 5: AI/ML Prognostics, RUL & Uncertainty Quantification
For DRDO Problem Statement 26054: Aero Piston Engine Digital Twin for MALE UAVs



## scripts/dt_builder/vol6_avionics_edge_interfaces.py (137 lines)

Volume 6: Avionics Hardware, Edge AI & System Interfaces
For DRDO Problem Statement 26054: Aero Piston Engine Digital Twin for MALE UAVs



## scripts/dt_builder/vol7_gcs_hmi_mission_fleet.py (141 lines)

Volume 7: GCS HMI, Mission Decision Support & Fleet Federated Learning
For DRDO Problem Statement 26054: Aero Piston Engine Digital Twin for MALE UAVs



## scripts/dt_builder/vol8_drdo_certification_supply.py (139 lines)

Volume 8: DRDO Ecosystem, Certification, Airworthiness & Supply Chain
For DRDO Problem Statement 26054: Aero Piston Engine Digital Twin for MALE UAVs



## scripts/dt_builder/vol9_red_team_gaps_evidence.py (142 lines)

Volume 9: Red-Team Review, Gaps, Benchmarking & Evidence Base
For DRDO Problem Statement 26054: Aero Piston Engine Digital Twin for MALE UAVs



## scripts/intent_builder/vol1_deconstruction_semantics.py (205 lines)

Volume 1: DRDO PS Deconstruction, Semantic Intent & The Master Solution Matrix
Reverse-engineering the engineering intent behind DRDO Problem Statement 26054.



## scripts/intent_builder/vol2_end_to_end_system.py (252 lines)

Volume 2: Reconstructed End-to-End System Architecture, Real-Time Latency & Modularity
Reverse-engineering the engineering intent behind DRDO Problem Statement 26054.



## scripts/intent_builder/vol3_physics_ai_coupling.py (151 lines)

Volume 3: The Physics-AI Coupling Engine, Degradation Tracking & RUL Feasibility
Reverse-engineering the engineering intent behind DRDO Problem Statement 26054.



## scripts/intent_builder/vol4_health_monitoring_params.py (144 lines)

Volume 4: Health Monitoring Parameters, Cross-Correlation & Diagnostic Spectrum
Reverse-engineering the engineering intent behind DRDO Problem Statement 26054.



## scripts/intent_builder/vol5_mission_reliability_gcs.py (135 lines)

Volume 5: Mission Reliability Enhancement, Mission Replay & Deployment Ecosystems
Reverse-engineering the engineering intent behind DRDO Problem Statement 26054.



## scripts/intent_builder/vol6_defence_certification_data.py (110 lines)

Volume 6: Defence-Grade Engineering, Certification Pathways & The Data Reality Check
Reverse-engineering the engineering intent behind DRDO Problem Statement 26054.



## scripts/intent_builder/vol7_credibility_gap_analysis.py (110 lines)

Volume 7: Credibility Engineering, Red-Team Review & Current Project Gap Analysis
Reverse-engineering the engineering intent behind DRDO Problem Statement 26054.



## scripts/intent_builder/vol8_master_intent_portal.py (59 lines)

Volume 8: Master DRDO Intent Synthesis & Architectural Navigation Portal
Reverse-engineering the engineering intent behind DRDO Problem Statement 26054.



## scripts/lib/anumaan_blender_lib.py (398 lines)



reset_scene:7, make_collections:17, unique_name:30, add_twin_nodes:38, create_pbr_material:177, material_library:212, skin_material:245, add_tracked_camera:251, studio_lighting:271, add_driver:306, loft_rings:319, curve_tube:347, tri_count:367, pack_and_save:389

## scripts/lib/anumaan_cad_lib.py (817 lines)

ANUMAAN CAD Mechanical Modeling Library
Provides high-density, manufacturing-grade mechanical component generators:
- Propeller drive flanges (counterbored bolt holes, central spigot, hollow bore)
- Cast reduction gearbox housings (radial reinforcement ribs, perimeter bolt circles, sight glass, inspection hatches, governor module)
- Engine blocks (inline-4 cast monoblocks, inter-cylinder valleys, stiffening webs, starter pockets)
- Deep structural oil sumps (cooling fins, flanged rails, magnetic drain plugs, turbo oil drain bosses)
- Billet engine mounting brackets (cooling fins, rubber isolation bushings, through-bolts)
- Cylinder heads & valve covers (recessed bolt wells, cam domes, oil filler necks, glow plugs)
- Common rail fuel injection (forged rails, pressure sensors, solenoid injec

bmesh_add_cylinder:23, add_hex_bolt:30, add_bolt_circle:70, build_propeller_flange:86, build_spiral_volute:116, build_plate_fin_cooler:163, build_detailed_alternator_saha:194, build_billet_engine_mount:309, build_tbolt_hose_clamp:365, build_fadec_ecu_box:395, build_tube_mesh:426, build_curved_tube_object:498, build_diecast_rib:507, build_organic_gearbox_casing:554, build_industrial_turbo:630

## scripts/lib/anumaan_twin_controller.py (215 lines)

ANUMAAN Universal Digital Twin Controller
Embedded into .blend assets alongside <asset_id>_manifest.json
Fully generic, reads all components, faults, cameras and mechanisms from the manifest.

get_manifest:11, ANUMAAN_PT_Controller:20, ANUMAAN_OT_SetDisplayMode:76, ANUMAAN_OT_SwitchCamera:99, ANUMAAN_OT_ApplyFault:109, ANUMAAN_OT_ClearState:160, register:183, unregister:204

## scripts/tools/audit_reachability.py (148 lines)

Reachability audit -- which Python modules are LIVE, HARNESS/TEST-only, or DEAD?

module_name:29, collect:37, imports_of:47, closure:84, main:95

## scripts/tools/build_all_proper_blends.py (280 lines)

Comprehensive Engine Blend Master Builder
Transforms and finalizes all 5 UAV engines into complete, production-grade .blend files:
1. Rotax 914 F Turbo: Complete 590-part CAD assembly from Rotax 914.stp with full PBR shading, turbo highlights, studio lights, camera.
2. Rotax 915 iS: Complete 45MB CAD geometry with full PBR shaders, studio lights, camera, and Collection_Rotax_915iS.
3. VRDE / Jayem 2.2L: Complete 472-part CRDi turbodiesel CAD assembly with studio lights, camera, and Collection_VRDE_2_2L.
4. Austro Engine AE300: Complete common-rail diesel CAD assembly with studio lights, camera, and Collection_Austro_AE300.
5. Rotax 912 iS Sport: Standard baseline digital twin with Collection_Rotax_912iS.
6. Anumaan Master Twin: Master scene containing all 5 distinct CAD collections for ins

create_pbr_mat:24, add_studio_setup:48, finalize_rotax_914:104, finalize_rotax_915:167, finalize_master_twin:217, main:273

## scripts/tools/build_master_twin_blend.py (133 lines)

Master Blend Builder for ANUMAAN Multi-Engine Digital Twin
Combines all 5 UAV engines into a single optimized master blend file:
- Rotax 912 iS Sport
- Rotax 914 F Turbo
- Rotax 915 iS A Turbo Intercooled
- Austro Engine AE300 / AE330
- VRDE / JAYEM 2.2L

main:25

## scripts/tools/build_rotax_914_turbo.py (284 lines)

Rotax 914 F Turbo CAD Model Rebuilder
Rebuilds the genuine Rotax 914 Turbo aero-engine directly from the CAD assembly geometry.
Creates discrete named components, authentic PBR materials, millimeter-to-meter scaling,
studio lighting, camera rigs, saves standalone .blend files and exports the web GLB.

create_pbr_material:24, setup_materials:49, build_rotax_914_model:68

## scripts/tools/compose_ai_target_sheets.py (126 lines)

Composite the alpha renders onto the ai-tagert studio backdrop and build sheets.

font:13, flatten:17, trim:23, fit:37, sheet:52

## scripts/tools/composite_showcase_hud.py (566 lines)

Aerospace HUD Compositor for Rotax 914 F Technical Cinematic Showcase
======================================================================
Composites high-end aerospace digital twin HUD graphics onto rendered frames:
- 3D-tracked anchor points with pulsing reticles
- Anti-aliased 45° angled leader lines
- Glassmorphic aerospace telemetry cards with detailed engineering specs
- Top global telemetry banner with live parameters
- Bottom 6-station progression ribbon
- Master Station 6 multi-sensor telemetry cluster
- Encodes 1080p MP4 cinematic video via OpenCV
- Generates 3×2 Master Contact Sheet via Pillow

draw_hud_overlay:182, composite_all_stations:410, composite_all_frames:446, encode_cinematic_mp4:476, generate_master_contact_sheet:508

## scripts/tools/create_engine_blend_files.py (196 lines)

Engine Blend Generator — Creates dedicated, fully-configured standalone .blend files
for all engine variants:
- VRDE / Jayem 2.2L (Indigenous DRDO CRDi Diesel) -> assets/blender/vrde_jayem_2_2l.blend
- Rotax 914 F (Turbocharged TCU)                  -> assets/blender/rotax_914.blend & rotax_914_f.blend
- Austro Engine AE300 (Jet-A1 Common Rail Diesel) -> assets/blender/austro_ae300.blend

setup_studio_lighting_and_camera:20, create_vrde_jayem_blend:80, create_rotax_914_blend:117, create_austro_ae300_blend:155, main:189

## scripts/tools/export_all_engine_glbs.py (98 lines)

Exporter Script: Exports all 5 UAV engines into optimized Draco-compressed GLB models for WebGL.

export_collection_to_glb:19, main:61

## scripts/tools/generate_all_engine_showcases.py (1170 lines)

Universal Multi-Engine Cinematic Showcase Generator — DRDO ANUMAAN
===================================================================
Generates complete 6-station cinematic technical showcases for all ANUMAAN engines:
- rotax_912is    : Rotax 912 iS Sport (Naturally Aspirated Spark Ignition, Dual FADEC)
- rotax_914      : Rotax 914 F (Turbocharged Spark Ignition)
- rotax_915is    : Rotax 915 iS (Turbocharged Intercooled Spark Ignition)
- austro_ae300   : Austro Engine AE300 / AE330 (Common-Rail Turbo Diesel, Jet-A1)
- vrde_jayem_2_2l: DRDO VRDE / Jayem 2.2L (Indigenous 180 HP CRDi Turbo Diesel)

generate_blender_script:523, composite_engine_hud:826, run_engine_showcase:1117

## scripts/tools/import_rotax_914_cad_to_blend.py (183 lines)

Import Rotax 914 CAD STL to Master Blend File
Imports the genuine 122.8 MB Rotax 914 Turbo CAD mesh, scales/centers/orients it properly,
separates into components/loose parts, applies multi-material shading (engine block, cylinder heads,
turbocharger turbine/compressor, exhaust downpipes, intake runners, fasteners), sets up studio lighting,
and saves to assets/blender/rotax_914.blend and assets/blender/rotax_914_f.blend.

create_pbr_material:21, main:46

## scripts/tools/inspect_blend.py (145 lines)



inspect_scene:7

## scripts/tools/probe_api.py (93 lines)



probe:5

## scripts/tools/render_acceptance.py (159 lines)

ANUMAAN - Master Acceptance Renderer
Renders full acceptance set per Section 15.3 and writes render_manifest.json

render_acceptance_set:14

## scripts/tools/render_ai_target_360.py (184 lines)

Render tei_pd170 at the angles defined by the ai-tagert 360 reference set.

side_of:38, aim:95, place_rig:98, fits:116, shoot:126, ortho_fit:154

## scripts/tools/render_all_engines.py (375 lines)

Multi-Engine 3D Rendering Pipeline — ANUMAAN
Renders high-resolution beauty shots and fault visualization stills for all 5 UAV engines:
- Rotax 912 iS (Naturally Aspirated Spark Ignition)
- Rotax 914 (Turbocharged Spark Ignition)
- Rotax 915 iS (Turbocharged Intercooled Spark Ignition)
- Austro AE300 / AE330 (Common-Rail Turbo Diesel)
- VRDE / JAYEM 2.2L (Indigenous 180 hp CRDi Turbo Diesel)

create_fault_emission_material:236, setup_camera:252, render_engine:268, main:361

## scripts/tools/render_austro_all_views.py (39 lines)





## scripts/tools/render_rotax_914_showcase.py (488 lines)

Rotax 914 F Turbo — Technical Digital Twin Cinematic Showcase
=============================================================
Produces a 20-second (480 frames @ 24fps) cinematic engineering showcase:

compute_engine_bounds:54, orbit_point:74, setup_world:88, setup_studio_lighting:107, setup_floor:142, setup_camera_choreography:173, compute_and_save_tracking_data:294, configure_render:336, render_station_stills:370, render_animation_frames:396, main:419

## scripts/tools/update_master_twin.py (49 lines)

Update Master Twin Blend:
Ensures assets/blender/anumaan_master_twin.blend has all 5 collections properly populated
with their distinct engine meshes and materials.

update_master_twin:15

## scripts/validate/validate_asset.py (236 lines)



run_validation:9

## tests/__init__.py (1 lines)





## tests/test_aces_channel_binding.py (111 lines)

ACES EGT/CHT channel-binding fix (B0.3).

test_egt_channels_bind_to_distinct_named_columns_not_to_water_temp:37, test_egt_values_are_no_longer_the_170_degree_misbinding:57, test_cht_egt3_egt4_now_resolve:75, test_find_channel_requires_start_of_string_match:88, test_manifest_records_the_unit_caveat:100

## tests/test_adversarial_validation.py (416 lines)

Adversarial Validation Suite — DRDO iDEX PS-26054
===================================================
Verifies behavioral correctness under controlled perturbations:

calibrated_runtime:56, run_ticks:62, TestSensorFaultDiscrimination:71, TestPrognosticSensitivity:142, TestDamageAccumulation:186, TestConformalRULIntegrity:235, TestDeterministicReplay:270, TestMultiEngineAgnostic:303, TestRuntimeHubAuthority:328, TestAdversarialSensors:352, TestEndToEndBehavioral:390

## tests/test_agent_and_graph.py (168 lines)

Unit Tests for Plane 2 Diagnostic Agent and Mission Knowledge Graph
DRDO / iDEX Problem Statement ID: 26054

TestDiagnosticAgent:19, TestMissionKnowledgeGraphAndReporter:48

## tests/test_analytical_pipeline.py (788 lines)

Comprehensive Test Suite — New Analytical Modules
DRDO / iDEX Problem Statement ID: 26054

nominal_state:43, _make_residual:62, TestSensorSanityValidator:79, TestResidualAutoencoder:142, TestGearboxSpectralAnalyser:245, TestTrendAnalyserFitting:324, TestProbabilisticRUL:387, TestScoreBuffer:470, TestMajorityVoteBuffer:516, TestDetectionPipeline:557, TestPS_Pillar2_EarlyWarning:638, TestPrognosticsWorker:748

## tests/test_camera_transitions.py (128 lines)



test_camera_movement_and_zooms:60

## tests/test_canonical_runtime_pipeline.py (158 lines)

End-to-End Acceptance Test for the Canonical Digital Twin Pipeline.
DRDO / iDEX Problem Statement ID: 26054.

test_canonical_runtime_pipeline_end_to_end:26, test_sensor_fault_shielding_and_attribution:97, test_engine_service_unified_state_serialization:119, test_multi_engine_agnostic_pipeline:148

## tests/test_causal_propagation.py (134 lines)

Unit Tests for Multi-Parameter Causal Fault Propagation
DRDO / iDEX PS-26054 Rotax 912 iS Digital Twin

test_streamer_fault_causality:12, test_engine_service_dynamic_subsystems:89

## tests/test_char_crank_telemetry.py (233 lines)

Characterization tests (B0.9): ml/crank_diagnostics, telemetry/{mavlink_efi,socketcan_bridge}.

traces:21, test_healthy_engine_is_nominal_and_uniform:32, test_dead_cylinder_attributed_and_net_absorbing:46, test_partial_misfire_reads_as_partial_but_still_flagged:63, test_misfire_rate_recovered_exactly:76, test_misfire_rate_monotone_in_fault_frequency:91, test_crank_diagnostics_reset_and_validation:102, test_healthy_four_cylinder_order2_dominance:115, test_order_helpers_edge_cases:130, test_angular_resample_speed_invariant_order_bin:137, test_envelope_spectrum_finds_modulation_tone:150, test_efi_to_anumaan_dict_mapping_and_units:162, test_efi_object_input_missing_and_bad_fields:180, test_mavlink_source_health_without_connection:188, test_socketcan_disconnected_is_inert:196, test_socketcan_pack_decode_roundtrip:205, test_socketcan_saturation_and_unknown_frame:225

## tests/test_char_evaluation.py (202 lines)

Characterization tests (B0.9): backend/evaluation/{conformal,damage_accumulation,prognostic_metrics}.

test_rainflow_astm_series_cycle_count:25, test_rainflow_total_is_half_the_number_of_ranges:36, test_rainflow_deterministic_and_simple_cases:41, test_turning_points_collapse_monotone_runs:50, test_coffin_manson_threshold_and_monotonic:54, test_shock_cooling_only_when_cooling_faster_than_limit:65, test_accumulator_damage_grows_with_swing_and_is_deterministic:73, test_accumulator_shock_cooling_streaming:91, test_accumulator_initial_damage_carried:103, _synthetic:111, test_split_conformal_coverage_on_seeded_set:117, test_conformal_interval_structure_and_monotonic_in_alpha:133, test_conformal_uncalibrated_raises_and_length_mismatch:145, test_coverage_curve_tracks_diagonal_roughly:153, test_adaptive_conformal_tracks_realised_coverage:165, test_prognostic_series_true_rul_and_validation:178, test_evaluate_good_predictor_passes_waterfall:185, test_evaluate_bad_predictor_gates_later_metrics:197

## tests/test_char_harness_osacbm_edge.py (213 lines)

Characterization tests (B0.9): evaluation/harness, osacbm, physics/exposure, edge/compressor.

test_harness_nominal_no_false_alarms_and_deterministic:19, test_harness_misfire_detected_by_crank_channel_on_right_cylinder:29, test_harness_cooling_degradation_plant_fails_and_twin_warns_first:41, test_harness_run_all_summary_and_markdown:51, test_default_scenarios_catalogue:60, test_osacbm_registry_headline:70, test_osacbm_registered_modules_import:81, test_osacbm_layering_violation_is_detected:86, test_exposure_baseline_environment_is_baseline:100, test_exposure_harsh_environment_accelerates_wear:111, test_exposure_start_stop_transitions:133, test_exposure_save_load_roundtrip:143, test_exposure_one_continuous_brownout_is_one_event:156, test_edge_frame_pack_layout_and_size:165, test_edge_compressor_build_publish_and_bandwidth:179, test_link_power_latency_budgets:202

## tests/test_char_mission.py (113 lines)

Characterization tests (B0.9): backend/mission/{reliability,prescriptive}.py

test_wilson_interval_values:11, test_profile_and_stress_factor:25, test_component_hazard_grows_with_damage:37, test_analytic_reliability_baseline:48, test_damage_lowers_reliability_and_derate_raises_it:60, test_monte_carlo_seeded_determinism_and_agreement_with_analytic:73, test_assess_verdicts:83, test_prescriptive_derate_options_shape_and_monotone_cost:91, test_prescriptive_advise_go_path:105

## tests/test_char_reliability.py (121 lines)

Characterization tests (B0.9): backend/reliability/{fmeca,isolability}.py

fmeca:13, test_failure_mode_scores:17, test_default_fmeca_headline_numbers:30, test_ranked_by_rpn_is_sorted_and_deterministic:42, test_fmeca_markdown_and_json:50, test_canonical_signature_collides_on_same_physics:60, _toy:66, test_toy_matrix_ambiguity_and_discriminator:74, test_isolability_monotone_in_channels_and_channel_value:89, test_default_fmeca_isolability_current_value:102, test_default_fmeca_dropping_channels_never_improves:115

## tests/test_char_twin.py (168 lines)

Characterization tests (B0.9): backend/twin/{validity,integrity}.py

test_chi2_bounds_shape:14, _feed:22, test_validity_nominal_is_trustworthy:30, test_validity_drift_and_fault_attribution:45, test_validity_bias_and_sensor_fault:58, test_validity_envelope_and_reset:68, test_validity_deterministic_for_same_input:79, _frame:90, test_default_constraints_zero_residual_on_ideal_frame:109, test_integrity_calibrated_accepts_nominal_and_flags_spoof:119, test_integrity_single_violation_is_sensor_fault:138, test_integrity_frozen_stale_and_lane_checks:149

## tests/test_char_validation_baseline.py (199 lines)

Characterization tests (B0.9): backend/evaluation/{validation,threshold_baseline}.py

test_threshold_debounce_and_levels:17, test_threshold_glitch_does_not_alarm_and_rearms:31, test_threshold_low_limits_and_unknown_channels:46, test_threshold_custom_limits:56, test_compare_detection_lead_time:61, test_false_alarm_rate:74, test_shield_quarantine_recovery_dwell:85, test_shield_dirty_again_resets_dwell:97, test_shield_shield_usable_health_index:106, test_novelty_gate_decisions:123, test_ad_scores_point_adjust_inflates:138, test_ad_scores_perfect_none_and_length_check:149, _Granule:159, _Model:181, test_validate_against_aces_fake_granule:186, test_validate_against_aces_missing_rpm_reports_error:197

## tests/test_copilot_and_knowledge.py (156 lines)

Test Suite for Ingested Knowledge Store, Document Loaders & Mission Copilot.
DRDO / iDEX Problem Statement ID: 26054

TestKnowledgeAndCopilot:21

## tests/test_core_pipeline_and_profile.py (157 lines)

Tests for backend/core/pipeline.py, channels.py, limits.py, and profile.py (B1.3, U1, U2, U3).

test_pipeline_layer_ordering:13, test_pipeline_unique_names:30, test_pipeline_execution_and_cadence:40, test_channel_registry:77, test_limits_check:94, test_engine_profile:138

## tests/test_data_and_federation_stack.py (107 lines)

Tests for DATA and Federation Stack (B7.1-B7.7, W7, INN-04, D19, D28, D35).

test_dataset_manifests_and_loaders:26, test_federated_colony_and_canary_gate:63

## tests/test_detect_stack.py (135 lines)

W1/W11: calibrated-residual detector, conformal thresholds, persistence gate, reservoir tier.

run:13, tail914:31, det914:38, test_frames_carry_command_fields:42, test_calibration_roundtrip:47, test_conformal_threshold_quantile:56, test_false_alarm_rate_bounded_on_fresh_nominal:62, test_calibration_is_per_tail:70, test_detects_faults_and_ranks_above_nominal:79, test_gate_and_evidence:87, test_persistence_gate:95, test_engine_agnostic_same_code_path:101, test_rejects_too_few_frames:110, test_reservoir_random_streams_and_separates:115, test_federated_fly_bloom_merge_equals_pooled:126

## tests/test_diag_stack.py (107 lines)

Tests for DIAG Stack (B5.3, B5.4, B5.5, B6.1, B6.3): BN diagnosis, active test selection, XAI, RUL, ISA-18.2.

test_bayesian_network_diagnosis:12, test_active_diagnostic_planner:28, test_explanation_generator:42, test_dual_path_rul_and_disagreement:53, test_isa18_alarm_management_and_shelving:83

## tests/test_edge_and_replay.py (66 lines)

W3/W4: recorder/replay bit-exactness and the edge node's gated downlink accounting.

flight:13, tail:26, test_record_replay_is_bit_exact:32, test_replay_detects_tampering:43, test_edge_gates_downlink_and_accounts:51, test_host_profile_is_labelled_measured:65

## tests/test_edgelink_stack.py (141 lines)

Tests for EDGELINK Stack (B2.6, B2.7, B9.1, OPT-01, OPT-02, OPT-03, INN-07, D17).

test_fadec_emulator_balancing_and_uds:22, test_datalink_emulator_priority_and_jamming:61, test_merkle_flight_log_tamper_detection:98, test_can_intrusion_detector:122

## tests/test_engine_agnostic_ratchet.py (128 lines)

Engine-agnosticism ratchet (docs/build/UNIVERSALITY_AUDIT.md, decision D27).

count_file:61, current_counts:69, _load_baseline:73, test_engine_specific_literals_never_increase:77, test_baseline_is_not_stale_upward:96, _update:107

## tests/test_engine_api.py (75 lines)

R4: engine API over the hub (uses a small hub injected into the router module).

client:11, test_list_and_profiles:23, test_state_has_no_truth_fields:31, test_fault_validation_and_select:39, test_levers:50, test_ws_engine_streams:55, test_ws_fleet:62, test_engine_schema:68

## tests/test_engine_config_provenance.py (90 lines)

Engine config provenance (B0.4).

test_all_configs_load:23, test_rotax_915is_exists_for_heron_mk_ii:31, test_every_numeric_field_has_a_classified_provenance_entry:44, test_every_provenance_entry_has_a_valid_status_and_ref:55, test_vrde_config_does_not_overclaim_as_a_verified_specification:65

## tests/test_fault_highlighting.py (147 lines)



MockMaterialSlot:59, MockMeshObject:63, MockCollections:82, test_fault_highlighting_and_material_swaps:90

## tests/test_fleet_stack.py (170 lines)

Tests for FLEET Stack (B10.1, B10.2, V7, R9, R10, R11).

test_performance_maps_and_atmosphere:29, test_mission_profiles:57, test_work_package_generator:76, test_fleet_economics_model:117, test_operational_history_tracker:151

## tests/test_flyhash_novelty.py (159 lines)

Tests for backend.ml.flyhash_novelty -- the FlyHash sparse-coding novelty layer.

test_feature_vector_has_documented_dimensionality:26, test_feature_vector_accepts_real_order_features:34, test_projection_row_fan_in_is_exact:44, test_encoder_sparsity_matches_target:51, test_similar_inputs_produce_similar_codes:60, test_detector_uncalibrated_never_flags_novel:83, test_detector_flags_genuine_outlier_after_calibration:91, test_reset_calibration_clears_state:117, test_edge_latency_budget:128, test_reproducible_with_fixed_seed:148, test_fan_in_cannot_exceed_input_dim:157

## tests/test_foundation_stack.py (93 lines)

Tests for FOUNDATION Stack (W8, W10, INN-06, D35).

test_maintenance_text_classifier:19, test_time_series_forecaster:42, test_in_context_tabular_classifier:65

## tests/test_frame_and_plant_source.py (90 lines)

B1.1 / B1.2(part 1): the canonical Frame contract and PlantSource.

test_frame_has_no_truth_or_twin_output_fields:22, test_frame_from_dict_refuses_forbidden_fields:30, test_frame_validates_source_and_cylinder_counts:35, test_unmeasured_channels_are_none_not_zero:42, test_plant_source_emits_frame_and_separate_truth:48, test_injected_fault_appears_in_truth_only_never_in_frame:58, test_same_seed_reproduces_and_different_builds_differ:69, test_engine_class_is_configuration:77, test_a_cooling_fault_moves_plant_readings_without_leaking_the_label:84

## tests/test_fun_req_compliance.py (290 lines)

Comprehensive Functional Requirements & Gap Resolution Compliance Test Suite
DRDO / iDEX Problem Statement ID: 26054 — Project ANUMAAN
Rotax 912 iS Sport MALE UAV Digital Twin

test_decoupled_plant_differential_dynamics:40, test_rotax_performance_maps_and_injection:64, test_sensor_drift_detection_and_residual_shielding:91, test_threshold_baseline_comparator_lead_time:130, test_canonical_mission_regimes:167, test_high_rate_vibration_dft_and_orders:195, test_conformal_rul_prediction_intervals:232, test_no_shortcut_fake_diagnosis_echo:260

## tests/test_independent_plant_adapter.py (150 lines)

Tests for backend.plant.adapter.IndependentPlantAdapter — the G01 wiring.

_make_adapter:20, test_nominal_frame_is_well_formed:26, test_nominal_residuals_are_structured_not_pure_noise:40, test_mapped_faults_move_the_expected_channel:70, test_unmapped_faults_pass_through_untouched:100, test_fault_switch_reinjects_plant_fault:122, test_truth_access_for_evaluation_only:141

## tests/test_llm_provider_default.py (41 lines)

Guards the B0.2 fix: the LLM must default to disabled, and must never default to
a Chinese-origin model. See docs/build/DECISIONS.md D14.

test_default_provider_is_none_and_disabled:12, test_backward_compat_alias_exists:28, test_qwen_is_not_the_default_provider_model:33

## tests/test_no_truth_leak.py (115 lines)

Guards against ground-truth leaking into the live inference path (B0.1).

_find_forbidden_attribute_reads:50, _iter_python_files:74, test_no_ground_truth_attribute_reads_in_live_inference_path:81, test_flyhash_novelty_calibration_does_not_reference_fault_id:97

## tests/test_physics_and_telemetry.py (127 lines)



TestRotaxPhysicsAndTelemetry:13

## tests/test_runtime_hub.py (121 lines)

R1-R3: concurrent per-engine runtimes, fault registry, lever dynamics, isolation, determinism.

hub:16, test_registry_filters_by_profile:22, test_invalid_fault_rejected:28, test_all_engines_tick_and_only_selected_gets_heavy:35, test_fault_isolated_to_one_engine_and_marked_manual:44, test_detector_alarms_on_injected_fault_not_on_other_engine:55, test_lever_first_order_dynamics_and_physics_response:66, test_determinism_same_seed_same_stream:86, test_cpu_cost_is_small:94, test_all_five_engines_concurrent_load_and_isolation:101

## tests/test_runtime_sensor_levers_and_replay.py (134 lines)

Tests for SensorLevers (R7) and bit-exact live-vs-replay (D05).

test_sensor_levers_operations:10, test_runtime_sensor_fault_kpi_exclusion:53, test_bit_exact_live_vs_replay:77

## tests/test_server_api.py (195 lines)

Unit & Integration Tests for Backend FastAPI Telemetry & Control Server
DRDO / iDEX Problem Statement ID: 26054

client:14, test_root_endpoint:19, test_health_endpoint:28, test_state_snapshot_schema:38, test_control_fault_activation_and_clearing:74, test_commanded_fault_highlights_immediately:95, test_control_throttle_and_environment:145, test_control_engine_stop_and_start:162, test_debrief_export_endpoint:181

## tests/test_twin_stack.py (84 lines)

Tests for Twin Stack (B4.1, B4.2, B4.4, B4.5, B4.6): dynamic twin, UKF estimation, SINDy, priors.

test_dynamic_thermofluid_model:13, test_thermofluid_ukf_parameter_tracking:31, test_sindy_sparse_law_discovery:52, test_degradation_particle_filter:63, test_hierarchical_fleet_priors_personalization:73

## tests/test_voice_copilot.py (132 lines)

Test Suite for Voice Mission Copilot Conversational Logic.
DRDO / iDEX Problem Statement ID: 26054

TestVoiceCopilot:23, TestVoiceConversationManager:112

## tests/test_waveform_stack.py (153 lines)

Tests for Waveform Stack (B2.1-B2.5, W3): CI combustion, rail acoustics, structural dynamics, high-rate DAQ.

test_ci_combustion_peak_pressure_class:16, test_common_rail_hydraulics_and_injector_coking:33, test_draper_resonance_and_bearing_orders:64, test_sensor_chain_timer_and_adc:95, test_waveform_source_and_recorder_npz_sha256:106, test_waveform_visibility_of_scalar_invisible_faults:128
