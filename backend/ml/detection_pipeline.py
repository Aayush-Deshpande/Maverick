"""
Integrated Real-Time Detection Pipeline — Plane 1
DRDO / iDEX Problem Statement ID: 26054

Implements the complete 9-stage deterministic inference pipeline at 20 Hz.
Companion 20-second background thread (PrognosticsWorker) provides trend/RUL.

PS reference: doc02 §1 Plane 1 architecture
  CAN Sensors → Sensor Sanity → Physics Residuals → Anomaly Score
  → Gearbox FFT → Fault Isolation → Prognostics → Majority Vote → JSON Event

Total latency target: < 20ms per frame at 20 Hz.

Architecture:
  Thread 1 (main, 20 Hz):  call pipeline.process_frame() each telemetry frame
  Thread 2 (daemon, 20 s): PrognosticsWorker reads shared ScoreBuffer
  JSON events emitted via on_diagnostic_event callback

Usage:
    from backend.ml.detection_pipeline import DetectionPipeline, ScoreBuffer
    from backend.ml.trend_analyser import PrognosticsWorker

    buffer = ScoreBuffer()
    worker = PrognosticsWorker(buffer, interval_sec=20.0)
    worker.start()

    pipeline = DetectionPipeline(score_buffer=buffer)
    pipeline.load_models()   # loads RF + autoencoder if available

    for frame in telemetry_stream:
        event = pipeline.process_frame(actual_state, prev_state, dt_sec)
        if event:
            send_to_gcs(event)

    worker.stop()
"""

import time
import json
import math
import collections
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, Callable, List

from backend.physics.thermo_model import (
    RotaxThermoModel, EnginePhysicalState, ResidualVector
)
from backend.physics.sensor_validator import (
    SensorSanityValidator, SanityReport, apply_residual_shielding
)
from backend.ml.anomaly_detector import ResidualAutoencoder, FEATURE_ORDER
from backend.ml.spectral_analyser import GearboxSpectralAnalyser, SpectralReport
from backend.ml.trend_analyser import ScoreBuffer
from backend.agent.diagnostic_agent import DiagnosticAgent, DiagnosticDirective


# ---------------------------------------------------------------------------
# Threshold baseline comparator report (F13 / G03)
# ---------------------------------------------------------------------------

@dataclass
class ThresholdBaselineReport:
    """
    Conventional fixed-threshold baseline comparison report (F13 / G03).
    Compares conventional avionics warning thresholds (Rotax operating limits)
    against the Physics-AI Digital Twin early anomaly detection.
    """
    conventional_breached: bool = False
    breached_parameters: List[str] = field(default_factory=list)
    conventional_breach_timestamp: Optional[float] = None
    twin_detect_timestamp: Optional[float] = None
    lead_time_sec: Optional[float] = None
    conventional_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "CHT_MAX_C": 135.0,
        "EGT_MAX_C": 850.0,
        "OIL_PRESS_MIN_BAR": 2.0,
        "OIL_PRESS_MAX_BAR": 5.5,
        "OIL_TEMP_MAX_C": 130.0,
        "VIB_RMS_MAX": 2.5,
        "BUS_VOLTAGE_MIN_V": 12.0,
    })

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Diagnostic event — the doc02 §3 JSON contract
# ---------------------------------------------------------------------------

@dataclass
class DiagnosticEvent:
    """
    Structured JSON event emitted by the pipeline upon anomaly or fault detection.
    Matches the exact schema from doc02 §3.
    """
    timestamp_iso: str
    sortie_id: str
    flight_context: Dict[str, Any]
    sensor_sanity: Dict[str, Any]
    ml_detection_payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


@dataclass
class PipelineState:
    """Internal state of the detection pipeline for one frame."""
    sanity_report: Optional[SanityReport] = None
    residuals: Optional[ResidualVector] = None
    ae_score: float = 0.0
    composite_score: float = 0.0
    spectral_report: Optional[SpectralReport] = None
    fault_id: int = 0
    fault_confidence: float = 0.0
    fault_name: str = "NOMINAL_FLIGHT"
    recommended_action: str = "Maintain standard flight profile."
    majority_vote_buffer: List[int] = field(default_factory=list)
    channel_scores: Dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Majority vote buffer
