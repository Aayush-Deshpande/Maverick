import bpy
import math

def update_wing_fold(self, context):
    ctrl = bpy.data.objects.get("CTRL_Wing_Fold")
    if ctrl:
        ctrl.location.z = 3.0 + self.tb3_wing_fold * 1.0
        if context and context.view_layer:
            context.view_layer.update()

def update_gear_retract(self, context):
    ctrl = bpy.data.objects.get("CTRL_Gear_Retract")
    if ctrl:
        ctrl.location.z = 3.0 + self.tb3_gear_retract * 1.0
        if context and context.view_layer:
            context.view_layer.update()

class TB3_PT_Controller(bpy.types.Panel):
    bl_label = "Bayraktar TB3 Digital Twin"
    bl_idname = "VIEW3D_PT_tb3_controller"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Bayraktar TB3"

    @classmethod
    def poll(cls, context):
        return bpy.data.objects.get("CTRL_Wing_Fold") is not None or bpy.data.objects.get("TB3_Root") is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Display Modes
        col = layout.column(align=True)
        col.label(text="Display Modes:", icon='RESTRICT_VIEW_OFF')
        row = col.row(align=True)
        row.operator("tb3.set_mode", text="Tactical PBR (image.png)").mode = 0
        row.operator("tb3.set_mode", text="Wireframe (fdda)").mode = 1
        col.operator("tb3.set_mode", text="X-Ray Digital Twin").mode = 2

        layout.separator()
        # Preset Cameras
        col = layout.column(align=True)
        col.label(text="Preset Cameras:", icon='CAMERA_DATA')
        row = col.row(align=True)
        row.operator("tb3.set_cam", text="Hero image.png").cam_name = "Cam_Hero_Image_PNG"
        row.operator("tb3.set_cam", text="Wireframe fdda").cam_name = "Cam_Wireframe_FDDA"

        layout.separator()
        # Carrier Wing Fold
        box_w = layout.box()
        box_w.label(text="Carrier Wing Fold (TCG Anadolu):", icon='ORIENTATION_GIMBAL')
        row_w = box_w.row(align=True)
        row_w.operator("tb3.wing_action", text="🛫 Unfold Wings").action = "UNFOLD"
        row_w.operator("tb3.wing_action", text="🚢 Fold 115°").action = "FOLD"
        box_w.prop(scene, "tb3_wing_fold", text="Fold Slider", slider=True)

        layout.separator()
        # Landing Gear System
        box_g = layout.box()
        box_g.label(text="Landing Gear System:", icon='MOD_PHYSICS')
        row_g = box_g.row(align=True)
        row_g.operator("tb3.gear_action", text="🛞 Lower Gear").action = "LOWER"
        row_g.operator("tb3.gear_action", text="✈ Retract Gear").action = "RETRACT"
        box_g.prop(scene, "tb3_gear_retract", text="Gear Retract", slider=True)

class TB3_OT_WingAction(bpy.types.Operator):
    bl_idname = "tb3.wing_action"
    bl_label = "Wing Fold Action"
    action: bpy.props.StringProperty()

    def execute(self, context):
        if self.action == "FOLD":
            context.scene.tb3_wing_fold = 1.0
        elif self.action == "UNFOLD":
            context.scene.tb3_wing_fold = 0.0
        return {'FINISHED'}

class TB3_OT_GearAction(bpy.types.Operator):
    bl_idname = "tb3.gear_action"
    bl_label = "Gear Retraction Action"
    action: bpy.props.StringProperty()

    def execute(self, context):
        if self.action == "RETRACT":
            context.scene.tb3_gear_retract = 1.0
        elif self.action == "LOWER":
            context.scene.tb3_gear_retract = 0.0
        return {'FINISHED'}

