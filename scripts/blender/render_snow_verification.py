import bpy
import os

scene = bpy.context.scene
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080

# 1. Render Chase Camera View (Mid Canyon)
scene.frame_set(550)
cam_chase = bpy.data.objects.get('Camera_UAV_Chase')
scene.camera = cam_chase

out_chase = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/snow_test_chase_view.png"))
scene.render.filepath = out_chase
print(f"Rendering chase camera to: {out_chase}...")
bpy.ops.render.render(write_still=True)

# 2. Render High Recon Overview (Showing mountain peaks and snowline)
cam_recon = bpy.data.objects.get('Camera_Canyon_Recon')
if cam_recon:
    scene.camera = cam_recon
    out_recon = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../renders/snow_test_recon_overview.png"))
    scene.render.filepath = out_recon
    print(f"Rendering recon overview to: {out_recon}...")
    bpy.ops.render.render(write_still=True)

# Restore chase camera as active
scene.camera = cam_chase
print("[OK] Snow verification renders complete!")
