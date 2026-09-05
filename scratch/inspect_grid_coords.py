import sys
import bpy
import numpy as np

dem = bpy.data.objects.get("Copernicus_DSM_COG_10_N34_00_E077_00_DEM")
mesh = dem.data

# Read first 10 vertices
verts = mesh.vertices
print(f"Vertex 0: {verts[0].co}")
print(f"Vertex 1: {verts[1].co}")
print(f"Vertex 899: {verts[899].co}")
print(f"Vertex 900: {verts[900].co}")
print(f"Vertex 809999: {verts[809999].co}")
