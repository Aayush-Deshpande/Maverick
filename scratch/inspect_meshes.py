import bpy
import mathutils

uav = bpy.data.objects.get('UAV_Predator_Master')

# Let's inspect Object_18 and Object_26 in detail:
obj18 = bpy.data.objects.get('Object_18')
obj26 = bpy.data.objects.get('Object_26')
obj40 = bpy.data.objects.get('Object_40')

print("Object 18 name/type:", obj18.name, obj18.type)
print("Object 26 name/type:", obj26.name, obj26.type)
print("Object 40 name/type:", obj40.name, obj40.type)

# What are the vertices of Object_40 (it only had 27 verts)?
mat40 = uav.matrix_world.inverted() @ obj40.matrix_world
v40 = [mat40 @ v.co for v in obj40.data.vertices]
print("Object 40 vertices:", v40[:10])

# What about the propeller? In an MQ-1, the propeller is at the back.
# Let's see all meshes and what they represent:
for mo in [o for o in uav.children_recursive if o.type == 'MESH']:
    mat = uav.matrix_world.inverted() @ mo.matrix_world
    verts = [mat @ v.co for v in mo.data.vertices]
    min_y = min(v.y for v in verts)
    max_y = max(v.y for v in verts)
    min_z = min(v.z for v in verts)
    max_z = max(v.z for v in verts)
    print(f"Mesh {mo.name:10s}: Y=[{min_y:5.2f}, {max_y:5.2f}] Z=[{min_z:5.2f}, {max_z:5.2f}]")
