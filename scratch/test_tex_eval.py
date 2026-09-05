import sys
import bpy

dem = bpy.data.objects.get("Copernicus_DSM_COG_10_N34_00_E077_00_DEM")
mod = dem.modifiers.get("DEM")
print("DEM Modifier Strength:", mod.strength)
print("DEM Modifier Midlevel:", mod.mid_level)
print("Texture Type:", mod.texture.type)

# Test raycast at (-20500, 11500)
loc_origin = dem.matrix_world.inverted() @ bpy.path.mathutils.Vector((-20500, 11500, 6500)) if hasattr(bpy.path, 'mathutils') else None
import mathutils
inv = dem.matrix_world.inverted()
hit, loc, norm, _ = dem.ray_cast(inv @ mathutils.Vector((-20500, 11500, 6500)), mathutils.Vector((0, 0, -1)), distance=6000)
print(f"Raycast at (-20500, 11500): hit={hit}, World Z={(dem.matrix_world @ loc).z if hit else None}")
