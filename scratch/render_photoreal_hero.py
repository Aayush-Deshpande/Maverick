import bpy
import math
import mathutils

# 1. Enable EEVEE Raytracing & High-Fidelity GI
eevee = bpy.context.scene.eevee
eevee.use_raytracing = True
eevee.ray_tracing_method = 'SCREEN'
eevee.fast_gi_method = 'GLOBAL_ILLUMINATION'
eevee.fast_gi_quality = 0.75
eevee.fast_gi_ray_count = 4
eevee.use_shadows = True
eevee.shadow_resolution_scale = 1.0
eevee.shadow_ray_count = 4

# View transform: AgX or Filmic
scene = bpy.context.scene
vt_names = [c.name for c in bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items]
scene.view_settings.view_transform = 'AgX' if 'AgX' in vt_names else 'Filmic'
scene.view_settings.look = 'High Contrast'
scene.view_settings.exposure = 0.1

# 2. Configure World: Deep Himalayan Sky (Nishita Multi-Scattering)
w = bpy.data.worlds.get('W_Tactical_Mountain')
if not w:
    w = bpy.data.worlds.new('W_Tactical_Mountain')
scene.world = w
tree_w = w.node_tree
tree_w.nodes.clear()

out_w = tree_w.nodes.new('ShaderNodeOutputWorld')
bg_w = tree_w.nodes.new('ShaderNodeBackground')
sky_w = tree_w.nodes.new('ShaderNodeTexSky')
sky_w.sky_type = 'MULTIPLE_SCATTERING'
sky_w.sun_elevation = math.radians(26.0)  # Low afternoon sun for dramatic mountain ridge relief
sky_w.sun_rotation = math.radians(105.0)  # Across canyon axis for illuminated cliff vs shadow cliff
sky_w.altitude = 4800.0                   # High altitude Ladakh atmosphere
sky_w.air_density = 0.50
sky_w.aerosol_density = 0.12
sky_w.ozone_density = 2.4
sky_w.sun_disc = True

bg_w.inputs['Strength'].default_value = 0.95
tree_w.links.new(sky_w.outputs['Color'], bg_w.inputs['Color'])
tree_w.links.new(bg_w.outputs['Background'], out_w.inputs['Surface'])

# 3. Configure Sun Light: Single Crisp Key Sunlight
sun_old = bpy.data.objects.get('Sun')
if sun_old:
    sun_old.hide_viewport = True
    sun_old.hide_render = True
    sun_old.data.energy = 0.0

sun_top = bpy.data.objects.get('Sun_TopGun')
if sun_top:
    sun_top.rotation_euler = (math.radians(64.0), math.radians(8.0), math.radians(105.0))
    sun_top.data.energy = 5.8
    sun_top.data.color = (1.0, 0.95, 0.88)   # Warm sunlight
    sun_top.data.angle = math.radians(1.2)    # Crisp shadow with soft edge penumbra

# 4. Build Photorealistic Multi-Band Himalayan Geology Shader
mat = bpy.data.materials.get('M_TopGun_Canyon_Simulation')
if not mat:
    mat = bpy.data.materials.new('M_TopGun_Canyon_Simulation')
tree_m = mat.node_tree
tree_m.nodes.clear()

# Node creation
node_out = tree_m.nodes.new('ShaderNodeOutputMaterial')
node_bsdf = tree_m.nodes.new('ShaderNodeBsdfPrincipled')
node_texcoord = tree_m.nodes.new('ShaderNodeTexCoord')
node_geom = tree_m.nodes.new('ShaderNodeNewGeometry')

# Separate Generated (UV) & World Normal
node_gen_xyz = tree_m.nodes.new('ShaderNodeSeparateXYZ')
node_world_xyz = tree_m.nodes.new('ShaderNodeSeparateXYZ')
node_norm_xyz = tree_m.nodes.new('ShaderNodeSeparateXYZ')

tree_m.links.new(node_texcoord.outputs['Generated'], node_gen_xyz.inputs['Vector'])
tree_m.links.new(node_geom.outputs['Position'], node_world_xyz.inputs['Vector'])
tree_m.links.new(node_geom.outputs['Normal'], node_norm_xyz.inputs['Vector'])

