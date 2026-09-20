"""
ANUMAAN - Master Acceptance Renderer
Renders full acceptance set per Section 15.3 and writes render_manifest.json
"""

import bpy
import json
import sys
import os
import math
from pathlib import Path
import mathutils

def render_acceptance_set(blend_path, manifest_path):
    blend_p = Path(blend_path).resolve()
    manifest_p = Path(manifest_path).resolve()
    ROOT = Path(__file__).resolve().parents[2]

    with open(manifest_p, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    is_engine = "engine_id" in manifest
    asset_id = manifest.get("engine_id") or manifest.get("platform_id")
    out_dir = ROOT / "renders" / asset_id / "acceptance"
    out_dir.mkdir(parents=True, exist_ok=True)

    scene = bpy.context.scene

    # Render settings: EEVEE for high performance, standard resolution
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'

    render_manifest = []

    def reset_all_twin():
        for o in bpy.data.objects:
            if o.type == 'MESH':
                o["twin_ghost"] = 0.0
                o["twin_fault_level"] = 0.0
                o["twin_fault_rgb"] = (0.0, 0.0, 0.0)
                o["twin_sensor_suspect"] = 0.0
                o.update_tag()
        bpy.context.view_layer.update()

    def do_render(filename, camera_name=None, transparent=False):
        if camera_name and camera_name in bpy.data.objects:
            scene.camera = bpy.data.objects[camera_name]
        scene.render.film_transparent = transparent
        out_path = out_dir / filename
        scene.render.filepath = str(out_path)
        bpy.ops.render.render(write_still=True)
        print(f"Rendered: {filename}")
        render_manifest.append({
            "filename": filename,
            "camera": scene.camera.name if scene.camera else "None",
            "film_transparent": transparent
        })

    # Reset all twin properties to nominal
    reset_all_twin()

    # 1. Hero Front Left
    do_render("01_hero_front_left.png", "Cam_Hero")

    # 2. Rear Right
    if "Cam_Beauty_Orbit" in bpy.data.objects:
        do_render("02_rear_right.png", "Cam_Beauty_Orbit")

    # 3. Subsystem Closeups
    if "Cam_Turbo" in bpy.data.objects:
        do_render("03_closeup_turbo.png", "Cam_Turbo")
    if "Cam_Fuel_System" in bpy.data.objects:
        do_render("04_closeup_fuel_system.png", "Cam_Fuel_System")
    if "Cam_Gearbox" in bpy.data.objects:
        do_render("05_closeup_gearbox.png", "Cam_Gearbox")

    # 4. Wireframe Clay
    if "Cam_Wireframe" in bpy.data.objects:
        do_render("06_wireframe_clay.png", "Cam_Wireframe")

    # 5. Fault State Renderings (for each manifest fault)
    fault_colors = {
        "MINOR": (1.0, 0.85, 0.0),
        "MAJOR": (1.0, 0.45, 0.0),
        "CRITICAL": (1.0, 0.05, 0.02)
    }

    if "faults" in manifest:
        raw_faults = manifest["faults"]
        if isinstance(raw_faults, dict):
            fault_list = [{"key": k, **v} for k, v in raw_faults.items()]
        else:
            fault_list = raw_faults
        for fidx, fault in enumerate(fault_list[:4]): # Render key faults
            fkey = fault.get("key", f"fault_{fidx}")
            aff = fault.get("affected_components", [])
            comp_key = aff[0] if aff else fault.get("component")
            sev = fault.get("severity", "MAJOR")
            rgb = fault.get("color") or fault_colors.get(sev, (1.0, 0.45, 0.0))

            # Set ghost on everything
            for o in bpy.data.objects:
                if o.type == 'MESH':
                    o["twin_ghost"] = 0.85
                    o["twin_fault_level"] = 0.0
                    o["twin_fault_rgb"] = (0.0, 0.0, 0.0)

            # Highlight target component
            if comp_key in manifest.get("components", {}):
                t_objs = manifest["components"][comp_key].get("objects", [])
                for oname in t_objs:
                    if oname in bpy.data.objects:
                        o = bpy.data.objects[oname]
                        o["twin_ghost"] = 0.0
                        o["twin_fault_level"] = 1.0
                        o["twin_fault_rgb"] = rgb
                        o.update_tag()

            bpy.context.view_layer.update()
            do_render(f"07_fault_{fkey.lower()}.png", "Cam_Hero")

    # 6. Sensor Suspect Example
    reset_all_twin()
    if "sensors" in manifest and manifest["sensors"]:
        first_sensor_key = list(manifest["sensors"].keys())[0]
        s_objs = manifest["sensors"][first_sensor_key].get("objects", [])
        for oname in s_objs:
            if oname in bpy.data.objects:
                bpy.data.objects[oname]["twin_sensor_suspect"] = 1.0
                bpy.data.objects[oname].update_tag()
        bpy.context.view_layer.update()
        do_render(f"08_sensor_suspect_{first_sensor_key.lower()}.png", "Cam_Hero")

    # Reset all twin properties back to nominal
    reset_all_twin()

    # Save manifest of renders
    manifest_out = out_dir / "render_manifest.json"
    with open(manifest_out, "w", encoding="utf-8") as f:
        json.dump(render_manifest, f, indent=2)

    print(f"Acceptance render suite complete! Saved to {out_dir}")

if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    b_path = args[0] if len(args) > 0 else ""
    m_path = args[1] if len(args) > 1 else ""
    if b_path and m_path:
        render_acceptance_set(b_path, m_path)
    else:
        print("Usage: render_acceptance.py <blend> <manifest>")
        sys.exit(1)
