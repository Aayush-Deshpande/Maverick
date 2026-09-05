import bpy

# Let's inspect the original GLTF file or the mesh vertices
# Let's find the camera/sensor ball and propeller!
uav = bpy.data.objects.get('UAV_Predator_Master')
for mo in [o for o in uav.children_recursive if o.type == 'MESH']:
    verts = [mo.matrix_world @ v.co for v in mo.data.vertices]
    # In world space at frame 1:
    avg_y = sum(v.y for v in verts) / len(verts)
    print(f"{mo.name}: {len(verts)} verts, Y center = {avg_y:.1f}")
