import bpy

dem = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
print("Current modifiers:", [(m.name, m.type) for m in dem.modifiers])

# Let's inspect Weighted_Normal
wn = dem.modifiers.get('Weighted_Normal')
if wn:
    print("Weighted normal props: mode=", wn.mode, "weight=", wn.weight, "keep_sharp=", wn.keep_sharp)

# Sun shadow cascade test
sun = bpy.data.objects.get('Sun_TopGun')
s = sun.data
s.shadow_cascade_max_distance = 18000.0   # 18km shadow distance for Himalayan scale
s.shadow_cascade_count = 4
s.use_shadow_jitter = True
s.shadow_filter_radius = 2.5
s.angle = 0.035 # ~2 degrees soft sun

print("Updated sun shadow max_distance to 18,000m!")
