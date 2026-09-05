import bpy
import mathutils

uav = bpy.data.objects.get('UAV_Predator_Master')
obj18 = bpy.data.objects.get('Object_18')
obj26 = bpy.data.objects.get('Object_26')

# Let's inspect the chain of parents from obj18 up to uav
curr = obj18
while curr:
    print(f"Node '{curr.name}': loc={curr.location}, rot={curr.rotation_euler}, scale={curr.scale}")
    curr = curr.parent

# Now let's calculate: where does Object_18 center lie relative to UAV_Predator_Master origin?
# Specifically, in UAV_Predator_Master local space:
mat_rel18 = uav.matrix_world.inverted() @ obj18.matrix_world
mat_rel26 = uav.matrix_world.inverted() @ obj26.matrix_world
print("Object 18 (Nose) translation relative to UAV:", mat_rel18.to_translation())
print("Object 26 (Tail) translation relative to UAV:", mat_rel26.to_translation())

# Let's test a point at local (0, 0, 0) of Object_18 vs Object_26:
pt_nose = uav.matrix_world.inverted() @ (obj18.matrix_world @ mathutils.Vector((0,0,0)))
pt_tail = uav.matrix_world.inverted() @ (obj26.matrix_world @ mathutils.Vector((0,0,0)))
print(f"Point on Nose mesh in UAV local space: {pt_nose}")
print(f"Point on Tail mesh in UAV local space: {pt_tail}")
