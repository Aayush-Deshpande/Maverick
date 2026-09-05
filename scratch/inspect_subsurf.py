import sys
import bpy

dem = bpy.data.objects.get("Copernicus_DSM_COG_10_N34_00_E077_00_DEM")
sub = dem.modifiers.get("Subsurf_Smooth")
print(f"Subsurf levels: {sub.levels}, render_levels={sub.render_levels}")
