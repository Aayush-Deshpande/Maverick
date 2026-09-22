"""
Engine class as configuration, not hardcoding — F31.

The twin was written around one engine, with its constants at module level. The
problem statement asks for a *scalable, modular* framework, and asserting that
in a document is not the same as demonstrating it. This module makes the engine
a data file, so the same twin can run:

  * Rotax 912 iS  — naturally aspirated spark ignition, AVGAS/MOGAS (Bayraktar TB2)
  * Rotax 914     — turbocharged spark ignition (MQ-1 Predator, IAI Heron,
                    Elbit Hermes 900, and the engine flown on the Altus II UAV
                    whose real telemetry is the NASA ACES dataset)
  * Austro AE300  — turbocharged common-rail compression ignition on Jet-A1
                    (TAPAS BH-201 / Rustom-2), licensed from the Mercedes OM640

That last pair is the point: a spark-ignition boxer and a kerosene-burning
inline diesel are genuinely different combustion architectures, so running both
through one twin is a demonstration of modularity rather than a claim about it.

Ignition mode drives real behavioural differences downstream — a CI engine has
no spark advance and cannot "misfire" in the SI sense, but suffers injector
coking, needle stick and rail-pressure decay, all of which appear as the same
per-cylinder torque deficit the crank-angle detector measures.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

__all__ = [
    "IgnitionMode",
    "InductionType",
    "CylinderLayout",
    "TurbochargerSpec",
    "EngineConfig",
    "load_engine_config",
    "available_engines",
    "CONFIG_DIR",
]

CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs" / "engines"


class IgnitionMode:
    SPARK = "SPARK_IGNITION"
    COMPRESSION = "COMPRESSION_IGNITION"


class InductionType:
    NATURALLY_ASPIRATED = "NATURALLY_ASPIRATED"
    TURBOCHARGED = "TURBOCHARGED"


@dataclass
class CylinderLayout:
    count: int = 4
    arrangement: str = "BOXER"  # BOXER | INLINE | V
    firing_order: List[int] = field(default_factory=lambda: [1, 4, 2, 3])
    bore_mm: float = 79.5
    stroke_mm: float = 61.0
    displacement_cc: float = 1211.0
    compression_ratio: float = 10.5

    @property
    def firing_interval_deg(self) -> float:
        """Crank degrees between firing events on a four-stroke."""
        return 720.0 / self.count

    @property
    def dominant_order(self) -> float:
        """Firing order in shaft orders — 2.0 for a four-cylinder four-stroke.

        This is the validation anchor for the crank-angle chain: a healthy
        engine's order spectrum must be dominated by this line, or the model
        is wrong.
        """
        return self.count / 2.0


@dataclass
class TurbochargerSpec:
    """Present only on boosted engines; see turbo_model.TurbochargerModel."""

    max_boost_kpa: float = 135.0  # absolute manifold pressure at full boost
    critical_altitude_ft: float = 16000.0  # above this, boost can no longer hold
    wastegate_controlled: bool = True
    max_shaft_rpm: float = 180000.0
    intercooled: bool = False
    lag_time_constant_sec: float = 0.8
    surge_margin_min: float = 0.12


@dataclass
class EngineConfig:
    """Everything the twin needs to know about which engine it is modelling."""

    # Identity
    engine_id: str
    display_name: str
    manufacturer: str
    platforms: List[str] = field(default_factory=list)

    # Combustion architecture
    ignition_mode: str = IgnitionMode.SPARK
    induction: str = InductionType.NATURALLY_ASPIRATED
    fuel: str = "AVGAS_100LL"
    cooling: str = "AIR_COOLED_BARRELS_LIQUID_HEADS"

    layout: CylinderLayout = field(default_factory=CylinderLayout)
    turbo: Optional[TurbochargerSpec] = None

    # Ratings
    rated_power_kw: float = 73.5
    rated_rpm: float = 5800.0
    max_continuous_power_kw: float = 69.0
    max_continuous_rpm: float = 5500.0
    idle_rpm: float = 1400.0
    gearbox_ratio: float = 2.4286
    dry_mass_kg: float = 64.0
    tbo_hours: float = 2000.0

    # Nominal fuel/air behaviour used by the thermodynamic model
    nominal_bsfc_g_kwh: float = 285.0
    nominal_lambda: float = 1.0
    nominal_inj_timing_btdc: float = 18.5
    nominal_ign_timing_btdc: Optional[float] = 24.0  # None on CI engines
    rail_pressure_bar: float = 3.0

    # Fuel thermal properties — drives the CFPP / waxing model (F42)
    fuel_cloud_point_c: Optional[float] = None  # kerosene only
    fuel_cfpp_c: Optional[float] = None

    source: str = ""

    # -- derived helpers ----------------------------------------------------

    @property
    def is_turbocharged(self) -> bool:
        return self.induction == InductionType.TURBOCHARGED and self.turbo is not None

    @property
    def is_compression_ignition(self) -> bool:
        return self.ignition_mode == IgnitionMode.COMPRESSION

    @property
    def is_heavy_fuel(self) -> bool:
        return self.fuel.upper().startswith(("JET", "JP", "DIESEL"))

    @property
    def cylinder_count(self) -> int:
        return self.layout.count

    def cht_channels(self) -> List[str]:
        return [f"CHT_{i}" for i in range(1, self.layout.count + 1)]

    def egt_channels(self) -> List[str]:
        return [f"EGT_{i}" for i in range(1, self.layout.count + 1)]

    def applicable_fault_modes(self) -> List[str]:
        """Fault modes physically possible on this engine class.

        Kept here rather than in the detector so that switching engine config
        cannot leave the classifier hunting for a spark misfire on a diesel.
        """
        common = [
            "COOLING_DEGRADATION", "OIL_PRESSURE_LOSS", "OIL_DEGRADATION",
            "SENSOR_DRIFT", "SENSOR_FAILURE", "BEARING_WEAR", "GEARBOX_WEAR",
            "AIR_FILTER_RESTRICTION", "ALTERNATOR_DEGRADATION",
            "COMBUSTION_INSTABILITY",
        ]
        if self.is_compression_ignition:
            common += [
                "INJECTOR_COKING_IDID", "INJECTOR_NEEDLE_STICK",
                "RAIL_PRESSURE_DECAY", "INJECTION_TIMING_DRIFT",
                "GLOW_PLUG_FAILURE", "FUEL_WAXING_CFPP",
            ]
        else:
            common += [
                "MISFIRE", "INJECTOR_CLOG", "IGNITION_TIMING_DRIFT",
                "LEAN_MIXTURE", "RICH_MIXTURE", "DETONATION",
            ]
        if self.is_turbocharged:
            common += [
                "WASTEGATE_STUCK", "TURBO_OVERSPEED", "TURBO_BEARING_WEAR",
                "COMPRESSOR_SURGE", "BOOST_LEAK",
            ]
            if self.turbo and self.turbo.intercooled:
                common.append("INTERCOOLER_FOULING")
        return common

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: Path | str) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path

    @classmethod
    def from_dict(cls, data: dict) -> "EngineConfig":
        data = dict(data)
        layout = data.pop("layout", None)
        turbo = data.pop("turbo", None)
        cfg = cls(**data)
        if layout:
            cfg.layout = CylinderLayout(**layout)
        if turbo:
            cfg.turbo = TurbochargerSpec(**turbo)
        return cfg


def load_engine_config(engine_id: str, config_dir: Path | str | None = None) -> EngineConfig:
    """Load an engine by id, e.g. `load_engine_config("rotax_914")`."""
    directory = Path(config_dir) if config_dir else CONFIG_DIR
    path = directory / f"{engine_id}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"no engine config {engine_id!r} in {directory}; "
            f"available: {', '.join(available_engines(directory)) or 'none'}"
        )
    return EngineConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))


def available_engines(config_dir: Path | str | None = None) -> List[str]:
    directory = Path(config_dir) if config_dir else CONFIG_DIR
    if not directory.exists():
        return []
    return sorted(p.stem for p in directory.glob("*.json"))
