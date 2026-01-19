import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty

import os

class AF_Settings(PropertyGroup):
    export_dir: StringProperty(
        name="Export Folder",
        description="Folder to export FBX files into",
        subtype="DIR_PATH",
        default="//Exports"
    )

def export_active_mesh_fbx(export_path: str):
    obj = bpy.context.active_object
    
    if obj is None or obj.type != 'MESH':
        raise RuntimeError("Please select the mesh to export.")
        
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    os.makedirs(os.path.dirname(export_path), exist_ok=True)
    
    bpy.ops.export_scene.fbx(
        filepath=export_path,
        use_selection=True,
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',
        object_types={'MESH'},
        use_mesh_modifiers=True,
        add_leaf_bones=False,
        bake_anim=False,
        axis_forward='-Y',
        axis_up='Z'
    )


class AF_OT_export(bpy.types.Operator):
    bl_idname = "af.export"
    bl_label = "Export Active Mesh (FBX)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.af
        export_dir = bpy.path.abspath(settings.export_dir)
        
        obj = bpy.context.active_object
        filename = f"{obj.name}.fbx"
        export_path = os.path.join(export_dir, filename)
        
        try:
            export_active_mesh_fbx(export_path)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        
        self.report({"INFO"}, f"Exported: {export_path}")
        return {"FINISHED"}


class AF_PT_panel(bpy.types.Panel):
    bl_label = "Asset Forge"
    bl_idname = "AF_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AssetForge"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.af
        
        layout.prop(settings, "export_dir")
        layout.separator()
        layout.operator("af.export", text="Export Asset")
