"""Fault registry (R2, D30): which plant faults an engine profile accepts, and which of them the scalar
channels can actually see.  Faults are filtered per profile from the engine config, never hard-coded per engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

from backend.physics.engine_config import EngineConfig
from backend.plant.virtual_engine import PLANT_FAULTS


@dataclass(frozen=True)
class FaultSpec:
    mode: str
    applies_to: Callable[[EngineConfig], bool]
    per_cylinder: bool
    scalar_visible: bool          # False = probed to change no thermal/pressure scalar (F22): waveform-only
    layer: str = "L2"             # D30 layering: L1 lever, L2 physical fault, L3 sensor fault
    description: str = ""


def _all(_c): return True
def _turbo(c): return c.is_turbocharged
def _ci(c): return c.is_compression_ignition


_SPECS = [
    FaultSpec("MISFIRE", _all, True, True, "L2", "Cylinder stops firing"),
    FaultSpec("COOLING_DEGRADATION", _all, False, True, "L2", "Reduced heat rejection"),
    FaultSpec("OIL_PRESSURE_LOSS", _all, False, True, "L2", "Oil pump / leak"),
    FaultSpec("AIR_FILTER_BLOCKAGE", _all, False, True, "L2", "Induction restriction"),
    FaultSpec("BOOST_LEAK", _turbo, False, True, "L2", "Charge-air leak"),
    FaultSpec("WASTEGATE_STUCK_OPEN", _turbo, False, True, "L2", "Wastegate stuck open"),
    FaultSpec("TURBO_BEARING_WEAR", _turbo, False, False, "L2", "Turbo bearing wear (waveform-only)"),
    FaultSpec("INJECTOR_COKING", _ci, True, False, "L2", "Injector coking (waveform-only)"),
    FaultSpec("INJECTOR_NEEDLE_STICK", _ci, True, False, "L2", "Needle sticking (waveform-only)"),
    FaultSpec("RAIL_PRESSURE_DECAY", _ci, False, False, "L2", "Rail pressure decay (waveform-only)"),
    FaultSpec("SENSOR_STUCK", _all, True, True, "L3", "Sensor frozen"),
    FaultSpec("SENSOR_BIAS_DRIFT", _all, True, True, "L3", "Sensor bias drift"),
]
FAULT_REGISTRY: Dict[str, FaultSpec] = {s.mode: s for s in _SPECS}
assert set(FAULT_REGISTRY) == set(PLANT_FAULTS), "registry must cover exactly the plant fault library"


def faults_for(cfg: EngineConfig) -> List[FaultSpec]:
    return [s for s in _SPECS if s.applies_to(cfg)]


def thermal_visible_faults(cfg: EngineConfig) -> List[str]:
    return [s.mode for s in faults_for(cfg) if s.scalar_visible and s.layer == "L2"]
