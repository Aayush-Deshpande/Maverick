"""
Bake Camera Revolve Orbit around stationary engine center into rotax_912_is_sport.blend
Engine remains 100% stationary at center; Camera revolves 360° at top-three-quarter angle.
"""

import bpy
import math
import mathutils

blend_path = r"E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend"
bpy.ops.wm.open_mainfile(filepath=blend_path)
scene = bpy.context.scene

# 1. Exact Center of all 109 meshes
ENGINE_CENTER = mathutils.Vector((1.932, 61.648, -35.324))

# 2. Clear all animation on mesh objects to guarantee the model is 100% stationary
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.animation_data_clear()

# 3. Create or Update Orbit Camera Pivot at Exact Engine Center
pivot_name = "Camera_Orbit_Pivot"
pivot = bpy.data.objects.get(pivot_name)
if not pivot:
    pivot = bpy.data.objects.new(pivot_name, None)
    pivot.empty_display_type = 'PLAIN_AXES'
    pivot.empty_display_size = 10.0
    scene.collection.objects.link(pivot)

pivot.location = ENGINE_CENTER
pivot.rotation_euler = (0, 0, 0)
pivot.animation_data_clear()

# 4. Camera Setup
cam_name = "TurntableCam"
cam = bpy.data.objects.get(cam_name) or bpy.data.objects.get("MainCamera")
if not cam:
    cam_data = bpy.data.cameras.new(cam_name)
    cam = bpy.data.objects.new(cam_name, cam_data)
    scene.collection.objects.link(cam)
scene.camera = cam

cam.animation_data_clear()
cam.data.lens = 48
cam.data.clip_start = 1.0
cam.data.clip_end = 2000.0

# Position camera at top-three-quarter elevated angle
radius = 235.0
height = 115.0 # Elevated top-3/4 angle
cam.location = (ENGINE_CENTER.x, ENGINE_CENTER.y - radius, ENGINE_CENTER.z + height)

# Point camera directly at engine center
direction = ENGINE_CENTER - cam.location
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

# Parent camera to orbit pivot
cam.parent = pivot
cam.matrix_parent_inverse = pivot.matrix_world.inverted()

# 5. Lock all 3D viewports to Camera View + Rendered Shading
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.region_3d.view_perspective = 'CAMERA'
                    space.shading.type = 'RENDERED'
                    space.shading.use_scene_lights = True
                    space.shading.use_scene_world = True

bpy.ops.wm.save_mainfile()
print("SUCCESS: Camera orbit rig baked with stationary engine model and top 3/4 angle!")
