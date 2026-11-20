"""Fault registry loader (card M0-02; DECISIONS D5, D7, D9).

configs/faults.json is the single source of truth for every fault id (F01-F37, S01-S07): which engines it applies
to, which model parameters it changes, the signature it must produce, the status it implies, and the maintenance /
mitigation text. Nothing else in the code may hold a fault list.

The loader validates the file against configs/schema/faults.schema.json and raises FaultRegistryError on any
problem: the server must refuse to start with a broken registry (T-CFG-1). Applicability is evaluated from the
engine config's hardware fields; an inapplicable or unknown fault raises FaultRejected with a reason, it is never
silently ignored.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import jsonschema

from backend.physics.engine_config import EngineConfig

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "configs" / "faults.json"
SCHEMA_PATH = ROOT / "configs" / "schema" / "faults.schema.json"


class FaultRegistryError(ValueError):
    """configs/faults.json is missing, invalid or inconsistent."""


class FaultRejected(ValueError):
    """A fault request that cannot be applied (unknown id, not applicable, bad cylinder/channel/severity)."""


def _config_value(cfg: EngineConfig, dotted: str) -> Any:
    obj: Any = cfg
    for part in dotted.split("."):
        if obj is None:
            return None
        obj = obj.get(part) if isinstance(obj, dict) else getattr(obj, part, None)
    return obj


@dataclass(frozen=True)
class FaultSpec:
    """Read-only view of one registry entry."""

    raw: Dict[str, Any]

    @property
    def id(self) -> str:
        return self.raw["id"]

    @property
    def name(self) -> str:
        return self.raw["name"]

    @property
    def kind(self) -> str:
        return self.raw["kind"]

    @property
    def scope(self) -> str:
        return self.raw["scope"]

    def applicability(self, cfg: EngineConfig) -> Tuple[bool, str]:
        """(applies, reason). The reason names the first failing condition."""
        for cond in self.raw["applies_when"]:
            value = _config_value(cfg, cond["field"])
            if value not in cond["in"]:
                return False, (f"{self.id} {self.name} needs {cond['field']} in {cond['in']}, "
                               f"but {cfg.engine_id} has {value!r}")
        return True, "applies"

    def signature_items(self, cfg: Optional[EngineConfig] = None) -> List[Dict[str, Any]]:
        """Expected-signature lines that hold for this engine: a line with its own applies_when (e.g. "rpm falls" only
        without a propeller governor, which would hold rpm) is dropped where the installation masks it (D59)."""
        items = self.raw["expected_signature"]
        if cfg is None:
            return list(items)
        return [i for i in items if all(_config_value(cfg, c["field"]) in c["in"] for c in i.get("applies_when", []))]

    def resolved_signature(self, cylinder: Optional[int] = None, channel: Optional[str] = None,
                           n_cylinders: int = 4, cfg: Optional[EngineConfig] = None) -> List[Dict[str, Any]]:
        """Expected signature with {cyl}, [*] and {channel} expanded to concrete channel names."""
        out: List[Dict[str, Any]] = []
        for item in self.signature_items(cfg):
            ch = item["channel"]
            if "{channel}" in ch:
                if channel is None:
                    raise FaultRejected(f"{self.id} needs a channel")
                ch = ch.replace("{channel}", channel)
            if "{cyl}" in ch:
                if cylinder is None:
                    raise FaultRejected(f"{self.id} needs a cylinder")
                ch = ch.replace("{cyl}", str(cylinder))
            if "[*]" in ch:
                for c in range(1, n_cylinders + 1):
                    out.append({**item, "channel": ch.replace("[*]", f"[{c}]")})
                continue
            out.append({**item, "channel": ch})
        return out


class FaultRegistry:
    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self._by_id: Dict[str, FaultSpec] = {}
        self._by_legacy: Dict[int, FaultSpec] = {}
        for entry in data["faults"]:
            spec = FaultSpec(entry)
            if spec.id in self._by_id:
                raise FaultRegistryError(f"duplicate fault id {spec.id}")
            self._by_id[spec.id] = spec
            for legacy in entry.get("legacy_ids", []):
                if legacy in self._by_legacy:
                    raise FaultRegistryError(f"legacy id {legacy} used by {self._by_legacy[legacy].id} and {spec.id}")
                self._by_legacy[legacy] = spec
            if spec.scope == "CYLINDER" and not any("{cyl}" in json.dumps(e) for e in
                                                    entry["parameter_effects"] + entry["expected_signature"]):
                raise FaultRegistryError(f"{spec.id} is per-cylinder but never uses {{cyl}}")
            if spec.kind == "SENSOR" and spec.scope != "CHANNEL":
                raise FaultRegistryError(f"{spec.id} is a sensor fault and must have scope CHANNEL")

    # -- lookups ------------------------------------------------------------------------------------------------

    def all(self) -> List[FaultSpec]:
        return list(self._by_id.values())

    def ids(self) -> List[str]:
        return list(self._by_id)

    def get(self, fault_id: str) -> FaultSpec:
        try:
            return self._by_id[fault_id]
        except KeyError:
            raise FaultRejected(f"unknown fault id {fault_id!r}; known ids: {', '.join(self._by_id)}") from None

    def by_legacy_id(self, legacy_id: int) -> FaultSpec:
        """Old numeric DRDO ids 1-8 map ONLY through legacy_ids (never by list position; audit #18)."""
        try:
            return self._by_legacy[int(legacy_id)]
        except (KeyError, ValueError):
            raise FaultRejected(f"legacy fault id {legacy_id!r} is not mapped in configs/faults.json") from None

    def applicable(self, cfg: EngineConfig) -> List[FaultSpec]:
        return [f for f in self._by_id.values() if f.applicability(cfg)[0]]

    def as_dict(self) -> Dict[str, Any]:
        return copy.deepcopy(self._data)

    # -- request validation -------------------------------------------------------------------------------------

    def validate_request(self, cfg: EngineConfig, fault_id: str, cylinder: Optional[int] = None,
                         channel: Optional[str] = None, severity: Optional[float] = None,
                         ramp_s: Optional[float] = None) -> FaultSpec:
        """Return the spec if the request is valid for this engine, else raise FaultRejected with the reason."""
        spec = self.get(fault_id)
        ok, reason = spec.applicability(cfg)
        if not ok:
            raise FaultRejected(reason)
        if spec.scope == "CYLINDER":
            if cylinder is None or not (1 <= int(cylinder) <= cfg.cylinder_count):
                raise FaultRejected(f"{spec.id} needs a cylinder 1..{cfg.cylinder_count}, got {cylinder!r}")
        elif cylinder is not None and spec.scope == "ENGINE":
            raise FaultRejected(f"{spec.id} is an engine-level fault; do not pass a cylinder")
        if spec.scope == "CHANNEL" and not channel:
            raise FaultRejected(f"{spec.id} is a sensor fault and needs a channel")
        if severity is not None and not (0.0 <= float(severity) <= 1.0):
            raise FaultRejected(f"severity must be within 0..1, got {severity!r}")
        if ramp_s is not None and float(ramp_s) < 0.0:
            raise FaultRejected(f"ramp_s must be >= 0, got {ramp_s!r}")
        return spec


def load_fault_registry(path: Path | str | None = None, schema_path: Path | str | None = None) -> FaultRegistry:
    """Load and validate the registry. Raises FaultRegistryError on any problem (the server must not start)."""
    path = Path(path) if path else REGISTRY_PATH
    schema_path = Path(schema_path) if schema_path else SCHEMA_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FaultRegistryError(f"fault registry not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise FaultRegistryError(f"fault registry is not valid JSON: {path}: {exc}") from None
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        where = "/".join(str(p) for p in exc.absolute_path)
        raise FaultRegistryError(f"fault registry invalid at {where or '<root>'}: {exc.message}") from None
    return FaultRegistry(data)
