"""EngineProfile (U1, D27): Unified profile joining physics config, asset manifest,
channels, applicable fault modes, and provenance summary.

Selecting an engine produces an EngineProfile, which drives the entire pipeline,
limits, detectors, and API schema without engine-specific literals anywhere else.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.core.channels import ChannelSpec, channel_specs
from backend.physics.engine_config import EngineConfig, available_engines, load_engine_config

MANIFEST_DIR = Path(__file__).resolve().parents[2] / "assets" / "manifests" / "engines"

# Known aliases between physics config IDs and 3D asset manifests
ASSET_ALIASES = {
    "austro_ae300": "austro_ae330",  # AE330 3D model used as labeled proxy for AE300
}


@dataclass
class EngineProfile:
    config: EngineConfig
    asset_manifest: Optional[Dict[str, Any]] = None
    channels: List[ChannelSpec] = field(default_factory=list)
    fault_modes: List[str] = field(default_factory=list)
    provenance_summary: Dict[str, int] = field(default_factory=dict)

    @property
    def engine_id(self) -> str:
        return self.config.engine_id

    @property
    def display_name(self) -> str:
        return self.config.display_name

    @property
    def n_cyl(self) -> int:
        return self.config.cylinder_count

    @property
    def is_ci(self) -> bool:
        return self.config.is_compression_ignition

    @property
    def is_turbo(self) -> bool:
        return self.config.is_turbocharged

    def get_components(self) -> Dict[str, Any]:
        """Return component list / mesh hierarchy from asset manifest if available."""
        if not self.asset_manifest:
            return {}
        return self.asset_manifest.get("components", {})

    def get_fault_targets(self) -> Dict[str, Any]:
        """Return the per-fault 3D targets (components, camera, cylinder awareness).

        This is the server-side authority for "which meshes does this fault light up".
        An engine with no asset manifest returns {}, and the viewport falls back to a
        position locator rather than highlighting the wrong geometry.
        """
        if not self.asset_manifest:
            return {}
        return self.asset_manifest.get("faults", {})

    @property
    def resolves_cylinders(self) -> bool:
        """Whether this engine's 3D asset separates individual cylinders.

        False means per-cylinder faults can only be shown at subsystem level in 3D, and
        the 2D cylinder instrument has to carry the cylinder identity. Exposed so the UI
        degrades explicitly instead of highlighting a whole bank as if it were one
        cylinder.
        """
        manifest = self.asset_manifest or {}
        if "resolves_cylinders" in manifest:
            return bool(manifest["resolves_cylinders"])
        return any(c.get("cylinder") for c in self.get_components().values())

    def to_schema(self) -> Dict[str, Any]:
        """Generate full API / UI schema dictionary for this engine profile."""
        return {
            "engine_id": self.engine_id,
            "display_name": self.display_name,
            "manufacturer": self.config.manufacturer,
            "platforms": self.config.platforms,
            "class": {
                "ignition": self.config.ignition_mode,
                "induction": self.config.induction,
                "cooling": self.config.cooling,
                "layout": self.config.layout.arrangement,
                "cylinder_count": self.n_cyl,
                "displacement_cc": self.config.layout.displacement_cc,
            },
            "channels": [
                {
                    "name": c.name,
                    "unit": c.unit,
                    "kind": c.kind,
                    "cylinder": c.cylinder,
                    "required": c.required,
                }
                for c in self.channels
            ],
            "operating_limits": self.config.operating_limits,
            "fault_modes": self.fault_modes,
            "components": list(self.get_components().keys()),
            # Full component records, not just their names. The Three.js viewport needs the
            # mesh names to highlight, the telemetry channel that measures each part, and
            # the cylinder it belongs to. Serving that here is what lets the client stop
            # carrying its own hardcoded mesh table and name-matched thermal guesses.
            "component_map": self.get_components(),
            "fault_targets": self.get_fault_targets(),
            "resolves_cylinders": self.resolves_cylinders,
            "thermal_coverage": (self.asset_manifest or {}).get("thermal_coverage", {}),
            "prop_reduction": (self.asset_manifest or {}).get("prop_reduction"),
            "provenance_summary": self.provenance_summary,
            "tbo_hours": self.config.tbo_hours,
            "rated_power_kw": self.config.rated_power_kw,
            "rated_rpm": self.config.rated_rpm,
        }


def _compute_provenance_summary(cfg: EngineConfig) -> Dict[str, int]:
    counts: Dict[str, int] = {"PUBLIC": 0, "MANUAL": 0, "ASSUMED": 0, "PLACEHOLDER": 0, "UNVERIFIED": 0}
    for entry in cfg.provenance.values():
        status = entry.get("status", "UNVERIFIED")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _load_asset_manifest(engine_id: str, manifest_dir: Path | None = None) -> Optional[Dict[str, Any]]:
    directory = manifest_dir or MANIFEST_DIR
    target_id = ASSET_ALIASES.get(engine_id, engine_id)
    manifest_path = directory / f"{target_id}.json"
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def load_profile(engine_id: str, config_dir: Path | str | None = None, manifest_dir: Path | None = None) -> EngineProfile:
    """Load an EngineProfile by engine_id, assembling config, channels, faults, manifest, provenance."""
    cfg = load_engine_config(engine_id, config_dir=config_dir)
    manifest = _load_asset_manifest(engine_id, manifest_dir=manifest_dir)
    chans = channel_specs(cfg)
    faults = cfg.applicable_fault_modes()
    prov_summary = _compute_provenance_summary(cfg)

    return EngineProfile(
        config=cfg,
        asset_manifest=manifest,
        channels=chans,
        fault_modes=faults,
        provenance_summary=prov_summary,
    )


def load_all_profiles(config_dir: Path | str | None = None, manifest_dir: Path | None = None) -> Dict[str, EngineProfile]:
    """Load all available engine profiles."""
    engine_ids = available_engines(config_dir)
    return {eid: load_profile(eid, config_dir=config_dir, manifest_dir=manifest_dir) for eid in engine_ids}
