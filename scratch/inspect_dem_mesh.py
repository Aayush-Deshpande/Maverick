import sys
import bpy
import numpy as np

dem = bpy.data.objects.get("Copernicus_DSM_COG_10_N34_00_E077_00_DEM")
mesh = dem.data
num_verts = len(mesh.vertices)
num_polys = len(mesh.polygons)
print(f"DEM Mesh: {num_verts} vertices, {num_polys} polygons")
print(f"Dimensions: {dem.dimensions}")
print(f"Location: {dem.location}")
