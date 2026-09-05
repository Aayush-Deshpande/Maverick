import bpy
import math
import mathutils

scene = bpy.context.scene
cam = bpy.data.objects.get('Camera_UAV_Chase')
uav = bpy.data.objects.get('UAV_Predator_Master')

if cam.animation_data: cam.animation_data_clear()
if uav.animation_data: uav.animation_data_clear()
cam.constraints.clear()
uav.constraints.clear()

# Ingress position and heading
pos = mathutils.Vector((-19500.0, 7000.0, 5800.0))
hdg_rad = math.radians(46.0)

fwd_vel = mathutils.Vector((math.sin(hdg_rad), math.cos(hdg_rad), 0.0)).normalized()
up_world = mathutils.Vector((0.0, 0.0, 1.0))
right_base = fwd_vel.cross(up_world).normalized()
up_base = right_base.cross(fwd_vel).normalized()

rot_mat = mathutils.Matrix((-right_base, -fwd_vel, up_base)).transposed()
uav.matrix_world = mathutils.Matrix.Translation(pos) @ rot_mat.to_4x4() @ mathutils.Matrix.Diagonal((36.0, 36.0, 36.0, 1.0))

tail_dir = -fwd_vel
cam.location = pos + tail_dir * 480.0 + up_world * 135.0
look_target = pos + fwd_vel * 120.0
cam_dir = (look_target - cam.location).normalized()
cam.rotation_euler = cam_dir.to_track_quat('-Z', 'Y').to_euler()

# EEVEE-Next Raytracing
eevee = scene.eevee
eevee.use_raytracing = True
eevee.ray_tracing_method = 'SCREEN'
eevee.fast_gi_method = 'GLOBAL_ILLUMINATION'
eevee.fast_gi_quality = 0.8
eevee.fast_gi_ray_count = 4
eevee.use_shadows = True
eevee.shadow_resolution_scale = 1.0

