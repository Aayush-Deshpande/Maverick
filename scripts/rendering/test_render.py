import bpy
import math
import os

OUT_DIR = r"E:\TalentForge\Clay\3d_engine\digital_twin_web\frames"
os.makedirs(OUT_DIR, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=r"E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend")
scene = bpy.context.scene

# Set up render engine - EEVEE with all high-end raytracing & shading features enabled
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'JPEG'
scene.render.image_settings.quality = 95

# World background - exact studio gray
if scene.world and scene.world.node_tree:
    for node in scene.world.node_tree.nodes:
        if node.type == 'BACKGROUND':
            node.inputs['Color'].default_value = (0.267, 0.263, 0.271, 1.0)
            node.inputs['Strength'].default_value = 1.0

# Find or create turntable root object
root = None
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        if root is None:
            root = obj

# Test single frame render
test_path = os.path.join(OUT_DIR, "test_frame.jpg")
scene.render.filepath = test_path
bpy.ops.render.render(write_still=True)
print(f"Rendered test frame to: {test_path}")
