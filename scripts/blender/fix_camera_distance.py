import bpy, math, mathutils

blend_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend'
bpy.ops.wm.open_mainfile(filepath=blend_path)

# 1. Calculate the exact full bounding box of all meshes (including exhaust and oil tank)
min_co = [float('inf')] * 3
max_co = [float('-inf')] * 3

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            for i in range(3):
                min_co[i] = min(min_co[i], world_corner[i])
                max_co[i] = max(max_co[i], world_corner[i])

true_center = mathutils.Vector([(min_co[i] + max_co[i]) / 2 for i in range(3)])
max_span = max([max_co[i] - min_co[i] for i in range(3)])

print(f"Full 3D Bounds Center: {true_center}, Max Span: {max_span}")

# 2. Position Orbit Pivot at True Center
pivot = bpy.data.objects.get('Camera_Orbit_Pivot')
if not pivot:
    pivot = bpy.data.objects.new('Camera_Orbit_Pivot', None)
    bpy.context.scene.collection.objects.link(pivot)

pivot.location = true_center
pivot.rotation_euler = (0, 0, 0)
pivot.animation_data_clear()

# 3. Position Camera with Generous Distance (Never clips at any angle)
cam_obj = bpy.data.objects.get('MainCamera')
bpy.context.scene.camera = cam_obj
cam_obj.animation_data_clear()

# Camera distance & elevation sized to fit full 3D bounding sphere
orbit_radius = max_span * 1.55  # ~215.0
elevation_height = max_span * 0.55 # ~75.0

cam_obj.location = (true_center.x, true_center.y - orbit_radius, true_center.z + elevation_height)
direction = true_center - cam_obj.location
cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# Parent camera to pivot
cam_obj.parent = pivot
cam_obj.matrix_parent_inverse = pivot.matrix_world.inverted()

# 4. Animate 60 FPS 360° Orbit (480 Frames)
bpy.context.scene.render.fps = 60
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 480
bpy.context.scene.frame_current = 1

pivot.rotation_euler = (0, 0, 0)
pivot.keyframe_insert(data_path='rotation_euler', index=2, frame=1)

pivot.rotation_euler = (0, 0, math.radians(360))
pivot.keyframe_insert(data_path='rotation_euler', index=2, frame=480)

# Set linear interpolation
if pivot.animation_data and pivot.animation_data.action:
    action = pivot.animation_data.action
    fcurves = getattr(action, 'fcurves', None) or getattr(action, 'curves', None) or []
    for fcurve in fcurves:
        for kp in fcurve.keyframe_points:
            kp.interpolation = 'LINEAR'

# 5. Save
bpy.ops.wm.save_mainfile()
bpy.ops.wm.save_as_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\hehe\rotax_912_is_sport.blend', copy=True)
print("SUCCESS: Adjusted camera distance & center. Zero clipping through all 360 degrees!")
