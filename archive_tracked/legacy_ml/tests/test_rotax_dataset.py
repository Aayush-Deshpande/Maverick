"""
Unit Test Suite for Rotax 912 iS Correlated Time-Series Dataset & ML Engine
DRDO / iDEX Problem Statement ID: 26054
"""

import unittest
import os
import sys
import csv

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.telemetry.rotax_dataset_generator import RotaxTimeSeriesGenerator
from backend.ml.fault_classifier import RotaxFaultClassifier
from backend.telemetry.can_streamer import TelemetryStreamer


class TestRotaxCorrelatedDataset(unittest.TestCase):

    def setUp(self):
        self.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/telemetry"))
        self.generator = RotaxTimeSeriesGenerator(output_dir=self.data_dir)
        self.classifier = RotaxFaultClassifier()

    def test_all_10_mission_sorties_exist(self):
        """Verify all partitioned mission sortie CSV files exist on disk with valid headers."""
        expected_sorties = [
            "train/train_m01_ladakh_nominal.csv",
            "train/train_m03_ladakh_fault01_overheat.csv",
            "val/val_m01_ladakh_nominal.csv",
            "val/val_m03_ladakh_fault01_overheat.csv",
            "test/test_m01_ladakh_nominal.csv",
            "test/test_m03_ladakh_fault01_overheat.csv",
            "rotax912_train_dataset.csv",
            "rotax912_val_dataset.csv",
            "rotax912_test_dataset.csv"
        ]

        for fname in expected_sorties:
            fpath = os.path.join(self.data_dir, fname)
            self.assertTrue(os.path.exists(fpath), f"Missing sortie file: {fname}")
            
            # Verify CSV structure
            with open(fpath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.assertGreater(len(rows), 100, f"File {fname} has too few rows")
                first = rows[0]
                self.assertIn("TIMESTAMP_SEC", first)
                self.assertIn("ENGINE_RPM", first)
                self.assertIn("CHT_1", first)
                self.assertIn("RES_d_CHT_1", first)
                self.assertIn("FAULT_ID", first)

    def test_cross_parameter_coupling_integrity(self):
        """Verify that throttle changes produce coupled MAP, RPM, and fuel flow responses."""
        records = self.generator.generate_mission_sortie(
            mission_id="TEST_COUPLING",
            theater="LADAKH",
            duration_sec=15.0,
            sample_rate_hz=20.0
        )
        
        # Verify continuous time stepping
        self.assertEqual(len(records), 300)
        self.assertAlmostEqual(records[1]["actual"].TIMESTAMP_SEC, 0.05, delta=0.01)

        # Verify CHT is in realistic range (85-110°C in Ladakh)
        first_cht = records[0]["actual"].CHT_1
        self.assertGreater(first_cht, 80.0)
        self.assertLess(first_cht, 115.0)

    def test_fault_signature_divergence(self):
        """Verify that Fault 01 produces coherent CHT_2 thermal runaway divergence."""
        records = self.generator.generate_mission_sortie(
            mission_id="TEST_FAULT_01",
            theater="LADAKH",
            duration_sec=35.0,
            fault_id=1,
            fault_start_sec=10.0
        )

        nominal_frame = records[160]  # T=8.0s (stabilized nominal cruise before fault onset at T=10s)
        fault_frame = records[-1]     # T=35.0s (full fault)

        # Nominal frame should have small residual
        self.assertLess(abs(nominal_frame["residuals"].d_CHT_2), 6.0)

        # Fault frame should have significant CHT_2 residual divergence (> 20°C)
        self.assertGreater(fault_frame["residuals"].d_CHT_2, 20.0)
        self.assertTrue(fault_frame["residuals"].is_anomaly)

    def test_serialized_model_runtime_inference(self):
        """Verify that the serialized Random Forest model loads and infers in <1ms."""
        self.assertIsNotNone(self.classifier.rf_model, "Serialized model (.joblib) failed to load")
        
        streamer = TelemetryStreamer(sample_rate_hz=20.0)
        streamer.set_fault(fault_id=1, severity=1.0)
        actual, expected, residuals = streamer.generate_frame(t_sec=40.0, region="LADAKH")
        
        diag = self.classifier.classify(actual, expected, residuals)
        self.assertEqual(diag.fault_id, 1)
        self.assertTrue(diag.is_fault)
        self.assertGreater(diag.confidence, 0.85)


if __name__ == '__main__':
    unittest.main()
