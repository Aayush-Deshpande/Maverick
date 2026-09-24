"""
Unit Test Suite for Rotax 912 iS Fast ML Fault Classifier & RUL Prognostics
DRDO / iDEX Problem Statement ID: 26054
"""

import unittest
import time
import sys
import os

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.telemetry.can_streamer import TelemetryStreamer
from backend.ml.fault_classifier import RotaxFaultClassifier, DiagnosticResult
from backend.ml.rul_estimator import RULEstimator, MissionGoNoGoAdvisory


class TestRotaxMLClassifier(unittest.TestCase):

    def setUp(self):
        self.streamer = TelemetryStreamer(sample_rate_hz=20.0)
        self.classifier = RotaxFaultClassifier()
        self.rul_estimator = RULEstimator()

    def test_nominal_flight_classification(self):
        """Test that healthy flight is classified as NOMINAL (Fault ID 0)."""
        actual, expected, residuals = self.streamer.generate_frame(t_sec=10.0, region="LADAKH")
        diag: DiagnosticResult = self.classifier.classify(actual, expected, residuals)

        self.assertEqual(diag.fault_id, 0)
        self.assertEqual(diag.fault_name, "NOMINAL_FLIGHT")
        self.assertFalse(diag.is_fault)
        self.assertGreater(diag.confidence, 0.70)

    def test_all_8_drdo_fault_classifications(self):
        """Test that every single one of the 8 DRDO canonical faults is correctly classified."""
        for fault_id in range(1, 9):
            self.streamer.reset_fault()
            self.streamer.time_sec = 0.0
            self.streamer.set_fault(fault_id=fault_id, severity=1.0)
            
            # Generate frame at T+40s (allowing full fault onset)
            actual, expected, residuals = self.streamer.generate_frame(t_sec=40.0, region="LADAKH")
            diag: DiagnosticResult = self.classifier.classify(actual, expected, residuals)

            self.assertEqual(
                diag.fault_id, fault_id,
                f"Expected Fault {fault_id} but got Fault {diag.fault_id} ({diag.fault_name})"
            )
            self.assertTrue(diag.is_fault)
            self.assertGreater(diag.confidence, 0.60)
            self.assertIsNotNone(diag.target_mesh)
            self.assertIn("▸", diag.recommended_action)

    def test_environmental_robustness_thar_desert(self):
        """Verify fault classification is accurate in Thar Desert (+44°C) without false alarms."""
        # 1. Nominal in Thar
        actual, expected, residuals = self.streamer.generate_frame(t_sec=10.0, region="THAR_DESERT")
        diag_nominal = self.classifier.classify(actual, expected, residuals)
        self.assertEqual(diag_nominal.fault_id, 0)

        # 2. Injected Oil Pressure Loss in Thar
        self.streamer.set_fault(fault_id=4, severity=1.0)
        actual, expected, residuals = self.streamer.generate_frame(t_sec=40.0, region="THAR_DESERT")
        diag_fault = self.classifier.classify(actual, expected, residuals)
        self.assertEqual(diag_fault.fault_id, 4)
        self.assertEqual(diag_fault.fault_name, "OIL_PRESSURE_LOSS")

    def test_inference_latency_budget(self):
        """Verify inference latency is well under the 5ms real-time requirement."""
        actual, expected, residuals = self.streamer.generate_frame(t_sec=10.0)
        
        start_time = time.perf_counter()
        for _ in range(1000):
            self.classifier.classify(actual, expected, residuals)
        elapsed_total = time.perf_counter() - start_time
        avg_latency_ms = (elapsed_total / 1000.0) * 1000.0

        # Avg latency should be < 1.0 ms
        self.assertLess(avg_latency_ms, 1.0, f"Latency too high: {avg_latency_ms:.3f} ms")

    def test_rul_mission_go_no_go_validation(self):
        """Test Pillar 1 pre-flight Go / No-Go validation based on component RUL."""
        # 1. Healthy engine with 350h minimum RUL for 18h sortie -> GO
        advisory_go = self.rul_estimator.evaluate_mission_feasibility(planned_sortie_hours=18.0)
        self.assertEqual(advisory_go.status, "GO")
        self.assertGreater(advisory_go.margin_hours, 100.0)

        # 2. Degraded engine with only 12h remaining on Oil Circuit for 18h sortie -> NO_GO
        self.rul_estimator.component_rul["Lubrication_Oil_Circuit"] = 12.0
        advisory_no_go = self.rul_estimator.evaluate_mission_feasibility(planned_sortie_hours=18.0)
        self.assertEqual(advisory_no_go.status, "NO_GO")
        self.assertEqual(advisory_no_go.limiting_subsystem, "Lubrication_Oil_Circuit")
        self.assertLess(advisory_no_go.margin_hours, 0.0)


if __name__ == '__main__':
    unittest.main()
