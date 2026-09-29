"""Generate asset manifests for the three Rotax engines from their shipped GLB geometry.

Why this exists
---------------
`EngineProfile.get_components()` reads `assets/manifests/engines/<id>.json`. Only the
Austro and TEI engines had a manifest, so `GET /api/engines/{id}/schema` returned
`"components": []` for every Rotax engine. That empty list is the reason the Three.js
twin carried its own hardcoded `ENGINE_FAULT_TARGETS` table and a name-matched thermal
lookup: there was no server-side authority for mesh names, so the client invented one.

This script builds that authority from the only source that cannot drift -- the GLB node
table itself -- and folds in the mesh groupings the twin had hardcoded. Running it is
idempotent; the manifests it writes are committed artefacts.

    python scripts/generate_rotax_manifests.py

Scope: rotax_912is, rotax_914, rotax_915is. The Austro AE300 and VRDE Jayem manifests are
left alone (AE330 already has a hand-authored one) because their 3D assets are not part of
the Rotax-focused UI.

Thermal mapping honesty
-----------------------
`thermal_channel` is only set where a real telemetry channel actually measures that part.
Everything else gets `null`, and the viewport renders those meshes neutral grey as
"unmonitored". That absence is information: it shows the sensor coverage of the engine
rather than interpolating a plausible-looking temperature across the whole model.
"""

from __future__ import annotations

import json
import re
import struct
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
GLB_DIR = ROOT / "apps" / "threejs_twin" / "assets" / "models" / "draco"
OUT_DIR = ROOT / "assets" / "manifests" / "engines"

ENGINES = ("rotax_912is", "rotax_914", "rotax_915is")

DISPLAY_NAMES = {
    "rotax_912is": "Rotax 912 iS Sport",
    "rotax_914": "Rotax 914 UL",
    "rotax_915is": "Rotax 915 iS",
}

# Reduction ratio engine:prop, used by the viewport to turn crank RPM into prop RPM.
PROP_REDUCTION = {"rotax_912is": 2.43, "rotax_914": 2.43, "rotax_915is": 2.43}


# ---------------------------------------------------------------------------
# GLB parsing
# ---------------------------------------------------------------------------
def glb_node_names(path: Path) -> List[str]:
    """Return every node name in a .glb's JSON chunk, in file order."""
    raw = path.read_bytes()
    if raw[:4] != b"glTF":
        raise ValueError(f"{path.name} is not a binary glTF")
    json_len = struct.unpack("<I", raw[12:16])[0]
    doc = json.loads(raw[20 : 20 + json_len].decode("utf-8"))
    return [n.get("name", "") for n in doc.get("nodes", []) if n.get("name")]


def group_of(name: str) -> str:
    """Collapse a mesh name to its logical component.

    Blender's glTF exporter splits one object into one mesh per material and suffixes
    `_M_<Material>_<n>`, so `Oil_Tank_M_Steel_0` and `Oil_Tank_M_Labels_0` are the same
    physical part. A trailing `_<digits>` (Blender's duplicate suffix) collapses too,
    except where the digit is a cylinder index -- see cylinder_of().
    """
    m = re.match(r"^(.*?)_M_[A-Za-z0-9]+_\d+(?:\.\d+)?$", name)
    if m:
        return m.group(1)
    m = re.match(r"^(.*?)_\d+(?:\.\d+)?$", name)
    if m:
        return m.group(1)
    return name.split(".")[0]


def cylinder_of(engine_id: str, name: str) -> Optional[int]:
    """Resolve a mesh to a 1-based cylinder index, or None.

    Only rotax_914 separates cylinders, and its heads are named `Cylinder_Head_2`
    through `Cylinder_Head_5` -- a 2..5 range for a 4-cylinder engine. That off-by-one
    is a property of the asset, so the offset is applied here once rather than being
    rediscovered by every consumer.
    """
    if engine_id != "rotax_914":
        return None
    m = re.match(r"^Rotax914_Cylinder_Head_(\d+)$", name)
    if not m:
        return None
    idx = int(m.group(1)) - 1  # heads 2..5 -> cylinders 1..4
    return idx if 1 <= idx <= 4 else None


