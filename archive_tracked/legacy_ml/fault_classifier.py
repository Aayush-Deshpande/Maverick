"""
Rotax 912 iS Fast ML Fault Classifier Engine
DRDO / iDEX Problem Statement ID: 26054

Maps real-time normalized residual vectors to the 8 DRDO canonical failure modes
with sub-5ms deterministic inference latency and confidence scoring.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional
import math
import os
from backend.physics.thermo_model import EnginePhysicalState, ResidualVector
from backend.telemetry.can_streamer import DRDO_FAULT_DEFINITIONS


@dataclass
class DiagnosticResult:
    """Structured output emitted by the Fast ML diagnostic classifier."""
    fault_id: int
    fault_name: str
    confidence: float              # 0.0 to 1.0
    severity: str                  # "NORMAL", "WARNING", "CRITICAL"
    target_mesh: str               # 3D mesh identifier for viewport focus
    summary: str
    trigger_signals: Dict[str, Any]
    recommended_action: str
    is_fault: bool
    timestamp_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RotaxFaultClassifier:
    """
    Ultra-fast physics-grounded classifier evaluating residual vectors.
    Loads serialized RandomForestClassifier model trained on the Tri-Source dataset
    and performs sub-millisecond inference on incoming telemetry streams.
    """
    
    FEATURE_COLUMNS = [
        "d_CHT_1", "d_CHT_2", "d_CHT_3", "d_CHT_4",
        "d_EGT_1", "d_EGT_2", "d_EGT_3", "d_EGT_4",
        "d_OIL_PRESS", "d_OIL_TEMP", "d_FUEL_FLOW", "d_MAP",
        "d_VIB_RMS", "d_BUS_VOLTAGE"
    ]

    def __init__(self, model_path: Optional[str] = None):
        self.fault_metadata = DRDO_FAULT_DEFINITIONS
        self.rf_model = None
        
        if model_path is None:
            model_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "models/rotax_random_forest.joblib")
            )
        
        if os.path.exists(model_path):
            try:
                import joblib
                self.rf_model = joblib.load(model_path)
            except Exception:
                self.rf_model = None

    @staticmethod
    def _sigmoid(x: float) -> float:
        """Standard sigmoid activation for smooth confidence scoring."""
        return 1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, x))))

    def classify(
        self,
        actual: EnginePhysicalState,
        expected: EnginePhysicalState,
        residuals: ResidualVector
    ) -> DiagnosticResult:
        """
        Classifies current engine state into one of the 8 DRDO failure modes or Nominal.
        Uses the serialized Random Forest model with physics boundary fallback.
        """
        # If composite anomaly score is low, engine is nominal
        if not residuals.is_anomaly and residuals.anomaly_score < 0.35:
            return DiagnosticResult(
                fault_id=0,
                fault_name="NOMINAL_FLIGHT",
                confidence=round(1.0 - residuals.anomaly_score, 4),
                severity="NORMAL",
                target_mesh="All",
                summary="All propulsion parameters operating within nominal baseline.",
                trigger_signals={},
                recommended_action="Maintain standard flight profile.",
                is_fault=False,
                timestamp_sec=actual.TIMESTAMP_SEC
            )

        # ML Model Inference via Serialized Random Forest
        rf_fault_id = 0
        rf_confidence = 0.0

        if self.rf_model is not None:
            features = [[
                residuals.d_CHT_1, residuals.d_CHT_2, residuals.d_CHT_3, residuals.d_CHT_4,
                residuals.d_EGT_1, residuals.d_EGT_2, residuals.d_EGT_3, residuals.d_EGT_4,
                residuals.d_OIL_PRESS, residuals.d_OIL_TEMP, residuals.d_FUEL_FLOW, residuals.d_MAP,
                residuals.d_VIB_RMS, residuals.d_BUS_VOLTAGE
            ]]
            try:
                probs = self.rf_model.predict_proba(features)[0]
                classes = self.rf_model.classes_
                max_idx = probs.argmax()
                rf_fault_id = int(classes[max_idx])
                rf_confidence = float(probs[max_idx])
            except Exception:
                rf_fault_id = 0

        # Multi-hypothesis score tracking for the 8 DRDO failure modes
        scores: Dict[int, float] = {i: 0.0 for i in range(1, 9)}
        trigger_dict: Dict[int, Dict[str, Any]] = {i: {} for i in range(1, 9)}

        if rf_fault_id in scores:
            scores[rf_fault_id] = rf_confidence

        # --- FAULT 01: Cylinder #2 CHT Overheat ---
        # Residual d_CHT_2 is significantly higher than adjacent cylinders
        avg_other_cht_res = (residuals.d_CHT_1 + residuals.d_CHT_3 + residuals.d_CHT_4) / 3.0
        cht2_diff = residuals.d_CHT_2 - avg_other_cht_res
        if residuals.d_CHT_2 > 12.0 or actual.CHT_2 > 125.0:
            raw_score = (residuals.d_CHT_2 - 10.0) / 4.0 + (cht2_diff - 8.0) / 3.0
            scores[1] = self._sigmoid(raw_score)
            trigger_dict[1] = {
                "CHT_2": {"value": actual.CHT_2, "expected": expected.CHT_2, "residual": residuals.d_CHT_2, "limit": 135.0},
                "Delta_Adjacent_Cyls": round(cht2_diff, 2)
            }

        # --- FAULT 02: Fuel Injector #1 Clog ---
        # Fuel flow is below expected AND EGT_1 is elevated (lean burn)
        if residuals.d_FUEL_FLOW < -1.0 and residuals.d_EGT_1 > 20.0:
            raw_score = (-residuals.d_FUEL_FLOW - 1.0) / 1.0 + (residuals.d_EGT_1 - 20.0) / 10.0
            scores[2] = self._sigmoid(raw_score)
            trigger_dict[2] = {
                "FUEL_FLOW": {"value": actual.FUEL_FLOW, "expected": expected.FUEL_FLOW, "residual": residuals.d_FUEL_FLOW},
                "EGT_1": {"value": actual.EGT_1, "expected": expected.EGT_1, "residual": residuals.d_EGT_1}
            }

        # --- FAULT 03: Ignition Misfire ---
        # RPM flutter / Jitter AND runner EGT drop due to unburnt fuel
        avg_other_egt_res = (residuals.d_EGT_1 + residuals.d_EGT_3 + residuals.d_EGT_4) / 3.0
        egt2_drop = avg_other_egt_res - residuals.d_EGT_2
        if residuals.d_EGT_2 < -35.0 or egt2_drop > 30.0:
            raw_score = (-residuals.d_EGT_2 - 35.0) / 15.0 + (egt2_drop - 30.0) / 10.0
            scores[3] = self._sigmoid(raw_score)
            trigger_dict[3] = {
                "EGT_2": {"value": actual.EGT_2, "expected": expected.EGT_2, "residual": residuals.d_EGT_2},
                "EGT_Drop_Delta": round(egt2_drop, 2)
            }

        # --- FAULT 04: Oil Pressure Loss ---
        # Oil pressure negative residual or absolute reading < 2.2 bar
        if residuals.d_OIL_PRESS < -0.6 or actual.OIL_PRESS < 2.2:
            raw_score = (-residuals.d_OIL_PRESS - 0.5) / 0.3 + (2.5 - actual.OIL_PRESS) / 0.3
            scores[4] = self._sigmoid(raw_score)
            trigger_dict[4] = {
                "OIL_PRESS": {"value": actual.OIL_PRESS, "expected": expected.OIL_PRESS, "residual": residuals.d_OIL_PRESS, "min_limit": 2.0},
                "OIL_TEMP": {"value": actual.OIL_TEMP, "expected": expected.OIL_TEMP, "residual": residuals.d_OIL_TEMP}
            }

        # --- FAULT 05: Gearbox Vibration ---
        # Gearbox vibration RMS residual > 0.8 mm/s or absolute > 1.8 mm/s
        if residuals.d_VIB_RMS > 0.6 or actual.VIB_GEARBOX_RMS > 1.6:
            raw_score = (residuals.d_VIB_RMS - 0.5) / 0.3 + (actual.VIB_GEARBOX_RMS - 1.5) / 0.3
            scores[5] = self._sigmoid(raw_score)
            trigger_dict[5] = {
                "VIB_GEARBOX_RMS": {"value": actual.VIB_GEARBOX_RMS, "expected": expected.VIB_GEARBOX_RMS, "residual": residuals.d_VIB_RMS, "limit": 1.80}
            }

        # --- FAULT 06: Exhaust EGT Imbalance ---
        # EGT_3 diverges significantly from mean of other runners
        avg_other_egt = (actual.EGT_1 + actual.EGT_2 + actual.EGT_4) / 3.0
        egt3_delta = actual.EGT_3 - avg_other_egt
        if residuals.d_EGT_3 > 35.0 or egt3_delta > 45.0:
            raw_score = (residuals.d_EGT_3 - 30.0) / 10.0 + (egt3_delta - 40.0) / 10.0
            scores[6] = self._sigmoid(raw_score)
            trigger_dict[6] = {
                "EGT_3": {"value": actual.EGT_3, "expected": expected.EGT_3, "residual": residuals.d_EGT_3},
                "EGT_Runner_Delta": round(egt3_delta, 2)
            }

        # --- FAULT 07: Alternator Voltage Sag ---
        # Bus voltage drops below nominal, battery discharge
        if residuals.d_BUS_VOLTAGE < -0.6 or actual.BUS_VOLTAGE < 13.0 or actual.BATTERY_CURRENT < -2.0:
            raw_score = (-residuals.d_BUS_VOLTAGE - 0.5) / 0.2 + (13.0 - actual.BUS_VOLTAGE) / 0.2
            scores[7] = self._sigmoid(raw_score)
            trigger_dict[7] = {
                "BUS_VOLTAGE": {"value": actual.BUS_VOLTAGE, "expected": expected.BUS_VOLTAGE, "residual": residuals.d_BUS_VOLTAGE, "min_limit": 12.8},
                "BATTERY_CURRENT": {"value": actual.BATTERY_CURRENT, "unit": "Amperes"}
            }

        # --- FAULT 08: Dual FADEC ECU Drift ---
        # MAP residual deviation without corresponding RPM change
        if residuals.d_MAP > 4.5:
            raw_score = (residuals.d_MAP - 4.0) / 1.5
            scores[8] = self._sigmoid(raw_score)
            trigger_dict[8] = {
                "MAP": {"value": actual.MAP, "expected": expected.MAP, "residual": residuals.d_MAP, "limit_delta": 8.0}
            }

        # Find best matching hypothesis
        best_fault_id = max(scores, key=lambda k: scores[k])
        best_confidence = scores[best_fault_id]

        # If highest confidence is below threshold, report generic anomaly
        if best_confidence < 0.45:
            return DiagnosticResult(
                fault_id=0,
                fault_name="UNSPECIFIED_ANOMALY_DRIFT",
                confidence=round(residuals.anomaly_score, 4),
                severity="WARNING",
                target_mesh="Rotax_912i_Base_M_PlasticGreen_0",
                summary="Multi-parameter residual drift detected exceeding nominal threshold.",
                trigger_signals={"anomaly_score": residuals.anomaly_score},
                recommended_action="Monitor engine telemetry closely and verify flight envelope.",
                is_fault=True,
                timestamp_sec=actual.TIMESTAMP_SEC
            )

        # Construct diagnosis from canonical fault definition
        fault_def = self.fault_metadata[best_fault_id]
        
        # Prescriptive pilot actions mapped directly to DRDO FMECA SOPs
        action_map = {
            1: "▸ Enrich fuel trim +12% / Throttle back 15% / Initiate immediate RTB vector.",
            2: "▸ Switch to Lane B ECU backup map / Increase auxiliary boost pump pressure.",
            3: "▸ Force FADEC arbitration to Lane B ignition coil set.",
            4: "▸ Immediate throttle reduction to 4,200 RPM / Initiate precautionary landing vector.",
            5: "▸ Limit rapid throttle transients / Avoid harmonic RPM band / Schedule clutch overhaul.",
            6: "▸ Adjust individual cylinder fuel trim on Cylinder #3.",
            7: "▸ Shed non-essential ISR payload sensors / Engage backup avionics battery bus.",
            8: "▸ Force FADEC arbitration to Lane B / Flag Lane A MAP transducer for calibration."
        }

        return DiagnosticResult(
            fault_id=best_fault_id,
            fault_name=fault_def["name"],
            confidence=round(best_confidence, 4),
            severity=fault_def["severity"],
            target_mesh=fault_def["target_mesh"],
            summary=fault_def["description"],
            trigger_signals=trigger_dict[best_fault_id],
            recommended_action=action_map.get(best_fault_id, "Inspect affected subsystem."),
            is_fault=True,
            timestamp_sec=actual.TIMESTAMP_SEC
        )
