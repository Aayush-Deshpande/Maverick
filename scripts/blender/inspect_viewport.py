import bpy

bpy.ops.wm.open_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend')

# Check shading in all 3D viewports
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    shading = space.shading
                    print(f"Viewport Shading type: {shading.type}, studio_light: {getattr(shading, 'studio_light', 'N/A')}, use_scene_lights: {getattr(shading, 'use_scene_lights', 'N/A')}, use_scene_world: {getattr(shading, 'use_scene_world', 'N/A')}")
