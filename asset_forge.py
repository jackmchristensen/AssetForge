import os
import bpy

from bpy import types as bt
from typing import Any

from .export import mesh_exporter, mesh_metadata
from .validation import validate_mesh

def update_export_dir(self, context):
    if self.export_dir:
        self.export_dir = bpy.path.abspath(self.export_dir)


class AF_Settings(bt.PropertyGroup):
    """User-configurable export settings for Asset Forge."""

    export_dir: bpy.props.StringProperty(
        name="Export Folder",
        description="Folder to export FBX files to.\nSupports relative paths using '//'.",
        subtype="DIR_PATH",
        default="",
        update=update_export_dir
    ) # type: ignore

    engine_dir: bpy.props.StringProperty(
        name="UE Project Folder",
        description="Folder containing Unreal Engine project to export to.",
        subtype="DIR_PATH",
        default=""
    ) # type: ignore

    asset_type: bpy.props.EnumProperty(
        name="Asset Type",
        description="Choose validation/export profile.",
        items=[
            ("PROP_SMALL", "Small Prop", "Small environment prop (tight budgets)"),
            ("HERO_PROP", "Hero Prop", "Close-up prop (higher budgets)"),
            ("MODULAR", "Modular", "Modular kit piece (grid/scale rules)")
        ],
        default="PROP_SMALL"
    ) # type: ignore


def ensure_active_mesh_object() -> bt.Object:
    obj = bpy.context.active_object

    if obj is None or obj.type != "MESH":
        raise RuntimeError("Please select a mesh to export.")

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    return obj


class AF_OT_export(bt.Operator):
    bl_idname: str  = "af.export"
    bl_label: str   = "Export Active Mesh (FBX)"
    bl_options: set = {"REGISTER", "UNDO"}

    def execute(self, context: bt.Context):
        settings: AF_Settings = context.scene.af
        export_dir: str = bpy.path.abspath(settings.export_dir)

        obj: bt.Object = ensure_active_mesh_object()
        filename: str = f"{obj.name}.fbx"
        object_export_path: str = os.path.join(export_dir, filename)

        obj_data: str = f"{obj.name}.json"
        data_export_path: str = os.path.join(export_dir, obj_data)

        mesh_data: dict[str, Any] = mesh_metadata.generate_metadata(obj, export_dir, bpy.context)
        mesh_data["validation"] = validate_mesh.generate_validation_data(obj)

        try:
            mesh_exporter.export_active_mesh_fbx(object_export_path)
            mesh_exporter.export_mesh_metadata(data_export_path, mesh_data)

        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        self.report({"INFO"}, f"Exported: {object_export_path}")
        return {"FINISHED"}


class AF_PT_panel(bt.Panel):
    bl_label: str       = "Asset Forge"
    bl_idname: str      = "AF_PT_panel"
    bl_space_type: str  = "VIEW_3D"
    bl_region_type: str = "UI"
    bl_category: str    = "AssetForge"

    def draw(self, context):
        layout: bt.UILayout = self.layout
        settings: AF_Settings = context.scene.af
        
        layout.use_property_split = True
        layout.use_property_decorate = True

        layout.prop(settings, "asset_type")
        layout.prop(settings, "export_dir")
        layout.prop(settings, "engine_dir")
        layout.separator()
        layout.operator("af.export", text="Export Asset")
