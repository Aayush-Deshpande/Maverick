import bpy, os

blend_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend'
bpy.ops.wm.open_mainfile(filepath=blend_path)

# Double check and remove any duplicate/conflicting meshes
to_remove = [o for o in bpy.data.objects if any(k in o.name for k in ['Covers_Custom', 'Gearbox_Type_3', 'Cert_912iScSport'])]
for o in to_remove:
    bpy.data.objects.remove(o, do_unlink=True)
print(f"Removed {len(to_remove)} conflicting objects before clean export.")

# Export clean GLB to digital_twin directory
clean_glb_path = r'E:\TalentForge\Clay\3d_engine\digital_twin\rotax_912_is_sport_packed.glb'
clean_glb_root = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport_packed.glb'

bpy.ops.export_scene.gltf(
    filepath=clean_glb_path,
    export_format='GLB',
    export_materials='EXPORT',
    export_image_format='AUTO',
    use_visible=False
)

import shutil
shutil.copy2(clean_glb_path, clean_glb_root)
print(f"SUCCESS: Exported clean, glitch-free GLB to {clean_glb_path} ({os.path.getsize(clean_glb_path):,} bytes)")
