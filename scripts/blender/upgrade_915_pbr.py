"""
Upgrade Rotax 915 iS materials to authentic aerospace PBR:
- Enamel blue -> Anodized Royal Blue (signature Rotax 915 iS valve covers)
- Metal exhaust pipes -> Heat-tinted stainless steel
- Metal more matte -> Cast A356 aluminum engine block
- Metal shinier -> Machined turbo compressor alloy
- Metal bolts -> Cadmium / zinc plated fasteners
- Plastic black -> Satin PA66-GF30 intake plenum polymer
"""
import os
import bpy

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

TARGETS = [
    os.path.join(PROJECT_ROOT, "assets", "blender", "engines", "rotax_915is", "rotax_915is.blend"),
    os.path.join(PROJECT_ROOT, "assets", "blender", "scenes", "anumaan_master_twin.blend"),
]

def upgrade_materials(blend_path):
    print(f"\nUpgrading 915 PBR in: {blend_path}")
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if not bsdf:
            continue
            
        mname = mat.name.lower()
        if "enamel blue" in mname:
            # Signature Rotax 915 iS blue anodized aluminum
            bsdf.inputs["Base Color"].default_value = (0.04, 0.22, 0.78, 1.0)
            bsdf.inputs["Metallic"].default_value = 0.88
            bsdf.inputs["Roughness"].default_value = 0.22
            print(f"  [ANODIZED BLUE] {mat.name}")
        elif "exhaust" in mname:
            # Heat-tinted stainless exhaust
            bsdf.inputs["Base Color"].default_value = (0.52, 0.46, 0.40, 1.0)
            bsdf.inputs["Metallic"].default_value = 0.92
            bsdf.inputs["Roughness"].default_value = 0.30
            print(f"  [EXHAUST STAINLESS] {mat.name}")
        elif "bolts" in mname or "clamp" in mname:
            # Zinc / cadmium plated fasteners
            bsdf.inputs["Base Color"].default_value = (0.82, 0.80, 0.68, 1.0)
            bsdf.inputs["Metallic"].default_value = 0.92
            bsdf.inputs["Roughness"].default_value = 0.24
            print(f"  [FASTENERS] {mat.name}")
        elif "shinier" in mname:
            # Machined compressor alloy
            bsdf.inputs["Base Color"].default_value = (0.88, 0.90, 0.92, 1.0)
            bsdf.inputs["Metallic"].default_value = 0.95
            bsdf.inputs["Roughness"].default_value = 0.18
            print(f"  [MACHINED ALLOY] {mat.name}")
        elif "more matte" in mname or mname == "metal":
            # Cast A356 aluminum
            bsdf.inputs["Base Color"].default_value = (0.72, 0.74, 0.77, 1.0)
            bsdf.inputs["Metallic"].default_value = 0.82
            bsdf.inputs["Roughness"].default_value = 0.38
            print(f"  [CAST ALUMINUM] {mat.name}")
        elif "plastic" in mname or "hose" in mname or "black iron" in mname:
            # Satin polymer PA66 / silicone
            bsdf.inputs["Base Color"].default_value = (0.03, 0.03, 0.04, 1.0)
            bsdf.inputs["Metallic"].default_value = 0.02
            bsdf.inputs["Roughness"].default_value = 0.36
            print(f"  [SATIN POLYMER] {mat.name}")
            
    bpy.ops.wm.save_mainfile()
    print("  Saved updated blend.")

for path in TARGETS:
    if os.path.exists(path):
        upgrade_materials(path)

print("\nRotax 915 iS PBR materials upgraded successfully!")
