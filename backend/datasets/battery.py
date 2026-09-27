"""Synthetic NASA PCoE-shaped scenario generator (not a NASA battery-file loader).

Dataset: NASA Ames Prognostics Center of Excellence Battery Aging Dataset
Units: B0005, B0006, B0007, B0018 (Charge/Discharge cycles until 70% rated capacity).
License: NASA Open Data / Public Domain
Evidence Class: SIMULATION
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from backend.core.frame import Frame, TruthRecord, FaultTruth
from backend.datasets.base import BaseDatasetLoader, DatasetManifest, DatasetRecord, EvidenceClass


class BatteryLoader(BaseDatasetLoader):
    """Loader for NASA PCoE battery electrochemical aging dataset."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        super().__init__(data_dir)

    def get_manifest(self) -> DatasetManifest:
        return DatasetManifest(
            name="NASA_PCOE_BATTERY",
            version="1.0",
            evidence_class=EvidenceClass.SIMULATION,
            license="NASA Public Domain / US Gov Work",
            citation="Saha & Goebel, Battery Data Set, NASA Ames Prognostics Data Repository, 2007",
            is_permissive=True,
            channel_mapping={
                "voltage_measured": "v_batt_volts",
                "current_measured": "i_batt_amps",
                "temperature_measured": "t_batt_c",
                "capacity": "capacity_ah",
            },
            num_units=4,
            num_samples=len(self.list_units()) * 168,
            description="Synthetic battery-like capacity fade; NASA PCoE source files are not read by this adapter.",
        )

    def list_units(self) -> List[str]:
        return ["B0005", "B0006", "B0007", "B0018"]

    def load_unit(self, unit_id: str) -> List[DatasetRecord]:
        records: List[DatasetRecord] = []
        rated_cap = 2.0  # Ah
        num_cycles = 168

        for cycle in range(1, num_cycles + 1):
            # Degradation curve with subtle capacity regeneration jumps
            t = float(cycle * 3600.0)
            fade = (cycle / 168.0) * 0.35 + (0.01 if cycle % 15 == 0 else 0.0)
            cap = max(1.2, rated_cap * (1.0 - fade))
            is_eol = cap <= 1.40  # 70% threshold

            frame = Frame(
                t=t,
                source="PLANT",
                engine_config_id="rotax_915is",
                tail_id=f"BATTERY-{unit_id}",
                rpm=0.0,
                map_kpa=101.3,
                cht=[25.0 + fade * 15.0] * 4,
                egt=[25.0] * 4,
                oil_p=0.0,
                oil_t=25.0,
                fuel_flow=0.0,
            )
            active_faults = [FaultTruth(mode="CAPACITY_EOL", location=None, severity=fade, onset_t=t)] if is_eol else []
            truth = TruthRecord(
                t=t,
                origin="SCRIPTED",
                active_faults=active_faults,
            )
            records.append(
                DatasetRecord(
                    dataset_name="NASA_PCOE_BATTERY",
                    unit_id=unit_id,
                    sample_index=cycle,
                    t_sec=t,
                    frame=frame,
                    truth=truth,
                )
            )
        return records
