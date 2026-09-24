"""Calibrated-residual detection stack (W1/W11): per-tail calibration, cheap scorers, conformal thresholds,
persistence gate, and the sparse reservoir tier. Consumes canonical ``Frame`` only."""

from backend.detect.calibration import TailCalibration
from backend.detect.detector import DetectionResult, PersistenceGate, ResidualDetector, conformal_threshold
from backend.detect.reservoir import Reservoir
from backend.detect.scorers import FlyBloomScorer, Mahalanobis, MaxAbsZ

__all__ = ["TailCalibration", "ResidualDetector", "DetectionResult", "PersistenceGate", "conformal_threshold",
           "Reservoir", "FlyBloomScorer", "Mahalanobis", "MaxAbsZ"]
