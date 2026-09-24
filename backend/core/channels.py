"""Channel registry (U2): the canonical channel list is DERIVED from the engine profile, never typed as CHT_1..4.

Names follow ``Frame.channels()`` (cht_1.., egt_1.., rpm, oil_p, ...).  Each spec carries unit, kind and a
``required`` flag so a UI or a detector can ask "what does this engine publish?" without engine-specific code."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from backend.physics.engine_config import EngineConfig


@dataclass(frozen=True)
class ChannelSpec:
    name: str
    unit: str
    kind: str           # per_cylinder | thermal | pressure | speed | flow | electrical | command | ambient
    cylinder: int | None = None
    required: bool = True


def channel_specs(cfg: EngineConfig) -> List[ChannelSpec]:
    n = cfg.cylinder_count
    out = [ChannelSpec(f"cht_{i}", "degC", "per_cylinder", i) for i in range(1, n + 1)]
    out += [ChannelSpec(f"egt_{i}", "degC", "per_cylinder", i) for i in range(1, n + 1)]
    out += [ChannelSpec("rpm", "rpm", "speed"), ChannelSpec("map_kpa", "kPa", "pressure"),
            ChannelSpec("oil_p", "bar", "pressure"), ChannelSpec("oil_t", "degC", "thermal"),
            ChannelSpec("fuel_flow", "kg/h", "flow"), ChannelSpec("throttle", "%", "command"),
            ChannelSpec("alt", "ft", "ambient"), ChannelSpec("oat", "degC", "ambient")]
    if cfg.is_compression_ignition:
        out += [ChannelSpec("rail_p", "bar", "pressure", required=False)]
    if cfg.is_turbocharged:
        out += [ChannelSpec("boost_target_kpa", "kPa", "pressure", required=False)]
    return out


def channel_names(cfg: EngineConfig) -> List[str]:
    return [c.name for c in channel_specs(cfg)]