# A. Elevation Mapping based on actual world Z (2,900m to 7,200m)
node_elev_map = tree_m.nodes.new('ShaderNodeMapRange')
node_elev_map.inputs['From Min'].default_value = 3200.0
node_elev_map.inputs['From Max'].default_value = 6800.0
node_elev_map.inputs['To Min'].default_value = 0.0
node_elev_map.inputs['To Max'].default_value = 1.0
tree_m.links.new(node_world_xyz.outputs['Z'], node_elev_map.inputs['Value'])

# B. Geological Rock Strata Color Ramp
node_rock_ramp = tree_m.nodes.new('ShaderNodeValToRGB')
cr = node_rock_ramp.color_ramp
cr.color_mode = 'RGB'
cr.interpolation = 'LINEAR'
cr.elements[0].position = 0.0
cr.elements[0].color = (0.38, 0.30, 0.22, 1.0)   # Alluvial canyon floor silt & sandstone
cr.elements[1].position = 1.0
cr.elements[1].color = (0.22, 0.23, 0.26, 1.0)   # High mountain granite slate
e1 = cr.elements.new(0.28)
e1.color = (0.34, 0.22, 0.16, 1.0)   # Red Himalayan ironstone / sandstone band
e2 = cr.elements.new(0.58)
e2.color = (0.24, 0.20, 0.18, 1.0)   # Dark weathered cliff face
tree_m.links.new(node_elev_map.outputs['Result'], node_rock_ramp.inputs['Fac'])

# C. High-Frequency Rock Micro-Fracture Noise
node_noise_micro = tree_m.nodes.new('ShaderNodeTexNoise')
node_noise_micro.inputs['Scale'].default_value = 120.0
node_noise_micro.inputs['Detail'].default_value = 6.0
node_noise_micro.inputs['Roughness'].default_value = 0.7
tree_m.links.new(node_texcoord.outputs['Generated'], node_noise_micro.inputs['Vector'])

# D. Mid-Scale Strata Wave Texture (Layered Himalayan rock bands)
node_wave = tree_m.nodes.new('ShaderNodeTexWave')
node_wave.wave_type = 'BANDS'
node_wave.bands_direction = 'Z'
node_wave.inputs['Scale'].default_value = 35.0
node_wave.inputs['Distortion'].default_value = 4.5
node_wave.inputs['Detail'].default_value = 4.0
tree_m.links.new(node_texcoord.outputs['Generated'], node_wave.inputs['Vector'])

# Mix rock color with wave strata banding
node_mix_strata = tree_m.nodes.new('ShaderNodeMix')
node_mix_strata.data_type = 'RGBA'
node_mix_strata.blend_type = 'OVERLAY'
node_mix_strata.inputs['Factor'].default_value = 0.35
tree_m.links.new(node_rock_ramp.outputs['Color'], node_mix_strata.inputs['A'])
tree_m.links.new(node_wave.outputs['Color'], node_mix_strata.inputs['B'])

# Mix with micro noise for realistic stone texture
node_mix_rock = tree_m.nodes.new('ShaderNodeMix')
node_mix_rock.data_type = 'RGBA'
node_mix_rock.blend_type = 'MULTIPLY'
node_mix_rock.inputs['Factor'].default_value = 0.25
tree_m.links.new(node_mix_strata.outputs['Result'], node_mix_rock.inputs['A'])
tree_m.links.new(node_noise_micro.outputs['Color'], node_mix_rock.inputs['B'])

# E. Glacial Snow Coverage Mask:
# 1. Snow elevation threshold (snow starts at ~4,800m and dominates above 5,400m)
node_snow_elev = tree_m.nodes.new('ShaderNodeMapRange')
node_snow_elev.inputs['From Min'].default_value = 4800.0
node_snow_elev.inputs['From Max'].default_value = 5800.0
node_snow_elev.inputs['To Min'].default_value = 0.0
node_snow_elev.inputs['To Max'].default_value = 1.0
tree_m.links.new(node_world_xyz.outputs['Z'], node_snow_elev.inputs['Value'])

# 2. Slope mask (snow sticks only to surfaces gentler than 40 degrees, Normal.Z > 0.60)
node_snow_slope = tree_m.nodes.new('ShaderNodeMapRange')
node_snow_slope.inputs['From Min'].default_value = 0.55
node_snow_slope.inputs['From Max'].default_value = 0.85
node_snow_slope.inputs['To Min'].default_value = 0.0
node_snow_slope.inputs['To Max'].default_value = 1.0
tree_m.links.new(node_norm_xyz.outputs['Z'], node_snow_slope.inputs['Value'])

