import bpy, math, mathutils

blend_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend'
bpy.ops.wm.open_mainfile(filepath=blend_path)

# Calculate bounding box of all meshes
min_co = [float('inf')] * 3
max_co = [float('-inf')] * 3

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            for i in range(3):
                min_co[i] = min(min_co[i], world_corner[i])
                max_co[i] = max(max_co[i], world_corner[i])

center = mathutils.Vector([(min_co[i] + max_co[i]) / 2 for i in range(3)])

# Set up pivot at true center
pivot = bpy.data.objects.get('Camera_Orbit_Pivot')
if not pivot:
    pivot = bpy.data.objects.new('Camera_Orbit_Pivot', None)
    bpy.context.scene.collection.objects.link(pivot)

pivot.location = center
pivot.rotation_euler = (0, 0, 0)
pivot.animation_data_clear()

# Camera placement with wide radius to ensure zero clipping on all 360 degrees
cam_obj = bpy.data.objects.get('MainCamera')
cam_obj.animation_data_clear()

orbit_radius = 290.0
elevation_height = 110.0

cam_obj.location = (center.x, center.y - orbit_radius, center.z + elevation_height)
direction = center - cam_obj.location
cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# Parent camera to pivot
cam_obj.parent = pivot
cam_obj.matrix_parent_inverse = pivot.matrix_world.inverted()

# Animate 60 FPS (480 Frames)
bpy.context.scene.render.fps = 60
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 480
bpy.context.scene.frame_current = 1

pivot.rotation_euler = (0, 0, 0)
pivot.keyframe_insert(data_path='rotation_euler', index=2, frame=1)

pivot.rotation_euler = (0, 0, math.radians(360))
pivot.keyframe_insert(data_path='rotation_euler', index=2, frame=480)

if pivot.animation_data and pivot.animation_data.action:
    action = pivot.animation_data.action
    fcurves = getattr(action, 'fcurves', None) or getattr(action, 'curves', None) or []
    for fcurve in fcurves:
        for kp in fcurve.keyframe_points:
            kp.interpolation = 'LINEAR'

# Save
bpy.ops.wm.save_mainfile()
bpy.ops.wm.save_as_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\hehe\rotax_912_is_sport.blend', copy=True)
print("Updated camera orbit with distance = 290.0 (wide framing).")
