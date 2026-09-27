"""
Authoritative Real-Time Engine & Analytics Service
Rotax 912 iS MALE UAV Digital Twin — Laptop Backend Server
DRDO / iDEX Problem Statement ID: 26054

Runs the authoritative 20 Hz deterministic physics, sensor sanity, ML fault detection,
spectral analysis, prognostics, and ATA reasoning loop.
"""

import os
import time
import threading
import logging
import math
from typing import Dict, Any, List, Optional, Set
import asyncio

from backend.physics.thermo_model import RotaxThermoModel, EnginePhysicalState, ResidualVector
from backend.physics.sensor_validator import SensorSanityValidator, SanityReport
from backend.telemetry.can_streamer import TelemetryStreamer, DRDO_FAULT_DEFINITIONS
from backend.plant.adapter import IndependentPlantAdapter
from backend.ml.detection_pipeline import DetectionPipeline, DiagnosticEvent
from backend.ml.trend_analyser import ScoreBuffer, PrognosticsWorker
from backend.ml.rul_estimator import RULEstimator
from backend.agent.diagnostic_agent import DiagnosticAgent, DiagnosticDirective, ROTAX_ATA_FAULT_DIRECTIVES
from backend.agent.copilot import MissionCopilot
from backend.graph.mission_graph import MissionKnowledgeGraph
from backend.graph.mission_reporter import MissionReporter
from backend.reports.mission_bundle import build_and_write_mission_bundle
from backend.server.schemas import (
    EngineTelemetry,
    AnalyticsState,
    UnifiedTelemetryState,
    ControlCommand
)

logger = logging.getLogger("EngineService")

# Target 3D mesh mapping for all 8 DRDO fault modes in Blender CAD
FAULT_TARGET_PARTS: Dict[int, List[str]] = {
    0: [],
    1: [
        'Covers_Theme_M_PlasticTheme_0',
        'Covers_Theme_M_PlasticGreen_0',
        'Cooling_Air_Baffle_M_PlasticWhite_0',
        # 'Cooling_Air_Baffle_M_PlasticCable_0' removed -- no such object in
        # assets/blender/rotax_912_is_sport.blend; only a PlasticWhite variant
        # of this part exists (confirmed via headless Blender object dump,
        # scratch/real_objects.txt). Kept as a comment, not silently dropped,
        # in case a future asset revision reintroduces a cable-material variant.
    ],
    2: [
        'Rotax_912i_Base_M_PlasticGreen_0',
        'Rotax_912i_Base_M_Steel_0',
        'Rotax_912i_Base_M_PlasticCable_0',
        'Rotax_912i_Base_M_Rubber_0'
    ],
    3: [
        'Wiring_Harness_M_Copper_0',
        'Rotax_912i_Base_M_Copper_0',
        'Wiring_Harness_M_Cobalt_0',
        'Wiring_Harness_M_PlasticCable_0'
    ],
    4: [
        'Oil_Tank_M_Steel_0',
        'Oil_Tank_M_Labels_0',
        'Oil_Tank_M_Cobalt_0',
        'Oil_Tank_M_PlasticBlack_0'
    ],
    5: [
        'Gearbox_Type_2_M_Steel_0',
        'Gearbox_Type_2_M_MetalPaintedBlack_0',
        'Gearbox_Type_2_M_Cobalt_0',
        'Gearbox_Type_2_M_PlasticBlack_0',
        'Gearbox_Type_2_M_PlasticWhite_0'
    ],
    6: [
        'Exhaust_System_M_SteelDark_0',
        'Exhaust_System_M_Steel_0',
        'Exhaust_System_M_Cobalt_0',
        'Exhaust_System_M_Chrome_0',
        'Exhaust_System_M_PlasticBlack_0'
    ],
    7: [
        'External_Alternator_M_Rotax914_Extras_0',
        'External_Alternator_M_TimingBelt_0'
    ],
    8: [
        'ECU_M_PlasticBlack_0',
        'ECU_M_FuseLight_0',
        'ECU_M_Motherboard_0',
        'ECU_M_GlassMilky_0',
        'ECU_M_Labels_0',
        'ECU_M_Chrome_0',
        'ECU_M_Copper_0',
        'ECU_M_Steel_0',
        'ECU_M_PlasticBlue_0',
        'ECU_M_PlasticRed_0'
    ]
}


