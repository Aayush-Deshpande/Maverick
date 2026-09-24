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
    "unit_caveat": (
        "EGT_1..4 and CHT: the channel BINDING is verified (B0.3, 2026-09-24) -- "
        "each resolves to a distinct, name-confirmed, physically-continuous "
        "per-cylinder signal, cross-checked against an independently-decoded "
        "ACES file in competitors/Adityaraj13b/AeroPulse (its CHT column "
        "matches this loader's binding to 5 significant figures). The numeric "
        "SCALE is NOT confirmed to be Celsius: ACES's own 'DEG' unit label is "
        "generic and, like the name field, suffers the same column-boundary "
        "artifact, so it cannot be read reliably at these column indices "
        "either. Observed EGT values run ~1200-1400 in ACES's native scale, "
        "too high to be a calibrated Celsius EGT reading but plausible as "
        "Fahrenheit (683-760C equivalent) or as an uncalibrated raw scale -- "
        "do not report an EGT/CHT figure in degrees Celsius, or compute a "
        "sim-to-real bias/error against this loader's thermo model (which IS "
        "in Celsius) until the ACES documentation PDF confirms the scale. "
        "Relative comparisons (this flight vs that flight, climb vs cruise, "
        "trend direction) remain valid regardless of the unit."
    ),
}

# Channel-name fragments to look for. The .mat name matrix is a fixed-width char
# array (16 character-position rows x n_channels columns); scipy strips
# trailing whitespace per row, so rows arrive at unequal lengths and must be
# right-padded before reading column-wise (see _decode_name_matrix). Even after
# that, the reconstructed 16-character name for column j is not always exactly
# and only column j's true name: ACES's own name field is evidently narrower
# than some true descriptions, so a channel's decoded name reliably STARTS with
# that channel's true (possibly truncated) name, and may then run on into the
# start of column j+1's name if there was room left in the 16-character field
# (e.g. column 92 decodes as "EGT 1 EGT 2 Altn" -- "EGT 1" is genuinely column
# 92's name; "EGT 2 Altn..." is the start of column 93's name bleeding into the
# same field). Confirmed empirically against M080001.mat (session 2026-09-24):
# every alias below was verified to occur at position 0 of its target column's
# decoded name, and find_channel() below now requires that position, which is
# what actually fixed the binding (see docs/IMPLEMENTATION_LOG.md B0.3) --
# matching *anywhere* in the string, as this used to do, picks up trailing
# bleed-through from the PRECEDING column instead (e.g. "egt 1" also occurs,
# at position 11, in column 91's decoded name "Water Temp EGT 1", which is
# actually the water/coolant temperature channel wearing a borrowed tail).
CHANNEL_ALIASES: Dict[str, Tuple[str, ...]] = {
    "ENGINE_RPM": ("engine speed",),
    "EGT_1": ("egt 1",),
    "EGT_2": ("egt 2",),
    "EGT_3": ("egt 3",),
    "EGT_4": ("egt 4",),
    "CHT": ("cht",),
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
#
# EGT_1..4 and CHT ranges below are deliberately wide and NOT asserted to be
# degrees Celsius -- see the "unit caveat" in ACES_PROVENANCE. They exist to
# catch a wrong binding (a channel that is obviously something else entirely,
# e.g. a voltage or a position feedback), not to validate a calibrated
# temperature. Do not narrow these to a "plausible Celsius EGT" band; that
# would silently re-introduce the same binding bug this range is here to catch,
# because the ACES-native scale for these specific channels runs materially
# higher than a calibrated Celsius EGT would (confirmed against both this
# file's own EGT/CHT columns and an independently-implemented ACES decode in
# competitors/Adityaraj13b/AeroPulse/data_sample/aces_demo.csv, whose CHT
# column matches this loader's CHT binding to 5 significant figures without
# any unit conversion applied).
_PLAUSIBLE_RANGE: Dict[str, Tuple[float, float]] = {
    "ENGINE_RPM": (0.0, 7000.0),
    "EGT_1": (100.0, 1800.0),
    "EGT_2": (100.0, 1800.0),
    "EGT_3": (100.0, 1800.0),
    "EGT_4": (100.0, 1800.0),
    "CHT": (50.0, 400.0),
    # Widened from the original (-60, 160) -- that band assumed a calibrated
    # Celsius reading and was silently rejecting the correctly-bound channel
    # (observed native-scale values run to ~220; see the unit caveat above).
    "COOLANT_TEMP": (-60.0, 260.0),
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
        """Column whose decoded name starts with ``fragment`` (case-insensitive).

        Requiring position 0 rather than "anywhere in the string" is the B0.3
        fix (docs/IMPLEMENTATION_LOG.md, session 2026-09-24): each column's
        decoded 16-character name reliably begins with that column's own true
        name and may run on into the next column's name if there is room left
        in the field, so a fragment can appear at the START of its true
        column's name (correct) or trailing off the END of the *previous*
        column's decoded name (wrong binding). Preferring the earliest column
        with a start-of-string match keeps this a single pass, matching the
        method's previous O(n) contract."""
        frag = fragment.lower()
        for i, n in enumerate(self.names):
            if n.lower().startswith(frag):
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
