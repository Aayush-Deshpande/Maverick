import bpy

uav = bpy.data.objects.get("UAV_Predator_Master")

def print_descendants(obj, indent=0):
    for c in obj.children:
        print("  " * indent + f"Object: {c.name}, type: {c.type}, dims: {c.dimensions}")
        if c.type == 'MESH':
            xs = [v.co.x for v in c.data.vertices]
            ys = [v.co.y for v in c.data.vertices]
            zs = [v.co.z for v in c.data.vertices]
            print("  " * indent + f"  Mesh vertex extent: X=[{min(xs):.2f}, {max(xs):.2f}], Y=[{min(ys):.2f}, {max(ys):.2f}], Z=[{min(zs):.2f}, {max(zs):.2f}]")
        print_descendants(c, indent + 1)

if uav:
    print_descendants(uav)