# ---------------------------------------------------------------------------

class MajorityVoteBuffer:
    """
    Buffers the last N fault_id predictions.
    Emits a confirmed fault only when ≥ threshold fraction agree on the same id.
    Prevents single-frame false alarms (FAR reduction per audit findings).
    """

    def __init__(self, window: int = 10, threshold: float = 0.8):
        """
        Args:
            window:    Number of recent frames to buffer (10 frames = 500ms at 20 Hz).
            threshold: Fraction that must agree (0.8 = 8/10 frames).
        """
        self._buf: collections.deque = collections.deque(maxlen=window)
        self._threshold = threshold
        self._window = window

    def update(self, fault_id: int) -> Optional[int]:
        """
        Update buffer and return confirmed fault_id if majority agrees,
        else return None (no confirmed fault).
        """
        self._buf.append(fault_id)
        if len(self._buf) < self._window:
            return None
        counts: Dict[int, int] = {}
        for fid in self._buf:
            counts[fid] = counts.get(fid, 0) + 1
        best_id  = max(counts, key=lambda k: counts[k])
        best_cnt = counts[best_id]
        if best_id != 0 and best_cnt >= int(self._threshold * self._window):
            return best_id
        return None

    def reset(self) -> None:
        self._buf.clear()


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

# Alert suppression: once a fault alert fires, hold off for 30 seconds
_ALERT_HOLDOFF_SEC = 30.0


