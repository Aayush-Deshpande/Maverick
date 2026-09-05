import sys
import time
import bpy

dem = bpy.data.objects.get("Copernicus_DSM_COG_10_N34_00_E077_00_DEM")
mod = dem.modifiers.get("DEM")
tex = mod.texture

# Test evaluate
t0 = time.time()
for _ in range(100):
    val = tex.evaluate((0.277, 0.603, 0.0))
elapsed_us = (time.time() - t0) * 10000.0 # us per call
print(f"Texture evaluate sample: {val}, took {elapsed_us:.2f} microseconds per evaluation!")
