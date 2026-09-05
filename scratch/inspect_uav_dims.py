import bpy
import mathutils

uav = bpy.data.objects.get("Tactical_UAV") or bpy.data.objects.get("UAV")
if uav:
    print(f"UAV Object name: {uav.name}")
    print(f"Dimensions: {uav.dimensions}")
    print(f"Bound box: {uav.bound_box}")
else:
    print("UAV object not found by exact name, searching objects:")
    for o in bpy.data.objects:
        if "uav" in o.name.lower() or "plane" in o.name.lower() or "drone" in o.name.lower():
            print(f"Candidate: {o.name}, dimensions: {o.dimensions}")
