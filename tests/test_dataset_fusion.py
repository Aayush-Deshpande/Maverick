"""
Unit Tests for Tri-Source Dataset Fusion Engine
DRDO / iDEX Problem Statement ID: 26054

Covers the NASA Source 2 ingestion path (backend/telemetry/dataset_fusion_engine.py),
which previously counted source2_nasa_benchmarks/*.csv files in the manifest but never
actually merged their records into the fused training/validation datasets.
"""

import os
import sys
import csv
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.telemetry.dataset_fusion_engine import TriSourceDatasetFusionEngine


# A tiny synthetic C-MAPSS-format run-to-failure file (2 engines, a few cycles each) — same
# whitespace layout as the real NASA train_FD001.txt: unit cycle op1 op2 op3 + 21 sensors.
def _make_cmapss_txt(path: str):
    sensors = " ".join(["100.0"] * 21)
    lines = []
    for unit, max_cycle in [(1, 3), (2, 5)]:
        for cycle in range(1, max_cycle + 1):
            lines.append(f"{unit} {cycle} 0.0 0.0 100.0 {sensors}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


class TestNASASourceFusion(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.engine = TriSourceDatasetFusionEngine(base_dir=self.tmp_dir)
        _make_cmapss_txt(os.path.join(self.engine.source2_dir, "train_FD001_test.txt"))

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_ingest_source2_nasa_produces_records(self):
        """_ingest_source2_nasa() parses the real NASA file format into fusable records."""
        records = self.engine._ingest_source2_nasa()
        # 2 engines: 3 + 5 cycles = 8 rows
        self.assertEqual(len(records), 8)
        for r in records:
            self.assertIn("telemetry", r)
            self.assertIn("residuals", r)
            self.assertIn("VIB_GEARBOX_RMS", r["telemetry"])
            self.assertIn("HEALTH_INDEX", r["telemetry"])
            self.assertIn("FAULT_ID", r["telemetry"])

    def test_last_cycle_of_each_engine_is_end_of_life(self):
        """The final cycle of each engine should have health_index=0 and RUL=0 (run-to-failure)."""
        records = self.engine._ingest_source2_nasa()
        # Sort by timestamp within an engine is not preserved across engines, but every
        # record with RUL_HOURS == 0 should also have HEALTH_INDEX == 0 (end-of-life row).
        eol_rows = [r for r in records if r["telemetry"]["RUL_HOURS"] == 0.0]
        self.assertEqual(len(eol_rows), 2)  # one per engine
        for r in eol_rows:
            self.assertEqual(r["telemetry"]["HEALTH_INDEX"], 0.0)

    def test_build_fused_master_datasets_merges_all_three_sources(self):
        """The fused manifest reports genuine per-source fused row counts, not just file counts."""
        train_path, val_path, manifest = self.engine.build_fused_master_datasets()

        self.assertTrue(os.path.exists(train_path))
        self.assertTrue(os.path.exists(val_path))

        # Source 2 must be genuinely fused (rows > 0), not merely counted.
        self.assertEqual(manifest["source2_nasa_files"], 1)
        self.assertEqual(manifest["source2_nasa_rows_fused"], 8)
        self.assertGreater(manifest["source3_drdo_rows_fused"], 0)
        self.assertEqual(
            manifest["total_rows"],
            manifest["source1_garmin_rows_fused"] + manifest["source2_nasa_rows_fused"]
            + manifest["source3_drdo_rows_fused"],
        )

        # The NASA-derived rows must actually be present in the written CSVs (not dropped).
        all_rows = list(csv.DictReader(open(train_path, encoding="utf-8"))) + \
            list(csv.DictReader(open(val_path, encoding="utf-8")))
        nasa_rows = [r for r in all_rows if float(r["ALTITUDE_FT"]) == 10000.0 and float(r["OAT_C"]) == 15.0]
        self.assertEqual(len(nasa_rows), 8)

    def test_no_source2_files_yields_no_records(self):
        """With an empty source2 dir, ingestion returns an empty list (no crash)."""
        empty_dir = tempfile.mkdtemp()
        engine = TriSourceDatasetFusionEngine(base_dir=empty_dir)
        self.assertEqual(engine._ingest_source2_nasa(), [])
        shutil.rmtree(empty_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
