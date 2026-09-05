import bpy, os

glb_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.glb'
blend_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend'
hehe_blend_path = r'E:\TalentForge\Clay\3d_engine\hehe\rotax_912_is_sport.blend'

# Clear scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import GLB
bpy.ops.import_scene.gltf(filepath=glb_path)

# Save as native .blend file for immediate one-click opening in Blender!
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
bpy.ops.wm.save_as_mainfile(filepath=hehe_blend_path)

print(f"Saved native Blender file: {blend_path}")
print(f"Saved native Blender file: {hehe_blend_path}")
