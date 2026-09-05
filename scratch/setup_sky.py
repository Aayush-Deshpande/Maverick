import bpy

w = bpy.data.worlds.get('W_Tactical_Mountain')
tree = w.node_tree
tree.nodes.clear()

# Create clean Nishita World setup
out = tree.nodes.new('ShaderNodeOutputWorld')
bg = tree.nodes.new('ShaderNodeBackground')
sky = tree.nodes.new('ShaderNodeTexSky')
sky.sky_type = 'NISHITA'
sky.sun_elevation = 0.45 # ~25 degrees afternoon sun
sky.sun_rotation = 2.1
sky.altitude = 5000.0 # 5,000m high altitude atmosphere (crisp deep blue Ladakh sky)
sky.air_density = 0.6
sky.dust_density = 0.2
sky.ozone_density = 2.0

bg.inputs['Strength'].default_value = 1.0

tree.links.new(sky.outputs['Color'], bg.inputs['Color'])
tree.links.new(bg.outputs['Background'], out.inputs['Surface'])

print(">>> Clean Nishita World Atmosphere Configured! <<<")
