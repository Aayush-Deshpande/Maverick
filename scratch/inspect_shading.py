import bpy

m = bpy.data.materials.get('M_TopGun_Canyon_Simulation')
print("=== MATERIAL NODES & LINKS ===")
for link in m.node_tree.links:
    print(f"{link.from_node.name} [{link.from_socket.name}] -> {link.to_node.name} [{link.to_socket.name}]")

w = bpy.data.worlds.get('W_Tactical_Mountain')
print("\n=== WORLD NODES & LINKS ===")
for link in w.node_tree.links:
    print(f"{link.from_node.name} [{link.from_socket.name}] -> {link.to_node.name} [{link.to_socket.name}]")

print("\n=== WORLD NODE VALUES ===")
for n in w.node_tree.nodes:
    print(f"Node {n.name} ({n.type}):")
    for inp in n.inputs:
        val = inp.default_value if hasattr(inp, 'default_value') else 'N/A'
        print(f"   input '{inp.name}': {val}")
