import bpy, math, mathutils

blend_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend'
bpy.ops.wm.open_mainfile(filepath=blend_path)

# 1. Set 90 FPS & 8-Second Timeline (720 Frames)
bpy.context.scene.render.fps = 90
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 720
bpy.context.scene.frame_current = 1

# 2. Find Engine Center & Ensure Engine is Stationary
master_engine = bpy.data.objects.get('Master_Engine_Controller')
if master_engine:
    master_engine.animation_data_clear()
    master_engine.rotation_euler = (0, 0, 0)
    center = master_engine.location
else:
    center = mathutils.Vector((0.966, 30.824, -17.662))

# 3. Create or Reset Camera Orbit Pivot Empty at Engine Center
pivot = bpy.data.objects.get('Camera_Orbit_Pivot')
if not pivot:
    pivot = bpy.data.objects.new('Camera_Orbit_Pivot', None)
    pivot.empty_display_type = 'PLAIN_AXES'
    pivot.empty_display_size = 15.0
    bpy.context.scene.collection.objects.link(pivot)

pivot.location = center
pivot.rotation_euler = (0, 0, 0)
pivot.animation_data_clear()

# 4. Set Up Camera at Elevated 3D Angle
cam_obj = bpy.data.objects.get('MainCamera')
if not cam_obj:
    cam_data = bpy.data.cameras.new('MainCamera')
    cam_obj = bpy.data.objects.new('MainCamera', cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)

bpy.context.scene.camera = cam_obj
cam_obj.animation_data_clear()

# Elevated 3D camera offset (distance and height calibrated for full engine + oil tank framing)
radius = 160.0
height = 65.0
cam_obj.location = (center.x, center.y - radius, center.z + height)

# Point camera directly at the engine center
direction = center - cam_obj.location
rot_quat = direction.to_track_quat('-Z', 'Y')
cam_obj.rotation_euler = rot_quat.to_euler()

# 5. Parent Camera to Orbit Pivot
cam_obj.parent = pivot
cam_obj.matrix_parent_inverse = pivot.matrix_world.inverted()

# 6. Animate Camera Orbit (0 to 360 Degrees at 90 FPS)
pivot.rotation_euler = (0, 0, 0)
pivot.keyframe_insert(data_path='rotation_euler', index=2, frame=1)

pivot.rotation_euler = (0, 0, math.radians(360))
pivot.keyframe_insert(data_path='rotation_euler', index=2, frame=720)

# Set Linear Interpolation for seamless infinite loop
if pivot.animation_data and pivot.animation_data.action:
    for fcurve in pivot.animation_data.action.fcurves:
        for kp in fcurve.keyframe_points:
            kp.interpolation = 'LINEAR'

# 7. Configure Viewports to Camera View + Rendered Shading
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'CAMERA'
                    space.shading.type = 'RENDERED'
                    space.shading.use_scene_lights = True
                    space.shading.use_scene_world = True
                    space.clip_start = 0.1
                    space.clip_end = 1000.0

# 8. Save
bpy.ops.wm.save_mainfile()
bpy.ops.wm.save_as_mainfile(filepath=r'E:\TalentForge\Clay\3d_engine\hehe\rotax_912_is_sport.blend', copy=True)
print("SUCCESS: Configured 90 FPS 360° Camera Orbit Animation centered on stationary engine!")
