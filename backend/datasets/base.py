"""Universal Dataset Abstraction and Metadata Contracts (B7.1, CAP-07, D19, D35).

Defines:
1. `DatasetManifest`: Provenance, evidence class, license, citation, and channel mapping.
2. `DatasetRecord`: Standardized time-series sample wrapping Frame + evaluation TruthRecord.
3. `BaseDatasetLoader`: Abstract base class for all benchmark dataset adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from backend.core.frame import Frame, TruthRecord


class EvidenceClass(str, Enum):
    SIMULATION = "SIMULATION"
    PUBLIC_PROXY = "PUBLIC_PROXY"
    BENCHMARK = "BENCHMARK"
    REAL_FLIGHT = "REAL_FLIGHT"


@dataclass
class DatasetManifest:
    name: str
    version: str
    evidence_class: EvidenceClass
    license: str
    citation: str
    is_permissive: bool
    channel_mapping: Dict[str, str]
    num_units: int
    num_samples: int
    description: str


@dataclass
class DatasetRecord:
    dataset_name: str
    unit_id: str
    sample_index: int
    t_sec: float
    frame: Frame
    truth: Optional[TruthRecord] = None


class BaseDatasetLoader(ABC):
    """Abstract loader for external benchmarks and flight telemetry datasets."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = data_dir or (Path(__file__).resolve().parents[2] / "data")

    @abstractmethod
    def get_manifest(self) -> DatasetManifest:
        """Return dataset provenance and licensing metadata."""
        pass

    @abstractmethod
    def load_unit(self, unit_id: str) -> List[DatasetRecord]:
        """Load full trajectory for a specific unit/engine."""
        pass

    @abstractmethod
    def list_units(self) -> List[str]:
        """List available unit/flight identifiers."""
        pass
