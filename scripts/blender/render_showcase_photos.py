"""
Render high-definition showcase beauty photos for all 5 finalized ANUMAAN aero engines.
Outputs crisp 1280x720 showcase renders to assets/renders/ and copies to artifact directory.
"""
import os
import shutil
import bpy
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
ARTIFACT_DIR = r"C:\Users\Prasad\.gemini\antigravity\brain\eb7686ec-6c7e-42f5-a015-137bf9ffe74b"
RENDERS_DIR = os.path.join(PROJECT_ROOT, "assets", "renders")
os.makedirs(RENDERS_DIR, exist_ok=True)

ENGINES = [
    ("rotax_912is", "Rotax 912 iS Sport (Naturally Aspirated Flat-4)"),
    ("rotax_914", "Rotax 914 UL/F (Turbocharged Flat-4)"),
    ("rotax_915is", "Rotax 915 iS (Turbocharged Intercooled Flat-4)"),
    ("austro_ae300", "Austro Engine AE300 (2.0L Common-Rail Diesel)"),
    ("vrde_jayem_2_2l", "VRDE Jayem 2.2L (2.2L CRDI Diesel for MALE UAVs)"),
]

def get_scene_bounds():
    min_c = Vector((float('inf'), float('inf'), float('inf')))
    max_c = Vector((float('-inf'), float('-inf'), float('-inf')))
    count = 0
    for o in bpy.data.objects:
        if o.type in ('MESH', 'CURVE') and not o.name.startswith("CompCam") and not o.name.startswith("Showcase"):
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

def setup_studio(scene, center, diag):
    # Clean previous studio lights/cameras
    for o in list(scene.objects):
        if o.type in ('CAMERA', 'LIGHT') or o.name.startswith("Showcase") or o.name.startswith("Comp"):
            bpy.data.objects.remove(o, do_unlink=True)
            
    # Studio Camera
    cam_data = bpy.data.cameras.new("ShowcaseCam")
    cam_data.lens = 50.0  # 50mm portrait perspective
    cam_data.clip_start = max(0.01, diag * 0.001)
    cam_data.clip_end = max(50000.0, diag * 25.0)
    cam_obj = bpy.data.objects.new("ShowcaseCam", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    
    # Beauty 3/4 viewpoint slightly elevated
    view_offset = Vector((1.35, -1.65, 0.85)).normalized() * (diag * 1.55)
    cam_obj.location = center + view_offset
    direction = center - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()
    
    # World background: Deep dark slate aerospace aesthetic (#0d1117)
    if not scene.world:
        scene.world = bpy.data.worlds.new("ShowcaseWorld")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.05, 0.07, 0.09, 1.0)
        bg.inputs[1].default_value = 0.9
        
    # Key Sun Light (Warm crisp daylight)
    key_data = bpy.data.lights.new("ShowcaseKey", type='SUN')
    key_data.energy = 4.5
    key_data.color = (1.0, 0.98, 0.95)
    key_obj = bpy.data.objects.new("ShowcaseKey", key_data)
    scene.collection.objects.link(key_obj)
    key_dir = Vector((-1.2, 1.0, -1.8)).normalized()
    key_obj.rotation_euler = key_dir.to_track_quat('-Z', 'Y').to_euler()
    
    # Fill Sun Light (Cool ambient skylight)
    fill_data = bpy.data.lights.new("ShowcaseFill", type='SUN')
    fill_data.energy = 2.2
    fill_data.color = (0.90, 0.94, 1.0)
    fill_obj = bpy.data.objects.new("ShowcaseFill", fill_data)
    scene.collection.objects.link(fill_obj)
    fill_dir = Vector((1.2, -0.6, -0.9)).normalized()
    fill_obj.rotation_euler = fill_dir.to_track_quat('-Z', 'Y').to_euler()
    
    # Rim Accent Light (Clean specular glint on top/rear metal edges)
    rim_data = bpy.data.lights.new("ShowcaseRim", type='SUN')
    rim_data.energy = 3.0
    rim_data.color = (0.95, 0.98, 1.0)
    rim_obj = bpy.data.objects.new("ShowcaseRim", rim_data)
    scene.collection.objects.link(rim_obj)
    rim_dir = Vector((0.3, -1.4, 0.9)).normalized()
    rim_obj.rotation_euler = rim_dir.to_track_quat('-Z', 'Y').to_euler()
    
    # High-Definition 1280x720 output
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False  # Solid aerospace dark background
    scene.view_settings.view_transform = 'Standard'

def render_final_photos():
    print("=" * 70)
    print("RENDERING HIGH-DEFINITION SHOWCASE BEAUTY PHOTOS FOR ALL 5 ENGINES")
    print("=" * 70)
    
    for eng_id, title in ENGINES:
        blend_path = os.path.join(PROJECT_ROOT, "assets", "blender", "engines", eng_id, f"{eng_id}.blend")
        out_file = os.path.join(RENDERS_DIR, f"final_{eng_id}.png")
        artifact_file = os.path.join(ARTIFACT_DIR, f"final_{eng_id}.png")
        
        print(f"\n[{eng_id.upper()}] Loading: {blend_path}")
        bpy.ops.wm.open_mainfile(filepath=blend_path)
        
        center, diag = get_scene_bounds()
        print(f"  Framing: center={center}, diag={diag:.3f}")
        
        setup_studio(bpy.context.scene, center, diag)
        
        bpy.context.scene.render.filepath = out_file
        bpy.ops.render.render(write_still=True)
        print(f"  [SAVED] {out_file}")
        
        if os.path.exists(out_file):
            shutil.copyfile(out_file, artifact_file)
            print(f"  [COPIED TO ARTIFACT] {artifact_file}")
            
    print("\nALL 5 FINAL SHOWCASE PHOTOS RENDERED SUCCESSFULLY!")

if __name__ == "__main__":
    render_final_photos()
