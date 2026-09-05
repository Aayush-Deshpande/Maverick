"""
Re-export Rotax 912 iS from Blender to glTF/GLB with maximum quality.
Bakes all Principled BSDF materials into proper glTF PBR.
"""
import bpy, os

OUT = r'E:\TalentForge\Clay\3d_engine\digital_twin_web\rotax_912_is_sport_packed.glb'

bpy.ops.wm.open_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend')

# Remove lights/cameras — only export meshes
for obj in list(bpy.data.objects):
    if obj.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(obj, do_unlink=True)

# Select all mesh objects
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.select_set(True)

# Print material count for verification
mat_count = 0
for mat in bpy.data.materials:
    if mat.users > 0:
        mat_count += 1
print(f"Exporting {mat_count} materials")

# Export with maximum quality glTF settings
bpy.ops.export_scene.gltf(
    filepath=OUT,
    export_format='GLB',
    
    # Geometry
    export_apply=True,           # Apply modifiers
    export_normals=True,         # Include normals for proper shading
    export_tangents=True,        # Include tangents for normal maps
    
    # Materials — this is critical
    export_materials='EXPORT',   # Export all materials
    
    # Images/Textures
    export_image_format='AUTO',  # Best format per texture
    
    # Only selected (meshes)
    use_selection=True,
    
    # No animation needed
    export_animations=False,
    export_skins=False,
    
    # No Draco compression — preserve full geometry quality
    export_draco_mesh_compression_enable=False,
)

# Verify file size
size_mb = os.path.getsize(OUT) / (1024*1024)
print(f"Exported: {OUT}")
print(f"Size: {size_mb:.1f} MB")
print("DONE — full quality GLB with proper PBR materials")