class TB3_OT_SetMode(bpy.types.Operator):
    bl_idname = "tb3.set_mode"
    bl_label = "Set Display Mode"
    mode: bpy.props.IntProperty(default=0)

    def execute(self, context):
        mat_pbr = bpy.data.materials.get("TB3_Tactical_PBR")
        mat_wire = bpy.data.materials.get("TB3_Wireframe_Clay")
        col_internal = bpy.data.collections.get("Internal_Systems")

        target_mat = mat_wire if self.mode == 1 else mat_pbr
        target_objs = ["Fuselage", "Wing_Inner_Left", "Wing_Inner_Right", "Wing_Outer_Left", "Wing_Outer_Right",
                       "Tail_Boom_Left", "Tail_Boom_Right", "Fin_Left", "Fin_Right", "Inverted_V_Stabilizer"]
        for oname in target_objs:
            obj = bpy.data.objects.get(oname)
            if obj and obj.data.materials:
                obj.data.materials[0] = target_mat

        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                for mod in obj.modifiers:
                    if mod.type == 'SUBSURF':
                        mod.levels = 0

        if mat_pbr and mat_pbr.node_tree:
            val_xray = mat_pbr.node_tree.nodes.get("XRayFactor")
            if val_xray:
                val_xray.outputs['Value'].default_value = 1.0 if self.mode == 2 else 0.0

        if col_internal:
            col_internal.hide_viewport = (self.mode != 2)

        self.report({'INFO'}, f"TB3 Display Mode set to {self.mode}")
        return {'FINISHED'}

class TB3_OT_SetCam(bpy.types.Operator):
    bl_idname = "tb3.set_cam"
    bl_label = "Set Active Camera"
    cam_name: bpy.props.StringProperty()

    def execute(self, context):
        cam = bpy.data.objects.get(self.cam_name)
        if cam and cam.type == 'CAMERA':
            context.scene.camera = cam
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.spaces.active.region_3d.view_perspective = 'CAMERA'
        return {'FINISHED'}

@bpy.app.handlers.persistent
def tb3_frame_change_handler(scene):
    ctrl_w = bpy.data.objects.get("CTRL_Wing_Fold")
    if ctrl_w:
        fold_val = max(0.0, min(1.0, ctrl_w.location.z - 3.0))
        if abs(scene.get("tb3_wing_fold", 0.0) - fold_val) > 0.01:
            scene["tb3_wing_fold"] = fold_val

    ctrl_g = bpy.data.objects.get("CTRL_Gear_Retract")
    if ctrl_g:
        gear_val = max(0.0, min(1.0, ctrl_g.location.z - 3.0))
        if abs(scene.get("tb3_gear_retract", 0.0) - gear_val) > 0.01:
            scene["tb3_gear_retract"] = gear_val

classes = [
    TB3_PT_Controller,
    TB3_OT_SetMode,
    TB3_OT_SetCam,
    TB3_OT_WingAction,
    TB3_OT_GearAction,
]

def register():
    if hasattr(bpy.types.Scene, "tb3_wing_fold"):
        try:
            del bpy.types.Scene.tb3_wing_fold
        except Exception:
            pass
    if hasattr(bpy.types.Scene, "tb3_gear_retract"):
        try:
            del bpy.types.Scene.tb3_gear_retract
        except Exception:
            pass

    bpy.types.Scene.tb3_wing_fold = bpy.props.FloatProperty(
        name="Carrier Wing Fold",
        description="Fold wings 0 to 115 degrees for TCG Anadolu naval carrier elevator stowage",
        min=0.0, max=1.0, default=0.0,
        update=update_wing_fold
    )
    bpy.types.Scene.tb3_gear_retract = bpy.props.FloatProperty(
        name="Gear Retract",
        description="Retract landing gear flush into belly wells",
        min=0.0, max=1.0, default=0.0,
        update=update_gear_retract
    )

    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception:
            pass

    if tb3_frame_change_handler not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(tb3_frame_change_handler)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
    if tb3_frame_change_handler in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(tb3_frame_change_handler)

if __name__ == "__main__":
    register()
