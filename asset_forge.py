import os
import bpy
import subprocess
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

    ue_project_path: bpy.props.StringProperty(
        name="UE Project File",
        description="Unreal Project you want to export the asset to.",
        subtype="FILE_PATH",
        default="",
    ) # type: ignore

    ue_master_material: bpy.props.StringProperty(
        name="Master Material",
        description="Unreal master material you want to instance.\nLeave blank if you do not want to instance a material.",
        default="",
    ) # type: ignore

    materials_dir: bpy.props.StringProperty(
        name="Materials Folder",
        description="The folder in your Unreal Engine project where materials are stored.",
        default="Materials"
    ) # type: ignore

    assets_dir: bpy.props.StringProperty(
        name="Assets Folder",
        description="The folder in your Unreal Engine project where assets are stored.",
        default="Assets"
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

    mesh_prefix: bpy.props.StringProperty(
        name="Mesh Prefix",
        description="Prefix used to denote static mesh assets.",
        default="SM_"
    ) # type: ignore

    texture_prefix: bpy.props.StringProperty(
        name="Texture Prefix",
        description="Prefix used to denote image texture files.",
        default="T_"
    ) # type: ignore

    material_prefix: bpy.props.StringProperty(
        name="Master Material Prefix",
        description="Prefix used to denote master materials.",
        default="M_"
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
        ue_project_path: str = bpy.path.abspath(settings.ue_project_path)

        obj: bt.Object = ensure_active_mesh_object()
        filename: str = f"{obj.name}.fbx"
        object_export_path: str = os.path.join(export_dir, filename)

        obj_data: str = f"{obj.name}.json"
        data_export_path: str = os.path.join(export_dir, obj_data)

        ue_assets_dir: str = f"/Game/{settings.assets_dir}"
        master_mat_path: str = ""
        if settings.ue_master_material != "":
            master_mat_path = f"/Game/{settings.materials_dir}/{settings.ue_master_material}"

        mesh_data: dict[str, Any] = mesh_metadata.generate_metadata(obj, export_dir, ue_project_path, ue_assets_dir, master_mat_path, bpy.context)
        mesh_data["validation"] = validate_mesh.generate_validation_data(obj)

        try:
            mesh_exporter.export_active_mesh_fbx(object_export_path)
            mesh_exporter.export_mesh_metadata(data_export_path, mesh_data)

        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        
        subprocess.Popen([
            "/home/jchristensen/opt/unreal/Linux_Unreal_Engine_5.7.2/Engine/Binaries/Linux/UnrealEditor",
            settings.ue_project_path,
            "-ExecutePythonScript=/home/jchristensen/.config/blender/5.0/scripts/addons/asset_forge/engine/ue_import.py",
            f"-manifest={settings.export_dir}/{obj.name}.json",
            "-unattended -nop4 -nosplash -stdout -FullStdOutLogOutput -log"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # Linux: detach from Blender session
            close_fds=True,
            env=os.environ.copy(),
        )

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
        layout.separator()
        layout.label(text="Unreal Engine Info:")
        layout.prop(settings, "ue_project_path")
        layout.prop(settings, "ue_master_material")
        layout.separator()
        layout.operator("af.export", text="Export Asset")

        
class AF_PT_Settings(bt.Panel):
    bl_label = "Settings"
    bl_idname = "AF_PT_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Asset Forge"
    bl_parent_id = "AF_PT_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        settings = context.scene.af

        layout.use_property_split = True
        layout.use_property_decorate = True

        layout.label(text="Unreal Engine Project Structure:")
        layout.prop(settings, "assets_dir")
        layout.prop(settings, "materials_dir")
        layout.separator()
        layout.label(text="Naming Structure:")
        layout.prop(settings, "mesh_prefix")
        layout.prop(settings, "texture_prefix")
        layout.prop(settings, "material_prefix")