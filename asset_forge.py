import os
import bpy

from bpy import types as bt
from typing import Any

from .export import metadata, obj_exporter


class AF_Settings(bt.PropertyGroup):
    """User-configurable export settings for Asset Forge."""

    export_dir: bpy.props.StringProperty(
        name="Export Folder",
        description="Folder to export FBX files into",
        subtype="DIR_PATH",
        default="//Exports",
    )  # type: ignore


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

        mesh_data: dict[str, Any] = metadata.generate_metadata(obj, data_export_path, bpy.context)

        try:
            obj_exporter.export_active_mesh_fbx(object_export_path)
            obj_exporter.export_mesh_metadata(data_export_path, mesh_data)

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

        layout.prop(settings, "export_dir")
        layout.separator()
        layout.operator("af.export", text="Export Asset")
