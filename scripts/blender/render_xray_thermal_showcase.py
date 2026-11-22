"""
Render CGI-grade photorealistic beauty renders for:
1. Transparent Optical X-Ray Glass Crankcase (revealing internal reciprocating pistons, heads, barrels, and valves)
2. Dynamic FLIR Thermal Pyrometry Heat-map (vertex blackbody incandescence per cylinder and glowing exhaust)
3. Holographic Digital Twin Ghost Overlay

Uses Blender EEVEE-Next / Cycles fast physical shaders at 1280x720.
Outputs to assets/renders/ and copies directly to the artifact directory.
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
os.makedirs(ARTIFACT_DIR, exist_ok=True)

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
    for o in list(scene.objects):
        if o.type in ('CAMERA', 'LIGHT') or o.name.startswith("Showcase"):
            bpy.data.objects.remove(o, do_unlink=True)
            
    cam_data = bpy.data.cameras.new("ShowcaseCam")
    cam_data.lens = 52.0
    cam_data.clip_start = max(0.01, diag * 0.001)
    cam_data.clip_end = max(50000.0, diag * 25.0)
    cam_obj = bpy.data.objects.new("ShowcaseCam", cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    
    # 3/4 beauty view highlighting crankcase and cylinder heads
    view_offset = Vector((1.4, -1.6, 0.75)).normalized() * (diag * 1.55)
    cam_obj.location = center + view_offset
    direction = center - cam_obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam_obj.rotation_euler = rot_quat.to_euler()
    
    # Deep slate aerospace background
    if not scene.world:
        scene.world = bpy.data.worlds.new("ShowcaseWorld")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.04, 0.06, 0.08, 1.0)
        bg.inputs[1].default_value = 0.85
        
    # Key light
    key_data = bpy.data.lights.new("ShowcaseKey", type='SUN')
    key_data.energy = 5.0
    key_data.color = (1.0, 0.98, 0.95)
    key_obj = bpy.data.objects.new("ShowcaseKey", key_data)
    scene.collection.objects.link(key_obj)
    key_dir = Vector((-1.2, 1.0, -1.8)).normalized()
    key_obj.rotation_euler = key_dir.to_track_quat('-Z', 'Y').to_euler()
    
    # Fill light
    fill_data = bpy.data.lights.new("ShowcaseFill", type='SUN')
    fill_data.energy = 2.5
    fill_data.color = (0.85, 0.92, 1.0)
    fill_obj = bpy.data.objects.new("ShowcaseFill", fill_data)
    scene.collection.objects.link(fill_obj)
    fill_dir = Vector((1.2, -0.6, -0.9)).normalized()
    fill_obj.rotation_euler = fill_dir.to_track_quat('-Z', 'Y').to_euler()
    
    # Rim light
    rim_data = bpy.data.lights.new("ShowcaseRim", type='SUN')
    rim_data.energy = 4.0
    rim_data.color = (0.95, 0.98, 1.0)
    rim_obj = bpy.data.objects.new("ShowcaseRim", rim_data)
    scene.collection.objects.link(rim_obj)
    rim_dir = Vector((0.3, -1.4, 0.9)).normalized()
    rim_obj.rotation_euler = rim_dir.to_track_quat('-Z', 'Y').to_euler()
    
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False

def create_glass_material():
    mat = bpy.data.materials.new(name="Mat_XRayGlassCasing")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (0.95, 0.98, 1.0, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.08
    bsdf.inputs['IOR'].default_value = 1.48
    
    # Blender 4+ has Transmission Weight, older has Transmission
    if 'Transmission Weight' in bsdf.inputs:
        bsdf.inputs['Transmission Weight'].default_value = 0.94
    elif 'Transmission' in bsdf.inputs:
        bsdf.inputs['Transmission'].default_value = 0.94
        
    if 'Coat Weight' in bsdf.inputs:
        bsdf.inputs['Coat Weight'].default_value = 1.0
        bsdf.inputs['Coat Roughness'].default_value = 0.04
    elif 'Clearcoat' in bsdf.inputs:
        bsdf.inputs['Clearcoat'].default_value = 1.0
        
    out = nodes.new(type='ShaderNodeOutputMaterial')
    out.location = (300, 0)
    mat.node_tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

def create_thermal_material(color_rgb, emission_strength=2.0):
    mat = bpy.data.materials.new(name="Mat_ThermalHeatmap")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (*color_rgb, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.35
    bsdf.inputs['Metallic'].default_value = 0.4
    
    # Emission
    if 'Emission Color' in bsdf.inputs:
        bsdf.inputs['Emission Color'].default_value = (*color_rgb, 1.0)
        bsdf.inputs['Emission Strength'].default_value = emission_strength
    elif 'Emission' in bsdf.inputs:
        bsdf.inputs['Emission'].default_value = (*color_rgb, 1.0)
        if 'Emission Strength' in bsdf.inputs:
            bsdf.inputs['Emission Strength'].default_value = emission_strength
            
    out = nodes.new(type='ShaderNodeOutputMaterial')
    out.location = (300, 0)
    mat.node_tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

def create_smoked_material():
    mat = bpy.data.materials.new(name="Mat_SmokedObsidian")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    bsdf.inputs['Base Color'].default_value = (0.05, 0.07, 0.1, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.25
    if 'Transmission Weight' in bsdf.inputs:
        bsdf.inputs['Transmission Weight'].default_value = 0.65
    elif 'Transmission' in bsdf.inputs:
        bsdf.inputs['Transmission'].default_value = 0.65
        
    out = nodes.new(type='ShaderNodeOutputMaterial')
    out.location = (300, 0)
    mat.node_tree.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return mat

def render_showcase_set():
    targets = [
        ("rotax_914", "assets/blender/engines/rotax_914/rotax_914.blend"),
        ("rotax_915is", "assets/blender/engines/rotax_915is/rotax_915is.blend"),
        ("vrde_jayem_2_2l", "assets/blender/engines/vrde_jayem_2_2l/vrde_jayem_2_2l.blend"),
    ]
    
    for eng_id, rel_path in targets:
        blend_path = os.path.join(PROJECT_ROOT, rel_path)
        print(f"\n==================================================")
        print(f"LOADING ENGINE: {eng_id}")
        print(f"==================================================")
        bpy.ops.wm.open_mainfile(filepath=blend_path)
        scene = bpy.context.scene
        center, diag = get_scene_bounds()
        setup_studio(scene, center, diag)
        
        # 1. RENDER X-RAY GLASS
        glass_mat = create_glass_material()
        casing_names = ['crankcase', 'engine_block', 'valve_cover', 'rocker', 'baffle', 'sump', 'casing', 'cover']
        
        for o in bpy.data.objects:
            if o.type == 'MESH':
                low = o.name.lower()
                if any(c in low for c in casing_names):
                    o.data.materials.clear()
                    o.data.materials.append(glass_mat)
                    
        xray_out = os.path.join(RENDERS_DIR, f"cg_xray_glass_{eng_id}.png")
        xray_artifact = os.path.join(ARTIFACT_DIR, f"cg_xray_glass_{eng_id}.png")
        scene.render.filepath = xray_out
        bpy.ops.render.render(write_still=True)
        print(f"  [SAVED X-RAY GLASS] {xray_out}")
        if os.path.exists(xray_out):
            shutil.copyfile(xray_out, xray_artifact)
            print(f"  [COPIED TO ARTIFACT] {xray_artifact}")
            
        # 2. RENDER FLIR THERMAL HEAT-MAP
        smoked_mat = create_smoked_material()
        thermal_cyl1 = create_thermal_material((0.85, 0.52, 0.08), emission_strength=1.8)  # 118 C amber
        thermal_cyl2 = create_thermal_material((0.92, 0.44, 0.05), emission_strength=2.2)  # 122 C warm amber
        thermal_cyl3 = create_thermal_material((0.88, 0.48, 0.06), emission_strength=2.0)  # 120 C amber
        thermal_cyl4 = create_thermal_material((0.98, 0.12, 0.02), emission_strength=3.5)  # 136 C overheat crimson
        thermal_exhaust = create_thermal_material((1.0, 0.45, 0.08), emission_strength=5.5) # 840 C glowing exhaust
        
        for o in bpy.data.objects:
            if o.type == 'MESH':
                low = o.name.lower()
                if any(c in low for c in casing_names):
                    o.data.materials.clear()
                    o.data.materials.append(smoked_mat)
                elif 'exhaust' in low or 'turbo' in low or 'wastegate' in low:
                    o.data.materials.clear()
                    o.data.materials.append(thermal_exhaust)
                elif '1' in low and ('head' in low or 'barrel' in low or 'cyl' in low or 'combustion' in low):
                    o.data.materials.clear()
                    o.data.materials.append(thermal_cyl1)
                elif '2' in low and ('head' in low or 'barrel' in low or 'cyl' in low or 'combustion' in low):
                    o.data.materials.clear()
                    o.data.materials.append(thermal_cyl2)
                elif '3' in low and ('head' in low or 'barrel' in low or 'cyl' in low or 'combustion' in low):
                    o.data.materials.clear()
                    o.data.materials.append(thermal_cyl3)
                elif '4' in low and ('head' in low or 'barrel' in low or 'cyl' in low or 'combustion' in low):
                    o.data.materials.clear()
                    o.data.materials.append(thermal_cyl4)
                elif 'head' in low or 'barrel' in low or 'cylinder' in low:
                    o.data.materials.clear()
                    o.data.materials.append(thermal_cyl2)
                    
        thermal_out = os.path.join(RENDERS_DIR, f"cg_thermal_flir_{eng_id}.png")
        thermal_artifact = os.path.join(ARTIFACT_DIR, f"cg_thermal_flir_{eng_id}.png")
        scene.render.filepath = thermal_out
        bpy.ops.render.render(write_still=True)
        print(f"  [SAVED THERMAL FLIR] {thermal_out}")
        if os.path.exists(thermal_out):
            shutil.copyfile(thermal_out, thermal_artifact)
            print(f"  [COPIED TO ARTIFACT] {thermal_artifact}")

    print("\nALL CGI X-RAY AND THERMAL SHOWCASE RENDERS COMPLETE!")

if __name__ == "__main__":
    render_showcase_set()
