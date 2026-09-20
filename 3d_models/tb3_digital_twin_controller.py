
import bpy

class VIEW3D_PT_TB3_DigitalTwin(bpy.types.Panel):
    """Bayraktar TB3 Interactive Digital Twin Control Panel"""
    bl_label = "Bayraktar TB3 Digital Twin"
    bl_idname = "VIEW3D_PT_tb3_digital_twin"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TB3 Twin"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # --- Digital Twin Inspection State ---
        box_state = layout.box()
        box_state.label(text="Inspection Mode", icon='RESTRICT_VIEW_OFF')
        row_mode = box_state.row(align=True)
        row_mode.operator("tb3.set_mode", text="Normal").mode = "NORMAL"
        row_mode.operator("tb3.set_mode", text="Ghost / X-Ray").mode = "GHOST"
        row_mode.operator("tb3.set_mode", text="Internal Only").mode = "INTERNAL"
        row_mode.operator("tb3.set_mode", text="Wireframe").mode = "WIREFRAME"

        # Ghost / X-Ray Opacity Slider
        col_xray = box_state.column()
        col_xray.prop(scene, '["xray_mode"]', text="X-Ray Opacity", slider=True)

        # --- Subsystem Isolation ---
        box_sub = layout.box()
        box_sub.label(text="Subsystem Isolation", icon='SELECT_SET')
        row_sub1 = box_sub.row(align=True)
        row_sub1.operator("tb3.isolate_subsystem", text="All Systems").subsystem = "ALL"
        row_sub1.operator("tb3.isolate_subsystem", text="Airframe").subsystem = "AIRFRAME"
        row_sub2 = box_sub.row(align=True)
        row_sub2.operator("tb3.isolate_subsystem", text="Propulsion").subsystem = "PROPULSION"
        row_sub2.operator("tb3.isolate_subsystem", text="Avionics").subsystem = "AVIONICS"
        row_sub3 = box_sub.row(align=True)
        row_sub3.operator("tb3.isolate_subsystem", text="Fuel System").subsystem = "FUEL"
        row_sub3.operator("tb3.isolate_subsystem", text="Sensors/Payload").subsystem = "SENSORS"

        # --- Mechanical Controls ---
        box_mech = layout.box()
        box_mech.label(text="Mechanical Elements", icon='TOOL_SETTINGS')
        box_mech.prop(scene, '["wing_fold"]', text="Wing Fold", slider=True)
        box_mech.prop(scene, '["gear_retract"]', text="Gear Retraction", slider=True)
        row_act = box_mech.row(align=True)
        row_act.operator("tb3.action_fold_wings", text="Toggle Wing Fold")
        row_act.operator("tb3.action_toggle_gear", text="Toggle Gear")

        # --- Camera Navigator ---
        box_cam = layout.box()
        box_cam.label(text="Camera Navigator", icon='CAMERA_DATA')
        col_cam = box_cam.column(align=True)
        col_cam.operator("tb3.switch_camera", text="Orbit / Beauty View").camera_name = "Cam_Beauty_Orbit"
        col_cam.operator("tb3.switch_camera", text="EO/IR Sensor Ball").camera_name = "Cam_Front_Sensor"
        col_cam.operator("tb3.switch_camera", text="Engine & Propeller").camera_name = "Cam_Engine_Prop"
        col_cam.operator("tb3.switch_camera", text="Wing Fold Mechanism").camera_name = "Cam_Wing_Fold"
        col_cam.operator("tb3.switch_camera", text="Landing Gear System").camera_name = "Cam_Undercarriage"


