import bpy
import json
from pathlib import Path

def probe():
    ROOT = Path(__file__).resolve().parents[2]
    out_file = ROOT / "build" / "logs" / "blender_api_probe.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    results = {}

    # 1. ShaderNodeBsdfPrincipled input sockets
    mat = bpy.data.materials.new("Probe_Mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
    results["principled_bsdf_inputs"] = [inp.name for inp in bsdf.inputs]
    results["principled_bsdf_outputs"] = [out.name for out in bsdf.outputs]

    # 2. scene.eevee and scene.cycles attributes
    scene = bpy.context.scene
    keywords = ["ray", "gtao", "ssr", "sample", "denois", "shadow"]
    
    eevee_attrs = []
    if hasattr(scene, "eevee"):
        for attr in dir(scene.eevee):
            if any(k in attr.lower() for k in keywords):
                eevee_attrs.append(attr)
    results["eevee_attributes"] = eevee_attrs

    cycles_attrs = []
    if hasattr(scene, "cycles"):
        for attr in dir(scene.cycles):
            if any(k in attr.lower() for k in keywords):
                cycles_attrs.append(attr)
    results["cycles_attributes"] = cycles_attrs

    # 3. view_transform and look enum items
    view_transforms = [item.identifier for item in scene.view_settings.bl_rna.properties['view_transform'].enum_items]
    results["view_transform_enum_items"] = view_transforms

    # Set view_transform to AgX if available, then read looks
    if "AgX" in view_transforms:
        scene.view_settings.view_transform = "AgX"
    results["look_enum_items_under_agx"] = [item.identifier for item in scene.view_settings.bl_rna.properties['look'].enum_items]

    # 4. Material blend / surface render method
    mat_props = dir(bpy.types.Material)
    results["material_has_blend_method"] = "blend_method" in mat_props
    results["material_has_surface_render_method"] = "surface_render_method" in mat_props
    if hasattr(mat, "surface_render_method"):
        results["surface_render_method_enum"] = [item.identifier for item in mat.bl_rna.properties["surface_render_method"].enum_items]

    # 5. Cycles compute devices
    cpref = bpy.context.preferences.addons.get("cycles")
    compute_devices = {}
    if cpref and hasattr(cpref, "preferences"):
        cprops = cpref.preferences
        for dtype in ["OPTIX", "CUDA", "HIP", "ONEAPI"]:
            try:
                cprops.compute_device_type = dtype
                devs = cprops.get_devices()
                dev_list = []
                if devs:
                    for d in devs:
                        for device in d:
                            dev_list.append({"name": device.name, "type": device.type, "use": device.use})
                compute_devices[dtype] = dev_list
            except Exception as e:
                compute_devices[dtype] = f"Error: {e}"
    results["cycles_compute_devices"] = compute_devices

    # 6. ShaderNodeAttribute
    attr_node = mat.node_tree.nodes.new("ShaderNodeAttribute")
    results["attribute_node_outputs"] = [out.name for out in attr_node.outputs]
    has_type = hasattr(attr_node, "attribute_type")
    results["attribute_node_has_attribute_type"] = has_type
    if has_type:
        accepted = [item.identifier for item in attr_node.bl_rna.properties["attribute_type"].enum_items]
        results["attribute_node_accepted_types"] = accepted
        results["attribute_type_accepts_OBJECT"] = "OBJECT" in accepted
    else:
        results["attribute_type_accepts_OBJECT"] = False

    # Clean up probe material
    bpy.data.materials.remove(mat)

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"API Probe successfully written to: {out_file}")

if __name__ == "__main__":
    probe()
