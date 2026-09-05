import bpy
import math

# 1. Configure EEVEE-Next Raytracing & GI
eevee = bpy.context.scene.eevee
eevee.use_raytracing = True
eevee.ray_tracing_method = 'SCREEN'
eevee.fast_gi_method = 'GLOBAL_ILLUMINATION'
eevee.fast_gi_quality = 1.0
eevee.fast_gi_ray_count = 8
eevee.use_shadows = True
eevee.shadow_resolution_scale = 1.0
eevee.shadow_ray_count = 8

# Color management: AgX or Filmic with high dynamic range
scene = bpy.context.scene
scene.view_settings.view_transform = 'AgX' if 'AgX' in [c.name for c in bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
scene.view_settings.look = 'High Contrast'
scene.view_settings.exposure = 0.2

# 2. Configure World: Clean Nishita Atmosphere
w = bpy.data.worlds.get('W_Tactical_Mountain')
if not w:
    w = bpy.data.worlds.new('W_Tactical_Mountain')
scene.world = w
w.use_nodes = True
tree_w = w.node_tree
tree_w.nodes.clear()

out_w = tree_w.nodes.new('ShaderNodeOutputWorld')
bg_w = tree_w.nodes.new('ShaderNodeBackground')
sky_w = tree_w.nodes.new('ShaderNodeTexSky')
sky_w.sky_type = 'MULTIPLE_SCATTERING'
sky_w.sun_elevation = math.radians(32.0)  # Dramatic late-afternoon sun
sky_w.sun_rotation = math.radians(115.0)  # Sun casting deep shadows across the canyon axis
sky_w.altitude = 4500.0                   # High altitude Ladakh atmosphere
sky_w.air_density = 0.55
sky_w.aerosol_density = 0.25
sky_w.ozone_density = 2.2
sky_w.sun_disc = True

bg_w.inputs['Strength'].default_value = 1.2
tree_w.links.new(sky_w.outputs['Color'], bg_w.inputs['Color'])
tree_w.links.new(bg_w.outputs['Background'], out_w.inputs['Surface'])

# 3. Configure Sun Light: Single Cinematic Directional Key Light
# Remove conflicting secondary sun
sun_old = bpy.data.objects.get('Sun')
if sun_old:
    sun_old.hide_viewport = True
    sun_old.hide_render = True
    sun_old.data.energy = 0.0

sun_top = bpy.data.objects.get('Sun_TopGun')
if sun_top:
    sun_top.rotation_euler = (math.radians(58.0), math.radians(12.0), math.radians(115.0))
    sun_top.data.energy = 6.5
    sun_top.data.color = (1.0, 0.96, 0.88)  # Warm golden Himalayan sunlight
    sun_top.data.angle = math.radians(2.0)   # Soft realistic sun shadow penumbra

# 4. Build Photorealistic Himalayan Terrain Shader
mat = bpy.data.materials.get('M_TopGun_Canyon_Simulation')
if not mat:
    mat = bpy.data.materials.new('M_TopGun_Canyon_Simulation')
mat.use_nodes = True
tree_m = mat.node_tree
tree_m.nodes.clear()

# Nodes
node_out = tree_m.nodes.new('ShaderNodeOutputMaterial')
node_bsdf = tree_m.nodes.new('ShaderNodeBsdfPrincipled')
node_geom = tree_m.nodes.new('ShaderNodeNewGeometry')
node_pos_xyz = tree_m.nodes.new('ShaderNodeSeparateXYZ')
node_norm_xyz = tree_m.nodes.new('ShaderNodeSeparateXYZ')

# Connect position and normal
tree_m.links.new(node_geom.outputs['Position'], node_pos_xyz.inputs['Vector'])
tree_m.links.new(node_geom.outputs['Normal'], node_norm_xyz.inputs['Vector'])

# A. Elevation Mapping (Z: 2,900m to 7,600m)
node_elev_map = tree_m.nodes.new('ShaderNodeMapRange')
node_elev_map.inputs['From Min'].default_value = 3000.0
node_elev_map.inputs['From Max'].default_value = 7200.0
node_elev_map.inputs['To Min'].default_value = 0.0
node_elev_map.inputs['To Max'].default_value = 1.0
tree_m.links.new(node_pos_xyz.outputs['Z'], node_elev_map.inputs['Value'])

# B. Multi-Strata Rock Gradient (Valley floor -> Sandstone -> Slate -> Granite)
node_rock_ramp = tree_m.nodes.new('ShaderNodeValToRGB')
cr = node_rock_ramp.color_ramp
cr.color_mode = 'RGB'
cr.interpolation = 'LINEAR'
cr.elements[0].position = 0.0
cr.elements[0].color = (0.35, 0.28, 0.20, 1.0)   # Alluvial valley floor silt & warm ochre
cr.elements[1].position = 1.0
cr.elements[1].color = (0.25, 0.26, 0.28, 1.0)   # High crag weathered stone
e1 = cr.elements.new(0.35)
e1.color = (0.28, 0.18, 0.13, 1.0)   # Red sandstone & ironstone strata
e2 = cr.elements.new(0.65)
e2.color = (0.20, 0.19, 0.18, 1.0)   # Dark granite slate rock
tree_m.links.new(node_elev_map.outputs['Result'], node_rock_ramp.inputs['Fac'])

# C. Detail Noise Texture for Rock Stratification and Crevices
node_noise = tree_m.nodes.new('ShaderNodeTexNoise')
node_noise.inputs['Scale'].default_value = 0.005
node_noise.inputs['Detail'].default_value = 8.0
node_noise.inputs['Roughness'].default_value = 0.65
node_noise.inputs['Distortion'].default_value = 0.5
tree_m.links.new(node_geom.outputs['Position'], node_noise.inputs['Vector'])

# Mix rock color with subtle geological noise variation
node_rock_mix = tree_m.nodes.new('ShaderNodeMix')
node_rock_mix.data_type = 'RGBA'
node_rock_mix.blend_type = 'MULTIPLY'
node_rock_mix.inputs['Factor'].default_value = 0.35
tree_m.links.new(node_noise.outputs['Color'], node_rock_mix.inputs['B'])
tree_m.links.new(node_rock_ramp.outputs['Color'], node_rock_mix.inputs['A'])

# D. Snow Coverage Mask (Slope + Elevation)
# Slope mask: Normal.Z > 0.65 (slopes gentler than ~45 deg hold snow)
node_slope_math = tree_m.nodes.new('ShaderNodeMath')
node_slope_math.operation = 'SMOOTH_MIN'
node_slope_math.inputs[1].default_value = 1.0

# Elevation threshold for snow: Snow line in Ladakh is ~5,100m
node_snow_elev = tree_m.nodes.new('ShaderNodeMapRange')
node_snow_elev.inputs['From Min'].default_value = 4900.0
node_snow_elev.inputs['From Max'].default_value = 6200.0
tree_m.links.new(node_pos_xyz.outputs['Z'], node_snow_elev.inputs['Value'])

# Combine: Snow Factor = Elevation * Slope
node_snow_mult = tree_m.nodes.new('ShaderNodeMath')
node_snow_mult.operation = 'MULTIPLY'
tree_m.links.new(node_snow_elev.outputs['Result'], node_snow_mult.inputs[0])
tree_m.links.new(node_norm_xyz.outputs['Z'], node_snow_mult.inputs[1])

# High contrast snow mask
node_snow_ramp = tree_m.nodes.new('ShaderNodeValToRGB')
crs = node_snow_ramp.color_ramp
crs.elements[0].position = 0.32
crs.elements[0].color = (0.0, 0.0, 0.0, 1.0)
crs.elements[1].position = 0.55
crs.elements[1].color = (1.0, 1.0, 1.0, 1.0)
tree_m.links.new(node_snow_mult.outputs['Value'], node_snow_ramp.inputs['Fac'])

# Pure Himalayan glacial snow color
node_snow_col = tree_m.nodes.new('ShaderNodeRGB')
node_snow_col.outputs['Color'].default_value = (0.92, 0.94, 0.99, 1.0)

# Final Mix: Rock + Glacial Snow
node_final_mix = tree_m.nodes.new('ShaderNodeMix')
node_final_mix.data_type = 'RGBA'
node_final_mix.blend_type = 'MIX'
tree_m.links.new(node_snow_ramp.outputs['Color'], node_final_mix.inputs['Factor'])
tree_m.links.new(node_rock_mix.outputs['Result'], node_final_mix.inputs['A'])
tree_m.links.new(node_snow_col.outputs['Color'], node_final_mix.inputs['B'])

# Roughness: Rock is rough (0.88), Snow is smooth/reflective (0.38)
node_rough_mix = tree_m.nodes.new('ShaderNodeMix')
node_rough_mix.data_type = 'FLOAT'
node_rough_mix.inputs['A'].default_value = 0.88
node_rough_mix.inputs['B'].default_value = 0.38
tree_m.links.new(node_snow_ramp.outputs['Color'], node_rough_mix.inputs['Factor'])

# Bump Normal for realistic rock crags
node_bump = tree_m.nodes.new('ShaderNodeBump')
node_bump.inputs['Strength'].default_value = 0.35
node_bump.inputs['Distance'].default_value = 15.0
tree_m.links.new(node_noise.outputs['Fac'], node_bump.inputs['Height'])

# Connect to Principled BSDF
tree_m.links.new(node_final_mix.outputs['Result'], node_bsdf.inputs['Base Color'])
tree_m.links.new(node_rough_mix.outputs['Result'], node_bsdf.inputs['Roughness'])
tree_m.links.new(node_bump.outputs['Normal'], node_bsdf.inputs['Normal'])
tree_m.links.new(node_bsdf.outputs['BSDF'], node_out.inputs['Surface'])

print(">>> Photorealistic Himalayan Terrain Shader Configured! <<<")

# Save a test render frame to verify visually
cam = bpy.data.objects.get('Camera_UAV_Chase')
uav = bpy.data.objects.get('UAV_Predator_Master')
scene.camera = cam
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.filepath = "e:/backup-llm/backup-no-llm/3d_engine/scratch/photoreal_terrain_test.png"
bpy.ops.render.render(write_still=True)
print(">>> Rendered test frame saved to scratch/photoreal_terrain_test.png <<<")
