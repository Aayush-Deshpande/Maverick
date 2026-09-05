import bpy

uav = bpy.data.objects.get('UAV_Predator_Master')
# Let's find vertices with highest Y and lowest Y in local space
all_verts = []
for mo in [o for o in uav.children_recursive if o.type == 'MESH']:
    mat = uav.matrix_world.inverted() @ mo.matrix_world
    for v in mo.data.vertices:
        all_verts.append((mat @ v.co, mo.name))

# Sort by local Y:
all_verts.sort(key=lambda item: item[0].y)
print("Lowest 5 local Y (tail or nose?):")
for v, name in all_verts[:5]:
    print(f"  {name}: {v}")

print("Highest 5 local Y (tail or nose?):")
for v, name in all_verts[-5:]:
    print(f"  {name}: {v}")