# Combine elevation and slope
node_snow_mult = tree_m.nodes.new('ShaderNodeMath')
node_snow_mult.operation = 'MULTIPLY'
tree_m.links.new(node_snow_elev.outputs['Result'], node_snow_mult.inputs[0])
tree_m.links.new(node_snow_slope.outputs['Result'], node_snow_mult.inputs[1])

# High-contrast snow threshold
node_snow_ramp = tree_m.nodes.new('ShaderNodeValToRGB')
crs = node_snow_ramp.color_ramp
crs.elements[0].position = 0.25
crs.elements[0].color = (0.0, 0.0, 0.0, 1.0)
crs.elements[1].position = 0.60
crs.elements[1].color = (1.0, 1.0, 1.0, 1.0)
tree_m.links.new(node_snow_mult.outputs['Value'], node_snow_ramp.inputs['Fac'])

# Pure Himalayan Glacial Snow color
node_snow_rgb = tree_m.nodes.new('ShaderNodeRGB')
node_snow_rgb.outputs['Color'].default_value = (0.95, 0.96, 1.00, 1.0)

# Final Mix: Rock + Snow
node_final_color = tree_m.nodes.new('ShaderNodeMix')
node_final_color.data_type = 'RGBA'
node_final_color.blend_type = 'MIX'
tree_m.links.new(node_snow_ramp.outputs['Color'], node_final_color.inputs['Factor'])
tree_m.links.new(node_mix_rock.outputs['Result'], node_final_color.inputs['A'])
tree_m.links.new(node_snow_rgb.outputs['Color'], node_final_color.inputs['B'])

# Roughness map: Rock is matte (0.85), Snow is smooth (0.32)
node_rough_mix = tree_m.nodes.new('ShaderNodeMix')
node_rough_mix.data_type = 'FLOAT'
node_rough_mix.inputs['A'].default_value = 0.85
node_rough_mix.inputs['B'].default_value = 0.32
tree_m.links.new(node_snow_ramp.outputs['Color'], node_rough_mix.inputs['Factor'])

# Rock Crags Bump Normal
node_bump = tree_m.nodes.new('ShaderNodeBump')
node_bump.inputs['Strength'].default_value = 0.45
node_bump.inputs['Distance'].default_value = 8.0
tree_m.links.new(node_noise_micro.outputs['Fac'], node_bump.inputs['Height'])

# Connect to Principled BSDF
tree_m.links.new(node_final_color.outputs['Result'], node_bsdf.inputs['Base Color'])
tree_m.links.new(node_rough_mix.outputs['Result'], node_bsdf.inputs['Roughness'])
tree_m.links.new(node_bump.outputs['Normal'], node_bsdf.inputs['Normal'])
tree_m.links.new(node_bsdf.outputs['BSDF'], node_out.inputs['Surface'])

print(">>> Photorealistic Himalayan Material Pipeline Built! <<<")

# Position camera in exact hero chase view to render frame
uav = bpy.data.objects.get('UAV_Predator_Master')
cam = bpy.data.objects.get('Camera_UAV_Chase')
pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))
hdg_rad = math.radians(46.0)

fwd_vel = mathutils.Vector((math.sin(hdg_rad), math.cos(hdg_rad), 0.0)).normalized()
up_world = mathutils.Vector((0.0, 0.0, 1.0))
right_base = fwd_vel.cross(up_world).normalized()
up_base = right_base.cross(fwd_vel).normalized()

rot_mat = mathutils.Matrix((-right_base, -fwd_vel, up_base)).transposed()
uav.matrix_world = mathutils.Matrix.Translation(pos) @ rot_mat.to_4x4() @ mathutils.Matrix.Diagonal((36.0, 36.0, 36.0, 1.0))

tail_dir = mathutils.Vector((-math.sin(hdg_rad), -math.cos(hdg_rad), 0.0)).normalized()
cam.location = pos + tail_dir * 480.0 + up_world * 135.0
look_target = pos + fwd_vel * 80.0
cam_dir = (look_target - cam.location).normalized()
cam_rot = cam_dir.to_track_quat('-Z', 'Y')
cam.rotation_euler = cam_rot.to_euler()

scene.camera = cam
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.filepath = "e:/backup-llm/backup-no-llm/3d_engine/scratch/photoreal_canyon_hero.png"
bpy.ops.render.render(write_still=True)
print(">>> Rendered hero chase test saved to scratch/photoreal_canyon_hero.png <<<")
