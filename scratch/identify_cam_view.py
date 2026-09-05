import bpy
import mathutils

uav = bpy.data.objects.get('UAV_Predator_Master')
obj18 = bpy.data.objects.get('Object_18')
obj26 = bpy.data.objects.get('Object_26')

# In camera_test.png, what vertex is closest to the camera?
cam = bpy.data.objects.get('Camera_UAV_Chase')
cam_pos = cam.location

print(f"Cam location: {cam_pos}")

# For all meshes in UAV, let's find the closest vertex to the camera:
closest_dist = float('inf')
closest_vert_world = None
closest_mesh = None

for mo in [o for o in uav.children_recursive if o.type == 'MESH']:
    for v in mo.data.vertices:
        w_co = mo.matrix_world @ v.co
        d = (w_co - cam_pos).length
        if d < closest_dist:
            closest_dist = d
            closest_vert_world = w_co
            closest_mesh = mo.name

print(f"Closest mesh to camera: {closest_mesh} at dist={closest_dist:.1f} BU")
print(f"World coord of closest vertex: {closest_vert_world}")
# Relative to uav_pos:
uav_pos = uav.location
rel = closest_vert_world - uav_pos
print(f"Relative to UAV location: ({rel.x:.1f}, {rel.y:.1f}, {rel.z:.1f})")

# Let's find the farthest vertex:
farthest_dist = 0
farthest_mesh = None
farthest_vert_world = None
for mo in [o for o in uav.children_recursive if o.type == 'MESH']:
    for v in mo.data.vertices:
        w_co = mo.matrix_world @ v.co
        d = (w_co - cam_pos).length
        if d > farthest_dist:
            farthest_dist = d
            farthest_vert_world = w_co
            farthest_mesh = mo.name

print(f"Farthest mesh from camera: {farthest_mesh} at dist={farthest_dist:.1f} BU")
print(f"World coord of farthest vertex: {farthest_vert_world}")
rel_far = farthest_vert_world - uav_pos
print(f"Relative to UAV location: ({rel_far.x:.1f}, {rel_far.y:.1f}, {rel_far.z:.1f})")
