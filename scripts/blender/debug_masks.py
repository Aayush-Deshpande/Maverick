import bpy
import os

terrain = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
mat = terrain.material_slots[0].material
nodes = mat.node_tree.nodes
links = mat.node_tree.links

bsdf = nodes.get('Principled BSDF')
me = nodes.get('Math_Elevation_Mask')
ms = nodes.get('Math_Slope_Mask')

scene = bpy.context.scene
scene.render.resolution_x = 960
scene.render.resolution_y = 540
cam_recon = bpy.data.objects.get('Camera_Canyon_Recon')
scene.camera = cam_recon

# 1. Test Elevation Mask alone
links.new(me.outputs['Value'], bsdf.inputs['Base Color'])
out_elev = os.path.abspath(r'e:\TalentForge\Clay\3d_engine\renders\debug_elev_mask.png')
scene.render.filepath = out_elev
bpy.ops.render.render(write_still=True)
print("[OK] Rendered debug_elev_mask.png")

# 2. Test Slope Mask alone
links.new(ms.outputs['Value'], bsdf.inputs['Base Color'])
out_slope = os.path.abspath(r'e:\TalentForge\Clay\3d_engine\renders\debug_slope_mask.png')
scene.render.filepath = out_slope
bpy.ops.render.render(write_still=True)
print("[OK] Rendered debug_slope_mask.png")
