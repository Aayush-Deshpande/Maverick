"""
Set rotax_912_is_sport.blend to default to RENDERED viewport shading on all screens and save.
"""

import bpy

blend_path = r"E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend"
bpy.ops.wm.open_mainfile(filepath=blend_path)

# Set Render Engine
bpy.context.scene.render.engine = 'BLENDER_EEVEE'

# Set every 3D viewport across all workspaces/screens to RENDERED
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'RENDERED'
                    space.shading.use_scene_lights = True
                    space.shading.use_scene_world = True

bpy.ops.wm.save_mainfile()
print("SUCCESS: Permanently set rotax_912_is_sport.blend to RENDERED viewport shading!")
