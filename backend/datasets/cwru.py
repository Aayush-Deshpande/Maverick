"""Synthetic CWRU-shaped scenario generator (not a CWRU signal-file loader).

Dataset: CWRU Bearing Data Center
Subsets: 12k Drive End Bearing, 48k Drive End Bearing, Fan End Bearing.
Fault Types: Ball Defect (BD), Inner Race (IR), Outer Race (OR @ 3/6/12 o'clock), Normal.
License: Public Educational Domain / CWRU
Evidence Class: SIMULATION
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from backend.core.frame import Frame, TruthRecord, FaultTruth
from backend.datasets.base import BaseDatasetLoader, DatasetManifest, DatasetRecord, EvidenceClass


class CWRULoader(BaseDatasetLoader):
    """Generate illustrative scalar scenarios; does not parse CWRU vibration files."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        super().__init__(data_dir)

    def get_manifest(self) -> DatasetManifest:
        return DatasetManifest(
            name="CWRU_BEARING",
            version="1.0",
            evidence_class=EvidenceClass.SIMULATION,
            license="Public Educational Domain (CWRU)",
            citation="Smith & Randall, Rolling element bearing diagnostics using the Case Western Reserve University data: A benchmark study, MSSP 2015",
            is_permissive=True,
            channel_mapping={
                "DE_time": "drive_end_vibration_accel_g",
                "FE_time": "fan_end_vibration_accel_g",
                "BA_time": "base_accel_g",
                "RPM": "shaft_rpm",
            },
            num_units=len(self.list_units()),
            num_samples=len(self.list_units()) * 100,
            description="Synthetic illustrative bearing-fault scenarios; no CWRU waveform data is loaded.",
        )

    def list_units(self) -> List[str]:
        return [
            "NORMAL_0HP", "NORMAL_1HP", "NORMAL_2HP", "NORMAL_3HP",
            "IR_007_0HP", "IR_014_0HP", "IR_021_0HP",
            "OR_007_6_0HP", "OR_014_6_0HP", "OR_021_6_0HP",
            "BALL_007_0HP", "BALL_014_0HP", "BALL_021_0HP",
        ]

    def load_unit(self, unit_id: str) -> List[DatasetRecord]:
        records: List[DatasetRecord] = []
        is_fault = "NORMAL" not in unit_id
        fault_name = "BEARING_" + unit_id.split("_")[0] if is_fault else "NOMINAL"

        # Generate 100 samples representing sequential time frames
        for i in range(100):
            t = i * 0.1
            vib_amp = 0.05 if not is_fault else 0.45
            frame = Frame(
                t=t,
                source="PLANT",
                engine_config_id="rotax_915is",
                tail_id=f"CWRU-{unit_id}",
                rpm=1797.0 + np.random.normal(0, 1.0),
                map_kpa=101.3,
                cht=[120.0] * 4,
                egt=[550.0] * 4,
                oil_p=4.2,
                oil_t=75.0 + (5.0 if is_fault else 0.0),
                fuel_flow=4.0,
            )
            active_faults = [FaultTruth(mode=fault_name, location=None, severity=1.0, onset_t=0.0)] if is_fault else []
            truth = TruthRecord(
                t=t,
                origin="SCRIPTED",
                active_faults=active_faults,
            )
            records.append(
                DatasetRecord(
                    dataset_name="CWRU_BEARING",
                    unit_id=unit_id,
                    sample_index=i,
                    t_sec=t,
                    frame=frame,
                    truth=truth,
                )
            )
        return records
