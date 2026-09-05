"""
Tri-Source Telemetry Fusion & Dataset Builder Engine
DRDO / iDEX Problem Statement ID: 26054

Fuses:
  - Source 1: Real-world Garmin G3X / G1000 avionics flight logs
  - Source 2: NASA C-MAPSS / CWRU bearing vibration & degradation benchmarks
  - Source 3: Physics-Informed Rotax 912 iS MALE UAV military sorties (Ladakh / Thar)
Calculates 1D thermodynamic residuals and exports master training & validation datasets.
"""

import os
import csv
import json
import glob
from dataclasses import replace
from typing import List, Dict, Any, Tuple, Optional
from backend.physics.thermo_model import RotaxThermoModel, EnginePhysicalState, ResidualVector
from backend.telemetry.can_streamer import TelemetryStreamer, DRDO_FAULT_DEFINITIONS
from backend.telemetry.parsers.garmin_parser import GarminG3XParser
from backend.telemetry.parsers.nasa_prognostics_parser import NASABenchmarkParser

# Baseline flight regime used to ground NASA Source 2 records onto the 27-parameter Rotax
# schema (see TriSourceDatasetFusionEngine._ingest_source2_nasa). NASA C-MAPSS/CWRU records
# only carry cycle/health/vibration/RUL — not Rotax-specific channels — so every other
# telemetry field is held at this fixed generic-cruise physics baseline while gearbox
# vibration, health index, and RUL are driven by the real NASA degradation trajectory.
NASA_GROUNDING_REGIME = {
    "altitude_ft": 10000.0, "oat_c": 15.0, "rpm": 5000.0,
    "tps": 65.0, "tas_knots": 90.0, "flight_phase": "CRUISE_LOITER",
}


