"""
NASA ACES real-telemetry loader — F48.

The single most damaging objection to this project, and to every competing one,
is that the model is validated against data produced by the same model. This
loader removes that objection for the physics layer by reading **real flight
telemetry from a real MALE-class UAV flying the engine we model**.

Source
------
ACES (Altus Cumulus Electrification Study), NASA GHRC DAAC, July-August 2002.
Altus II UAV operating out of Naval Air Facility Key West, powered by a
**Rotax 914** turbocharged four-cylinder — the same engine used on the MQ-1
Predator, IAI Heron and Hermes 900, and the engine `configs/engines/rotax_914.json`
describes. Data are `.mat` files: `M*` mechanical/engine, `A*` aircraft state,
780 channels at 1 Hz in hour-long granules.

  DOI 10.5067/ACES/MULTIPLE/DATA101

What this data can and cannot support
-------------------------------------
CAN:  validating that our thermodynamic model reproduces real relationships —
      RPM vs throttle vs altitude, EGT vs power, charge/coolant temperature
      behaviour, fuel flow — on a real engine in real flight.
CAN:  supplying a genuine nominal baseline for anomaly detection, so "normal"
      is learned from an actual engine rather than from our own generator.
CANNOT: supply fault labels or RUL ground truth. Every ACES flight completed
      safely. There are no run-to-failure trajectories and no instances of the
      eight PS fault modes. Any "anomaly" found here is a flight-envelope
      transient, not a failure, and must never be reported as one.

That limitation is recorded here, in the loader, so it travels with the data
rather than living in a document nobody reads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "ACESGranule",
    "load_granule",
    "list_granules",
    "CHANNEL_ALIASES",
    "ACES_PROVENANCE",
]

ACES_PROVENANCE = {
    "dataset": "ACES Aircraft and Mechanical Data V1",
    "doi": "10.5067/ACES/MULTIPLE/DATA101",
    "platform": "Altus II UAV",
    "engine": "Rotax 914 (turbocharged, 4-cyl)",
    "campaign": "Altus Cumulus Electrification Study, Key West FL, Jul-Aug 2002",
    "daac": "NASA GHRC",
    "sample_rate_hz": 1.0,
    "has_fault_labels": False,
    "has_run_to_failure": False,
    "caveat": (
        "All flights completed safely. No labelled faults, no RUL ground truth. "
        "Usable for physics validation and nominal baselining only."
    ),
}

# Channel-name fragments to look for. The .mat name matrix is a fixed-width char
# array with embedded newlines, so reconstructed names are approximate at their
# boundaries; matching on a distinctive fragment is more robust than equality.
CHANNEL_ALIASES: Dict[str, Tuple[str, ...]] = {
    "ENGINE_RPM": ("engine speed",),
    "EGT_1": ("egt 1",),
    "EGT_2": ("egt 2",),
    "COOLANT_TEMP": ("water temp",),
    "ALTERNATOR_TEMP": ("altntr temp",),
    "ENGINE_THERMO_2": ("eng thermo",),
    "FUEL_PRESSURE": ("fuel  press", "fuel press"),
    "FUEL_BURNED": ("fuel burned",),
    "FUEL_LEVEL_1": ("fuel level #1",),
    "BUS_VOLTAGE": ("pwr sup volt",),
    "BATTERY_VOLTAGE": ("bat 1 volt",),
    "BATTERY_TEMP": ("bat 1 temp",),
    "ALTITUDE_FT": ("altitude msl",),
    "DENSITY_ALTITUDE_FT": ("density alt",),
    "STATIC_PRESSURE": ("static press",),
    "AIRSPEED": ("airspeed",),
    "THROTTLE_CMD": ("throttle cmd",),
    "OAT_C": ("atmos temp",),
    "COOLING_FLAP_POS": ("cool flp pos",),
    "PROP_PITCH_FBK": ("prop p fdbk",),
}

# Sanity envelopes used to confirm a resolved channel really is what we think.
# A name-matching heuristic that silently binds the wrong column would poison
# every downstream validation result, so binding is checked against physics.
_PLAUSIBLE_RANGE: Dict[str, Tuple[float, float]] = {
    "ENGINE_RPM": (0.0, 7000.0),
    "EGT_1": (0.0, 1100.0),
    "EGT_2": (0.0, 1100.0),
    "COOLANT_TEMP": (-60.0, 160.0),
    "ALTITUDE_FT": (-1500.0, 60000.0),
    "BUS_VOLTAGE": (0.0, 40.0),
    "BATTERY_VOLTAGE": (0.0, 40.0),
    "THROTTLE_CMD": (-10.0, 120.0),
    "OAT_C": (-90.0, 60.0),
}


def _decode_name_matrix(rows: Sequence[str], width: int) -> List[str]:
    """Rebuild per-channel names from the fixed-width char matrix.

    scipy strips trailing whitespace per row, so rows arrive at unequal lengths;
    they must be right-padded before reading column-wise or every channel after
    the first short row is misaligned.
    """
    padded = [str(r).ljust(width) for r in rows]
    names: List[str] = []
    for j in range(width):
        raw = "".join(r[j] for r in padded)
        cleaned = raw.replace("\x00", " ").replace("\x7f", " ").replace("\n", " ")
        names.append(re.sub(r"\s+", " ", cleaned).strip())
    return names


@dataclass
class ACESGranule:
    """One hour of Altus II telemetry."""

    path: Path
    names: List[str]
    units: List[str]
    data: "object"  # numpy ndarray (n_channels, n_samples)
    kind: str  # "mechanical" | "aircraft"

    @property
    def n_channels(self) -> int:
        return int(self.data.shape[0])

    @property
    def n_samples(self) -> int:
        return int(self.data.shape[1])

    @property
    def duration_sec(self) -> float:
        return float(self.n_samples) / ACES_PROVENANCE["sample_rate_hz"]

    def find_channel(self, fragment: str) -> Optional[int]:
        frag = fragment.lower()
        for i, n in enumerate(self.names):
            if frag in n.lower():
                return i
        return None

    def resolve(self, canonical: str) -> Optional[int]:
        """Map a canonical ANUMAAN channel name onto this file's column index."""
        for frag in CHANNEL_ALIASES.get(canonical, ()):
            idx = self.find_channel(frag)
            if idx is not None:
                return idx
        return None

    def series(self, canonical: str, validate: bool = True):
        """Return one channel's samples, or None if absent/implausible."""
        import numpy as np

        idx = self.resolve(canonical)
        if idx is None:
            return None
        values = np.asarray(self.data[idx], dtype="float64")
        if validate and canonical in _PLAUSIBLE_RANGE:
            lo, hi = _PLAUSIBLE_RANGE[canonical]
            finite = values[np.isfinite(values)]
            if finite.size:
                med = float(np.median(finite))
                if not (lo <= med <= hi):
                    # Name matched but the physics does not: refuse to bind.
                    return None
        return values

    def available(self) -> Dict[str, int]:
        """Canonical channels that resolve *and* pass the plausibility check."""
        out: Dict[str, int] = {}
        for canonical in CHANNEL_ALIASES:
            if self.series(canonical) is not None:
                idx = self.resolve(canonical)
                if idx is not None:
                    out[canonical] = idx
        return out

    def to_frame(self):
        """pandas DataFrame of the resolvable canonical channels, if pandas exists."""
        import pandas as pd

        cols = {}
        for canonical in CHANNEL_ALIASES:
            s = self.series(canonical)
            if s is not None:
                cols[canonical] = s
        df = pd.DataFrame(cols)
        df.insert(0, "t_sec", [i / ACES_PROVENANCE["sample_rate_hz"] for i in range(len(df))])
        return df


def load_granule(path: Path | str) -> ACESGranule:
    """Load one ACES `.mat` granule."""
    import scipy.io as sio

    path = Path(path)
    mat = sio.loadmat(str(path))
    data = mat["data"]
    width = int(data.shape[0])
    names = _decode_name_matrix(list(mat["m_name"]), width)
    units = _decode_name_matrix(list(mat["m_units"]), width) if "m_units" in mat else [""] * width
    kind = "mechanical" if path.name.upper().startswith("M") else "aircraft"
    return ACESGranule(path=path, names=names, units=units, data=data, kind=kind)


def list_granules(root: Path | str, kind: str = "mechanical") -> List[Path]:
    """All granules of a kind under `root`, sorted."""
    root = Path(root)
    prefix = "M" if kind == "mechanical" else "A"
    return sorted(p for p in root.rglob("*.mat") if p.name.upper().startswith(prefix))
