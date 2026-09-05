import bpy
import mathutils

uav = bpy.data.objects.get("UAV_Predator_Master")
print(f"UAV world scale: {uav.scale}")

# Find maximum lateral coordinate among all vertices of all descendant meshes
max_wing_x = 0.0
for c in uav.children_recursive:
    if c.type == 'MESH':
        for v in c.data.vertices:
            # transform vertex to UAV_Predator_Master local space
            world_co = c.matrix_world @ v.co
            local_co = uav.matrix_world.inverted() @ world_co
            if abs(local_co.x) > max_wing_x:
                max_wing_x = abs(local_co.x)

print(f"Max lateral semi-span in UAV local space: {max_wing_x:.2f} m")
