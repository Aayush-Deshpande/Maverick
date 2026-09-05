import bpy, sys

glb_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.glb'
print(f"Testing import of: {glb_path}")

try:
    bpy.ops.import_scene.gltf(filepath=glb_path)
    print("SUCCESS: Blender imported GLB without any errors!")
except Exception as e:
    import traceback
    print("ERROR in Blender import:")
    traceback.print_exc()
