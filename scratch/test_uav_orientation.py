import bpy
import mathutils

uav = bpy.data.objects.get('UAV_Predator_Master')

print("--- UAV HIERARCHY AND BOUNDS ---")
mesh_objs = [o for o in uav.children_recursive if o.type == 'MESH']
for mo in mesh_objs:
    # get bounding box in UAV local space
    mat = uav.matrix_world.inverted() @ mo.matrix_world
    bb = [mat @ mathutils.Vector(b) for b in mo.bound_box]
    xs = [b.x for b in bb]
    ys = [b.y for b in bb]
    zs = [b.z for b in bb]
    print(f"Mesh {mo.name}: X=[{min(xs):.1f}, {max(xs):.1f}] Y=[{min(ys):.1f}, {max(ys):.1f}] Z=[{min(zs):.1f}, {max(zs):.1f}]")

# Now let's see which end is the propeller and which end is the nose!
# Let's inspect object names:
for o in uav.children_recursive:
    print(f"Child: {o.name} (type={o.type})")
