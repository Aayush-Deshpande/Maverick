import bpy
import mathutils

uav = bpy.data.objects.get('UAV_Predator_Master')
cam = bpy.data.objects.get('Camera_UAV_Chase')

for obj in (uav, cam):
    if obj and obj.animation_data:
        obj.animation_data_clear()

uav_pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))
# Let's use standard Blender Euler rotation:
# In the original blend at Frame 50:
# uav.rotation_euler = Euler((0.0, 0.0, -0.8421), 'XYZ')
# Let's test two renders:
# Render A: rotation_euler.z = -0.8421 (approx -48 deg)
# Render B: rotation_euler.z = -0.8421 + pi (180 deg flipped)

# Let's test Render B (flipped by 180 deg):
uav.location = uav_pos
uav.rotation_euler = mathutils.Euler((0.0, 0.0, -0.8421 + 3.14159265), 'XYZ')
uav.scale = (36.0, 36.0, 36.0)

# Camera placed at Frame 50 relative offset:
# At frame 50, UAV was at (-18911, 7841, 5756), Cam was at (-19335, 7234, 5836)
# Offset = (-424, -607, +80)
cam.location = uav_pos + mathutils.Vector((-424.0, -607.0, 140.0))
look_target = uav_pos + mathutils.Vector((50.0, 50.0, 20.0))
cam_dir = (look_target - cam.location).normalized()
cam.rotation_euler = cam_dir.to_track_quat('-Z', 'Y').to_euler()

scene = bpy.context.scene
scene.camera = cam
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = 'e:/backup-llm/backup-no-llm/3d_engine/scratch/flipped_180_test.png'

bpy.ops.render.render(write_still=True)
print(">>> RENDER SAVED: e:/backup-llm/backup-no-llm/3d_engine/scratch/flipped_180_test.png <<<")