# ---------------------------------------------------------------------------
# Subsystem + thermal classification
# ---------------------------------------------------------------------------
# Ordered: first match wins. (regex, subsystem, thermal_channel)
# thermal_channel of None means "no sensor measures this part".
CLASSIFY: Tuple[Tuple[str, str, Optional[str]], ...] = (
    # --- exhaust / turbo path: hottest, measured by EGT
    (r"exhaust|turbine|downpipe|collector|muffler", "Exhaust", "egt_max"),
    (r"turbo|wastegate|overboost|magnetovalve", "Turbocharger", "egt_max"),
    # --- combustion core: measured by CHT
    (r"cylinder_head", "Block_Cylinders", "cht_indexed"),
    (r"cylinder_bank|crankcase|rocker_cover|912i_base|^main engine$", "Block_Cylinders", "cht_max"),
    # --- lubrication: measured by oil temperature
    (r"oil_tank|^oil tank$|oil_sump|oil_cooler|oil_filter", "Lubrication", "oil_t"),
    # --- charge air / cooling air: intake air approximates OAT
    (r"intercooler|intake_manifold|air_baffle|^air baffles$|cooling_air", "Intake_Charge_Air", "oat"),
    # --- fuel: measured by fuel temperature
    (r"fuel_pump|fuel_filter|common_rail|injector", "Fuel_System", "fuel_t"),
    # --- coolant circuit: 912/914 report no coolant-temperature channel, so honestly unmonitored
    (r"water_hose|coolant|thermostat|water_pump|radiator", "Cooling", None),
    # --- drivetrain
    (r"gearbox|tranny|prop_flange|prop_shaft|flywheel|starter_ring", "Gearbox_Prop_Drive", None),
    # --- electrical / control
    (r"^ecu|fusebox|wiring_harness|starter|relay|alternator|generator|connector|harness", "Electrical_Control", None),
    # --- structure / hardware / cosmetic
    (r"suspension|mount|lift_eye", "Structure", None),
    (r"fitting|fastener|bolt|nut|clamp|washer|dowel|retainer", "Hardware", None),
    (r"cover|cert|label|plate|theme|seal|blanket|sticker", "Cosmetic", None),
    (r"vacuum_pump|belt|sensor|dipstick|breather|sight_glass|governor", "Accessories", None),
)


def classify(group: str) -> Tuple[str, Optional[str]]:
    low = group.lower()
    for pattern, subsystem, channel in CLASSIFY:
        if re.search(pattern, low):
            return subsystem, channel
    return "Unclassified", None


def resolve_thermal(spec: Optional[str], cylinder: Optional[int]) -> Optional[str]:
    """Turn a classification token into a concrete channel reference.

    `cht_indexed` becomes `cht_<n>` where the asset resolves a cylinder, and falls back to
    the bank maximum where it does not -- so a model without per-cylinder geometry says
    "hottest cylinder" instead of pretending to know which one.
    """
    if spec is None:
        return None
    if spec == "cht_indexed":
        return f"cht_{cylinder}" if cylinder else "cht_max"
    return spec


