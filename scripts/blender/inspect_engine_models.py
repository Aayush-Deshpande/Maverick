import bpy
import mathutils

def inspect_blend(name):
    print(f"\n=================== {name} ===================")
    print("Collections:", [c.name for c in bpy.data.collections])
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    print(f"Total Mesh Objects: {len(meshes)}")
    
    if not meshes:
        return
        
    min_c = mathutils.Vector((float('inf'), float('inf'), float('inf')))
    max_c = mathutils.Vector((float('-inf'), float('-inf'), float('-inf')))
    
    for o in meshes:
        if o.name == 'Plane001': # Ground plane in 915
            continue
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c)
            min_c.x = min(min_c.x, w.x)
            min_c.y = min(min_c.y, w.y)
            min_c.z = min(min_c.z, w.z)
            max_c.x = max(max_c.x, w.x)
            max_c.y = max(max_c.y, w.y)
            max_c.z = max(max_c.z, w.z)
            
    print(f"BBox Min:    {min_c}")
    print(f"BBox Max:    {max_c}")
    print(f"Center:      {(min_c + max_c) * 0.5}")
    print(f"Dimensions:  {max_c - min_c}")
    print(f"Materials:   {len(bpy.data.materials)} ({[m.name for m in bpy.data.materials[:10]]}...)")

if __name__ == "__main__":
    inspect_blend("CURRENT OPEN FILE")
