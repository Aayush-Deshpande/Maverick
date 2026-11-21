"""
Render Before vs After comparison frames for all 5 engines.
Outputs high-res side-by-side composite images for user inspection.
"""
import os
import sys
import bpy
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

ENGINES = ["austro_ae300", "vrde_jayem_2_2l", "rotax_915is", "rotax_914", "rotax_912is"]

def setup_camera_and_lighting(scene, center, diag):
    # Remove existing cameras and lights
    for o in list(scene.objects):
        if o.type in ('CAMERA', 'LIGHT'):
            bpy.data.objects.remove(o, do_unlink=True)
            
    # Create Camera
    cam_data = bpy.data.cameras.new("CompCam")
    cam_data.lens = 45.0
    cam_obj = bpy.data.objects.new("CompCam", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    
    # 3/4 front-top viewpoint
    view_offset = Vector((1.2, -1.6, 0.9)).normalized() * (diag * 1.5)
    cam_obj.location = center + view_offset
    direction = center - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()
    
    # Neutral Studio Lighting
    # Key light
    key_data = bpy.data.lights.new("KeyLight", type='SUN')
    key_data.energy = 3.5
    key_data.color = (1.0, 0.98, 0.95)
    key_obj = bpy.data.objects.new("KeyLight", key_data)
    scene.collection.objects.link(key_obj)
    key_dir = Vector((-1.0, 1.0, -1.5)).normalized()
    key_obj.rotation_euler = key_dir.to_track_quat('-Z', 'Y').to_euler()
    
    # Fill light
    fill_data = bpy.data.lights.new("FillLight", type='SUN')
    fill_data.energy = 1.5
    fill_data.color = (0.92, 0.95, 1.0)
    fill_obj = bpy.data.objects.new("FillLight", fill_data)
    scene.collection.objects.link(fill_obj)
    fill_dir = Vector((1.0, -0.5, -0.8)).normalized()
    fill_obj.rotation_euler = fill_dir.to_track_quat('-Z', 'Y').to_euler()
    
    # Rim light
    rim_data = bpy.data.lights.new("RimLight", type='SUN')
    rim_data.energy = 2.0
    rim_data.color = (0.95, 0.98, 1.0)
    rim_obj = bpy.data.objects.new("RimLight", rim_data)
    scene.collection.objects.link(rim_obj)
    rim_dir = Vector((0.2, -1.2, 0.8)).normalized()
    rim_obj.rotation_euler = rim_dir.to_track_quat('-Z', 'Y').to_euler()
    
    # Render settings
    scene.render.resolution_x = 960
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'

def get_scene_bounds():
    min_c = Vector((float('inf'), float('inf'), float('inf')))
    max_c = Vector((float('-inf'), float('-inf'), float('-inf')))
    count = 0
    for o in bpy.data.objects:
        if o.type in ('MESH', 'CURVE') and not o.name.startswith("VerifyCam"):
            for corner in o.bound_box:
                v = o.matrix_world @ Vector(corner)
                min_c.x = min(min_c.x, v.x)
                min_c.y = min(min_c.y, v.y)
                min_c.z = min(min_c.z, v.z)
                max_c.x = max(max_c.x, v.x)
                max_c.y = max(max_c.y, v.y)
                max_c.z = max(max_c.z, v.z)
            count += 1
    if count == 0:
        return Vector((0,0,0)), 1.0
    center = (min_c + max_c) / 2
    diag = (max_c - min_c).length
    return center, max(diag, 0.1)

def render_engine(eng):
    orig_path = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", eng, "variants", f"{eng}_original.blend")
    curr_path = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", eng, f"{eng}.blend")
    renders_dir = os.path.join(PROJECT_ROOT, "assets", "renders")
    os.makedirs(renders_dir, exist_ok=True)
    
    out_before = os.path.join(renders_dir, f"{eng}_before.png")
    out_after = os.path.join(renders_dir, f"{eng}_after.png")
    
    # Step 1: Open current engine to get target center & diag
    print(f"\n[{eng.upper()}] Loading current blend: {curr_path}")
    bpy.ops.wm.open_mainfile(filepath=curr_path)
    center, diag = get_scene_bounds()
    print(f"  Bounds: center={center}, diag={diag:.3f}")
    
    setup_camera_and_lighting(bpy.context.scene, center, diag)
    bpy.context.scene.render.filepath = out_after
    bpy.ops.render.render(write_still=True)
    print(f"  [RENDER AFTER] Saved to {out_after}")
    
    # Step 2: Open original engine and apply the exact same center & diag camera framing
    print(f"[{eng.upper()}] Loading original blend: {orig_path}")
    bpy.ops.wm.open_mainfile(filepath=orig_path)
    setup_camera_and_lighting(bpy.context.scene, center, diag)
    bpy.context.scene.render.filepath = out_before
    bpy.ops.render.render(write_still=True)
    print(f"  [RENDER BEFORE] Saved to {out_before}")

# Check command line args
target_engine = sys.argv[-1] if len(sys.argv) > 1 and sys.argv[-1] in ENGINES else None
engines_to_render = [target_engine] if target_engine else ENGINES

for eng in engines_to_render:
    render_engine(eng)

print("\nAll renders complete.")
