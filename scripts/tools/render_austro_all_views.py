import bpy
import os
import shutil
from pathlib import Path

blend_path = r"e:\backup-llm\backup-no-llm\3d_engine\assets\models\engines\austro_ae330.blend"
renders_dir = r"e:\backup-llm\backup-no-llm\3d_engine\assets\renders\engines\austro_ae330"
os.makedirs(renders_dir, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=blend_path)

scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'

try:
    scene.eevee.taa_render_samples = 64
    scene.eevee.use_raytracing = True
except Exception as e:
    print(f"EEVEE settings note: {e}")

cameras = ["Cam_Hero", "Cam_Gearbox", "Cam_Beauty_Orbit", "Cam_Wireframe", "Cam_Turbo", "Cam_Fuel_System"]

for cam_name in cameras:
    cam_obj = bpy.data.objects.get(cam_name)
    if not cam_obj:
        print(f"Warning: Camera {cam_name} not found!")
        continue
    scene.camera = cam_obj
    out_path = os.path.join(renders_dir, f"{cam_name}.png")
    scene.render.filepath = out_path
    print(f"Rendering {cam_name} -> {out_path}...")
    bpy.ops.render.render(write_still=True)

print("ALL RENDERS COMPLETE!")
