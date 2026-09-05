import bpy

cam = bpy.data.objects.get('Camera_UAV_Chase')
fp = bpy.data.objects.get('FlightPath_Canyon_Corridor')

print("Before:")
print("  CAM constraints:", [c.name for c in cam.constraints])
print("  FP hide:", fp.hide_viewport)

# Hide the curve object
fp.hide_viewport = True
fp.hide_render = True

# Remove all constraints on the camera (we drive camera rotation directly in code!)
cam.constraints.clear()

print("After:")
print("  CAM constraints:", [c.name for c in cam.constraints])
print("  FP hide:", fp.hide_viewport)
print(">>> DOTTED LINE SOURCES REMOVED SUCCESSFULLY! <<<")
