import bpy
import mathutils
import math
import os

OUT_DIR = r"E:\TalentForge\Clay\3d_engine\digital_twin_web\frames"
os.makedirs(OUT_DIR, exist_ok=True)

# Open base blend file
bpy.ops.wm.open_mainfile(filepath=r"E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend")
scene = bpy.context.scene

# Clean existing lights & cameras to setup precision studio rig
for obj in list(bpy.data.objects):
    if obj.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(obj, do_unlink=True)

# =========================================================================
# EXACT COMPONENT-BY-COMPONENT PBR SHADER COLOR GRADING
# =========================================================================
for mat in bpy.data.materials:
    if mat.use_nodes and mat.node_tree:
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                mname = mat.name.lower()
                
                # 1. VALVE COVERS (Dark Forest Racing Green)
                if any(k in mname for k in ['green', 'plasticgreen', 'plastictheme', 'theme_m_plastic']):
                    node.inputs['Base Color'].default_value = (0.015, 0.28, 0.08, 1.0) # #1C3124 deep forest green
                    node.inputs['Roughness'].default_value = 0.30
                    node.inputs['Metallic'].default_value = 0.06
                
                # 2. INTAKE RUNNERS & CHROME TUBES (Polished Specular Chrome)
                elif 'chrome' in mname:
                    node.inputs['Base Color'].default_value = (0.92, 0.94, 0.97, 1.0) # Bright specular chrome
                    node.inputs['Roughness'].default_value = 0.06
                    node.inputs['Metallic'].default_value = 0.98
                
                # 3. AIRBOX & COMPONENT LABELS / EMBOSSED TEXT (Off-White Lettering)
                elif 'label' in mname or 'fuse' in mname:
                    node.inputs['Base Color'].default_value = (0.85, 0.86, 0.88, 1.0) # Crisp off-white
                    node.inputs['Roughness'].default_value = 0.25
                    node.inputs['Metallic'].default_value = 0.0
                
                # 4. AIRBOX BODY, CABLING, RUBBER HOSES, BELTS (Pure Matte Jet Black)
                elif any(k in mname for k in ['black', 'rubber', 'cable', 'timing', 'theme_m_black', 'plug', 'lead']):
                    node.inputs['Base Color'].default_value = (0.006, 0.006, 0.008, 1.0) # Pure matte jet black
                    node.inputs['Roughness'].default_value = 0.65
                    node.inputs['Metallic'].default_value = 0.0
                
                # 5. EXHAUST SYSTEM & DOWNPIPE (Dark Heat-Treated Gunmetal Steel)
                elif 'exhaust' in mname or 'steeldark' in mname:
                    node.inputs['Base Color'].default_value = (0.12, 0.13, 0.15, 1.0) # Dark heat-treated gunmetal
                    node.inputs['Roughness'].default_value = 0.38
                    node.inputs['Metallic'].default_value = 0.92
                
                # 6. OIL TANK / RESERVOIR (Warm Bronze-Grey Shadowed Steel)
                elif 'oil_tank' in mname or 'tank' in mname:
                    node.inputs['Base Color'].default_value = (0.15, 0.14, 0.14, 1.0) # Warm bronze-grey
                    node.inputs['Roughness'].default_value = 0.35
                    node.inputs['Metallic'].default_value = 0.85
                
                # 7. ALTERNATOR & STATOR FINS (Cast Aeronautical Aluminum Alloy)
                elif any(k in mname for k in ['alternator', 'rotax914', 'rotax915', 'extras', 'a12']):
                    node.inputs['Base Color'].default_value = (0.24, 0.25, 0.27, 1.0) # Cast alloy silver
                    node.inputs['Roughness'].default_value = 0.30
                    node.inputs['Metallic'].default_value = 0.88
                
                # 8. GEARBOX & REDUCTION DRIVE HUB (Machined Dark Steel)
                elif 'gearbox' in mname or 'steelblack' in mname or 'steel' in mname:
                    node.inputs['Base Color'].default_value = (0.18, 0.19, 0.21, 1.0) # Dark machined steel
                    node.inputs['Roughness'].default_value = 0.32
                    node.inputs['Metallic'].default_value = 0.90
                
                # 9. GENERAL CASTINGS & ENGINE CRANKCASE
                else:
                    node.inputs['Base Color'].default_value = (0.20, 0.21, 0.23, 1.0)
                    node.inputs['Roughness'].default_value = 0.35
                    node.inputs['Metallic'].default_value = 0.85

