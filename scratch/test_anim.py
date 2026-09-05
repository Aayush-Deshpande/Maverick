import bpy
import mathutils

uav = bpy.data.objects.get('UAV_Predator_Master')
cam = bpy.data.objects.get('Camera_UAV_Chase')
dem = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')

print("--- EVALUATING FRAMES ---")
for f in [1, 50, 100, 200, 260, 300, 400, 460, 500, 600, 700, 800, 820, 900, 1000, 1100, 1200]:
    bpy.context.scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    u_eval = uav.evaluated_get(dg)
    c_eval = cam.evaluated_get(dg)
    
    # raycast down to dem
    orig = u_eval.location.copy()
    orig.z = 10000.0
    # In object local coords for dem:
    orig_local = dem.matrix_world.inverted() @ orig
    dir_local = dem.matrix_world.inverted().to_3x3() @ mathutils.Vector((0, 0, -1))
    hit, loc, norm, idx = dem.ray_cast(orig_local, dir_local)
    if hit:
        loc_world = dem.matrix_world @ loc
        terr_z = loc_world.z
        agl = u_eval.location.z - terr_z
    else:
        terr_z = 0.0
        agl = 0.0
    
    # Check forward vector of UAV:
    # Let's see what direction UAV moves from frame f to f+1
    bpy.context.scene.frame_set(f + 1)
    dg2 = bpy.context.evaluated_depsgraph_get()
    u_next = uav.evaluated_get(dg2)
    vel = u_next.location - u_eval.location
    bpy.context.scene.frame_set(f)
    
    # Check camera vector relative to UAV
    cam_offset = c_eval.location - u_eval.location
    
    print(f"F{f:4d}: UAV=({u_eval.location.x:7.0f},{u_eval.location.y:7.0f},{u_eval.location.z:5.0f}) TerrZ={terr_z:5.0f} AGL={agl:5.0f} | Vel=({vel.x:5.1f},{vel.y:5.1f},{vel.z:5.1f}) | CamOff=({cam_offset.x:6.0f},{cam_offset.y:6.0f},{cam_offset.z:5.0f})")
