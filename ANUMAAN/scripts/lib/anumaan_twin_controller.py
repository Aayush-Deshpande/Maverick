"""
ANUMAAN Universal Digital Twin Controller
Embedded into .blend assets alongside <asset_id>_manifest.json
Fully generic, reads all components, faults, cameras and mechanisms from the manifest.
"""

import bpy
import json
import mathutils

def get_manifest():
    for text in bpy.data.texts:
        if text.name.endswith("_manifest.json"):
            try:
                return json.loads(text.as_string())
            except Exception as e:
                print(f"Error parsing manifest {text.name}: {e}")
    return None

class ANUMAAN_PT_Controller(bpy.types.Panel):
    bl_label = "ANUMAAN Digital Twin"
    bl_idname = "VIEW3D_PT_anumaan_controller"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Digital Twin'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        manifest = get_manifest()

        if not manifest:
            layout.label(text="No manifest text block found!", icon='ERROR')
            return

        is_engine = "engine_id" in manifest
        asset_id = manifest.get("engine_id") or manifest.get("platform_id")
        layout.label(text=f"Asset: {manifest.get('display_name', asset_id)}", icon='OBJECT_DATA')

        # Display Modes
        box_mode = layout.box()
        box_mode.label(text="Display Mode", icon='SHADING_RENDERED')
        row = box_mode.row(align=True)
        row.operator("anumaan.set_display_mode", text="PBR").mode = 0
        row.operator("anumaan.set_display_mode", text="Ghost / X-Ray").mode = 1
        row.operator("anumaan.set_display_mode", text="Wire Clay").mode = 3

        # Mechanisms (for airframes)
        if not is_engine and "mechanisms" in manifest:
            box_mech = layout.box()
            box_mech.label(text="Mechanisms", icon='DRIVER')
            for mech_name in manifest["mechanisms"].keys():
                if hasattr(scene, mech_name):
                    box_mech.prop(scene, mech_name, slider=True)

        # Cameras
        box_cam = layout.box()
        box_cam.label(text="Cameras", icon='CAMERA_DATA')
        col_cams = box_cam.column(align=True)
        for cam_name in manifest.get("cameras", []):
            if cam_name in bpy.data.objects:
                col_cams.operator("anumaan.switch_camera", text=cam_name.replace("Cam_", "")).camera_name = cam_name

        # Faults
        if "faults" in manifest and manifest["faults"]:
            box_fault = layout.box()
            box_fault.label(text="Fault Simulation", icon='ERROR')
            box_fault.prop(scene, "anumaan_active_fault_idx", text="Fault")
            box_fault.prop(scene, "anumaan_fault_severity", text="Severity", slider=True)
            box_fault.operator("anumaan.apply_fault", text="Inject Fault State", icon='COLORSET_01_VEC')

        # Clear button
        layout.separator()
        layout.operator("anumaan.clear_state", text="Reset All to Nominal", icon='LOOP_BACK')

class ANUMAAN_OT_SetDisplayMode(bpy.types.Operator):
    bl_idname = "anumaan.set_display_mode"
    bl_label = "Set Display Mode"
    mode: bpy.props.IntProperty(default=0)

    def execute(self, context):
        scene = context.scene
        scene["display_mode"] = self.mode

        # Update XRayFactor on materials
        for mat in bpy.data.materials:
            if mat.node_tree:
                for n in mat.node_tree.nodes:
                    if n.name == "XRayFactor":
                        n.outputs['Value'].default_value = 1.0 if self.mode == 1 else 0.0

        for obj in bpy.data.objects:
            obj["twin_ghost"] = 0.85 if self.mode == 1 else 0.0
            obj.update_tag()

        context.view_layer.update()
        return {'FINISHED'}

class ANUMAAN_OT_SwitchCamera(bpy.types.Operator):
    bl_idname = "anumaan.switch_camera"
    bl_label = "Switch Camera"
    camera_name: bpy.props.StringProperty()

    def execute(self, context):
        if self.camera_name in bpy.data.objects:
            context.scene.camera = bpy.data.objects[self.camera_name]
        return {'FINISHED'}

