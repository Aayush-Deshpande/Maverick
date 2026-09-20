import bpy
import math
import os

blend_path = r"e:\backup-llm\backup-no-llm\3d_engine\3d_models\bayraktar_tb3_digital_twin.blend"
bpy.ops.wm.open_mainfile(filepath=blend_path)
scene = bpy.context.scene

# Clean SATCOM dome material
satcom = bpy.data.objects.get("SATCOM_Radome")
if satcom:
    mat_satcom = bpy.data.materials.get("TB3_SATCOM_Dome")
    if not mat_satcom:
        mat_satcom = bpy.data.materials.new("TB3_SATCOM_Dome")
        mat_satcom.use_nodes = True
        bsdf = mat_satcom.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = (0.12, 0.13, 0.14, 1.0)
            bsdf.inputs['Roughness'].default_value = 0.40
            bsdf.inputs['Metallic'].default_value = 0.05
    satcom.data.materials.clear()
    satcom.data.materials.append(mat_satcom)

# Setup Hero Camera matching image.png framing
cam_hero = bpy.data.objects.get("Cam_Hero_Image_PNG")
if not cam_hero:
    cam_data = bpy.data.cameras.new("Cam_Hero_Image_PNG")
    cam_hero = bpy.data.objects.new("Cam_Hero_Image_PNG", cam_data)
    scene.collection.objects.link(cam_hero)

# Target at aircraft center
tgt = bpy.data.objects.get("Target_Hero")
if not tgt:
    tgt = bpy.data.objects.new("Target_Hero", None)
    scene.collection.objects.link(tgt)
tgt.location = (0.1, 0.3, 0.9)

# Position camera for exact angle of image.png
cam_hero.location = (-9.6, 8.8, 7.2)
cam_hero.data.lens = 40.0

cam_hero.constraints.clear()
tt = cam_hero.constraints.new(type='TRACK_TO')
tt.target = tgt
tt.track_axis = 'TRACK_NEGATIVE_Z'
tt.up_axis = 'UP_Y'
scene.camera = cam_hero

# Studio Lighting Suite matching image.png
for obj in list(scene.objects):
    if obj.type == 'LIGHT':
        bpy.data.objects.remove(obj, do_unlink=True)

# 1. Main Overhead Soft Studio Key Area Light
key_data = bpy.data.lights.new("Studio_Key_Area", 'AREA')
key_data.shape = 'RECTANGLE'
key_data.size = 12.0
key_data.size_y = 8.0
key_data.energy = 2600.0
key_data.color = (1.0, 1.0, 1.0)
key_obj = bpy.data.objects.new("Studio_Key_Area", key_data)
key_obj.location = (-7.0, 6.0, 9.0)
scene.collection.objects.link(key_obj)

# 2. Soft Fill Area Light (Illuminates far wing & tail)
fill_data = bpy.data.lights.new("Studio_Fill_Area", 'AREA')
fill_data.shape = 'RECTANGLE'
fill_data.size = 10.0
fill_data.size_y = 10.0
fill_data.energy = 1400.0
fill_data.color = (0.95, 0.96, 1.0)
fill_obj = bpy.data.objects.new("Studio_Fill_Area", fill_data)
fill_obj.location = (8.0, -2.0, 7.5)
scene.collection.objects.link(fill_obj)

# 3. Top Rim/Highlight Area Light (Casts sleek edge highlights on wings and fuselage)
top_data = bpy.data.lights.new("Studio_Top_Area", 'AREA')
top_data.shape = 'RECTANGLE'
top_data.size = 14.0
top_data.size_y = 14.0
top_data.energy = 1200.0
top_data.color = (1.0, 1.0, 1.0)
top_obj = bpy.data.objects.new("Studio_Top_Area", top_data)
top_obj.location = (0.0, 2.0, 11.0)
scene.collection.objects.link(top_obj)

# Seamless Studio Floor matching image.png (#16171a dark matte studio)
floor = bpy.data.objects.get("Studio_Ground_Plane")
if floor:
    floor.location = (0, 0, 0)
    floor.scale = (40, 40, 1)
    if floor.data.materials:
        mat_fl = floor.data.materials[0]
        bsdf_fl = mat_fl.node_tree.nodes.get("Principled BSDF")
        if bsdf_fl:
            bsdf_fl.inputs['Base Color'].default_value = (0.024, 0.024, 0.026, 1.0)
            bsdf_fl.inputs['Roughness'].default_value = 0.80

# World Background
if scene.world and scene.world.node_tree:
    bg = scene.world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs['Color'].default_value = (0.024, 0.024, 0.026, 1.0)
        bg.inputs['Strength'].default_value = 0.8

out_hero = r"e:\backup-llm\backup-no-llm\3d_engine\3d_models\renders\test_hero_angle_v2.png"
scene.render.filepath = out_hero
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
bpy.ops.render.render(write_still=True)
print(f"Rendered test_hero_angle_v2 to: {out_hero}")
