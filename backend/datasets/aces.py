"""Synthetic ACES-shaped scenario generator (not a NASA ACES file loader).

Dataset: NASA ACES Flight Experiments (Altus II UAV / Rotax 914 Turbocharged Spark Ignition Engine).
The real raw-file parser is ``backend/telemetry/aces_loader.py``. This adapter currently
generates a hand-authored nominal trajectory and must be treated as SIMULATION evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from backend.core.frame import Frame, TruthRecord, FaultTruth
from backend.datasets.base import BaseDatasetLoader, DatasetManifest, DatasetRecord, EvidenceClass


class ACESLoader(BaseDatasetLoader):
    """Generate a synthetic ACES-shaped trajectory; does not read NASA ACES files."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        super().__init__(data_dir)

    def get_manifest(self) -> DatasetManifest:
        return DatasetManifest(
            name="NASA_ACES_ALTUS_II",
            version="1.0",
            evidence_class=EvidenceClass.SIMULATION,
            license="NASA Open Data / US Public Domain",
            citation="NASA Dryden Flight Research Center, Altus II High-Altitude UAV Airborne Combustion Research Flights, 1999",
            is_permissive=True,
            channel_mapping={
                "ENG_RPM": "rpm",
                "MAP_INHG": "map_kpa",
                "OIL_PRESS_PSI": "oil_p_bar",
                "OIL_TEMP_F": "oil_t_c",
                "CHT_1..4": "cht",
                "EGT_1..4": "egt",
            },
            num_units=8,
            num_samples=len(self.list_units()) * 150,
            description="Synthetic illustrative Rotax 914 trajectory; raw NASA ACES files are not read by this adapter.",
        )

    def list_units(self) -> List[str]:
        return [f"ACES_FLIGHT_{i:02d}" for i in range(1, 9)]

    def load_unit(self, unit_id: str) -> List[DatasetRecord]:
        records: List[DatasetRecord] = []
        # Simulate / stream ACES flight trajectory with altitude climb and cruise
        for i in range(150):
            t = i * 1.0  # 1 Hz telemetry
            # Altitude profile climbing to 20,000 ft
            alt_m = min(6000.0, 50.0 + i * 40.0)
            rpm = 5200.0 + np.random.normal(0, 15.0)

            frame = Frame(
                t=t,
                source="PLANT",
                engine_config_id="rotax_914",
                tail_id=f"ACES-ROTAX914-{unit_id}",
                rpm=rpm,
                map_kpa=125.0 - (alt_m / 6000.0) * 10.0,
                cht=[135.0 + (alt_m / 6000.0) * 15.0 + (c * 2.0) for c in range(4)],
                egt=[780.0 + (alt_m / 6000.0) * 25.0 + (c * 5.0) for c in range(4)],
                oil_p=4.8 - (alt_m / 6000.0) * 0.4,
                oil_t=88.0 + (alt_m / 6000.0) * 10.0,
                fuel_flow=6.2,
                alt=alt_m * 3.28084,
            )
            truth = TruthRecord(
                t=t,
                origin="SCRIPTED",
                active_faults=[],  # Nominal flight
            )
            records.append(
                DatasetRecord(
                    dataset_name="NASA_ACES_ALTUS_II",
                    unit_id=unit_id,
                    sample_index=i,
                    t_sec=t,
                    frame=frame,
                    truth=truth,
                )
            )
        return records
