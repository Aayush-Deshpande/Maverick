import bpy

uav = bpy.data.objects.get('UAV_Predator_Master')
mesh_objs = [o for o in uav.children_recursive if o.type == 'MESH']
for mo in mesh_objs:
    mats = [m.name for m in mo.data.materials if m]
    print(f"Mesh {mo.name}: mats={mats}")