class TB3_OT_SetMode(bpy.types.Operator):
    bl_idname = "tb3.set_mode"
    bl_label = "Set Inspection Mode"
    mode: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        mat_skin = bpy.data.materials.get("TB3_Skin_TacticalGray")
        mat_decal = bpy.data.materials.get("TB3_Decal_Material")
        fuse_col = bpy.data.collections.get("Fuselage")
        wings_col = bpy.data.collections.get("Wings")
        tail_col = bpy.data.collections.get("Tail")
        int_col = bpy.data.collections.get("Internal_Systems")

        def set_xray_val(val):
            for m in [mat_skin, mat_decal]:
                if m and m.node_tree:
                    vn = m.node_tree.nodes.get("XRayFactor")
                    if vn: vn.outputs[0].default_value = val

        if self.mode == "NORMAL":
            scene["xray_mode"] = 0.0
            set_xray_val(0.0)
            if fuse_col: fuse_col.hide_viewport = False
            if wings_col: wings_col.hide_viewport = False
            if tail_col: tail_col.hide_viewport = False
            for obj in bpy.data.objects:
                obj.display_type = 'TEXTURED'

        elif self.mode == "GHOST":
            scene["xray_mode"] = 0.85
            set_xray_val(0.85)
            if fuse_col: fuse_col.hide_viewport = False
            if wings_col: wings_col.hide_viewport = False
            if tail_col: tail_col.hide_viewport = False
            if int_col: int_col.hide_viewport = False

        elif self.mode == "INTERNAL":
            scene["xray_mode"] = 1.0
            set_xray_val(1.0)
            if fuse_col: fuse_col.hide_viewport = True
            if wings_col: wings_col.hide_viewport = True
            if tail_col: tail_col.hide_viewport = True
            if int_col: int_col.hide_viewport = False

        elif self.mode == "WIREFRAME":
            scene["xray_mode"] = 0.5
            for obj in bpy.data.objects:
                if "Fuselage" in obj.name or "Wing" in obj.name or "Tail" in obj.name:
                    obj.show_wire = True
                    obj.display_type = 'WIRE'
        return {'FINISHED'}


class TB3_OT_IsolateSubsystem(bpy.types.Operator):
    bl_idname = "tb3.isolate_subsystem"
    bl_label = "Isolate Subsystem"
    subsystem: bpy.props.StringProperty()

    def execute(self, context):
        cols_map = {
            "AIRFRAME": ["Fuselage", "Wings", "Tail", "Structural_Airframe"],
            "PROPULSION": ["Propulsion", "Propulsion_Internal"],
            "AVIONICS": ["Avionics_Electronics"],
            "FUEL": ["Fuel_System"],
            "SENSORS": ["Sensors_Payload"],
        }
        all_cols = ["Fuselage", "Wings", "Tail", "Propulsion", "Landing_Gear", "Sensors_Payload", "Control_Surfaces", "Internal_Systems"]
        if self.subsystem == "ALL":
            for cname in all_cols:
                c = bpy.data.collections.get(cname)
                if c: c.hide_viewport = False
        else:
            targets = cols_map.get(self.subsystem, [])
            for cname in all_cols:
                c = bpy.data.collections.get(cname)
                if c:
                    c.hide_viewport = not (cname in targets)
            int_c = bpy.data.collections.get("Internal_Systems")
            if int_c: int_c.hide_viewport = False
        return {'FINISHED'}


class TB3_OT_SwitchCamera(bpy.types.Operator):
    bl_idname = "tb3.switch_camera"
    bl_label = "Switch Camera"
    camera_name: bpy.props.StringProperty()

    def execute(self, context):
        cam = bpy.data.objects.get(self.camera_name)
        if cam:
            context.scene.camera = cam
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.spaces[0].region_3d.view_perspective = 'CAMERA'
        return {'FINISHED'}


class TB3_OT_ActionFoldWings(bpy.types.Operator):
    bl_idname = "tb3.action_fold_wings"
    bl_label = "Toggle Wing Fold"

    def execute(self, context):
        scene = context.scene
        curr = scene.get("wing_fold", 0.0)
        new_val = 1.0 if curr < 0.5 else 0.0
        scene["wing_fold"] = new_val
        scene.frame_set(60 if new_val == 1.0 else 1)
        return {'FINISHED'}


class TB3_OT_ActionToggleGear(bpy.types.Operator):
    bl_idname = "tb3.action_toggle_gear"
    bl_label = "Toggle Landing Gear"

    def execute(self, context):
        scene = context.scene
        curr = scene.get("gear_retract", 0.0)
        new_val = 1.0 if curr < 0.5 else 0.0
        scene["gear_retract"] = new_val
        scene.frame_set(180 if new_val == 1.0 else 130)
        return {'FINISHED'}


classes = (
    VIEW3D_PT_TB3_DigitalTwin,
    TB3_OT_SetMode,
    TB3_OT_IsolateSubsystem,
    TB3_OT_SwitchCamera,
    TB3_OT_ActionFoldWings,
    TB3_OT_ActionToggleGear,
)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass

if __name__ == "__main__":
    register()
