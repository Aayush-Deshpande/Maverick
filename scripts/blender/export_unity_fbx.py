import bpy, os

bpy.ops.wm.open_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend')

# The model is ~60-88 cm in Blender units (centimeters)
# Export with scale=1 (1 Blender unit = 1 cm) -> Unity will get centimeter-scale
# We will set Transform Scale to (0.01, 0.01, 0.01) in Unity importer settings OR
# export with global_scale=0.01 so 1 Unity unit = 1 meter

fbx_path = r'E:\Unity_Projects\My project\Assets\3D_Models\rotax_912_is_sport.fbx'

bpy.ops.object.select_all(action='SELECT')

bpy.ops.export_scene.fbx(
    filepath=fbx_path,
    use_selection=False,
    global_scale=1.0,           # Keep Blender units as-is (centimeters)
    apply_unit_scale=True,
    apply_scale_options='FBX_SCALE_ALL',
    bake_space_transform=True,
    object_types={'MESH'},
    mesh_smooth_type='FACE',
    use_mesh_modifiers=True,
    axis_forward='-Z',
    axis_up='Y'                 # Unity Y-up coordinate system
)

sz = os.path.getsize(fbx_path)
print(f"SUCCESS: Exported FBX to {fbx_path} ({sz:,} bytes)")
print("NOTE: Model is ~60-88 units (cm). In Unity, set localScale to (0.01, 0.01, 0.01)")
print("This makes the engine ~0.6m x 0.88m x 0.3m = physically correct Rotax 912 size")