# ---------------------------------------------------------------------------
# Fault -> component targets
# ---------------------------------------------------------------------------
# Migrated out of apps/threejs_twin/index.html (ENGINE_FAULT_TARGETS), keyed by the fault
# modes the runtime profile actually exposes (GET /api/engines -> faults[].mode). The
# descriptions keep the original honesty about what the geometry can and cannot resolve.
FAULT_TARGETS: Dict[str, Dict[str, dict]] = {
    "rotax_912is": {
        "MISFIRE": {
            "components": ["Wiring_Harness"],
            "camera": {"azimuth_deg": -115, "elevation_deg": 30},
            "description": "Ignition harness meshes are highlighted. The harness is shared across cylinders in this asset, so no cylinder-specific lead is claimed.",
        },
        "COOLING_DEGRADATION": {
            "components": ["Cooling_Air_Baffle", "Water_Hoses"],
            "camera": {"azimuth_deg": -140, "elevation_deg": 24},
            "description": "Cooling baffle and coolant hoses are highlighted while the plant models reduced heat rejection.",
        },
        "OIL_PRESSURE_LOSS": {
            "components": ["Oil_Tank"],
            "camera": {"azimuth_deg": 135, "elevation_deg": 18},
            "description": "Oil reservoir meshes are highlighted; the scavenge pump and lines are not separately named in this asset.",
        },
        "AIR_FILTER_BLOCKAGE": {
            "components": ["Cooling_Air_Baffle"],
            "camera": {"azimuth_deg": 75, "elevation_deg": 24},
            "description": "The intake filter is not a separate mesh in this asset; the intake-air baffle is highlighted as airflow-system context.",
        },
        "SENSOR_STUCK": {
            "components": ["ECU"],
            "camera": {"azimuth_deg": 45, "elevation_deg": 24},
            "description": "A temperature channel is frozen while the plant continues to evolve. The ECU enclosure stands in for the affected sensor lane, which this asset does not separate.",
        },
        "SENSOR_BIAS_DRIFT": {
            "components": ["ECU"],
            "camera": {"azimuth_deg": 45, "elevation_deg": 24},
            "description": "A temperature channel drifts away from its true plant value. The ECU enclosure stands in for the affected sensor lane.",
        },
    },
    "rotax_914": {
        "MISFIRE": {
            "components": ["Rotax914_Cylinder_Head", "Rotax914_Cylinder_Bank"],
            "camera": {"azimuth_deg": -45, "elevation_deg": 18},
            "description": "Combustion imbalance detected. This asset resolves individual cylinder heads, so the affected cylinder is highlighted directly.",
            "per_cylinder": True,
        },
        "COOLING_DEGRADATION": {
            "components": ["Rotax914_Cylinder_Head", "Rotax914_Coolant_Line"],
            "camera": {"azimuth_deg": -25, "elevation_deg": 24},
            "description": "Cylinder heads and coolant circuit are highlighted while the plant models reduced heat rejection.",
        },
        "OIL_PRESSURE_LOSS": {
            "components": ["Rotax914_Crankcase_Block"],
            "camera": {"azimuth_deg": 135, "elevation_deg": 20},
            "description": "The engine case is shown as system context; this asset does not expose a separately named oil pump.",
        },
        "AIR_FILTER_BLOCKAGE": {
            "components": ["Rotax914_Intake_Manifold"],
            "camera": {"azimuth_deg": 90, "elevation_deg": 24},
            "description": "The air filter is not separated in this asset; the induction manifold is highlighted as airflow-system context.",
        },
        "BOOST_LEAK": {
            "components": ["Rotax914_Turbo_Compressor", "Rotax914_Intake_Manifold"],
            "camera": {"azimuth_deg": 90, "elevation_deg": 22},
            "description": "Charge-air pressure loss is active; the turbo compressor and intake path are highlighted.",
        },
        "WASTEGATE_STUCK_OPEN": {
            "components": ["Rotax914_Turbo_Wastegate"],
            "camera": {"azimuth_deg": 180, "elevation_deg": 16},
            "description": "Boost control is outside its expected range. The wastegate assembly is highlighted for inspection.",
        },
        "TURBO_BEARING_WEAR": {
            "components": ["Rotax914_Turbo_Compressor", "Rotax914_Turbo_Turbine_Exhaust"],
            "camera": {"azimuth_deg": 180, "elevation_deg": 18},
            "description": "A waveform-only fault modelled by the plant; the turbo rotating assembly is highlighted for visual context.",
        },
        "SENSOR_STUCK": {
            "components": ["Rotax914_Cylinder_Head"],
            "camera": {"azimuth_deg": -45, "elevation_deg": 18},
            "description": "A cylinder-head temperature sensor is frozen while plant temperature continues to evolve.",
            "per_cylinder": True,
        },
        "SENSOR_BIAS_DRIFT": {
            "components": ["Rotax914_Cylinder_Head"],
            "camera": {"azimuth_deg": -45, "elevation_deg": 18},
            "description": "A cylinder-head temperature channel drifts away from its true plant value.",
            "per_cylinder": True,
        },
    },
    "rotax_915is": {
        "MISFIRE": {
            "components": ["Main engine"],
            "camera": {"azimuth_deg": -45, "elevation_deg": 18},
            "description": "Combustion imbalance detected. This asset does not separate cylinders, so the engine core is highlighted and the cylinder identity is carried by the 2D cylinder instrument.",
        },
        "COOLING_DEGRADATION": {
            "components": ["Air baffles", "Main engine"],
            "camera": {"azimuth_deg": -35, "elevation_deg": 23},
            "description": "The engine and its cooling baffles are highlighted while the plant models reduced heat rejection.",
        },
        "OIL_PRESSURE_LOSS": {
            "components": ["Oil tank"],
            "camera": {"azimuth_deg": 130, "elevation_deg": 22},
            "description": "Oil pressure loss is active in the physics plant; the reservoir is highlighted as system context.",
        },
        "AIR_FILTER_BLOCKAGE": {
            "components": ["Air baffles"],
            "camera": {"azimuth_deg": 75, "elevation_deg": 24},
            "description": "The intake filter is not separately named in this asset; the intake-air baffles are highlighted as context.",
        },
        "BOOST_LEAK": {
            "components": ["Intercooler"],
            "camera": {"azimuth_deg": 90, "elevation_deg": 22},
            "description": "Charge-air pressure loss is active; the intercooler and charge-air path are highlighted.",
        },
        "WASTEGATE_STUCK_OPEN": {
            "components": ["Overboost valve", "Magnetovalve"],
            "camera": {"azimuth_deg": 180, "elevation_deg": 18},
            "description": "Boost control is outside its expected range. The overboost and control valves are highlighted.",
        },
        "TURBO_BEARING_WEAR": {
            "components": ["Main engine"],
            "camera": {"azimuth_deg": 180, "elevation_deg": 18},
            "description": "Turbo internals are not separated in this asset; the engine assembly is highlighted as visual context.",
        },
        "SENSOR_STUCK": {
            "components": ["ECU"],
            "camera": {"azimuth_deg": 45, "elevation_deg": 22},
            "description": "A temperature channel is frozen while the plant continues to evolve. The ECU stands in for the affected sensor lane.",
        },
        "SENSOR_BIAS_DRIFT": {
            "components": ["ECU"],
            "camera": {"azimuth_deg": 45, "elevation_deg": 22},
            "description": "A temperature channel drifts away from its true plant value. The ECU stands in for the affected sensor lane.",
        },
    },
}