# Calculate bounding box center of the engine
min_co = [float('inf')] * 3
max_co = [float('-inf')] * 3
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        for v in obj.bound_box:
            world_co = obj.matrix_world @ mathutils.Vector(v)
            for i in range(3):
                min_co[i] = min(min_co[i], world_co[i])
                max_co[i] = max(max_co[i], world_co[i])

center = [(min_co[i] + max_co[i]) / 2 for i in range(3)]
size = [max_co[i] - min_co[i] for i in range(3)]
max_dim = max(size)

# Setup World Environment - Deep Studio Neutral Slate Gray
scene.world.use_nodes = True
world_tree = scene.world.node_tree
world_tree.nodes.clear()

node_bg = world_tree.nodes.new(type='ShaderNodeBackground')
node_bg.inputs['Color'].default_value = (0.22, 0.22, 0.23, 1.0) # #646466 background
node_bg.inputs['Strength'].default_value = 0.5

node_env = world_tree.nodes.new(type='ShaderNodeTexEnvironment')
exr_path = r"E:\Blender\5.2\datafiles\studiolights\world\sunset.exr"
if os.path.exists(exr_path):
    node_env.image = bpy.data.images.load(exr_path)

node_mix = world_tree.nodes.new(type='ShaderNodeMixShader')
node_lightpath = world_tree.nodes.new(type='ShaderNodeLightPath')
node_output = world_tree.nodes.new(type='ShaderNodeOutputWorld')

node_env_bg = world_tree.nodes.new(type='ShaderNodeBackground')
node_env_bg.inputs['Strength'].default_value = 0.70

world_tree.links.new(node_env.outputs['Color'], node_env_bg.inputs['Color'])
world_tree.links.new(node_lightpath.outputs['Is Camera Ray'], node_mix.inputs['Fac'])
world_tree.links.new(node_env_bg.outputs['Background'], node_mix.inputs[1])
world_tree.links.new(node_bg.outputs['Background'], node_mix.inputs[2])
world_tree.links.new(node_mix.outputs['Shader'], node_output.inputs['Surface'])

# High-contrast Sun Key from top-left
sun_data = bpy.data.lights.new(name="SunKey", type='SUN')
sun_data.energy = 5.2
sun_data.color = (1.0, 0.96, 0.91)
if hasattr(sun_data, 'use_contact_shadow'):
    sun_data.use_contact_shadow = True
    sun_data.contact_shadow_distance = 1.0

sun_obj = bpy.data.objects.new(name="SunKey", object_data=sun_data)
sun_obj.rotation_euler = (math.radians(55), math.radians(25), math.radians(50))
scene.collection.objects.link(sun_obj)

# Subtle Fill Light
fill_data = bpy.data.lights.new(name="FillLight", type='SUN')
fill_data.energy = 0.35
fill_data.color = (0.70, 0.80, 0.95)
fill_obj = bpy.data.objects.new(name="FillLight", object_data=fill_data)
fill_obj.rotation_euler = (math.radians(-40), math.radians(-30), math.radians(-140))
scene.collection.objects.link(fill_obj)

# Create Camera - Telephoto CAD perspective
cam_data = bpy.data.cameras.new(name="TurntableCam")
cam_data.lens = 48
cam_obj = bpy.data.objects.new(name="TurntableCam", object_data=cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

# Camera Orbit Settings
radius = max_dim * 2.35
cam_height = center[2] + max_dim * 0.85
total_frames = 120

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'JPEG'
scene.render.image_settings.quality = 90

print(f"Starting render of {total_frames} custom component-graded frames...")
target_vec = mathutils.Vector(center)

for f in range(total_frames):
    angle = (f / total_frames) * 2 * math.pi + math.radians(-50)
    cx = center[0] + radius * math.cos(angle)
    cy = center[1] + radius * math.sin(angle)
    cz = cam_height
    
    cam_obj.location = (cx, cy, cz)
    direction = target_vec - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    
    frame_path = os.path.join(OUT_DIR, f"frame_{f:03d}.jpg")
    scene.render.filepath = frame_path
    bpy.ops.render.render(write_still=True)
    if f % 20 == 0 or f == total_frames - 1:
        print(f"Rendered frame {f+1}/{total_frames} -> {frame_path}")

print("EXACT COMPONENT-GRADED TURNTABLE COMPLETE!")
