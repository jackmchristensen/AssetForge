import os
import bpy
import subprocess

from bpy import types as bt
from typing import Any
from pathlib import Path
from sys import platform

from .export import mesh_exporter, mesh_metadata
from .validation import validate_asset
from . import config


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
        default=config.get_setting("naming.mesh_prefix", "SM_")
    ) # type: ignore

    texture_prefix: bpy.props.StringProperty(
        name="Texture Prefix",
        description="Prefix used to denote image texture files.",
        default=config.get_setting("naming.texture_prefix", "T_")
    ) # type: ignore

    material_prefix: bpy.props.StringProperty(
        name="Master Material Prefix",
        description="Prefix used to denote master materials.",
        default=config.get_setting("naming.material_prefix", "M_")
    ) # type: ignore

    material_instance_prefix: bpy.props.StringProperty(
        name="Material Instance Prefix",
        description="Prefix used to denote material instances.",
        default=config.get_setting("naming.material_instance_prefix", "MI_")
    ) # type: ignore

    pass


def ensure_active_mesh_object() -> bt.Object:
    obj = bpy.context.active_object

    if obj is None or obj.type != "MESH":
        raise RuntimeError("Please select a mesh to export.")

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    
    view_layer = bpy.context.view_layer
    assert view_layer is not None
    view_layer.objects.active = obj

    return obj


def _get_ue_path() -> str:
    platform_map = {
        "linux": "linux",
        "linux2": "linux",
        "win32": "windows",
        "darwin": "darwin"
    }

    platform_key = platform_map.get(platform, "")
    return config.get_setting(f"unreal_engine.paths.{platform_key}", "")


def run_ue_import(obj_name: str, context: bt.Context) -> None:
    settings: AF_Settings = context.scene.af # type: ignore

    p = Path(__file__).resolve().parent
    engine_script = str(p / "engine" / "ue_import.py")
    export_dir: str = bpy.path.abspath(settings.export_dir)
    project_path: str = bpy.path.abspath(settings.ue_project_path)
    manifest_path: str = os.path.join(export_dir, f"{obj_name}.json")

    kwargs: dict[str, Any] = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "env": os.environ.copy(),
    }
    if platform == "win32":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
        kwargs["close_fds"] = True


    subprocess.Popen([
        _get_ue_path(),
        f"{project_path}",
        f"-ExecutePythonScript={engine_script}",
        f"-manifest={manifest_path}",
        "-unattended -nop4 -nosplash -stdout -FullStdOutLogOutput -log"
        ],
        **kwargs
    )


class AF_OT_export(bt.Operator):
    bl_idname: str  = "af.export"
    bl_label: str   = "Export Active Mesh (FBX)"
    bl_options: set = {"REGISTER", "UNDO"}

    def execute(self, context: bt.Context):
        settings: AF_Settings = context.scene.af # type: ignore
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
        mesh_data["validation"] = validate_asset.generate_validation_data(obj)

        try:
            mesh_exporter.export_active_mesh_fbx(object_export_path)
            mesh_exporter.export_mesh_metadata(data_export_path, mesh_data)

            if not mesh_data["validation"]["passed"]:
                raise RuntimeError(f"Asset failed validation checks. Errors: {mesh_data['validation']['errors']}")
            else:
                run_ue_import(obj.name, context)
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
        layout= self.layout
        assert layout is not None

        settings: AF_Settings = context.scene.af # type: ignore
        
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
        layout= self.layout
        assert layout is not None

        settings = context.scene.af # type: ignore

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
        layout.prop(settings, "material_instance_prefix")


