import bpy
import mathutils

uav = bpy.data.objects.get('UAV_Predator_Master')
cam = bpy.data.objects.get('Camera_UAV_Chase')

print("--- ORIGINAL BAKED ANIMATION ROTATIONS ---")
for f in [1, 100, 300, 500, 700, 900, 1100]:
    bpy.context.scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    u_eval = uav.evaluated_get(dg)
    c_eval = cam.evaluated_get(dg)
    
    # Calculate velocity vector from f to f+1:
    bpy.context.scene.frame_set(f + 1)
    dg2 = bpy.context.evaluated_depsgraph_get()
    u_next = uav.evaluated_get(dg2)
    vel = (u_next.location - u_eval.location).normalized()
    bpy.context.scene.frame_set(f)
    
    # What direction was the UAV nose pointing in world space at frame f?
    # Nose is local +Y:
    nose_dir = (u_eval.matrix_world.to_3x3() @ mathutils.Vector((0, 1, 0))).normalized()
    
    # Dot product between velocity and nose direction:
    alignment = vel.dot(nose_dir)
    
    print(f"F{f:4d}: Rot={u_eval.rotation_euler} | Vel=({vel.x:.2f},{vel.y:.2f},{vel.z:.2f}) | Nose=({nose_dir.x:.2f},{nose_dir.y:.2f},{nose_dir.z:.2f}) | Dot={alignment:.2f}")
