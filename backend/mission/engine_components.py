"""Component Hazard Mapping per Engine Architecture (Phase 7).

Generates physical component hazard models conditioned on EngineConfig
(Spark vs Compression Ignition, Turbocharged vs NA, Cylinder Count).
"""

from __future__ import annotations

from typing import List
from backend.mission.reliability import ComponentHazard
from backend.physics.engine_config import EngineConfig


def components_for(cfg: EngineConfig) -> List[ComponentHazard]:
    """Build tailored component reliability hazards for the specified engine."""
    components: List[ComponentHazard] = []

    # 1. Per-cylinder head assemblies
    for i in range(1, cfg.cylinder_count + 1):
        components.append(
            ComponentHazard(f"cylinder_head_{i}", 2.0e-5, damage_exponent=3.5, mission_critical=True)
        )

    # 2. Fuel delivery & Injection
    if cfg.is_compression_ignition:
        components.append(ComponentHazard("common_rail", 2.5e-5, damage_exponent=2.5, mission_critical=True))
        components.append(ComponentHazard("hp_fuel_pump", 3.5e-5, damage_exponent=2.8, mission_critical=True))
        for i in range(1, cfg.cylinder_count + 1):
            components.append(ComponentHazard(f"injector_{i}", 3.2e-5, damage_exponent=2.6, mission_critical=True))
        components.append(ComponentHazard("glow_plugs", 1.5e-5, damage_exponent=1.5, mission_critical=False))
    else:
        components.append(ComponentHazard("fuel_pump", 3.0e-5, damage_exponent=2.2, mission_critical=True))
        for i in range(1, cfg.cylinder_count + 1):
            components.append(ComponentHazard(f"injector_{i}", 2.2e-5, damage_exponent=2.0, mission_critical=True))
            components.append(ComponentHazard(f"ignition_coil_{i}", 2.8e-5, damage_exponent=2.2, mission_critical=True))

    # 3. Turbocharger & Boost Control
    if cfg.is_turbocharged:
        components.append(ComponentHazard("turbocharger", 5.5e-5, damage_exponent=3.0, mission_critical=True))
        components.append(ComponentHazard("wastegate_actuator", 2.0e-5, damage_exponent=2.0, mission_critical=True))
        if cfg.turbo and cfg.turbo.intercooled:
            components.append(ComponentHazard("intercooler", 1.2e-5, damage_exponent=1.8, mission_critical=False))

    # 4. Mechanical Core & Transmission
    components.append(ComponentHazard("oil_pump", 2.2e-5, damage_exponent=2.5, mission_critical=True))
    components.append(ComponentHazard("main_bearings", 1.5e-5, damage_exponent=4.0, mission_critical=True))
    components.append(ComponentHazard("reduction_gearbox", 2.8e-5, damage_exponent=3.5, mission_critical=True))
    components.append(ComponentHazard("water_pump", 2.0e-5, damage_exponent=2.2, mission_critical=True))

    # 5. Electrical & Control
    components.append(ComponentHazard("alternator", 6.0e-5, damage_exponent=1.5, mission_critical=False))
    components.append(ComponentHazard("ecu_lane_a", 4.0e-5, damage_exponent=0.5, mission_critical=False))
    components.append(ComponentHazard("ecu_lane_b", 4.0e-5, damage_exponent=0.5, mission_critical=False))

    return components