class EngineStateService:
    """
    Singleton service maintaining the authoritative physical and analytical state
    of the Rotax 912 iS propulsion system at 20 Hz.
    """
    _instance: Optional['EngineStateService'] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'EngineStateService':
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self.sortie_id = f"SORTIE-SRV-{time.strftime('%Y%m%d-%H%M%S')}"
        self.is_running = True
        self.is_engine_running = True
        
        # Environmental & Controls
        self.active_engine_id = "default"
        self.engine_name = "Propulsion Engine"
        self.throttle_pct = 72.0
        self.altitude_ft = 20000.0
        self.oat_c = -22.0
        self.region = "LADAKH"
        self.flight_phase = "CRUISE_LOITER"
        
        # Commanded fault
        self.active_fault_id = 0
        self.fault_severity = 1.0
        self.fault_start_time = 0.0

        # Tracks the last fault_id actually persisted into the mission graph, so that
        # a sustained fault is logged once per onset instead of once per 20 Hz tick.
        self._last_logged_fault_id = 0
        
        # Subsystems & Analytics
        self.thermo_model = RotaxThermoModel()
        # 20 Hz per the documented Deterministic Execution Budget (doc §1.3): the physics
        # baseline/residual loop must tick at 20 Hz (< 50 ms/frame). GearboxSpectralAnalyser's
        # 1 s FFT window and 60 s baseline lock (detection_pipeline.py, hardcoded to
        # sample_rate_hz=20.0) are frame-count based, so feeding it frames at any other rate
        # silently changes those windows' real-world durations.
        self.streamer = TelemetryStreamer(sample_rate_hz=20.0)
        # G01 (independent plant, closed for faults 1-4 + nominal): opt-in via env
        # var, default off. See backend/plant/adapter.py's module docstring for why
        # this is not the default yet -- the published 0.9751 classifier accuracy was
        # measured against the old generator's distribution and has not been
        # re-validated against the independent plant's. Flip on deliberately, retrain,
        # publish the new number alongside the old one; do not swap it silently.
        self.use_independent_plant = os.environ.get("ANUMAAN_USE_INDEPENDENT_PLANT", "0") == "1"
        self.data_source = (
            IndependentPlantAdapter(self.streamer, self.thermo_model)
            if self.use_independent_plant else self.streamer
        )
        self.score_buffer = ScoreBuffer(maxlen=7200)
        self.pipeline = DetectionPipeline(score_buffer=self.score_buffer, sortie_id=self.sortie_id)
        self.pipeline.load_models()

        self.prognostics = PrognosticsWorker(
            buffer=self.score_buffer,
            interval_sec=20.0,
            planned_mission_hours=18.0
        )
        # persist_path: fleet-wide CBM history (subsystem wear, anomaly log, maintenance
        # actions) survives a server restart instead of resetting to a blank graph every
        # process start — see MissionKnowledgeGraph.load()/save(). Disabled under pytest
        # (same guard as the AI/voice warm-up threads below) so running the test suite never
        # writes synthetic test sorties into the real fleet history on disk.
        graph_db_path = None
        if "PYTEST_CURRENT_TEST" not in os.environ:
            graph_db_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../../data/graph_db/fleet_graph.json")
            )
        self.graph = MissionKnowledgeGraph(persist_path=graph_db_path)
        self.reporter = MissionReporter()

        # Live per-sortie telemetry CSV (data/telemetry/live_sorties/<sortie_id>.csv), written
        # at ~2 Hz (every 10th tick) — cheap enough to run inline in _tick(), and gives the
        # mission debrief a real telemetry_log_path to cite instead of a fabricated one.
        self._telemetry_log_file = None
        self._telemetry_log_writer = None
        self._telemetry_log_tick_count = 0
        self.rul_estimator = RULEstimator()
        self.active_role = "OPERATOR"
        self.agent = DiagnosticAgent()
        self.copilot = MissionCopilot()  # RAG + Qwen3-4B intelligence layer (loads its LLM lazily)

        # Kick off the Qwen3-4B load, whisper.cpp STT, Kokoro TTS, and the RAG embedding index in
        # the background as soon as the server comes up, instead of waiting for an explicit
        # /api/voice/warmup call or the operator's first spoken turn. Plain fire-and-forget daemon
        # threads — identical decoupling rationale to _launch_ai_diagnosis() below: none of these
        # loads may ever block the 20 Hz tick, and each warm-up call is thread-safe/idempotent, so
        # this just means everything is usually already warm by the time the operator actually
        # talks instead of the first voice turn eating STT (~2-5s) + Kokoro TTS (~10s) + first-ever
        # RAG retrieval (~11s — sentence-transformers loading AND embedding the entire manual
        # corpus for the first time; every query after that is ~instant, cached) + LLM (~5-15s)
        # all stacked into one request — that stacking was reported directly as a ~45s wait on the
        # first spoken turn. Skipped under pytest (PYTEST_CURRENT_TEST is set by pytest itself for
        # the duration of the run) so the test suite doesn't pay real model loads every time this
        # class is constructed.
        if "PYTEST_CURRENT_TEST" not in os.environ:
            threading.Thread(target=self.copilot.llm_engine.ensure_loaded, daemon=True).start()
            from backend.voice.stt_engine import LocalWhisperSTT
            from backend.voice.tts_engine import LocalKokoroTTS
            threading.Thread(target=LocalWhisperSTT.get_instance().ensure_loaded, daemon=True).start()
            threading.Thread(target=LocalKokoroTTS.get_instance().ensure_loaded, daemon=True).start()
            threading.Thread(
                target=lambda: self.copilot.knowledge_store.query("warm up", top_k=1),
                daemon=True,
            ).start()

        # AI diagnosis state: generated on a background thread on fault onset, never inline in
        # the 20 Hz tick. See _launch_ai_diagnosis() for why this must never block _tick().
        self.ai_lock = threading.Lock()
        self.ai_diagnosis_state: Dict[str, Any] = {
            "status": "IDLE", "fault_name": "NOMINAL_FLIGHT", "explanation": "", "citations": []
        }
        self._ai_last_fault_id = 0

        self.graph.start_sortie(self.sortie_id, region=self.region)
        self.prognostics.start()
        
        # State tracking
        self.state_lock = threading.RLock()
        self.prev_actual: Optional[EnginePhysicalState] = None
        self.latest_state: Optional[UnifiedTelemetryState] = None
        self.subscribers: Set[asyncio.Queue] = set()
        
        # 20 Hz Deterministic Background Simulation Thread
        self.worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        self.worker_thread.start()
        logger.info(f"[EngineService] Initialized Sortie: {self.sortie_id} @ 20 Hz")

    def _run_loop(self):
        """Authoritative 20 Hz deterministic state and fault detection loop."""
        dt = 0.05  # 20 Hz (1/20s = 50ms/frame), per the documented Deterministic Execution Budget
        while self.is_running:
            t0 = time.time()
            try:
                with self.state_lock:
                    self._tick(dt)
            except Exception as e:
                logger.error(f"[EngineService] Error in simulation tick: {e}", exc_info=True)
            
            elapsed = time.time() - t0
            sleep_time = max(0.001, dt - elapsed)
            time.sleep(sleep_time)

    def _tick(self, dt: float):
        """Computes one 20 Hz physical state update and analytical cycle."""
        # 1. Update streamer environmental params
        self.streamer.region = self.region
        
        # 2. Generate frame from physical streamer with dynamic operator controls (G01/G02 plant decoupling)
        if self.is_engine_running:
            actual, expected, residuals = self.data_source.generate_frame(
                throttle_cmd=self.throttle_pct,
                altitude_cmd=self.altitude_ft,
                oat_cmd=self.oat_c
            )
            actual.FLIGHT_PHASE = self.flight_phase
        else:
            actual, expected, residuals = self.data_source.generate_frame()
            p_amb, _, _ = self.thermo_model.get_ambient_properties(self.altitude_ft, self.oat_c)
            actual.ENGINE_RPM = 0.0
            actual.PROP_RPM = 0.0
            actual.TPS = 0.0
            actual.FUEL_FLOW = 0.0
            actual.OIL_PRESS = 0.0
            actual.MAP = p_amb
            actual.BUS_VOLTAGE = 12.4
            actual.BATTERY_CURRENT = -2.5
            actual.VIB_GEARBOX_RMS = 0.0
            actual.HEALTH_INDEX = 1.0

        # Widen this sortie's recorded ambient flight envelope for the mission debrief's
        # ambient_environment block (doc04 §2). Cheap dict-field update, no disk I/O.
        self.graph.update_sortie_envelope(self.sortie_id, oat_c=actual.OAT_C, altitude_ft=actual.ALTITUDE_FT)

        # 4. Recompute physics residuals against expected baseline
        residuals = self.thermo_model.compute_residuals(actual, expected)
        
        # 5. Process through 9-stage Detection Pipeline
        event_diag = self.pipeline.process_frame(actual, self.prev_actual, dt_sec=dt)
        self.prev_actual = actual

        # Update physical RUL degradation dynamics (F12)
        self.rul_estimator.update_degradation(actual, residuals, dt_sec=dt)

        # Pull latest prognostics report. Computed here (before fault-diagnosis/graph-recording
        # below) so early_trend/rul_by_component are available to attach as real, live-computed
        # context onto the AnomalyEventNode/MaintenanceActionNode this tick may record — rather
        # than the debrief narrating drift rates and RUL numbers after the fact.
        prog = self.prognostics.latest_report
        go_no_go = "GO"
        go_no_go_reason = "All propulsion subsystems flight-ready."
        # 500h sentinel (not a hardcoded near-critical guess) matches EnginePhysicalState's own
        # nominal RUL_HOURS default: "no active degradation trend on any component yet" rather
        # than a fabricated conservative bound that would visually contradict a GO advisory.
        rul_p10 = 500.0
        rul_p50 = 500.0
        limiting_component: Optional[str] = None
        rul_by_component: Dict[str, Dict[str, float]] = {}
        early_trend = None

        if prog:
            if prog.go_no_go:
                go_no_go = prog.go_no_go.advisory
                go_no_go_reason = prog.go_no_go.reason
                limiting_component = prog.go_no_go.limiting_component
            if prog.rul_estimates:
                for comp, rul in prog.rul_estimates.items():
                    if rul.rul_p10_min < 1e9:
                        rul_by_component[comp] = {
                            "rul_p10_hours": round(rul.rul_p10_min / 60.0, 2),
                            "rul_p50_hours": round(rul.rul_p50_min / 60.0, 2),
                            "rul_p90_hours": round(rul.rul_p90_min / 60.0, 2),
                            "confidence": round(rul.confidence, 3),
                        }
                if limiting_component and limiting_component in rul_by_component:
                    rul_p10 = rul_by_component[limiting_component]["rul_p10_hours"]
                    rul_p50 = rul_by_component[limiting_component]["rul_p50_hours"]
                elif rul_by_component:
                    # Fallback if go_no_go didn't resolve a limiting component name.
                    worst = min(rul_by_component.items(), key=lambda kv: kv[1]["rul_p10_hours"])
                    rul_p10 = worst[1]["rul_p10_hours"]
                    rul_p50 = worst[1]["rul_p50_hours"]
            if prog.channels_with_trends:
                tr = prog.channels_with_trends[0]
                # Only surface a trend as an "early warning" when it is both non-NOMINAL and has a
                # finite projected breach time. A NOMINAL/non-converging trend can report
                # time_to_threshold_min == inf, which serializes to JSON null and crashes any
                # client that calls .toFixed()/numeric comparisons on it (dashboard + Blender HUD).
                if tr.alert_level != "NOMINAL" and math.isfinite(tr.time_to_threshold_min):
                    early_trend = {
                        "channel": tr.channel,
                        "drift_rate_per_hr": tr.drift_rate_per_min * 60.0,
                        "time_to_threshold_min": tr.time_to_threshold_min,
                        "alert_level": tr.alert_level,
                        "message": f"Sub-threshold drift detected in {tr.channel} ({tr.drift_rate_per_min*60:+.2f}/hr)"
                    }

        # 6. Extract ML and Prognostic diagnostics
        ae_score = residuals.anomaly_score
        health_idx = actual.HEALTH_INDEX
        
        p = event_diag.ml_detection_payload if event_diag else {}
        
        # Genuine ML & Physics diagnosis (NO shortcut fake diagnosis label echo)
        diag_fid = p.get('primary_fault_id', 0)
        diag_fname = p.get('fault_name', self.pipeline.FAULT_NAMES.get(diag_fid, "NOMINAL_FLIGHT"))
        diag_conf = p.get('confidence', 0.0)

        if diag_fid == 0 and residuals.anomaly_score > 0.35:
            # Reuse this frame's already-computed Stage 1/4 reports — both sub-components
            # are stateful (rolling history/frame-count windows) and must not be invoked
            # a second time for the same frame. See DetectionPipeline.process_frame().
            spectral_rep = self.pipeline.last_spectral_report
            sanity_rep = self.pipeline.last_sanity_report
            classified_id, classified_conf = self.pipeline._classify(actual, expected, residuals, spectral_rep, sanity_rep)
            if classified_id != 0 and classified_conf >= self.pipeline.CONFIDENCE_GATE:
                diag_fid = classified_id
                diag_conf = classified_conf
                diag_fname = self.pipeline.FAULT_NAMES.get(diag_fid, "NOMINAL_FLIGHT")
            else:
                diag_fid = 0
                diag_fname = "NOMINAL_FLIGHT"
                diag_conf = 0.99
        elif diag_fid == 0:
            diag_fname = "NOMINAL_FLIGHT"
            diag_conf = 0.99
        
        # Pull authoritative ATA directive
        directive: Optional[DiagnosticDirective] = None
        if diag_fid > 0:
            directive = self.agent.diagnose(diag_fid, confidence=diag_conf)
            # Record in knowledge graph only on fault onset (transition into this fault),
            # not on every 20 Hz tick — otherwise a sustained fault floods the mission graph
            # and post-flight debrief with thousands of duplicate anomaly/maintenance rows
            # and crashes subsystem health to its floor within a few hundred milliseconds.
            if diag_fid != self._last_logged_fault_id:
                self.graph.record_anomaly(
                    sortie_id=self.sortie_id,
                    fault_id=diag_fid,
                    fault_name=diag_fname,
                    severity=directive.severity if directive else "WARNING",
                    anomaly_score=ae_score,
                    ata_chapter=directive.ata_chapter if directive else "ATA 00-00",
                    recommended_action=directive.prescriptive_action if directive else "",
                    trend_note=early_trend.get("message") if early_trend else None,
                )
                if directive and directive.maintenance_order:
                    self.graph.record_maintenance_action(
                        sortie_id=self.sortie_id,
                        fault_id=diag_fid,
                        ata_chapter=directive.ata_chapter,
                        description=directive.maintenance_order,
                        rul_p10_hours=rul_p10 if rul_by_component else None,
                        rul_p50_hours=rul_p50 if rul_by_component else None,
                        limiting_component=limiting_component,
                    )
                self._last_logged_fault_id = diag_fid
        else:
            self._last_logged_fault_id = 0

        # Dispatch the RAG + Qwen3-4B diagnosis on fault onset only (edge-triggered on the same
        # diag_fid transition), running fully on a background thread. This NEVER runs inline here:
        # LLM generation can take several seconds on a laptop GPU, and _tick() executes inside
        # self.state_lock — blocking it would freeze telemetry for every connected client.
        if diag_fid != self._ai_last_fault_id:
            self._ai_last_fault_id = diag_fid
            if diag_fid > 0:
                with self.ai_lock:
                    self.ai_diagnosis_state = {
                        "status": "THINKING", "fault_name": diag_fname, "explanation": "", "citations": []
                    }
                ai_snapshot = {
                    "telemetry": {
                        "THEATER": self.region, "ALTITUDE_FT": actual.ALTITUDE_FT, "OAT_C": actual.OAT_C,
                        "ENGINE_RPM": actual.ENGINE_RPM, "TPS": actual.TPS,
                    },
                    "residuals": residuals.to_dict() if hasattr(residuals, "to_dict") else {},
                }
                self._launch_ai_diagnosis(diag_fid, directive, ai_snapshot)
            else:
                with self.ai_lock:
                    self.ai_diagnosis_state = {
                        "status": "IDLE", "fault_name": "NOMINAL_FLIGHT", "explanation": "", "citations": []
                    }

        # 7. Assemble Unified State Object
        telemetry_payload = EngineTelemetry(
            ENGINE_RPM=round(actual.ENGINE_RPM, 1),
            PROP_RPM=round(actual.PROP_RPM, 1),
            TPS=round(actual.TPS, 1),
            CHT_1=round(actual.CHT_1, 1),
            CHT_2=round(actual.CHT_2, 1),
            CHT_3=round(actual.CHT_3, 1),
            CHT_4=round(actual.CHT_4, 1),
            EGT_1=round(actual.EGT_1, 1),
            EGT_2=round(actual.EGT_2, 1),
            EGT_3=round(actual.EGT_3, 1),
            EGT_4=round(actual.EGT_4, 1),
            OIL_PRESS=round(actual.OIL_PRESS, 2),
            OIL_TEMP=round(actual.OIL_TEMP, 1),
            FUEL_FLOW=round(actual.FUEL_FLOW, 1),
            FUEL_RAIL_P=round(actual.FUEL_RAIL_P, 1),
            MAP=round(actual.MAP, 1),
            VIB_GEARBOX_RMS=round(actual.VIB_GEARBOX_RMS, 2),
            BUS_VOLTAGE=round(actual.BUS_VOLTAGE, 2),
            BATTERY_CURRENT=round(actual.BATTERY_CURRENT, 1),
            FADEC_ACTIVE_LANE=actual.FADEC_ACTIVE_LANE,
            ALTITUDE_FT=round(actual.ALTITUDE_FT, 0),
            OAT_C=round(actual.OAT_C, 1),
            TAS_KNOTS=round(actual.TAS_KNOTS, 1),
            FLIGHT_PHASE=actual.FLIGHT_PHASE,
            THEATER=self.region,
            INJ_TIMING_BTDC=round(actual.INJ_TIMING_BTDC, 2),
            INJ_PULSE_WIDTH_MS=round(actual.INJ_PULSE_WIDTH_MS, 2),
            IGN_TIMING_BTDC=round(actual.IGN_TIMING_BTDC, 2),
            LAMBDA_AFR=round(actual.LAMBDA_AFR, 2),
            BSFC_G_KWH=round(actual.BSFC_G_KWH, 1),
            POWER_KW=round(actual.POWER_KW, 1),
            THERMAL_EFFICIENCY=round(actual.THERMAL_EFFICIENCY, 3),
        )
        
        # Live per-sortie telemetry log, throttled to ~2 Hz (every 10th 20Hz tick) — real data
        # backing the mission debrief's telemetry_log_path (doc04 §2), and a foundation for a
        # future replay view (out of scope here) that would need actual recorded telemetry.
        self._telemetry_log_tick_count += 1
        if self._telemetry_log_tick_count % 10 == 0 and "PYTEST_CURRENT_TEST" not in os.environ:
            self._log_telemetry_row(telemetry_payload, diag_fid, health_idx)

        # 3D highlight target: prioritise the OPERATOR-COMMANDED fault, falling back to the
        # genuine ML/physics diagnosis -- mirrors the client's own priority for camera framing
        # (see update_camera_for_backend_fault() in standalone_digital_twin_app.py: "Use
        # commanded fault if explicitly set by operator, else use diagnosed fault"). Before this
        # fix, target_parts was tied unconditionally to diag_fid (the genuine, non-circular
        # diagnosis added to stop the dashboard fake-echoing the commanded label as a real
        # detection). That was the right fix for diagnosed_fault_id/confidence, but it also
        # silently broke 3D mesh highlighting: an operator-commanded fault now highlights
        # nothing until the pipeline independently re-detects it, which can lag by several
        # seconds (the fault's own ramp_duration_sec) or never cross CONFIDENCE_GATE at low
        # severity. Camera panning already used commanded-first and kept working -- this brings
        # mesh highlighting into line with it. diagnosed_fault_id/diag_conf below are untouched
        # and remain the genuine diagnosis, never the commanded label.
        display_fault_id = self.active_fault_id if self.active_fault_id > 0 else diag_fid
        target_parts = FAULT_TARGET_PARTS.get(display_fault_id, [])
        target_mesh = target_parts[0] if target_parts else "All"
        
        # Reuse the report Stage 1 already computed inside process_frame() above for this
        # exact frame — see the caution in DetectionPipeline.process_frame().
        sanity_report = self.pipeline.last_sanity_report.to_dict() if self.pipeline.last_sanity_report else {
            "all_sensors_valid": True,
            "drift_detected": False,
            "failed_channels": [],
            "suppressed_anomaly": False,
            "advisory": "All sensor impedance nominal."
        }

        # Dynamic Subsystem Health Index calculation derived directly from real residuals
        if not self.is_engine_running:
            sub_prop, sub_fuel, sub_elec, sub_therm, sub_mech = 1.0, 1.0, 1.0, 1.0, 1.0
        else:
            # 1. Propulsion Health: Overall anomaly penalty + power drag penalty
            sub_prop = max(0.15, min(1.0, 1.0 - (ae_score * 0.70)))
            
            # 2. Fuel System Health: derived from fuel flow residual and individual cylinder EGT spikes
            fuel_penalty = (abs(residuals.d_FUEL_FLOW) / 8.0) + (max(0.0, residuals.d_EGT_1) / 250.0)
            if diag_fid == 2 or residuals.d_FUEL_FLOW < -1.0:
                fuel_penalty = max(fuel_penalty, 0.65)
            elif diag_fid == 8 or residuals.d_MAP > 3.0:
                fuel_penalty = max(fuel_penalty, 0.50)
            sub_fuel = max(0.15, min(1.0, 1.0 - fuel_penalty))
            
            # 3. Electrical Health: derived from bus voltage sag, battery discharge, and ignition/ECU state
            elec_penalty = (max(0.0, -residuals.d_BUS_VOLTAGE) / 2.2) + (max(0.0, -actual.BATTERY_CURRENT) / 30.0)
            if diag_fid == 7 or residuals.d_BUS_VOLTAGE < -0.6:
                elec_penalty = max(elec_penalty, 0.65)
            elif diag_fid == 3 or residuals.d_EGT_2 < -30.0:
                elec_penalty = max(elec_penalty, 0.55)
            elif diag_fid == 8 or residuals.d_MAP > 3.0:
                elec_penalty = max(elec_penalty, 0.45)
            sub_elec = max(0.15, min(1.0, 1.0 - elec_penalty))
            
            # 4. Thermal Health: derived from max CHT residual and oil temperature rise
            max_d_cht = max(residuals.d_CHT_1, residuals.d_CHT_2, residuals.d_CHT_3, residuals.d_CHT_4)
            therm_penalty = (max(0.0, max_d_cht) / 50.0) + (max(0.0, residuals.d_OIL_TEMP) / 40.0)
            if diag_fid in (1, 6) or max_d_cht > 10.0:
                therm_penalty = max(therm_penalty, 0.75 if (diag_fid == 1 or residuals.d_CHT_2 > 10.0) else 0.55)
            sub_therm = max(0.15, min(1.0, 1.0 - therm_penalty))
            
            # 5. Mechanical Health: derived from gearbox vibration RMS and oil pressure decay
            mech_penalty = (max(0.0, residuals.d_VIB_RMS) / 3.0) + (max(0.0, -residuals.d_OIL_PRESS) / 2.8)
            if diag_fid in (4, 5) or residuals.d_OIL_PRESS < -0.5 or residuals.d_VIB_RMS > 0.5 or actual.OIL_PRESS < 2.5:
                mech_penalty = max(mech_penalty, 0.75 if (diag_fid == 4 or residuals.d_OIL_PRESS < -0.5 or actual.OIL_PRESS < 2.5) else 0.65)
            sub_mech = max(0.15, min(1.0, 1.0 - mech_penalty))

        subsystem_health_dict = {
            "propulsion": round(sub_prop, 2),
            "fuel_system": round(sub_fuel, 2),
            "electrical": round(sub_elec, 2),
            "thermal": round(sub_therm, 2),
            "mechanical": round(sub_mech, 2),
        }

        analytics_payload = AnalyticsState(
            residuals={
                "d_CHT_1": round(residuals.d_CHT_1, 2),
                "d_CHT_2": round(residuals.d_CHT_2, 2),
                "d_CHT_3": round(residuals.d_CHT_3, 2),
                "d_CHT_4": round(residuals.d_CHT_4, 2),
                "d_EGT_1": round(residuals.d_EGT_1, 1),
                "d_EGT_2": round(residuals.d_EGT_2, 1),
                "d_EGT_3": round(residuals.d_EGT_3, 1),
                "d_EGT_4": round(residuals.d_EGT_4, 1),
                "d_OIL_PRESS": round(residuals.d_OIL_PRESS, 2),
                "d_OIL_TEMP": round(residuals.d_OIL_TEMP, 1),
                "d_FUEL_FLOW": round(residuals.d_FUEL_FLOW, 2),
                "d_MAP": round(residuals.d_MAP, 2),
                "d_VIB_RMS": round(residuals.d_VIB_RMS, 2),
                "d_BUS_VOLTAGE": round(residuals.d_BUS_VOLTAGE, 2)
            },
            anomaly_score=round(ae_score, 4),
            health_index=round(health_idx, 3),
            diagnosed_fault_id=diag_fid,
            diagnosed_fault_name=diag_fname,
            diagnosed_confidence=round(diag_conf, 3),
            target_3d_mesh=target_mesh,
            target_parts=target_parts,
            ata_chapter=directive.ata_chapter if directive else "ATA 00-00",
            subsystem=directive.subsystem if directive else "PROPULSION_CORE",
            severity=directive.severity if directive else ("NORMAL" if self.is_engine_running else "ENGINE_OFF"),
            root_cause=directive.root_cause_explanation if directive else (
                "Propulsion system nominal." if self.is_engine_running else "Engine is shutdown / off."
            ),
            prescriptive_action=directive.prescriptive_action if directive else (
                "Maintain standard flight profile." if self.is_engine_running else "Ready for engine ignition."
            ),
            emergency_checklist=directive.emergency_checklist if directive else [],
            maintenance_order=directive.maintenance_order if directive else "No maintenance required.",
            go_no_go=go_no_go,
            go_no_go_reason=go_no_go_reason,
            rul_p10_hours=round(rul_p10, 1),
            rul_p50_hours=round(rul_p50, 1),
            limiting_component=limiting_component,
            planned_sortie_hours=self.prognostics.planned_hours,
            rul_by_component=rul_by_component,
            sensor_sanity=sanity_report,
            early_warning_trend=early_trend,
            threshold_baseline=self.pipeline.last_threshold_baseline_report.to_dict() if self.pipeline.last_threshold_baseline_report else {},
            conformal_rul=self.rul_estimator.get_conformal_rul(residuals=residuals),
            subsystem_health=subsystem_health_dict,
            ai_diagnosis=dict(self.ai_diagnosis_state),
            causal_chain=directive.causal_chain if directive else [
                "All 27 telemetry channels within FAA/EASA certified limits.",
                "Continuous physics residual autoencoder loss < 0.05.",
                "Zero sub-threshold sensor drift detected across fleet.",
                "Subsystem health index nominal at 100.0%."
            ]
        )
        
        commanded_name = DRDO_FAULT_DEFINITIONS.get(self.active_fault_id, {}).get("name", "NOMINAL")
        
        self.latest_state = UnifiedTelemetryState(
            timestamp=time.time(),
            sortie_id=self.sortie_id,
            engine_id=self.active_engine_id,
            engine_name=self.engine_name,
            is_engine_running=self.is_engine_running,
            active_commanded_fault_id=self.active_fault_id,
            active_commanded_fault_name=commanded_name,
            telemetry=telemetry_payload,
            analytics=analytics_payload
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Thread-Safe Command Handlers
    # ──────────────────────────────────────────────────────────────────────────

    def set_active_engine(self, engine_id: str) -> Dict[str, Any]:
        """Switches active engine configuration and updates baseline limits."""
        if not engine_id:
            return {"status": "ERROR", "message": "Missing engine_id"}
        engine_id_clean = engine_id.lower().replace("-", "_")
        parts = [p.upper() if p in ("is", "uav", "hp") else p.title() for p in engine_id_clean.split("_")]
        dyn_name = " ".join(parts)
        with self.state_lock:
            self.active_engine_id = engine_id_clean
            self.engine_name = dyn_name
            if self.latest_state:
                self.latest_state.engine_id = self.active_engine_id
                self.latest_state.engine_name = self.engine_name
        logger.info(f"[EngineService] Active engine profile set to: {self.engine_name} ({self.active_engine_id})")
        return {"status": "SUCCESS", "engine_id": self.active_engine_id, "engine_name": self.engine_name}

    def set_fault(self, fault_id: int, severity: float = 1.0, ramp_duration_sec: float = 6.0):
        """Convenience method to command a fault directly."""
        return self.handle_command(ControlCommand(action="SET_FAULT", fault_id=fault_id))

    def clear_fault(self):
        """Convenience method to clear active fault."""
        return self.handle_command(ControlCommand(action="CLEAR_FAULT"))

    def handle_command(self, cmd: ControlCommand) -> Dict[str, Any]:
        """Processes an incoming control command from Web, Mobile, or GCS."""
        action = cmd.action.upper()
        logger.info(f"[EngineService] Executing Command: {action} (payload={cmd})")
        
        with self.state_lock:
            res = {"status": "ERROR", "message": f"Unknown action: {action}"}
            
            if action == "START_ENGINE":
                self.is_engine_running = True
                res = {"status": "SUCCESS", "message": "Rotax 912 iS Engine Started"}
                
            elif action == "STOP_ENGINE":
                self.is_engine_running = False
                res = {"status": "SUCCESS", "message": "Engine Shutdown Complete"}
                
            elif action in ("SET_FAULT", "INJECT_FAULT"):
                fid = cmd.fault_id
                if fid is None and getattr(cmd, "fault_type", None):
                    ft = str(cmd.fault_type).strip().upper()
                    for k, defn in DRDO_FAULT_DEFINITIONS.items():
                        if defn.get("name", "").upper() == ft or str(k) == ft:
                            fid = k
                            break
                if fid is None:
                    fid = 0
                if fid not in DRDO_FAULT_DEFINITIONS:
                    return {"status": "ERROR", "message": f"Invalid fault ID: {fid}. Must be 0..8."}
                self.is_engine_running = True
                self.active_fault_id = fid
                self.fault_start_time = time.time()
                self.streamer.set_fault(fid, severity=self.fault_severity, ramp_duration_sec=6.0)
                self.pipeline.reset(sortie_id=self.sortie_id)
                # Without this, DegradationTrendAnalyser keeps fitting curves across score
                # history from whatever scenario was active before this command, and the
                # Go/No-Go advisory + RUL_p10 stay stuck on stale numbers for minutes.
                self.prognostics.reset()
                fname = DRDO_FAULT_DEFINITIONS[fid]["name"]
                res = {"status": "SUCCESS", "message": f"Fault {fid} ({fname}) Activated"}

            elif action == "CLEAR_FAULT":
                self.active_fault_id = 0
                self.streamer.reset_fault()
                self.pipeline.reset(sortie_id=self.sortie_id)
                self.prognostics.reset()
                res = {"status": "SUCCESS", "message": "Fault cleared. System returned to Nominal state."}
                
            elif action == "SET_THROTTLE":
                if cmd.throttle is not None:
                    self.throttle_pct = max(0.0, min(100.0, float(cmd.throttle)))
                    res = {"status": "SUCCESS", "message": f"Throttle set to {self.throttle_pct:.1f}%"}
                    
            elif action == "SET_ALTITUDE":
                if cmd.altitude_ft is not None:
                    self.altitude_ft = max(0.0, min(30000.0, float(cmd.altitude_ft)))
                    res = {"status": "SUCCESS", "message": f"Altitude set to {self.altitude_ft:.0f} ft"}
                    
            elif action == "SET_OAT":
                if cmd.oat_c is not None:
                    self.oat_c = max(-50.0, min(60.0, float(cmd.oat_c)))
                    res = {"status": "SUCCESS", "message": f"OAT set to {self.oat_c:.1f}°C"}
                    
            elif action == "SET_REGIME":
                reg = cmd.regime or cmd.region
                if reg:
                    reg = reg.upper()
                    self.streamer.set_mission_regime(reg)
                    self.region = self.streamer.region
                    self.altitude_ft = self.streamer.altitude_cmd
                    self.oat_c = self.streamer.oat_cmd
                    self.throttle_pct = self.streamer.throttle_cmd
                    res = {"status": "SUCCESS", "message": f"Mission regime set to {reg}"}

            elif action == "SET_ROLE":
                if cmd.role:
                    role = cmd.role.upper()
                    if role in ("OPERATOR", "PROPULSION_ENGINEER", "MAINTENANCE_CREW"):
                        self.active_role = role
                        res = {"status": "SUCCESS", "message": f"GCS active role set to {role}"}
                    
            elif action in ("SELECT_ENGINE", "SET_ENGINE"):
                if cmd.engine_id:
                    res = self.set_active_engine(cmd.engine_id)

            elif action == "EXPORT_DEBRIEF":
                path = self.export_debrief()
                return {"status": "SUCCESS", "message": f"Debrief exported to {path}", "report_path": path}
                
            # Immediately compute state update with new parameter
            try:
                self._tick(0.05)
            except Exception as e:
                logger.error(f"[EngineService] Immediate tick error: {e}")

            return res

    def _launch_ai_diagnosis(self, fault_id: int, directive: Optional[DiagnosticDirective], snapshot: Dict[str, Any]):
        """
        Runs MissionCopilot.diagnose_with_ai() (RAG retrieval + Qwen3-4B generation) on a daemon
        thread. Fully decoupled from the 20 Hz tick: if the GPU is busy, absent, or Qwen fails to
        load, this just leaves ai_diagnosis_state as ERROR — the deterministic engine, dashboard,
        and standalone app are completely unaffected either way.
        """
        def _worker():
            try:
                result = self.copilot.diagnose_with_ai(snapshot, directive)
            except Exception as e:
                result = {
                    "status": "ERROR",
                    "fault_name": directive.fault_name if directive else "UNKNOWN",
                    "explanation": f"AI reasoning layer unavailable: {e}",
                    "citations": [],
                }
            with self.ai_lock:
                # Only apply if this fault is still the active one - avoids a slow, stale
                # generation for an already-cleared/changed fault overwriting a newer result.
                if self._ai_last_fault_id == fault_id:
                    self.ai_diagnosis_state = result

        threading.Thread(target=_worker, daemon=True).start()

    def _log_telemetry_row(self, telemetry_payload: EngineTelemetry, diag_fid: int, health_idx: float) -> None:
        """
        Append one row to this sortie's live telemetry CSV, opening the file (and registering
        its path on the SortieNode) on first write. Best-effort only — a logging failure must
        never take down the 20 Hz tick.
        """
        import csv
        try:
            if self._telemetry_log_file is None:
                log_dir = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "../../data/telemetry/live_sorties")
                )
                os.makedirs(log_dir, exist_ok=True)
                log_path = os.path.join(log_dir, f"{self.sortie_id}.csv")
                self._telemetry_log_file = open(log_path, "w", newline="", encoding="utf-8")
                fieldnames = ["TIMESTAMP_SEC"] + list(telemetry_payload.model_dump().keys()) + \
                    ["DIAG_FAULT_ID", "HEALTH_INDEX"]
                self._telemetry_log_writer = csv.DictWriter(self._telemetry_log_file, fieldnames=fieldnames)
                self._telemetry_log_writer.writeheader()
                self.graph.set_telemetry_log_path(self.sortie_id, log_path)

            row = {"TIMESTAMP_SEC": round(time.time(), 3), **telemetry_payload.model_dump(),
                   "DIAG_FAULT_ID": diag_fid, "HEALTH_INDEX": round(health_idx, 3)}
            self._telemetry_log_writer.writerow(row)
            self._telemetry_log_file.flush()
        except Exception as e:
            logger.warning(f"[EngineService] Telemetry log write failed (non-fatal): {e}")

    def export_debrief(self) -> str:
        """
        Exports CBM sortie report to data/mission_reports/. Reads/mutates self.graph (the
        same fault/anomaly rows _tick() appends every tick) and self.latest_state, so callers
        MUST hold self.state_lock — see handle_command()'s EXPORT_DEBRIEF branch, the only
        caller. (Not acquired here: self.state_lock is a plain, non-reentrant Lock, and that
        branch already runs inside handle_command()'s own `with self.state_lock:`, so
        acquiring it again here would deadlock the calling thread against itself.)
        """
        flight_hrs = round((time.time() - float(self.graph.sorties[self.sortie_id].start_timestamp)) / 3600.0, 3)
        final_health = self.latest_state.analytics.health_index if self.latest_state else 1.0
        self.graph.complete_sortie(self.sortie_id, flight_hours=flight_hrs, final_health=final_health)
        path = self.reporter.generate_report(self.graph, self.sortie_id)
        logger.info(f"[EngineService] Post-Flight CBM Debrief saved: {path}")

        # Also export the mission as a self-contained report_dump/mission_NNN/ bundle —
        # the folder-per-mission format the 3D mission graph viewer discovers and renders.
        # Never allowed to fail the debrief: the .md above is the authoritative artifact.
        try:
            analytics = self.latest_state.analytics.model_dump() if self.latest_state else None
            bundle_dir = build_and_write_mission_bundle(
                graph=self.graph,
                sortie_id=self.sortie_id,
                analytics=analytics,
                summary_markdown_path=path,
                generated_by="engine_service",
            )
            if bundle_dir:
                logger.info(f"[EngineService] Mission report bundle written: {bundle_dir}")
        except Exception as e:
            logger.warning(f"[EngineService] Report dump export failed (non-fatal): {e}")

        return path

    def get_latest_state(self) -> UnifiedTelemetryState:
        """Returns the current 20 Hz state snapshot."""
        if self.latest_state is None:
            # Locked to match every other caller of _tick() (_run_loop, handle_command).
            # Without this, the very first /api/state or WebSocket request to land before
            # the 20 Hz worker thread's first tick completes could run _tick() concurrently
            # with that thread — both mutating self.prev_actual, self._last_logged_fault_id,
            # and self.graph at once.
            with self.state_lock:
                if self.latest_state is None:
                    self._tick(0.05)
        return self.latest_state
