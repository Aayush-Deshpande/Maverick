import bpy

terrain = bpy.data.objects.get('Copernicus_DSM_COG_10_N34_00_E077_00_DEM')
mat = terrain.material_slots[0].material
nodes = mat.node_tree.nodes

mix = nodes.get('Mix_Snow_Blend')
print("Mix_Snow_Blend:")
print("  blend_type:", mix.blend_type)
print("  data_type:", mix.data_type)
print("  factor_mode:", getattr(mix, 'factor_mode', None))
print("  clamp_factor:", mix.clamp_factor)
print("  clamp_result:", mix.clamp_result)

for i, inp in enumerate(mix.inputs):
    link_info = ""
    if inp.is_linked:
        l = inp.links[0]
        link_info = f" <-- {l.from_node.name}.{l.from_socket.name}"
    print(f"  [{i}] name='{inp.name}' ident='{inp.identifier}' type='{inp.type}' val={inp.default_value}{link_info}")

for i, out in enumerate(mix.outputs):
    link_info = ""
    if out.is_linked:
        l = out.links[0]
        link_info = f" --> {l.to_node.name}.{l.to_socket.name}"
    print(f"  OUT [{i}] name='{out.name}' ident='{out.identifier}' type='{out.type}'{link_info}")
