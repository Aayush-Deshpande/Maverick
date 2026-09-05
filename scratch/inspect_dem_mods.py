import sys
import bpy

dem = bpy.data.objects.get("Copernicus_DSM_COG_10_N34_00_E077_00_DEM")
print("Modifiers on DEM:")
for mod in dem.modifiers:
    print(f"  {mod.name}: type={mod.type}")
    if mod.type == 'DISPLACE':
        print(f"    texture={mod.texture}, strength={mod.strength}, mid_level={mod.mid_level}")
