import sys
import bpy

dem = bpy.data.objects.get("Copernicus_DSM_COG_10_N34_00_E077_00_DEM")
mod = dem.modifiers.get("DEM")
tex = mod.texture
img = tex.image
print(f"Texture image: {img.name}, size={img.size[0]}x{img.size[1]}, channels={img.channels}")
print(f"Filepath: {img.filepath}")
