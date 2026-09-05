import bpy
import mathutils

cam = bpy.data.objects.get('Camera_UAV_Chase')
uav = bpy.data.objects.get('UAV_Predator_Master')

uav_pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))
fwd = mathutils.Vector((1.0, 1.0, 0.0)).normalized()
up = mathutils.Vector((0.0, 0.0, 1.0))
tail_dir = -fwd

cam_pos = uav_pos + tail_dir * 550.0 + up * 160.0
look_target = uav_pos + fwd * 80.0 + up * 20.0
cam_dir = (look_target - cam_pos).normalized()
cam_quat = cam_dir.to_track_quat('-Z', 'Y')

print(f"UAV pos: {uav_pos}")
print(f"Cam pos: {cam_pos}")
print(f"Cam distance to UAV: {(cam_pos - uav_pos).length:.1f} BU")
print(f"Cam Euler: {cam_quat.to_euler()}")

# Check that camera is BEHIND the UAV (cam.x < uav.x and cam.y < uav.y since fwd is +X, +Y):
assert cam_pos.x < uav_pos.x, "Cam is not behind in X!"
assert cam_pos.y < uav_pos.y, "Cam is not behind in Y!"
assert cam_pos.z > uav_pos.z, "Cam is not above UAV!"
print(">>> CHASE CAMERA GEOMETRY VERIFIED PERFECTLY! <<<")