class ANUMAAN_OT_ApplyFault(bpy.types.Operator):
    bl_idname = "anumaan.apply_fault"
    bl_label = "Apply Fault"

    def execute(self, context):
        manifest = get_manifest()
        if not manifest or "faults" not in manifest:
            return {'CANCELLED'}

        idx = context.scene.anumaan_active_fault_idx
        if idx < 0 or idx >= len(manifest["faults"]):
            return {'CANCELLED'}

        fault = manifest["faults"][idx]
        target_comp = fault.get("component")
        sev = fault.get("severity", "MAJOR")
        level = context.scene.anumaan_fault_severity

        # Color map per Section 13.1
        colors = {
            "MINOR": (1.0, 0.85, 0.0),
            "MAJOR": (1.0, 0.45, 0.0),
            "CRITICAL": (1.0, 0.05, 0.02)
        }
        rgb = colors.get(sev, (1.0, 0.45, 0.0))

        # Find target objects
        target_objs = []
        if target_comp and "components" in manifest:
            cinfo = manifest["components"].get(target_comp, {})
            target_objs = cinfo.get("objects", [])

        # Reset all objects to ghosted
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                obj["twin_ghost"] = 0.85
                obj["twin_fault_level"] = 0.0
                obj["twin_fault_rgb"] = (0.0, 0.0, 0.0)

        # Highlight target objects
        for oname in target_objs:
            if oname in bpy.data.objects:
                o = bpy.data.objects[oname]
                o["twin_ghost"] = 0.0
                o["twin_fault_level"] = level
                o["twin_fault_rgb"] = rgb
                o.update_tag()

        context.view_layer.update()
        return {'FINISHED'}

class ANUMAAN_OT_ClearState(bpy.types.Operator):
    bl_idname = "anumaan.clear_state"
    bl_label = "Clear State"

    def execute(self, context):
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                obj["twin_ghost"] = 0.0
                obj["twin_fault_level"] = 0.0
                obj["twin_fault_rgb"] = (0.0, 0.0, 0.0)
                obj["twin_sensor_suspect"] = 0.0
                obj.update_tag()

        for mat in bpy.data.materials:
            if mat.node_tree:
                for n in mat.node_tree.nodes:
                    if n.name == "XRayFactor":
                        n.outputs['Value'].default_value = 0.0

        context.scene["display_mode"] = 0
        context.view_layer.update()
        return {'FINISHED'}

def register():
    manifest = get_manifest()
    items = []
    if manifest and "faults" in manifest:
        for i, f in enumerate(manifest["faults"]):
            items.append((str(i), f.get("title", f.get("key")), f.get("key"), i))
    if not items:
        items = [("0", "None", "None", 0)]

    bpy.types.Scene.anumaan_active_fault_idx = bpy.props.IntProperty(name="Active Fault", default=0)
    bpy.types.Scene.anumaan_fault_severity = bpy.props.FloatProperty(name="Severity", min=0.1, max=1.0, default=1.0)

    try:
        bpy.utils.register_class(ANUMAAN_PT_Controller)
        bpy.utils.register_class(ANUMAAN_OT_SetDisplayMode)
        bpy.utils.register_class(ANUMAAN_OT_SwitchCamera)
        bpy.utils.register_class(ANUMAAN_OT_ApplyFault)
        bpy.utils.register_class(ANUMAAN_OT_ClearState)
    except Exception as e:
        print(f"Controller register note: {e}")

def unregister():
    try:
        bpy.utils.unregister_class(ANUMAAN_PT_Controller)
        bpy.utils.unregister_class(ANUMAAN_OT_SetDisplayMode)
        bpy.utils.unregister_class(ANUMAAN_OT_SwitchCamera)
        bpy.utils.unregister_class(ANUMAAN_OT_ApplyFault)
        bpy.utils.unregister_class(ANUMAAN_OT_ClearState)
    except Exception:
        pass

if __name__ == "__main__":
    register()