class TriSourceDatasetFusionEngine:
    """
    Fuses multi-source telemetry streams, calculates theoretical physics baselines,
    and produces standardized datasets for ML training and mission replay.
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/telemetry"))
        else:
            self.base_dir = base_dir

        self.source1_dir = os.path.join(self.base_dir, "source1_avionics_logs")
        self.source2_dir = os.path.join(self.base_dir, "source2_nasa_benchmarks")
        self.source3_dir = os.path.join(self.base_dir, "source3_drdo_missions")
        self.fused_dir = os.path.join(self.base_dir, "fused_master")

        os.makedirs(self.source1_dir, exist_ok=True)
        os.makedirs(self.source2_dir, exist_ok=True)
        os.makedirs(self.source3_dir, exist_ok=True)
        os.makedirs(self.fused_dir, exist_ok=True)

        self.thermo_model = RotaxThermoModel()
        self.streamer = TelemetryStreamer(sample_rate_hz=20.0)
        self.garmin_parser = GarminG3XParser()
        self.nasa_parser = NASABenchmarkParser()

    def generate_all_source3_drdo_sorties(self) -> Dict[str, str]:
        """
        Generates individual, structured CSV flight logs for Source 3 (DRDO military sorties):
        - Nominal flights in Ladakh & Thar
        - The 8 canonical DRDO failure mode sorties
        """
        generated_files = {}

        # 1. Nominal Ladakh High-Altitude Loiter (20s duration @ 20 Hz = 400 frames for quick build, scaleable)
        ladakh_nominal = self.streamer.generate_flight_log(duration_sec=30.0, region="LADAKH", fault_id=0)
        p1 = os.path.join(self.source3_dir, "sortie_01_ladakh_nominal.csv")
        self._write_records_to_csv(ladakh_nominal, p1)
        generated_files["sortie_01_ladakh_nominal"] = p1

        # 2. Nominal Thar Desert Heat Loiter
        thar_nominal = self.streamer.generate_flight_log(duration_sec=30.0, region="THAR_DESERT", fault_id=0)
        p2 = os.path.join(self.source3_dir, "sortie_02_thar_nominal.csv")
        self._write_records_to_csv(thar_nominal, p2)
        generated_files["sortie_02_thar_nominal"] = p2

        # 3. All 8 Fault Sorties
        fault_scenarios = [
            (1, "LADAKH", "sortie_03_ladakh_fault01_cyl2_overheat"),
            (2, "LADAKH", "sortie_04_ladakh_fault02_injector_clog"),
            (3, "LADAKH", "sortie_05_ladakh_fault03_ignition_misfire"),
            (4, "THAR_DESERT", "sortie_06_thar_fault04_oil_pressure_loss"),
            (5, "LADAKH", "sortie_07_ladakh_fault05_gearbox_vibration"),
            (6, "LADAKH", "sortie_08_ladakh_fault06_egt_imbalance"),
            (7, "THAR_DESERT", "sortie_09_thar_fault07_alternator_sag"),
            (8, "LADAKH", "sortie_10_ladakh_fault08_fadec_drift")
        ]

        for fid, reg, fname in fault_scenarios:
            log = self.streamer.generate_flight_log(duration_sec=40.0, region=reg, fault_id=fid, fault_start_sec=10.0)
            out_path = os.path.join(self.source3_dir, f"{fname}.csv")
            self._write_records_to_csv(log, out_path)
            generated_files[fname] = out_path

        return generated_files

    def _write_records_to_csv(self, records: List[Dict[str, Any]], filepath: str):
        """Helper to write raw telemetry + physics baselines + residuals to a standard CSV."""
        if not records:
            return

        # Flatten nested record structure
        fieldnames = [
            "TIMESTAMP_SEC", "ENGINE_RPM", "PROP_RPM", "TPS",
            "CHT_1", "CHT_2", "CHT_3", "CHT_4",
            "EGT_1", "EGT_2", "EGT_3", "EGT_4",
            "OIL_PRESS", "OIL_TEMP", "FUEL_FLOW", "FUEL_RAIL_P", "MAP",
            "VIB_GEARBOX_RMS", "BUS_VOLTAGE", "BATTERY_CURRENT", "FADEC_ACTIVE_LANE",
            "ALTITUDE_FT", "OAT_C", "TAS_KNOTS", "FLIGHT_PHASE",
            "HEALTH_INDEX", "FAULT_ID", "RUL_HOURS",
            # Residual features
            "RES_d_CHT_1", "RES_d_CHT_2", "RES_d_CHT_3", "RES_d_CHT_4",
            "RES_d_EGT_1", "RES_d_EGT_2", "RES_d_EGT_3", "RES_d_EGT_4",
            "RES_d_OIL_PRESS", "RES_d_OIL_TEMP", "RES_d_FUEL_FLOW", "RES_d_MAP",
            "RES_d_VIB_RMS", "RES_d_BUS_VOLTAGE", "RES_ANOMALY_SCORE", "RES_IS_ANOMALY"
        ]

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                tel = r["telemetry"]
                res = r["residuals"]
                row = {
                    "TIMESTAMP_SEC": r.get("timestamp_sec", tel.get("TIMESTAMP_SEC", 0.0)),
                    "ENGINE_RPM": tel["ENGINE_RPM"],
                    "PROP_RPM": tel["PROP_RPM"],
                    "TPS": tel["TPS"],
                    "CHT_1": tel["CHT_1"],
                    "CHT_2": tel["CHT_2"],
                    "CHT_3": tel["CHT_3"],
                    "CHT_4": tel["CHT_4"],
                    "EGT_1": tel["EGT_1"],
                    "EGT_2": tel["EGT_2"],
                    "EGT_3": tel["EGT_3"],
                    "EGT_4": tel["EGT_4"],
                    "OIL_PRESS": tel["OIL_PRESS"],
                    "OIL_TEMP": tel["OIL_TEMP"],
                    "FUEL_FLOW": tel["FUEL_FLOW"],
                    "FUEL_RAIL_P": tel["FUEL_RAIL_P"],
                    "MAP": tel["MAP"],
                    "VIB_GEARBOX_RMS": tel["VIB_GEARBOX_RMS"],
                    "BUS_VOLTAGE": tel["BUS_VOLTAGE"],
                    "BATTERY_CURRENT": tel["BATTERY_CURRENT"],
                    "FADEC_ACTIVE_LANE": tel["FADEC_ACTIVE_LANE"],
                    "ALTITUDE_FT": tel["ALTITUDE_FT"],
                    "OAT_C": tel["OAT_C"],
                    "TAS_KNOTS": tel["TAS_KNOTS"],
                    "FLIGHT_PHASE": tel["FLIGHT_PHASE"],
                    "HEALTH_INDEX": tel["HEALTH_INDEX"],
                    "FAULT_ID": tel["FAULT_ID"],
                    "RUL_HOURS": tel["RUL_HOURS"],
                    "RES_d_CHT_1": res.get("d_CHT_1", 0.0),
                    "RES_d_CHT_2": res.get("d_CHT_2", 0.0),
                    "RES_d_CHT_3": res.get("d_CHT_3", 0.0),
                    "RES_d_CHT_4": res.get("d_CHT_4", 0.0),
                    "RES_d_EGT_1": res.get("d_EGT_1", 0.0),
                    "RES_d_EGT_2": res.get("d_EGT_2", 0.0),
                    "RES_d_EGT_3": res.get("d_EGT_3", 0.0),
                    "RES_d_EGT_4": res.get("d_EGT_4", 0.0),
                    "RES_d_OIL_PRESS": res.get("d_OIL_PRESS", 0.0),
                    "RES_d_OIL_TEMP": res.get("d_OIL_TEMP", 0.0),
                    "RES_d_FUEL_FLOW": res.get("d_FUEL_FLOW", 0.0),
                    "RES_d_MAP": res.get("d_MAP", 0.0),
                    "RES_d_VIB_RMS": res.get("d_VIB_RMS", 0.0),
                    "RES_d_BUS_VOLTAGE": res.get("d_BUS_VOLTAGE", 0.0),
                    "RES_ANOMALY_SCORE": res.get("anomaly_score", res.get("ANOMALY_SCORE", 0.0)),
                    "RES_IS_ANOMALY": 1 if res.get("is_anomaly", res.get("IS_ANOMALY", False)) else 0
                }
                writer.writerow(row)

    def _ingest_source2_nasa(self) -> List[Dict[str, Any]]:
        """
        Ingests every NASA C-MAPSS run-to-failure file in source2_dir and grounds each
        (cycle, health_index, vib_gearbox_rms, true_rul_hours) record onto the Rotax
        27-parameter schema: gearbox vibration, health index, RUL, and FAULT_ID are driven
        by the real NASA degradation trajectory; every other channel holds at
        NASA_GROUNDING_REGIME's physics baseline (NASA data carries no Rotax-specific
        thermal/electrical/fuel channels to ground those with).

        NASA C-MAPSS "cycles" are flight cycles of a turbofan, not Rotax flight-hours — this
        treats 1 cycle ~= 1 hour-equivalent purely as a long-run degradation *shape* proxy
        (matching the existing NASABenchmarkParser field naming, e.g. true_rul_hours), not a
        literal unit conversion. The genuine contribution is real per-engine failure-timing
        diversity (100 independently-degrading NASA engines) that the single-sortie DRDO
        physics generator has no way to produce on its own (see doc03 §4).
        """
        nasa_files = glob.glob(os.path.join(self.source2_dir, "*.txt")) + \
            glob.glob(os.path.join(self.source2_dir, "*.csv"))
        if not nasa_files:
            return []

        expected = self.thermo_model.compute_expected_state(**NASA_GROUNDING_REGIME)
        # Rotax doc03 §1 fault threshold for VIB_GEARBOX_RMS ("> 1.80 mm/s (3rd harmonic)").
        VIB_FAULT_THRESHOLD = 1.80
        GEARBOX_FAULT_ID = 5

        records = []
        for path in nasa_files:
            try:
                trajectory = self.nasa_parser.parse_run_to_failure_trajectory(path)
            except Exception:
                continue
            for row in trajectory:
                fault_id = GEARBOX_FAULT_ID if row["vib_gearbox_rms"] >= VIB_FAULT_THRESHOLD else 0
                actual = replace(
                    expected,
                    VIB_GEARBOX_RMS=round(row["vib_gearbox_rms"], 3),
                    HEALTH_INDEX=round(row["health_index"], 4),
                    FAULT_ID=fault_id,
                    RUL_HOURS=round(row["true_rul_hours"], 1),
                )
                res = self.thermo_model.compute_residuals(actual, expected)
                records.append({
                    "timestamp_sec": row["cycle_hours"],
                    "telemetry": actual.to_dict(),
                    "residuals": res.to_dict(),
                })
        return records

    def build_fused_master_datasets(self) -> Tuple[str, str, Dict[str, Any]]:
        """
        Fuses Source 1 (Garmin), Source 2 (NASA), and Source 3 (DRDO Sorties)
        into Master Training and Validation CSV datasets.
        """
        # Step 1: Ensure all Source 3 sorties are generated
        self.generate_all_source3_drdo_sorties()

        # Step 2: Ingest Source 1 (Garmin Logs)
        source1_records = []
        garmin_files = glob.glob(os.path.join(self.source1_dir, "*.csv"))
        for gfile in garmin_files:
            parsed_states = self.garmin_parser.parse_csv_file(gfile)
            for state in parsed_states:
                exp = self.thermo_model.compute_expected_state(
                    altitude_ft=state.ALTITUDE_FT,
                    oat_c=state.OAT_C,
                    rpm=state.ENGINE_RPM,
                    tps=state.TPS,
                    tas_knots=state.TAS_KNOTS
                )
                res = self.thermo_model.compute_residuals(state, exp)
                source1_records.append({
                    "telemetry": state.to_dict(),
                    "residuals": res.to_dict()
                })

        # Step 2b: Ingest Source 2 (real NASA C-MAPSS run-to-failure data, if present)
        source2_records = self._ingest_source2_nasa()

        # Step 3: Ingest Source 3 Sortie Files
        source3_records = []
        source3_files = glob.glob(os.path.join(self.source3_dir, "*.csv"))
        for sfile in source3_files:
            with open(sfile, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tel_dict = {
                        k: float(v) if k not in ["FADEC_ACTIVE_LANE", "FLIGHT_PHASE"] else v
                        for k, v in row.items() if not k.startswith("RES_")
                    }
                    res_dict = {
                        k.replace("RES_", ""): float(v) if k != "RES_IS_ANOMALY" else (v == "1")
                        for k, v in row.items() if k.startswith("RES_")
                    }
                    source3_records.append({
                        "telemetry": tel_dict,
                        "residuals": res_dict
                    })

        all_records = source1_records + source2_records + source3_records
        total_count = len(all_records)

        # 80% Train, 20% Validation split
        split_idx = int(total_count * 0.8)
        train_records = all_records[:split_idx]
        val_records = all_records[split_idx:]

        train_path = os.path.join(self.fused_dir, "master_training_dataset.csv")
        val_path = os.path.join(self.fused_dir, "master_validation_dataset.csv")

        self._write_records_to_csv(train_records, train_path)
        self._write_records_to_csv(val_records, val_path)

        # Write manifest
        manifest = {
            "total_rows": total_count,
            "training_rows": len(train_records),
            "validation_rows": len(val_records),
            "source1_garmin_files": len(garmin_files),
            "source1_garmin_rows_fused": len(source1_records),
            "source2_nasa_files": len(glob.glob(os.path.join(self.source2_dir, "*.txt"))) +
                len(glob.glob(os.path.join(self.source2_dir, "*.csv"))),
            "source2_nasa_rows_fused": len(source2_records),
            "source3_drdo_sorties": len(source3_files),
            "source3_drdo_rows_fused": len(source3_records),
            "features_included": 27,
            "residual_dimensions": 14,
            "train_dataset_path": train_path,
            "val_dataset_path": val_path
        }

        manifest_path = os.path.join(self.fused_dir, "dataset_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return train_path, val_path, manifest
