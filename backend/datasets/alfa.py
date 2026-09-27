"""Synthetic ALFA-shaped scenario generator (not an ALFA dataset file loader).

Dataset: Air Lab Failure and Anomaly Dataset (ALFA)
Focus: Autonomous fixed-wing UAV flights with injected control surface, engine, and actuator faults.
License: CC BY-NC-SA 4.0 (Research use)
Evidence Class: SIMULATION
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from backend.core.frame import Frame, TruthRecord, FaultTruth
from backend.datasets.base import BaseDatasetLoader, DatasetManifest, DatasetRecord, EvidenceClass


class ALFALoader(BaseDatasetLoader):
    """Generate a synthetic ALFA-shaped scenario; does not parse ALFA source files."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        super().__init__(data_dir)

    def get_manifest(self) -> DatasetManifest:
        return DatasetManifest(
            name="ALFA_UAV_FAILURE",
            version="1.0",
            evidence_class=EvidenceClass.SIMULATION,
            license="CC BY-NC-SA 4.0",
            citation="Keipour et al., ALFA: A Dataset for UAV Fault Issues Detection and Autonomous Recovery, IJRR 2021",
            is_permissive=False,  # NC license -> labeled research-only
            channel_mapping={
                "airspeed": "airspeed_tas_mps",
                "throttle": "throttle_pct",
                "roll": "roll_deg",
                "pitch": "pitch_deg",
                "engine_rpm": "rpm",
            },
            num_units=len(self.list_units()),
            num_samples=len(self.list_units()) * 200,
            description="Synthetic engine-failure demonstration; not evidence from ALFA flight logs.",
        )

    def list_units(self) -> List[str]:
        return [f"FLIGHT_ENGINE_FAIL_{i:02d}" for i in range(1, 11)] + [f"FLIGHT_SURFACE_FAIL_{i:02d}" for i in range(1, 11)]

    def load_unit(self, unit_id: str) -> List[DatasetRecord]:
        records: List[DatasetRecord] = []
        is_eng_fail = "ENGINE" in unit_id

        # 200 samples (20 seconds @ 10 Hz)
        for i in range(200):
            t = i * 0.1
            has_failed = (t >= 8.0)
            rpm = 5500.0 if not has_failed else (2800.0 if is_eng_fail else 5500.0)

            frame = Frame(
                t=t,
                source="PLANT",
                engine_config_id="rotax_915is",
                tail_id=f"ALFA-{unit_id}",
                rpm=rpm + np.random.normal(0, 10.0),
                map_kpa=105.0 if not has_failed else 60.0,
                cht=[140.0 - (20.0 if (has_failed and is_eng_fail) else 0.0)] * 4,
                egt=[600.0 - (150.0 if (has_failed and is_eng_fail) else 0.0)] * 4,
                oil_p=4.5,
                oil_t=80.0,
                fuel_flow=5.0,
            )
            active_faults = [FaultTruth(mode="ENGINE_POWER_LOSS", location=None, severity=1.0, onset_t=8.0)] if (has_failed and is_eng_fail) else []
            truth = TruthRecord(
                t=t,
                origin="SCRIPTED",
                active_faults=active_faults,
            )
            records.append(
                DatasetRecord(
                    dataset_name="ALFA_UAV_FAILURE",
                    unit_id=unit_id,
                    sample_index=i,
                    t_sec=t,
                    frame=frame,
                    truth=truth,
                )
            )
        return records
