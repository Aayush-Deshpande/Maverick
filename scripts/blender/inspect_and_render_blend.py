import bpy, mathutils

blend_path = r'E:\TalentForge\Clay\3d_engine\rotax_912_is_sport.blend'
bpy.ops.wm.open_mainfile(filepath=blend_path)

min_co = [float('inf')] * 3
max_co = [float('-inf')] * 3

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            for i in range(3):
                min_co[i] = min(min_co[i], world_corner[i])
                max_co[i] = max(max_co[i], world_corner[i])

print(f"Overall Bounding Box:")
print(f"Min: {min_co}")
print(f"Max: {max_co}")
print(f"Dimensions: {[max_co[i] - min_co[i] for i in range(3)]}")

# Setup Camera
cam_data = bpy.data.cameras.new('TestCam')
cam_obj = bpy.data.objects.new('TestCam', cam_data)
bpy.context.scene.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj

center = [(min_co[i] + max_co[i]) / 2 for i in range(3)]
size = max([max_co[i] - min_co[i] for i in range(3)])
print(f"Scene center: {center}, size: {size}")

cam_obj.location = (center[0] + size * 1.2, center[1] - size * 1.2, center[2] + size * 0.8)
direction = mathutils.Vector(center) - cam_obj.location
rot_quat = direction.to_track_quat('-Z', 'Y')
cam_obj.rotation_euler = rot_quat.to_euler()
cam_data.clip_end = max(10000.0, size * 10.0)

# Setup Light
light_data = bpy.data.lights.new('TestSun', 'SUN')
light_data.energy = 5.0
light_obj = bpy.data.objects.new('TestSun', light_data)
bpy.context.scene.collection.objects.link(light_obj)
light_obj.location = (center[0] + size, center[1] - size, center[2] + size * 2)

bpy.context.scene.render.resolution_x = 1024
bpy.context.scene.render.resolution_y = 768
render_out = r'E:\TalentForge\Clay\3d_engine\render_check.png'
bpy.context.scene.render.filepath = render_out

bpy.ops.render.render(write_still=True)
print(f"Rendered image saved to: {render_out}")
