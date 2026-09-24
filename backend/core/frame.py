"""
Canonical low-rate telemetry contract -- B1.1.

Implements docs/build/INTERFACES.md Sec 1 (``Frame``) and Sec 2 (``TruthRecord``).
This is the seam that makes decision D04 ("plant != twin, ground truth isolated")
structural rather than a convention:

  * ``Frame``       -- what a real ECU / MAVLink / CAN source can publish. It has
                       NO field for a fault ID, health index or RUL, so a detector
                       written against it cannot read ground truth even by accident.
  * ``TruthRecord`` -- what only the plant knows (active faults, hidden
                       parameters, whether it has failed). Read by evaluation code
                       only. tests/test_no_truth_leak.py enforces that inference
                       packages never touch these names.

It does not replace ``EnginePhysicalState`` yet -- the live service still runs on
that (see docs/build/SUPERSEDED_VS_CURRENT.md S01/S06). This module is the
target every source adapter (backend/sources/) emits, and the input the future
staged pipeline (B1.3/B1.4) will consume.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

__all__ = [
    "FRAME_SCHEMA_VERSION",
    "FORBIDDEN_FRAME_FIELDS",
    "SOURCE_KINDS",
    "Frame",
    "FaultTruth",
    "TruthRecord",
    "frame_from_plant",
    "truth_from_plant",
]

FRAME_SCHEMA_VERSION = "frame/1"

# Names that must never appear as Frame content: they are outputs of the twin or
# ground truth stamped by the synthetic plant (INTERFACES Sec 1, "Forbidden in Frame").
FORBIDDEN_FRAME_FIELDS = frozenset({"FAULT_ID", "HEALTH_INDEX", "RUL_HOURS"})

SOURCE_KINDS = frozenset({"PLANT", "REPLAY", "MAVLINK", "CAN", "SITL"})

# Quality bit flags (INTERFACES Sec 1: quality[channel] bitmask).
Q_STALE = 1 << 0
Q_FROZEN = 1 << 1
Q_OUT_OF_RANGE = 1 << 2
Q_LANE_DISAGREE = 1 << 3
Q_SHIELDED = 1 << 4
Q_INTERPOLATED = 1 << 5


@dataclass
class Frame:
    """One low-rate telemetry sample in engine-agnostic canonical form.

    Per-cylinder channels are lists indexed from 0 (cylinder 1 = index 0). Any
    channel a source cannot supply is ``None`` (scalars) or an empty list, never
    a made-up default -- a detector must be able to tell "not measured" from
    "measured zero".
    """

    t: float                              # s, monotonic, source clock
    source: str                           # one of SOURCE_KINDS
    engine_config_id: str                 # names a file in configs/engines/
    tail_id: str = "TAIL-UNKNOWN"
    engine_serial: str = "SN-UNKNOWN"

    rpm: Optional[float] = None           # crankshaft rpm
    prop_rpm: Optional[float] = None
    throttle: Optional[float] = None      # %
    map_kpa: Optional[float] = None       # kPa absolute
    boost_target_kpa: Optional[float] = None

    cht: List[float] = field(default_factory=list)   # degC, one entry per cylinder
    egt: List[float] = field(default_factory=list)   # degC per cylinder
    coolant_t: Optional[float] = None

    oil_p: Optional[float] = None         # bar
    oil_t: Optional[float] = None         # degC
    fuel_flow: Optional[float] = None     # kg/h (mass flow; convert at the adapter)
    fuel_t: Optional[float] = None        # degC
    rail_p: Optional[float] = None        # bar

    soi_cmd: List[float] = field(default_factory=list)   # deg BTDC, per cylinder
    qty_cmd: List[float] = field(default_factory=list)   # mm3/stroke, per cylinder
    ign_cmd: Optional[float] = None       # deg BTDC, SI only
    fadec_trim: List[float] = field(default_factory=list)   # %, cylinder balancing
    fadec_adapt: List[float] = field(default_factory=list)  # %, drift adaptation
    fadec_lane: Optional[str] = None      # "A" | "B"

    bus_v: Optional[float] = None         # V
    bus_i: Optional[float] = None         # A
    batt_i: Optional[float] = None        # A

    alt: Optional[float] = None           # ft, pressure altitude
    oat: Optional[float] = None           # degC
    tas: Optional[float] = None           # kt
    phase: Optional[str] = None

    quality: Dict[str, int] = field(default_factory=dict)
    schema_version: str = FRAME_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.source not in SOURCE_KINDS:
            raise ValueError(f"Frame.source {self.source!r} not in {sorted(SOURCE_KINDS)}")
        if len(self.cht) and len(self.egt) and len(self.cht) != len(self.egt):
            raise ValueError("Frame.cht and Frame.egt must have one entry per cylinder each")

    @property
    def n_cylinders(self) -> int:
        return max(len(self.cht), len(self.egt), len(self.soi_cmd))

    def channels(self) -> Dict[str, Any]:
        """Flat canonical-name view (per-cylinder series numbered from 1, plus scalars), skipping unmeasured
        channels. Convenient for logging and for feature builders."""
        out: Dict[str, Any] = {}
        for name in ("rpm", "prop_rpm", "throttle", "map_kpa", "coolant_t", "oil_p", "oil_t",
                     "fuel_flow", "fuel_t", "rail_p", "bus_v", "bus_i", "batt_i", "alt", "oat", "tas"):
            v = getattr(self, name)
            if v is not None:
                out[name] = v
        for prefix, series in (("cht", self.cht), ("egt", self.egt),
                               ("fadec_trim", self.fadec_trim), ("fadec_adapt", self.fadec_adapt)):
            for i, v in enumerate(series, start=1):
                out[f"{prefix}_{i}"] = v
        return out

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Frame":
        """Build from a plain dict, refusing truth/twin-output field names outright."""
        bad = FORBIDDEN_FRAME_FIELDS.intersection(data)
        if bad:
            raise ValueError(
                f"Frame must not carry {sorted(bad)}: those are twin outputs or ground truth "
                f"(docs/build/INTERFACES.md Sec 1)"
            )
        return cls(**data)


@dataclass
class FaultTruth:
    """One plant-side active fault. ``mode`` is the plant's fault name; ``location``
    is a cylinder index (1-based) or None for engine-level faults."""

    mode: str
    location: Optional[int]
    severity: float
    onset_t: float
    ramp_sec: float = 0.0


@dataclass
class TruthRecord:
    """Ground truth for one instant. Evaluation-only (INTERFACES Sec 2)."""

    t: float
    active_faults: List[FaultTruth] = field(default_factory=list)
    plant_params: Dict[str, Any] = field(default_factory=dict)
    failed: bool = False
    failure_mode: Optional[str] = None
    schema_version: str = "truth/1"

    @property
    def is_nominal(self) -> bool:
        return not self.active_faults


# --------------------------------------------------------------------------
# VirtualEngine -> Frame / TruthRecord
# --------------------------------------------------------------------------

def frame_from_plant(raw: Dict[str, float], engine_config_id: str, n_cylinders: int,
                     tail_id: str = "TAIL-PLANT", engine_serial: str = "SN-PLANT") -> Frame:
    """Map a ``VirtualEngine.step()`` sensor frame onto a canonical ``Frame``.

    Uses only keys the plant publishes as sensor readings; ``VirtualEngine.step``
    never includes ground truth. Plant FUEL_FLOW is power_kW x 0.30 + 1.5, i.e. a
    mass flow in kg/h at ~0.30 kg/kWh, matching the Frame contract's unit.
    """
    return Frame(
        t=float(raw["T_SEC"]),
        source="PLANT",
        engine_config_id=engine_config_id,
        tail_id=tail_id,
        engine_serial=engine_serial,
        rpm=raw.get("ENGINE_RPM"),
        throttle=raw.get("TPS"),
        map_kpa=raw.get("MAP"),
        cht=[raw[f"CHT_{i}"] for i in range(1, n_cylinders + 1) if f"CHT_{i}" in raw],
        egt=[raw[f"EGT_{i}"] for i in range(1, n_cylinders + 1) if f"EGT_{i}" in raw],
        oil_p=raw.get("OIL_PRESS"),
        oil_t=raw.get("OIL_TEMP"),
        fuel_flow=raw.get("FUEL_FLOW"),
        fuel_t=raw.get("FUEL_TEMP_C"),
        bus_v=raw.get("BUS_VOLTAGE"),
        batt_i=raw.get("BATTERY_CURRENT"),
        alt=raw.get("ALTITUDE_FT"),
        oat=raw.get("OAT_C"),
    )


def truth_from_plant(truth: Dict[str, Any]) -> TruthRecord:
    """Map ``VirtualEngine.truth()`` onto a ``TruthRecord``."""
    faults = [
        FaultTruth(mode=f["name"], location=f.get("cylinder"), severity=f["severity"],
                   onset_t=f["onset_t"], ramp_sec=f.get("ramp_sec", 0.0))
        for f in truth.get("active_faults", [])
    ]
    params = {k: truth[k] for k in ("cht_true", "cooling_degradation", "bore_wear") if k in truth}
    return TruthRecord(
        t=float(truth["t_sec"]),
        active_faults=faults,
        plant_params=params,
        failed=bool(truth.get("failed", False)),
        failure_mode=truth.get("failure_reason"),
    )
