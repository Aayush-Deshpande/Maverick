"""Render component-level fault stills from the real Blender assembly, driven by the shared component map.

Run headless:
    blender -b assets/blender/rotax_912_is_sport.blend -P scripts/render_component_stills.py -- <out_dir>

Uses the same ghost and fault materials (same values) and the same orbit-camera maths as
apps/blender_twin/standalone_fault_diagnostic_app.py, and the same fault -> component pipeline as the web
twin (frontend/public/twin/component_map.json). So the web twin and Blender show the same components
for the same fault, and these stills are what the landing film puts beside the web render.
"""

import json
import math
import sys
from pathlib import Path

import bpy
import mathutils

ROOT = Path(bpy.data.filepath).resolve().parents[2]
OUT = Path(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else ROOT / "output" / "blender_stills"
OUT.mkdir(parents=True, exist_ok=True)
MAP = json.loads((ROOT / "frontend" / "public" / "twin" / "component_map.json").read_text(encoding="utf-8"))
ENGINE = MAP["engines"]["rotax_912is"]

# Orbit framing, from the diagnostic app: ENGINE_CENTER and FAULT_DATABASE['FAULT_4'] (oil pressure).
SHOTS = {
    "nominal": {"center": (1.932, 61.648, -35.324), "angle": -35.0, "elev": 24.0, "dist": 245.0, "fault": None},
    "oil_pressure_loss": {"center": (-24.76, 105.82, -20.31), "angle": 140.0, "elev": 18.0, "dist": 175.0, "fault": "OIL_PRESSURE_LOSS"},
}


def materials():
    ghost = bpy.data.materials.new("M_GhostVision_XRay")
    ghost.use_nodes = True
    b = ghost.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (0.06, 0.22, 0.38, 1.0)
    b.inputs["Metallic"].default_value = 0.1
    b.inputs["Roughness"].default_value = 0.15
    b.inputs["Alpha"].default_value = 0.22
    for k in ("Transmission Weight", "Transmission"):
        if k in b.inputs:
            b.inputs[k].default_value = 0.8
            break
    if "Emission Color" in b.inputs:
        b.inputs["Emission Color"].default_value = (0.01, 0.08, 0.18, 1.0)
        b.inputs["Emission Strength"].default_value = 0.6
    for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "HASHED")):
        if hasattr(ghost, attr):
            try:
                setattr(ghost, attr, val)
            except Exception:
                pass

    fault = bpy.data.materials.new("M_Fault_RedHighlight")
    fault.use_nodes = True
    f = fault.node_tree.nodes.get("Principled BSDF")
    f.inputs["Base Color"].default_value = (1.0, 0.28, 0.05, 1.0)
    f.inputs["Metallic"].default_value = 0.1
    f.inputs["Roughness"].default_value = 0.1
    if "Emission Color" in f.inputs:
        f.inputs["Emission Color"].default_value = (1.0, 0.28, 0.05, 1.0)
        f.inputs["Emission Strength"].default_value = 4.5
    return ghost, fault


def fault_prefixes(mode):
    stages = ENGINE["faults"][mode]["pipeline"]
    return [p for stage in stages for p in stage]


def apply(mode, ghost, fault, originals):
    prefixes = fault_prefixes(mode) if mode else []
    hits = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        if not mode:
            for i, m in enumerate(originals[obj.name]):
                if i < len(obj.material_slots):
                    obj.material_slots[i].material = m
            continue
        is_target = any(obj.name.startswith(p) for p in prefixes)
        hits += is_target
        mat = fault if is_target else ghost
        if not obj.material_slots:
            obj.data.materials.append(mat)
        for slot in obj.material_slots:
            slot.material = mat
    return hits


def place_camera(shot):
    scene = bpy.context.scene
    cam = scene.camera
    if cam is None:
        cam = bpy.data.objects.new("StillCam", bpy.data.cameras.new("StillCam"))
        scene.collection.objects.link(cam)
        scene.camera = cam
    c = mathutils.Vector(shot["center"])
    a, e, d = math.radians(shot["angle"]), math.radians(shot["elev"]), shot["dist"]
    # identical to the diagnostic app's orbit (Blender is Z-up)
    cam.location = c + mathutils.Vector((d * math.cos(a) * math.cos(e), d * math.sin(a) * math.cos(e), d * math.sin(e)))
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    cam.data.clip_end = 5000


def main():
    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x, scene.render.resolution_y = 1600, 900
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    originals = {o.name: [s.material for s in o.material_slots] for o in bpy.data.objects if o.type == "MESH"}
    ghost, fault = materials()
    report = {}
    for name, shot in SHOTS.items():
        hits = apply(shot["fault"], ghost, fault, originals)
        place_camera(shot)
        scene.render.filepath = str(OUT / f"rotax_912is_{name}.png")
        bpy.ops.render.render(write_still=True)
        report[name] = {"fault": shot["fault"], "highlighted_meshes": hits}
    (OUT / "render_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("RENDER_REPORT", json.dumps(report))


main()
