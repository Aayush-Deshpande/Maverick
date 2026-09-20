import bpy
import math
import os
import shutil
import mathutils

blend_path = r"e:\backup-llm\backup-no-llm\3d_engine\3d_models\bayraktar_tb3_digital_twin.blend"
renders_dir = r"e:\backup-llm\backup-no-llm\3d_engine\3d_models\renders"
artifacts_dir = r"C:\Users\Aayush\.gemini\antigravity-ide\brain\59abf336-b0e2-4242-aa30-d1e91dfcd0a7"

bpy.ops.wm.open_mainfile(filepath=blend_path)
scene = bpy.context.scene

# Configure EEVEE
scene.render.engine = 'BLENDER_EEVEE'
if hasattr(scene, 'eevee'):
    if hasattr(scene.eevee, 'use_gtao'): scene.eevee.use_gtao = True
    if hasattr(scene.eevee, 'use_ssr'): scene.eevee.use_ssr = True

scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100

def create_or_get_cam(name, loc, tgt_loc, lens=45.0):
    cam_obj = bpy.data.objects.get(name)
    if not cam_obj:
        cam_data = bpy.data.cameras.new(name)
        cam_obj = bpy.data.objects.new(name, cam_data)
        scene.collection.objects.link(cam_obj)
    cam_obj.location = loc
    cam_obj.data.lens = lens
    cam_obj.constraints.clear()
    tgt = bpy.data.objects.get(f"Target_{name}")
    if not tgt:
        tgt = bpy.data.objects.new(f"Target_{name}", None)
        scene.collection.objects.link(tgt)
    tgt.location = tgt_loc
    tt = cam_obj.constraints.new(type='TRACK_TO')
    tt.target = tgt
    tt.track_axis = 'TRACK_NEGATIVE_Z'
    tt.up_axis = 'UP_Y'
    return cam_obj

# 1. Render Matching 82ba0fb294.jpg (Front-right 3/4 elevated perspective)
cam_82ba = create_or_get_cam("Cam_Ref_82ba", (8.2, 7.8, 4.4), (0.0, 0.4, 0.95), lens=42.0)
scene.camera = cam_82ba
out_82ba = os.path.join(renders_dir, "render_05_turbosquid_base_82ba.png")
scene.render.filepath = out_82ba
bpy.ops.render.render(write_still=True)
shutil.copy2(out_82ba, os.path.join(artifacts_dir, "render_05_turbosquid_base_82ba.png"))
print(f"Saved 82ba match: {out_82ba}")

# 2. Render Matching 9c6e6ad97d (1).jpg (Aft-starboard 3/4 tail view with PT-2 & Turkish flag)
cam_9c6e = create_or_get_cam("Cam_Ref_9c6e", (7.4, -6.8, 3.4), (0.0, -0.8, 1.2), lens=44.0)
scene.camera = cam_9c6e
out_9c6e = os.path.join(renders_dir, "render_06_starboard_flight_9c6e.png")
scene.render.filepath = out_9c6e
bpy.ops.render.render(write_still=True)
shutil.copy2(out_9c6e, os.path.join(artifacts_dir, "render_06_starboard_flight_9c6e.png"))
print(f"Saved 9c6e match: {out_9c6e}")

print("Comparison gallery renders complete!")
