"""
=============================================================================
BAYRAKTAR TB3 UCAV - MASTER DIGITAL TWIN VERIFICATION & PRODUCTION RENDERS
=============================================================================
Renders:
1. Hero image.png pass (Cam_Hero_Image_PNG, Tactical Carbon PBR, Dark Studio Floor)
2. Ghost Mode / Wireframe pass (Cam_Wireframe_FDDA, Subdiv Level 0 Quad Topology,
   matching bayraktar-tb3-ucav-3d-model-fdda7fefdc.jpg with "Subdivision Level 0")
3. Aselsan CATS EO/IR & MAM-L Close-up pass (Cam_Front_Sensor)
4. Carrier Wing Fold pass (Frame 60, 115° shipboard stowage)
=============================================================================
"""

import bpy
import os
import math
import shutil
import mathutils

blend_path = r"e:\backup-llm\backup-no-llm\3d_engine\3d_models\bayraktar_tb3_digital_twin.blend"
renders_dir = r"e:\backup-llm\backup-no-llm\3d_engine\3d_models\renders"
artifacts_dir = r"C:\Users\Aayush\.gemini\antigravity-ide\brain\59abf336-b0e2-4242-aa30-d1e91dfcd0a7"
os.makedirs(renders_dir, exist_ok=True)

# 1. Open Master Blend File
bpy.ops.wm.open_mainfile(filepath=blend_path)
scene = bpy.context.scene

# Configure EEVEE for grain-free, 120 FPS speed and ultra-high clarity
scene.render.engine = 'BLENDER_EEVEE'
if hasattr(scene, 'eevee'):
    if hasattr(scene.eevee, 'use_gtao'):
        scene.eevee.use_gtao = True
    if hasattr(scene.eevee, 'use_ssr'):
        scene.eevee.use_ssr = True

scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'

ground_plane = bpy.data.objects.get("Studio_Ground_Plane")
mat_pbr = bpy.data.materials.get("TB3_Tactical_PBR")
mat_satcom = bpy.data.materials.get("TB3_SATCOM_Dome")

# Objects with tactical PBR
airframe_objs = [
    "Fuselage", "Wing_Inner_Left", "Wing_Inner_Right",
    "Wing_Outer_Left", "Wing_Outer_Right", "Tail_Boom_Left", "Tail_Boom_Right",
    "Fin_Left", "Fin_Right", "Inverted_V_Stabilizer", "Ventral_Radiator_Scoop"
]

def restore_tactical_pbr():
    for oname in airframe_objs:
        obj = bpy.data.objects.get(oname)
        if obj and obj.data.materials and mat_pbr:
            obj.data.materials[0] = mat_pbr
        if obj:
            wire_mod = obj.modifiers.get("Wire_Overlay")
            if wire_mod:
                obj.modifiers.remove(wire_mod)
    satcom = bpy.data.objects.get("SATCOM_Radome")
    if satcom and mat_satcom:
        satcom.data.materials[0] = mat_satcom
    if ground_plane:
        ground_plane.hide_render = False
    for obj in bpy.data.objects:
        if "MAML" in obj.name or "Guided_bomb" in obj.name or "Bomb" in obj.name:
            obj.hide_render = False

print("\n----------------------------------------------------------------------")
print("PASS 1: RENDERING HERO TACTICAL PBR (MATCHING IMAGE.PNG)")
print("----------------------------------------------------------------------")
restore_tactical_pbr()
scene.frame_set(1)

cam_hero = bpy.data.objects.get("Cam_Hero_Image_PNG")
if cam_hero:
    scene.camera = cam_hero

hero_out = os.path.join(renders_dir, "render_01_hero_image_png.png")
scene.render.filepath = hero_out
bpy.ops.render.render(write_still=True)
print(f"  -> Saved Pass 1: {hero_out}")
shutil.copy2(hero_out, os.path.join(artifacts_dir, "render_01_hero_image_png.png"))

print("\n----------------------------------------------------------------------")
print("PASS 2: RENDERING GHOST / WIREFRAME TOPOLOGY (MATCHING FDDA7FEFDC.JPG)")
print("----------------------------------------------------------------------")
# Hide ground floor so camera can view from underneath
if ground_plane:
    ground_plane.hide_render = True

# Hide munitions & internal boxes for clean wireframe inspection
for obj in bpy.data.objects:
    name_lower = obj.name.lower()
    if any(k in name_lower for k in ["maml", "bomb", "guided", "cube", "box", "internal"]):
        obj.hide_render = True

# Setup Wireframe materials: Uniform warm clay + crisp emission lines
mat_clay = bpy.data.materials.new("TB3_Clay_Warm_Render")
mat_clay.use_nodes = True
bsdf_clay = mat_clay.node_tree.nodes.get("Principled BSDF")
if bsdf_clay:
    bsdf_clay.inputs['Base Color'].default_value = (0.44, 0.41, 0.37, 1.0)
    bsdf_clay.inputs['Roughness'].default_value = 0.45
    if 'Specular IOR Level' in bsdf_clay.inputs:
        bsdf_clay.inputs['Specular IOR Level'].default_value = 0.25

