import bpy

blend_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend'
bpy.ops.wm.open_mainfile(filepath=blend_path)

# Set all 3D viewports to MATERIAL preview mode by default
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'
                    space.shading.use_scene_lights = True
                    space.shading.use_scene_world = True

# Add sun lamp and world if not present
if not bpy.data.worlds.get('StudioWorld'):
    world = bpy.data.worlds.new('StudioWorld')
    bpy.context.scene.world = world

bpy.ops.wm.save_as_mainfile(filepath=blend_path)
bpy.ops.wm.save_as_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\hehe\rotax_912_is_sport.blend')
print("Successfully configured viewport to MATERIAL shading by default!")
