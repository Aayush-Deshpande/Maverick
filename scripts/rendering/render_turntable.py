import bpy
import mathutils
import math
import os
import shutil

OUT_DIR = r"E:\TalentForge\Clay\3d_engine\digital_twin_web\frames"
os.makedirs(OUT_DIR, exist_ok=True)

# Open base blend file
bpy.ops.wm.open_mainfile(filepath=r"E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend")
scene = bpy.context.scene

# Clean existing lights & cameras to setup precision studio rig
for obj in list(bpy.data.objects):
    if obj.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(obj, do_unlink=True)

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
print(f"Engine center: {center}, max dimension: {max_dim}")

# Setup World Environment with Sunset EXR for photorealistic reflections
scene.world.use_nodes = True
world_tree = scene.world.node_tree
world_tree.nodes.clear()

node_bg = world_tree.nodes.new(type='ShaderNodeBackground')
node_bg.inputs['Color'].default_value = (0.267, 0.263, 0.271, 1.0) # #444345 studio gray
node_bg.inputs['Strength'].default_value = 0.7

node_env = world_tree.nodes.new(type='ShaderNodeTexEnvironment')
exr_path = r"E:\Blender\5.2\datafiles\studiolights\world\sunset.exr"
if os.path.exists(exr_path):
    node_env.image = bpy.data.images.load(exr_path)

# Mix background color for camera rays, and HDRI for reflection rays
node_mix = world_tree.nodes.new(type='ShaderNodeMixShader')
node_lightpath = world_tree.nodes.new(type='ShaderNodeLightPath')
node_output = world_tree.nodes.new(type='ShaderNodeOutputWorld')

node_env_bg = world_tree.nodes.new(type='ShaderNodeBackground')
node_env_bg.inputs['Strength'].default_value = 1.0

world_tree.links.new(node_env.outputs['Color'], node_env_bg.inputs['Color'])
world_tree.links.new(node_lightpath.outputs['Is Camera Ray'], node_mix.inputs['Fac'])
world_tree.links.new(node_env_bg.outputs['Background'], node_mix.inputs[1])
world_tree.links.new(node_bg.outputs['Background'], node_mix.inputs[2])
world_tree.links.new(node_mix.outputs['Shader'], node_output.inputs['Surface'])

# Setup Studio Sun Key Light
sun_data = bpy.data.lights.new(name="SunKey", type='SUN')
sun_data.energy = 4.0
sun_data.color = (1.0, 0.97, 0.92)
sun_obj = bpy.data.objects.new(name="SunKey", object_data=sun_data)
sun_obj.rotation_euler = (math.radians(50), math.radians(20), math.radians(45))
scene.collection.objects.link(sun_obj)

# Setup Fill Light
fill_data = bpy.data.lights.new(name="FillLight", type='SUN')
fill_data.energy = 1.0
fill_data.color = (0.75, 0.82, 0.95)
fill_obj = bpy.data.objects.new(name="FillLight", object_data=fill_data)
fill_obj.rotation_euler = (math.radians(-30), math.radians(-40), math.radians(-135))
scene.collection.objects.link(fill_obj)

# Create Camera - cleanly framed with wide margins
cam_data = bpy.data.cameras.new(name="TurntableCam")
cam_data.lens = 48 # Crisp standard focal length
cam_obj = bpy.data.objects.new(name="TurntableCam", object_data=cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

# Camera Orbit Settings - framed to keep entire engine centered
radius = max_dim * 2.35
cam_height = center[2] + max_dim * 0.85
total_frames = 120 # 120 frames = 3 deg step, silky smooth 60-120fps turntable

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'JPEG'
scene.render.image_settings.quality = 88 # Optimized for fast transfer & GPU decompression

print(f"Starting render of {total_frames} raytraced turntable frames...")
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
    if f % 10 == 0 or f == total_frames - 1:
        print(f"Rendered frame {f+1}/{total_frames} -> {frame_path}")

print("TURNTABLE RENDERING COMPLETE!")