class DetectionPipeline:
    """
    9-Stage real-time detection pipeline (Plane 1).

    Stage 1  Sensor Sanity          < 0.1ms
    Stage 2  Physics Residuals      < 0.5ms
    Stage 3  Anomaly Score          < 2ms   (AE + Z-score max)
    Stage 4  Gearbox FFT            < 2ms   (self-timed, 1s window)
    Stage 5  Channel Score Buffer   < 0.1ms (write to ScoreBuffer)
    Stage 6  Fault Isolation        < 5ms   (RF, only if score > ANOMALY_GATE)
    Stage 7  Majority Vote          < 0.1ms
    Stage 8  Trend Summary          < 0.1ms (read latest from PrognosticsWorker)
    Stage 9  JSON Event Emit        < 0.5ms (if fault confirmed or trend alert)
    """

    ANOMALY_GATE = 0.35          # RF runs only above this composite score
    CONFIDENCE_GATE = 0.55       # Only report fault if RF confidence > this
    TREND_EMIT_SCORE = 0.20      # Emit trend alert if score rising above this
    FAULT_MESH_MAP = {
        1: "Covers_Theme_M_PlasticTheme_0",
        2: "Rotax_912i_Base_M_PlasticGreen_0",
        3: "Wiring_Harness_M_Copper_0",
        4: "Oil_Tank_M_Steel_0",
        5: "Gearbox_Type_2_M_Steel_0",
        6: "Exhaust_System_M_SteelDark_0",
        7: "External_Alternator_M_Steel_0",
        8: "ECU_M_PlasticBlack_0",
    }
    FAULT_NAMES = {
        0: "NOMINAL_FLIGHT",
        1: "CYLINDER_2_CHT_OVERHEAT",
        2: "FUEL_INJECTOR_1_CLOG",
        3: "IGNITION_MISFIRE",
        4: "OIL_PRESSURE_LOSS",
        5: "GEARBOX_VIBRATION",
        6: "EXHAUST_EGT_IMBALANCE",
        7: "ALTERNATOR_VOLTAGE_SAG",
        8: "DUAL_FADEC_ECU_DRIFT",
    }
    PRESCRIPTIVE_ACTIONS = {
        1: "Enrich fuel trim +12% / Throttle back 15% / Initiate RTB vector.",
        2: "Switch to Lane B ECU backup map / Activate auxiliary boost pump.",
        3: "Force FADEC arbitration to redundant Lane B ignition coil set.",
        4: "Immediate throttle to 4,200 RPM / Initiate precautionary landing.",
        5: "Limit rapid throttle transients / Schedule post-flight clutch overhaul.",
        6: "Adjust individual cylinder fuel trim on Cylinder #3.",
        7: "Shed non-essential ISR payload / Engage backup avionics battery bus.",
        8: "Force FADEC to Lane B / Flag Lane A MAP transducer for calibration.",
    }

    def __init__(self,
                 score_buffer: ScoreBuffer,
                 sortie_id: str = "SORTIE-UNKNOWN",
                 on_diagnostic_event: Optional[Callable[[DiagnosticEvent], None]] = None):
        """
        Args:
            score_buffer:        Shared buffer written each frame, read by PrognosticsWorker.
            sortie_id:           Mission identifier for JSON events.
            on_diagnostic_event: Optional callback called with DiagnosticEvent when a
                                 fault is confirmed or a trend alert fires.
        """
        self._buffer = score_buffer
        self._sortie_id = sortie_id
        self._on_event = on_diagnostic_event

        # Sub-components
        self._thermo = RotaxThermoModel()
        self._sanity = SensorSanityValidator()
        self._autoencoder = ResidualAutoencoder()
        self._spectral = GearboxSpectralAnalyser(sample_rate_hz=20.0)
        self._vote = MajorityVoteBuffer(window=10, threshold=0.8)
        self._agent = DiagnosticAgent()

        # RF model (optional — loaded separately)
        self._rf_model = None
        self._rf_classes = None

        # Last-alert holdoff
        self._last_alert_time: float = 0.0

        # Prognostics report reference (set by caller after creating PrognosticsWorker)
        self._prognostics_worker = None

        self._frame_count: int = 0

        # Last per-frame reports from the stateful Stage 1 / Stage 4 sub-components — the
        # public surface external callers (EngineStateService) must read from instead of
        # calling self._sanity.validate() / self._spectral.update() a second time.
        self.last_sanity_report: Optional[SanityReport] = None
        self.last_spectral_report: Optional[SpectralReport] = None

        # Threshold baseline comparator (F13 / G03)
        self._twin_first_detect_time: Optional[float] = None
        self._baseline_first_breach_time: Optional[float] = None
        self._baseline_breached_params: List[str] = []
        self.last_threshold_baseline_report: Optional[ThresholdBaselineReport] = None

    def load_models(self,
                    rf_path: Optional[str] = None,
                    ae_path: Optional[str] = None) -> None:
        """
        Load serialised models. Gracefully skips if files don't exist.
        RF: joblib file. AE: JSON file.
        """
        import os
        # Random Forest
        if rf_path is None:
            rf_path = os.path.join(os.path.dirname(__file__),
                                   "models/rotax_random_forest.joblib")
        if os.path.exists(rf_path):
            try:
                import joblib
                self._rf_model = joblib.load(rf_path)
                self._rf_classes = list(self._rf_model.classes_)
            except Exception:
                self._rf_model = None

        # Autoencoder
        if ae_path is None:
            ae_path = os.path.join(os.path.dirname(__file__),
                                   "models/rotax_autoencoder.json")
        if os.path.exists(ae_path):
            try:
                self._autoencoder.load(ae_path)
            except Exception:
                pass

    def set_prognostics_worker(self, worker) -> None:
        """Attach the PrognosticsWorker so Stage 8 can read its latest report."""
        self._prognostics_worker = worker

    def reset(self, sortie_id: str = "SORTIE-UNKNOWN") -> None:
        """Reset all state for a new sortie."""
        self._sortie_id = sortie_id
        self._sanity.reset()
        self._spectral.reset()
        self._vote.reset()
        self._last_alert_time = 0.0
        self._frame_count = 0
        self._twin_first_detect_time = None
        self._baseline_first_breach_time = None
        self._baseline_breached_params = []
        self.last_threshold_baseline_report = None

    # ------------------------------------------------------------------
    # Main entry point — called once per 20 Hz frame
    # ------------------------------------------------------------------

    def process_frame(self,
                      actual: EnginePhysicalState,
                      prev_actual: Optional[EnginePhysicalState],
                      dt_sec: float = 0.05,
                      ) -> Optional[DiagnosticEvent]:
        """
        Run the full 9-stage pipeline for one telemetry frame.

        Args:
            actual:      Current EnginePhysicalState from CAN/streamer.
            prev_actual: Previous frame state (for sensor sanity rate check).
            dt_sec:      Time since last frame (seconds). Default 0.05s = 20 Hz.

        Returns:
            DiagnosticEvent if a fault is confirmed or trend alert fires.
            None if nominal or below thresholds.
        """
        self._frame_count += 1
        now = actual.TIMESTAMP_SEC if actual.TIMESTAMP_SEC > 0 else time.time()

        # ── Stage 1: Sensor Sanity ────────────────────────────────────
        # SensorSanityValidator is stateful (rolling per-channel history + previous-value
        # rate tracking) — it must be called exactly once per real frame. Calling it again
        # with the same `actual` frame (e.g. from EngineStateService wanting the report for
        # its own use) pushes duplicate/zero-delta samples into that history, artificially
        # deflating the rolling variance until it can spuriously trip FROZEN_ADC on a
        # perfectly healthy sensor. Callers must read self.last_sanity_report instead.
        if prev_actual is not None:
            sanity = self._sanity.validate(actual, dt_sec)
        else:
            from backend.physics.sensor_validator import SanityReport as SR
            sanity = SR(all_sensors_valid=True, drift_detected=False)
        self.last_sanity_report = sanity

        # ── Stage 2: Physics Residuals ────────────────────────────────
        expected = self._thermo.compute_expected_state(
            altitude_ft=actual.ALTITUDE_FT,
            oat_c=actual.OAT_C,
            rpm=actual.ENGINE_RPM,
            tps=actual.TPS,
            tas_knots=actual.TAS_KNOTS,
            flight_phase=actual.FLIGHT_PHASE,
        )
        residuals = self._thermo.compute_residuals(actual, expected)
        # Stage 2b: Residual Shielding (F14) — zero residuals on failing/drifting channels
        if sanity and sanity.failed_channels:
            residuals = apply_residual_shielding(residuals, sanity.failed_channels)

        # ── Stage 3: Anomaly Score ─────────────────────────────────────
        ae_score = 0.0
        if self._autoencoder.is_trained:
            raw_vec = self._autoencoder.residual_to_vector(residuals)
            ae_score = self._autoencoder.score(raw_vec)

        # Composite: max(AE, physics Z-score) — AE catches multi-channel drift,
        # Z-score catches single-channel acute spikes
        composite_score = max(ae_score, residuals.anomaly_score)

        # ── Stage 4: Gearbox FFT ──────────────────────────────────────
        # Same one-call-per-frame constraint as Stage 1: GearboxSpectralAnalyser accumulates
        # a rolling sample buffer and a 60s baseline lock by frame count, so a duplicate call
        # here would silently shrink those windows' real-world duration. Callers must read
        # self.last_spectral_report instead of calling update() again.
        high_rate_vib = getattr(actual, 'high_rate_vib_buffer', None)
        spectral = self._spectral.update(
            actual.VIB_GEARBOX_RMS,
            actual.ENGINE_RPM,
            high_rate_burst=high_rate_vib,
            fs_hz=2000.0,
        )
        self.last_spectral_report = spectral

        # Blend gearbox spectral anomaly into composite if elevated
        if spectral.ready and spectral.anomaly_score > composite_score:
            composite_score = max(composite_score, spectral.anomaly_score * 0.8)

        # ── Stage 5: Write to ScoreBuffer ─────────────────────────────
        channel_scores = {
            "d_CHT_1":     abs(residuals.d_CHT_1) / 15.0,
            "d_CHT_2":     abs(residuals.d_CHT_2) / 15.0,
            "d_CHT_3":     abs(residuals.d_CHT_3) / 15.0,
            "d_CHT_4":     abs(residuals.d_CHT_4) / 15.0,
            "d_EGT_1":     abs(residuals.d_EGT_1) / 60.0,
            "d_EGT_2":     abs(residuals.d_EGT_2) / 60.0,
            "d_EGT_3":     abs(residuals.d_EGT_3) / 60.0,
            "d_EGT_4":     abs(residuals.d_EGT_4) / 60.0,
            "d_OIL_PRESS": abs(residuals.d_OIL_PRESS) / 2.0,
            "d_OIL_TEMP":  abs(residuals.d_OIL_TEMP) / 20.0,
            "d_FUEL_FLOW": abs(residuals.d_FUEL_FLOW) / 6.0,
            "d_MAP":       abs(residuals.d_MAP) / 10.0,
            "d_VIB_RMS":   abs(residuals.d_VIB_RMS) / 2.5,
            "d_BUS_VOLTAGE": abs(residuals.d_BUS_VOLTAGE) / 2.0,
            "__composite__": composite_score,
        }
        # Clamp to [0, 1]
        channel_scores = {k: min(1.0, v) for k, v in channel_scores.items()}
        self._buffer.append(now, composite_score, channel_scores)

        # ── Stage 6: Fault Isolation (only if above anomaly gate) ─────
        fault_id = 0
        fault_confidence = 0.0

        if composite_score > self.ANOMALY_GATE:
            fault_id, fault_confidence = self._classify(actual, expected, residuals,
                                                         spectral, sanity)

        # ── Stage 7: Majority Vote ────────────────────────────────────
        confirmed_fault_id = self._vote.update(fault_id)

        # ── Threshold Baseline Comparator (F13 / G03) ─────────────────
        breached_now = []
        if actual.CHT_1 > 135.0 or actual.CHT_2 > 135.0 or actual.CHT_3 > 135.0 or actual.CHT_4 > 135.0:
            breached_now.append("CHT_REDLINE")
        if actual.EGT_1 > 850.0 or actual.EGT_2 > 850.0 or actual.EGT_3 > 850.0 or actual.EGT_4 > 850.0:
            breached_now.append("EGT_REDLINE")
        if actual.OIL_PRESS < 2.0 or actual.OIL_PRESS > 5.5:
            breached_now.append("OIL_PRESS_REDLINE")
        if actual.OIL_TEMP > 130.0:
            breached_now.append("OIL_TEMP_REDLINE")
        if actual.VIB_GEARBOX_RMS > 2.5:
            breached_now.append("VIB_REDLINE")
        if actual.BUS_VOLTAGE < 12.0:
            breached_now.append("BUS_VOLTAGE_REDLINE")

        if breached_now:
            for p in breached_now:
                if p not in self._baseline_breached_params:
                    self._baseline_breached_params.append(p)
            if self._baseline_first_breach_time is None:
                self._baseline_first_breach_time = now

        # Digital Twin detection condition
        twin_alarmed = (composite_score >= self.ANOMALY_GATE) or (confirmed_fault_id is not None and confirmed_fault_id > 0)
        if twin_alarmed and self._twin_first_detect_time is None:
            self._twin_first_detect_time = now

        lead_time_sec = None
        if self._twin_first_detect_time is not None:
            if self._baseline_first_breach_time is not None:
                lead_time_sec = max(0.0, self._baseline_first_breach_time - self._twin_first_detect_time)
            else:
                lead_time_sec = max(0.0, now - self._twin_first_detect_time)

        self.last_threshold_baseline_report = ThresholdBaselineReport(
            conventional_breached=len(self._baseline_breached_params) > 0,
            breached_parameters=list(self._baseline_breached_params),
            conventional_breach_timestamp=self._baseline_first_breach_time,
            twin_detect_timestamp=self._twin_first_detect_time,
            lead_time_sec=lead_time_sec,
        )

        # ── Stage 8: Read Prognostics Summary ─────────────────────────
        prog_report = None
        if self._prognostics_worker is not None:
            prog_report = self._prognostics_worker.latest_report

        # ── Stage 9: Emit JSON Event ──────────────────────────────────
        event = self._maybe_emit(
            actual, expected, residuals, sanity,
            confirmed_fault_id, fault_confidence,
            composite_score, spectral, prog_report, now,
        )
        return event

    # ------------------------------------------------------------------
    # Stage 6: Classification
    # ------------------------------------------------------------------

    def _classify(self,
                  actual: EnginePhysicalState,
                  expected: EnginePhysicalState,
                  residuals: ResidualVector,
                  spectral: SpectralReport,
                  sanity: SanityReport) -> tuple:
        """
        Returns (fault_id, confidence).
        Uses RF model if available, otherwise physics boundary fallback.
        Sensor-failed channels are excluded from scoring.
        """
        failed = set(sanity.failed_channels) if sanity else set()

        # Try RF model first
        if self._rf_model is not None:
            features = [[
                residuals.d_CHT_1, residuals.d_CHT_2, residuals.d_CHT_3, residuals.d_CHT_4,
                residuals.d_EGT_1, residuals.d_EGT_2, residuals.d_EGT_3, residuals.d_EGT_4,
                residuals.d_OIL_PRESS, residuals.d_OIL_TEMP, residuals.d_FUEL_FLOW, residuals.d_MAP,
                residuals.d_VIB_RMS, residuals.d_BUS_VOLTAGE,
            ]]
            try:
                probs = self._rf_model.predict_proba(features)[0]
                classes = self._rf_classes or list(self._rf_model.classes_)
                max_idx = max(range(len(probs)), key=lambda i: probs[i])
                rf_id = int(classes[max_idx])
                rf_conf = float(probs[max_idx])
                if rf_id != 0 and rf_conf >= self.CONFIDENCE_GATE:
                    return rf_id, rf_conf
            except Exception:
                pass

        # Physics boundary fallback (same logic as RotaxFaultClassifier)
        scores: Dict[int, float] = {i: 0.0 for i in range(1, 9)}

        def sig(x: float) -> float:
            return 1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, x))))

        # F1: CHT_2 Overheat
        if "CHT_2" not in failed:
            avg_o = (residuals.d_CHT_1 + residuals.d_CHT_3 + residuals.d_CHT_4) / 3.0
            if residuals.d_CHT_2 > 12.0 or actual.CHT_2 > 125.0:
                scores[1] = sig((residuals.d_CHT_2 - 10.0) / 4.0 + (residuals.d_CHT_2 - avg_o - 8.0) / 3.0)
        # F2: Injector Clog
        if "FUEL_FLOW" not in failed and residuals.d_FUEL_FLOW < -1.0 and residuals.d_EGT_1 > 20.0:
            scores[2] = sig((-residuals.d_FUEL_FLOW - 1.0) + (residuals.d_EGT_1 - 20.0) / 10.0)
        # F3: Ignition Misfire
        if "EGT_2" not in failed:
            avg_e = (residuals.d_EGT_1 + residuals.d_EGT_3 + residuals.d_EGT_4) / 3.0
            if residuals.d_EGT_2 < -35.0 or (avg_e - residuals.d_EGT_2) > 30.0:
                scores[3] = sig((-residuals.d_EGT_2 - 35.0) / 15.0)
        # F4: Oil Pressure Loss
        if "OIL_PRESS" not in failed and (residuals.d_OIL_PRESS < -0.6 or actual.OIL_PRESS < 2.2):
            scores[4] = sig((-residuals.d_OIL_PRESS - 0.5) / 0.3 + (2.5 - actual.OIL_PRESS) / 0.3)
        # F5: Gearbox Vibration — use spectral if ready, else VIB_RMS
        if "VIB_GEARBOX_RMS" not in failed:
            if spectral is not None and getattr(spectral, 'ready', False) and spectral.harmonic_ratio >= 6.0:
                scores[5] = sig((spectral.harmonic_ratio - 4.0) / 2.0)
            elif residuals.d_VIB_RMS > 0.6 or actual.VIB_GEARBOX_RMS > 1.6:
                scores[5] = sig((residuals.d_VIB_RMS - 0.5) / 0.3)
        # F6: EGT Imbalance
        if "EGT_3" not in failed:
            avg_egt = (actual.EGT_1 + actual.EGT_2 + actual.EGT_4) / 3.0
            if residuals.d_EGT_3 > 35.0 or (actual.EGT_3 - avg_egt) > 45.0:
                scores[6] = sig((residuals.d_EGT_3 - 30.0) / 10.0)
        # F7: Voltage Sag
        if "BUS_VOLTAGE" not in failed and (residuals.d_BUS_VOLTAGE < -0.8 and actual.BUS_VOLTAGE < 13.0):
            scores[7] = sig((-residuals.d_BUS_VOLTAGE - 0.8) / 0.3)
        # F8: FADEC Drift
        if "MAP" not in failed and residuals.d_MAP > 4.5:
            scores[8] = sig((residuals.d_MAP - 4.0) / 1.5)

        best_id   = max(scores, key=lambda k: scores[k])
        best_conf = scores[best_id]
        if best_conf < self.CONFIDENCE_GATE:
            return 0, best_conf
        return best_id, best_conf

    # ------------------------------------------------------------------
    # Stage 9: Event emission
    # ------------------------------------------------------------------

    def _maybe_emit(self,
                    actual: EnginePhysicalState,
                    expected: EnginePhysicalState,
                    residuals: ResidualVector,
                    sanity: SanityReport,
                    confirmed_fault_id: Optional[int],
                    fault_confidence: float,
                    composite_score: float,
                    spectral: SpectralReport,
                    prog_report,
                    now: float) -> Optional[DiagnosticEvent]:
        """
        Build and emit a DiagnosticEvent if:
        - A fault is majority-vote confirmed, OR
        - A degradation trend alert is active (WATCH/WARNING/CRITICAL)

        Respects ALERT_HOLDOFF_SEC to avoid flooding the GCS.
        """
        has_confirmed_fault = confirmed_fault_id is not None and confirmed_fault_id != 0
        has_trend_alert = (prog_report is not None and
                           prog_report.most_critical_alert in ("WATCH", "WARNING", "CRITICAL"))

        if not has_confirmed_fault and not has_trend_alert:
            return None

        # Holdoff: don't emit more than once per 30 seconds
        if now - self._last_alert_time < _ALERT_HOLDOFF_SEC:
            return None
        self._last_alert_time = now

        # Build trigger residuals dict
        trigger_residuals = {
            "CHT_2": {"actual": actual.CHT_2,
                      "physics_expected": expected.CHT_2,
                      "residual": residuals.d_CHT_2, "unit": "deg_C"},
            "EGT_1": {"actual": actual.EGT_1,
                      "physics_expected": expected.EGT_1,
                      "residual": residuals.d_EGT_1, "unit": "deg_C"},
            "OIL_PRESS": {"actual": actual.OIL_PRESS,
                          "physics_expected": expected.OIL_PRESS,
                          "residual": residuals.d_OIL_PRESS, "unit": "bar"},
            "VIB_GEARBOX_RMS": {"actual": actual.VIB_GEARBOX_RMS,
                                 "physics_expected": expected.VIB_GEARBOX_RMS,
                                 "residual": residuals.d_VIB_RMS, "unit": "mm/s"},
            "BUS_VOLTAGE": {"actual": actual.BUS_VOLTAGE,
                            "physics_expected": expected.BUS_VOLTAGE,
                            "residual": residuals.d_BUS_VOLTAGE, "unit": "V"},
        }

        # Trend payload
        trend_payload = {}
        if prog_report is not None and prog_report.channels_with_trends:
            tr = prog_report.channels_with_trends[0]
            ttb = tr.time_to_threshold_min
            trend_payload = {
                "channel": tr.channel,
                "alert_level": tr.alert_level,
                "drift_rate_per_min": tr.drift_rate_per_min,
                "time_to_threshold_min": round(ttb, 1) if ttb < 1e9 else None,
                "model_type": tr.model.model_type if tr.model else None,
                "r_squared": tr.model.r_squared if tr.model else None,
            }

        # RUL payload
        rul_payload = {}
        go_no_go = "UNKNOWN"
        if prog_report is not None:
            for comp, rul in prog_report.rul_estimates.items():
                if rul.rul_p10_min < 1e9:
                    rul_payload[comp] = {
                        "rul_p10_hours": round(rul.rul_p10_min / 60.0, 2),
                        "rul_p50_hours": round(rul.rul_p50_min / 60.0, 2),
                        "rul_p90_hours": round(rul.rul_p90_min / 60.0, 2),
                        "confidence": rul.confidence,
                    }
            if prog_report.go_no_go:
                go_no_go = prog_report.go_no_go.advisory

        fault_id = confirmed_fault_id or 0
        directive = None
        if fault_id > 0:
            directive = self._agent.diagnose(
                fault_id=fault_id,
                confidence=fault_confidence,
                trigger_residuals=trigger_residuals
            )
            fault_name = directive.fault_name
            target_mesh = directive.target_3d_mesh
            action = directive.prescriptive_action
            ata_chapter = directive.ata_chapter
            manual_ref = directive.manual_reference
            checklist = directive.emergency_checklist
            explanation = directive.root_cause_explanation
            maint_order = directive.maintenance_order
        else:
            fault_name = self.FAULT_NAMES.get(0, "NOMINAL_FLIGHT")
            target_mesh = "Rotax_912i_Base_M_PlasticGreen_0"
            action = "Maintain standard flight profile."
            ata_chapter = "ATA 00-00"
            manual_ref = "Rotax 912 iS Standard Operation"
            checklist = []
            explanation = "Propulsion parameters within nominal envelope."
            maint_order = "No maintenance required."

        import datetime
        ts_iso = datetime.datetime.utcfromtimestamp(now).isoformat() + "Z"

        payload = {
            "anomaly_score": round(composite_score, 4),
            "primary_fault_id": fault_id,
            "fault_name": fault_name,
            "confidence": round(fault_confidence, 4),
            "target_mesh": target_mesh,
            "trigger_residuals": trigger_residuals,
            "spectral_harmonic_ratio": spectral.harmonic_ratio if spectral.ready else None,
            "trend_report": trend_payload,
            "rul_estimates": rul_payload,
            "go_no_go_advisory": go_no_go,
            "recommended_action": action,
            "ata_chapter": ata_chapter,
            "manual_reference": manual_ref,
            "root_cause_explanation": explanation,
            "emergency_checklist": checklist,
            "maintenance_order": maint_order,
            "sensor_failures": sanity.failed_channels if sanity else [],
            "threshold_baseline": self.last_threshold_baseline_report.to_dict() if self.last_threshold_baseline_report else {},
        }

        event = DiagnosticEvent(
            timestamp_iso=ts_iso,
            sortie_id=self._sortie_id,
            flight_context={
                "altitude_ft": actual.ALTITUDE_FT,
                "oat_celsius": actual.OAT_C,
                "flight_phase": actual.FLIGHT_PHASE,
                "engine_rpm": actual.ENGINE_RPM,
                "throttle_tps_percent": actual.TPS,
            },
            sensor_sanity={
                "all_sensors_valid": sanity.all_sensors_valid if sanity else True,
                "drift_detected": sanity.drift_detected if sanity else False,
                "failed_channels": sanity.failed_channels if sanity else [],
            },
            ml_detection_payload=payload,
        )

        if self._on_event is not None:
            try:
                self._on_event(event)
            except Exception:
                pass

        return event
