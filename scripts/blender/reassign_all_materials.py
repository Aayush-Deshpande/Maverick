import bpy

blend_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend'
bpy.ops.wm.open_mainfile(filepath=blend_path)

# Dictionary of all 32 material names
known_mats = [
    'M_Chrome', 'M_Cobalt', 'M_Steel', 'M_SteelDark', 'M_SteelBlack',
    'M_MetalPaintedBlack', 'M_Black', 'M_PlasticBlack', 'M_PlasticCable',
    'M_PlasticWhite', 'M_PlasticGreen', 'M_PlasticTheme', 'M_Copper',
    'M_PlasticRed', 'M_PlasticRedDarker', 'M_PlasticBlue', 'M_PlasticLightBlue',
    'M_PlasticYellow', 'M_FuseLight', 'M_PlasticBegue', 'M_Motherboard',
    'M_Rubber', 'M_Glass', 'M_GlassMilky', 'M_TimingBelt', 'M_Labels',
    'M_Rotax914_Extras', 'Rotax915_Extras', 'Rotax915_A12', 'Rotax914_A12'
]

reassigned_count = 0

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        # Find which known material name is in the object name
        matched_mat_name = None
        for km in known_mats:
            if km in obj.name:
                matched_mat_name = km
                break
                
        if matched_mat_name and matched_mat_name in bpy.data.materials:
            target_mat = bpy.data.materials[matched_mat_name]
            if obj.data.materials:
                obj.data.materials[0] = target_mat
            else:
                obj.data.materials.append(target_mat)
            reassigned_count += 1
            print(f"Reassigned {obj.name} -> {matched_mat_name}")

print(f"\nTotal meshes correctly assigned to real materials: {reassigned_count} / {len([o for o in bpy.data.objects if o.type == 'MESH'])}")

bpy.ops.wm.save_as_mainfile(filepath=blend_path, check_existing=False)
bpy.ops.wm.save_as_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\hehe\rotax_912_is_sport.blend', check_existing=False)