mat_wire_line = bpy.data.materials.new("TB3_Line_Crisp_Render")
mat_wire_line.use_nodes = True
wnodes = mat_wire_line.node_tree.nodes
wlinks = mat_wire_line.node_tree.links
wnodes.clear()
out_n = wnodes.new('ShaderNodeOutputMaterial')
emit_n = wnodes.new('ShaderNodeEmission')
emit_n.inputs['Color'].default_value = (0.94, 0.92, 0.88, 1.0)
emit_n.inputs['Strength'].default_value = 1.4
wlinks.new(emit_n.outputs['Emission'], out_n.inputs['Surface'])

for obj in bpy.data.objects:
    if obj.type == 'MESH' and not obj.hide_render and obj.name != "Studio_Ground_Plane":
        w = obj.modifiers.get("Wire_Overlay")
        if w: obj.modifiers.remove(w)
        for mod in obj.modifiers:
            if mod.type == 'SUBSURF':
                mod.levels = 0
                mod.render_levels = 0
        for poly in obj.data.polygons:
            poly.material_index = 0
        obj.data.materials.clear()
        obj.data.materials.append(mat_clay)
        obj.data.materials.append(mat_wire_line)
        wmod = obj.modifiers.new(name="Wire_Overlay", type='WIREFRAME')
        wmod.thickness = 0.0038
        wmod.use_replace = False
        wmod.material_offset = 1

# Clay lighting suite for Pass 2
for obj in list(scene.objects):
    if obj.type == 'LIGHT':
        bpy.data.objects.remove(obj, do_unlink=True)

l1_data = bpy.data.lights.new("Studio_Clay_Key", 'AREA')
l1_data.size = 20.0
l1_data.size_y = 20.0
l1_data.energy = 4500.0
l1_data.color = (1.0, 0.98, 0.95)
l1_obj = bpy.data.objects.new("Studio_Clay_Key", l1_data)
l1_obj.location = (6.0, 4.0, -3.0)
scene.collection.objects.link(l1_obj)

l2_data = bpy.data.lights.new("Studio_Clay_Fill", 'AREA')
l2_data.size = 18.0
l2_data.size_y = 18.0
l2_data.energy = 2800.0
l2_data.color = (0.95, 0.96, 1.0)
l2_obj = bpy.data.objects.new("Studio_Clay_Fill", l2_data)
l2_obj.location = (-6.0, -2.0, 1.0)
scene.collection.objects.link(l2_obj)

l3_data = bpy.data.lights.new("Studio_Clay_Top", 'AREA')
l3_data.size = 20.0
l3_data.size_y = 20.0
l3_data.energy = 1800.0
l3_data.color = (1.0, 1.0, 1.0)
l3_obj = bpy.data.objects.new("Studio_Clay_Top", l3_data)
l3_obj.location = (0.0, 0.0, 7.0)
scene.collection.objects.link(l3_obj)

cam_wire = bpy.data.objects.get("Cam_Wireframe_FDDA")
if cam_wire:
    scene.camera = cam_wire

wire_out = os.path.join(renders_dir, "render_02_wireframe_subdiv0_fdda.png")
scene.render.filepath = wire_out
bpy.ops.render.render(write_still=True)
print(f"  -> Saved Pass 2: {wire_out}")

# Reopen blend file to restore clean master state
bpy.ops.wm.open_mainfile(filepath=blend_path)
scene = bpy.context.scene

print("\n----------------------------------------------------------------------")
print("PASS 3: RENDERING CATS EO/IR TURRET & MAM-L CLOSE-UP")
print("----------------------------------------------------------------------")
cam_sensor = bpy.data.objects.get("Cam_Front_Sensor")
if cam_sensor:
    scene.camera = cam_sensor

sensor_out = os.path.join(renders_dir, "render_03_cats_turret_maml_detail.png")
scene.render.filepath = sensor_out
bpy.ops.render.render(write_still=True)
print(f"  -> Saved Pass 3: {sensor_out}")
shutil.copy2(sensor_out, os.path.join(artifacts_dir, "render_03_cats_turret_maml_detail.png"))

print("\n----------------------------------------------------------------------")
print("PASS 4: RENDERING CARRIER WING FOLD (115° SHIPBOARD STOWAGE)")
print("----------------------------------------------------------------------")
scene.frame_set(170) # Folded at 115 degrees on carrier deck
cam_hero = bpy.data.objects.get("Cam_Hero_Image_PNG")
if cam_hero:
    scene.camera = cam_hero

fold_out = os.path.join(renders_dir, "render_04_carrier_wing_fold.png")
scene.render.filepath = fold_out
bpy.ops.render.render(write_still=True)
print(f"  -> Saved Pass 4: {fold_out}")
shutil.copy2(fold_out, os.path.join(artifacts_dir, "render_04_carrier_wing_fold.png"))

print("\nAll 4 production verification passes rendered successfully!")