scene.view_settings.view_transform = 'AgX' if 'AgX' in [c.name for c in bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
scene.view_settings.look = 'High Contrast'
scene.view_settings.exposure = 0.15

# World: Nishita Atmosphere with warm sun
w = bpy.data.worlds.get('W_Tactical_Mountain')
scene.world = w
tree_w = w.node_tree
tree_w.nodes.clear()

out_w = tree_w.nodes.new('ShaderNodeOutputWorld')
bg_w = tree_w.nodes.new('ShaderNodeBackground')
sky_w = tree_w.nodes.new('ShaderNodeTexSky')
sky_w.sky_type = 'MULTIPLE_SCATTERING'
# Sun positioned to shine diagonally down the canyon axis (reveals gorge depth & rock faces)
sky_w.sun_elevation = math.radians(34.0)
sky_w.sun_rotation = math.radians(225.0) # Shining towards Northeast along flight path
sky_w.altitude = 4500.0
sky_w.air_density = 0.50
sky_w.aerosol_density = 0.10
sky_w.ozone_density = 2.4
sky_w.sun_disc = True

bg_w.inputs['Strength'].default_value = 1.0
tree_w.links.new(sky_w.outputs['Color'], bg_w.inputs['Color'])
tree_w.links.new(bg_w.outputs['Background'], out_w.inputs['Surface'])

# Sunlight: Matching direction
sun_old = bpy.data.objects.get('Sun')
if sun_old: sun_old.data.energy = 0.0

sun_top = bpy.data.objects.get('Sun_TopGun')
if sun_top:
    sun_top.rotation_euler = (math.radians(56.0), math.radians(-12.0), math.radians(225.0))
    sun_top.data.energy = 6.2
    sun_top.data.color = (1.0, 0.95, 0.88)
    sun_top.data.angle = math.radians(1.2)

# Material: Authentic Himalayan Geological Palette
mat = bpy.data.materials.get('M_TopGun_Canyon_Simulation')
tree_m = mat.node_tree
tree_m.nodes.clear()

node_out = tree_m.nodes.new('ShaderNodeOutputMaterial')
node_bsdf = tree_m.nodes.new('ShaderNodeBsdfPrincipled')
node_geom = tree_m.nodes.new('ShaderNodeNewGeometry')

node_world_xyz = tree_m.nodes.new('ShaderNodeSeparateXYZ')
node_norm_xyz = tree_m.nodes.new('ShaderNodeSeparateXYZ')
tree_m.links.new(node_geom.outputs['Position'], node_world_xyz.inputs['Vector'])
tree_m.links.new(node_geom.outputs['Normal'], node_norm_xyz.inputs['Vector'])

# Elevation ramp (3,000m to 7,200m)
node_elev_map = tree_m.nodes.new('ShaderNodeMapRange')
node_elev_map.inputs['From Min'].default_value = 3200.0
node_elev_map.inputs['From Max'].default_value = 6800.0
tree_m.links.new(node_world_xyz.outputs['Z'], node_elev_map.inputs['Value'])

# Rock Color Ramp: Warm Sandstone -> Terracotta -> Slate -> Granite Crag
node_rock_ramp = tree_m.nodes.new('ShaderNodeValToRGB')
cr = node_rock_ramp.color_ramp
cr.color_mode = 'RGB'
cr.interpolation = 'LINEAR'
cr.elements[0].position = 0.0
cr.elements[0].color = (0.46, 0.36, 0.24, 1.0)   # Riverbed ochre & silt
cr.elements[1].position = 1.0
cr.elements[1].color = (0.20, 0.20, 0.22, 1.0)   # High summit dark granite
e1 = cr.elements.new(0.32)
e1.color = (0.42, 0.24, 0.16, 1.0)   # Terracotta red sandstone cliff band
e2 = cr.elements.new(0.62)
e2.color = (0.28, 0.24, 0.21, 1.0)   # Weathered mountain stone
tree_m.links.new(node_elev_map.outputs['Result'], node_rock_ramp.inputs['Fac'])

# Geological Strata Layering (Z-sine wave for stratified rock bands)
node_scale_z = tree_m.nodes.new('ShaderNodeMath')
node_scale_z.operation = 'MULTIPLY'
node_scale_z.inputs[1].default_value = 0.035  # Band thickness ~30m
tree_m.links.new(node_world_xyz.outputs['Z'], node_scale_z.inputs[0])

node_sine = tree_m.nodes.new('ShaderNodeMath')
node_sine.operation = 'SINE'
tree_m.links.new(node_scale_z.outputs['Value'], node_sine.inputs[0])

# Strata Banding Mix
node_strata_mix = tree_m.nodes.new('ShaderNodeMix')
node_strata_mix.data_type = 'RGBA'
node_strata_mix.blend_type = 'OVERLAY'
node_strata_mix.inputs['Factor'].default_value = 0.40
tree_m.links.new(node_rock_ramp.outputs['Color'], node_strata_mix.inputs['A'])
node_band_col = tree_m.nodes.new('ShaderNodeRGB')
node_band_col.outputs['Color'].default_value = (0.48, 0.25, 0.16, 1.0)
tree_m.links.new(node_band_col.outputs['Color'], node_strata_mix.inputs['B'])

# World-scale Rock Micro-Detail Noise (10-meter crag roughness)
node_noise_rock = tree_m.nodes.new('ShaderNodeTexNoise')
node_noise_rock.inputs['Scale'].default_value = 0.05
node_noise_rock.inputs['Detail'].default_value = 6.0
node_noise_rock.inputs['Roughness'].default_value = 0.70
node_noise_rock.inputs['Distortion'].default_value = 0.8
tree_m.links.new(node_geom.outputs['Position'], node_noise_rock.inputs['Vector'])

# Multiply rock color with noise
node_rock_final = tree_m.nodes.new('ShaderNodeMix')
node_rock_final.data_type = 'RGBA'
node_rock_final.blend_type = 'MULTIPLY'
node_rock_final.inputs['Factor'].default_value = 0.35
tree_m.links.new(node_strata_mix.outputs['Result'], node_rock_final.inputs['A'])
tree_m.links.new(node_noise_rock.outputs['Color'], node_rock_final.inputs['B'])

# Realistic Ladakh Snowline: Snow only on peaks above 5,400m AMSL!
node_snow_elev = tree_m.nodes.new('ShaderNodeMapRange')
node_snow_elev.inputs['From Min'].default_value = 5400.0
node_snow_elev.inputs['From Max'].default_value = 6400.0
tree_m.links.new(node_world_xyz.outputs['Z'], node_snow_elev.inputs['Value'])

# Slope mask (snow only on slopes gentler than 38 degrees)
node_snow_slope = tree_m.nodes.new('ShaderNodeMapRange')
node_snow_slope.inputs['From Min'].default_value = 0.65
node_snow_slope.inputs['From Max'].default_value = 0.90
tree_m.links.new(node_norm_xyz.outputs['Z'], node_snow_slope.inputs['Value'])

node_snow_mult = tree_m.nodes.new('ShaderNodeMath')
node_snow_mult.operation = 'MULTIPLY'
tree_m.links.new(node_snow_elev.outputs['Result'], node_snow_mult.inputs[0])
tree_m.links.new(node_snow_slope.outputs['Result'], node_snow_mult.inputs[1])

node_snow_ramp = tree_m.nodes.new('ShaderNodeValToRGB')
crs = node_snow_ramp.color_ramp
crs.elements[0].position = 0.20
crs.elements[0].color = (0.0, 0.0, 0.0, 1.0)
crs.elements[1].position = 0.55
crs.elements[1].color = (1.0, 1.0, 1.0, 1.0)
tree_m.links.new(node_snow_mult.outputs['Value'], node_snow_ramp.inputs['Fac'])

# Pure Himalayan Glacial Snow color
node_snow_rgb = tree_m.nodes.new('ShaderNodeRGB')
node_snow_rgb.outputs['Color'].default_value = (0.95, 0.96, 0.99, 1.0)

# Blend Rock + Snow
node_mix_surface = tree_m.nodes.new('ShaderNodeMix')
node_mix_surface.data_type = 'RGBA'
node_mix_surface.blend_type = 'MIX'
tree_m.links.new(node_snow_ramp.outputs['Color'], node_mix_surface.inputs['Factor'])
tree_m.links.new(node_rock_final.outputs['Result'], node_mix_surface.inputs['A'])
tree_m.links.new(node_snow_rgb.outputs['Color'], node_mix_surface.inputs['B'])

# Roughness map: Rock (0.85), Snow (0.35)
node_rough = tree_m.nodes.new('ShaderNodeMix')
node_rough.data_type = 'FLOAT'
node_rough.inputs['A'].default_value = 0.85
node_rough.inputs['B'].default_value = 0.35
tree_m.links.new(node_snow_ramp.outputs['Color'], node_rough.inputs['Factor'])

# Rock Bump Normal for sharp ridges
node_bump = tree_m.nodes.new('ShaderNodeBump')
node_bump.inputs['Strength'].default_value = 0.45
node_bump.inputs['Distance'].default_value = 6.0
tree_m.links.new(node_noise_rock.outputs['Fac'], node_bump.inputs['Height'])

# Output to BSDF
tree_m.links.new(node_mix_surface.outputs['Result'], node_bsdf.inputs['Base Color'])
tree_m.links.new(node_rough.outputs['Result'], node_bsdf.inputs['Roughness'])
tree_m.links.new(node_bump.outputs['Normal'], node_bsdf.inputs['Normal'])
tree_m.links.new(node_bsdf.outputs['BSDF'], node_out.inputs['Surface'])

# Render test frame
scene.camera = cam
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.filepath = "e:/backup-llm/backup-no-llm/3d_engine/scratch/canyon_photoreal_golden.png"
bpy.ops.render.render(write_still=True)
print(">>> Golden canyon test render saved! <<<")
