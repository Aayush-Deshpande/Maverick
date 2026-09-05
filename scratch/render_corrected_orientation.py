import bpy
import mathutils

uav = bpy.data.objects.get('UAV_Predator_Master')
cam = bpy.data.objects.get('Camera_UAV_Chase')

uav_pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))
# Flight direction along canyon: towards (+X, +Y)
fwd = mathutils.Vector((1.0, 1.0, 0.0)).normalized()
up = mathutils.Vector((0.0, 0.0, 1.0))

# To make the NOSE point in flight direction `fwd`:
# Since the raw mesh had nose facing backwards, we invert the mesh forward axis:
# mesh_fwd = -fwd:
mesh_fwd = -fwd
mesh_right = mesh_fwd.cross(up).normalized()
mesh_up = mesh_right.cross(mesh_fwd).normalized()

rot_mat = mathutils.Matrix((mesh_right, mesh_fwd, mesh_up)).transposed()
uav.matrix_world = mathutils.Matrix.Translation(uav_pos) @ rot_mat.to_4x4() @ mathutils.Matrix.Diagonal((36.0, 36.0, 36.0, 1.0))

# Camera is behind the flight direction (behind the tail):
cam_pos = uav_pos - fwd * 480.0 + up * 140.0
look_target = uav_pos + fwd * 60.0 + up * 15.0
cam_dir = (look_target - cam_pos).normalized()
cam.location = cam_pos
cam.rotation_euler = cam_dir.to_track_quat('-Z', 'Y').to_euler()

scene = bpy.context.scene
scene.camera = cam
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = 'e:/backup-llm/backup-no-llm/3d_engine/scratch/hero_chase_corrected.png'

bpy.ops.render.render(write_still=True)
print(">>> RENDER SAVED: e:/backup-llm/backup-no-llm/3d_engine/scratch/hero_chase_corrected.png <<<")