# Meshes whose rotation should track prop RPM (the twin matched on 'prop'/'flange').
PROP_PATTERN = r"prop|flange"


def build(engine_id: str) -> dict:
    glb = GLB_DIR / f"{engine_id}.glb"
    names = glb_node_names(glb)

    components: "OrderedDict[str, dict]" = OrderedDict()
    for name in names:
        group = group_of(name)
        cyl = cylinder_of(engine_id, name)
        # A per-cylinder mesh gets its own component so it can be highlighted alone.
        key = f"{group}_Cyl{cyl}" if cyl else group
        entry = components.get(key)
        if entry is None:
            subsystem, spec = classify(group)
            entry = {
                "subsystem": subsystem,
                "objects": [],
                "thermal_channel": resolve_thermal(spec, cyl),
                "cylinder": cyl,
                "prop_driven": bool(re.search(PROP_PATTERN, group.lower())),
            }
            components[key] = entry
        entry["objects"].append(name)

    # Component names are the authority the viewport highlights against; sort for a
    # stable diff between regenerations.
    components = OrderedDict(sorted(components.items()))

    faults = {}
    for mode, spec in FAULT_TARGETS.get(engine_id, {}).items():
        resolved, missing = [], []
        for wanted in spec["components"]:
            hits = [k for k in components if k == wanted or k.startswith(wanted)]
            (resolved.extend(hits) if hits else missing.append(wanted))
        faults[mode] = {
            "description": spec["description"],
            "affected_components": sorted(set(resolved)),
            "camera": spec["camera"],
            "per_cylinder": bool(spec.get("per_cylinder")),
            # Recorded rather than dropped: a target that no longer resolves is a real
            # asset regression, and the contract test in tests/ asserts this stays empty.
            "unresolved_components": missing,
        }

    monitored = sum(1 for c in components.values() if c["thermal_channel"])
    return {
        "engine_id": engine_id,
        "display_name": DISPLAY_NAMES[engine_id],
        "manifest_version": 2,
        "generated_by": "scripts/generate_rotax_manifests.py",
        "glb": f"apps/threejs_twin/assets/models/draco/{engine_id}.glb",
        "prop_reduction": PROP_REDUCTION[engine_id],
        "node_count": len(names),
        "resolves_cylinders": any(c["cylinder"] for c in components.values()),
        "thermal_coverage": {
            "monitored_components": monitored,
            "total_components": len(components),
        },
        "components": components,
        "faults": faults,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for engine_id in ENGINES:
        manifest = build(engine_id)
        out = OUT_DIR / f"{engine_id}.json"
        out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        cov = manifest["thermal_coverage"]
        unresolved = sum(len(f["unresolved_components"]) for f in manifest["faults"].values())
        print(
            f"{engine_id}: {manifest['node_count']} nodes -> "
            f"{cov['total_components']} components "
            f"({cov['monitored_components']} thermally monitored), "
            f"{len(manifest['faults'])} faults, "
            f"cylinders={'yes' if manifest['resolves_cylinders'] else 'no'}, "
            f"unresolved={unresolved}"
        )


if __name__ == "__main__":
    main()
