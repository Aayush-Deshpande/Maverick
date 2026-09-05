import bpy

uav = bpy.data.objects.get('UAV_Predator_Master')
obj18 = bpy.data.objects.get('Object_18')
obj26 = bpy.data.objects.get('Object_26')

# Check radius in X/Z at Y = +4.0 (obj18) vs Y = -3.8 (obj26)
mat18 = uav.matrix_world.inverted() @ obj18.matrix_world
v18_tip = [mat18 @ v.co for v in obj18.data.vertices if (mat18 @ v.co).y > 4.0]
print(f"Object 18 near +4.0 Y count={len(v18_tip)}, max radial distance from axis={max((v.x**2 + v.z**2)**0.5 for v in v18_tip):.3f}")

mat26 = uav.matrix_world.inverted() @ obj26.matrix_world
v26_tip = [mat26 @ v.co for v in obj26.data.vertices if (mat26 @ v.co).y < -3.5]
print(f"Object 26 near -3.5 Y count={len(v26_tip)}, max radial distance from axis={max((v.x**2 + v.z**2)**0.5 for v in v26_tip):.3f}")

# Also check propeller: where is the 2-blade or 3-blade propeller in the model?
for mo in [o for o in uav.children_recursive if o.type == 'MESH']:
    mat = uav.matrix_world.inverted() @ mo.matrix_world
    verts = [mat @ v.co for v in mo.data.vertices]
    # propeller blades are thin, have some radius in X/Z but narrow in Y:
    y_span = max(v.y for v in verts) - min(v.y for v in verts)
    x_span = max(v.x for v in verts) - min(v.x for v in verts)
    z_span = max(v.z for v in verts) - min(v.z for v in verts)
    if y_span < 0.3 and (x_span > 0.5 or z_span > 0.5):
        print(f"PROPELLER CANDIDATE? {mo.name}: Y_center={sum(v.y for v in verts)/len(verts):.2f}, Y_span={y_span:.3f}, X_span={x_span:.3f}, Z_span={z_span:.3f}")
