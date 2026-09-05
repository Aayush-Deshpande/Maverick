import bpy
import os

terrain = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
mat = terrain.material_slots[0].material
nodes = mat.node_tree.nodes
links = mat.node_tree.links

me = nodes.get('Math_Elevation_Mask')
ms = nodes.get('Math_Slope_Mask')
sm = nodes.get('Math_Snow_Mask')
bsdf = nodes.get('Principled BSDF')
mix_snow = nodes.get('Mix_Snow_Blend')

# Elevation threshold: 0.45 (top 35% of peaks above 5,035m AMSL)
me.inputs[1].default_value = 0.45

# Slope threshold: 0.15 (allows alpine ridges while excluding sheer 90 deg vertical cliff drops)
ms.inputs[1].default_value = 0.15

# Connect Mix_Snow_Blend Result_Color to Base Color
links.new(mix_snow.outputs[2], bsdf.inputs['Base Color'])

# Save to terrain.blend
bpy.ops.wm.save_mainfile()
print("[OK] Saved calibrated snow mask to Models/terrain.blend!")

scene = bpy.context.scene
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080

cam_recon = bpy.data.objects.get('Camera_Canyon_Recon')
scene.camera = cam_recon
out_recon = os.path.abspath(r'e:\TalentForge\Clay\3d_engine\renders\snow_35_calibrated_recon.png')
scene.render.filepath = out_recon
bpy.ops.render.render(write_still=True)
print("[OK] Rendered snow_35_calibrated_recon.png")

scene.frame_set(550)
cam_chase = bpy.data.objects.get('Camera_UAV_Chase')
scene.camera = cam_chase
out_chase = os.path.abspath(r'e:\TalentForge\Clay\3d_engine\renders\snow_35_calibrated_chase.png')
scene.render.filepath = out_chase
bpy.ops.render.render(write_still=True)
print("[OK] Rendered snow_35_calibrated_chase.png")
