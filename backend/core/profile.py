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
