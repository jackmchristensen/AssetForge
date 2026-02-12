import os
import bpy
import subprocess
import json

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


def make_setting_updater(key_path: str, property_name: str):
    def update_func(self, context):
        value = getattr(self, property_name)
        config.save_setting(key_path, value)
    return update_func


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
    
    export_ext: bpy.props.EnumProperty(
        name="Export As",
        description="Choose what 3D object you'd like to export.",
        items=[
            ("fbx", "FBX", "FBX file"),
            ("obj", "OBJ", "OBJ file")
        ],
        default="fbx"
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

    import_strictness: bpy.props.EnumProperty(
        name="Import Strictness",
        description="How strict validation should be to import into Unreal Editor.",
        items=[
            ("ERRORS_ONLY", "Errors Only", "Do not send to Unreal Editor if asset fails to pass validation."),
            ("ERRORS_AND_WARNINGS", "Errors and Warnings", "Do not send to Unreal Editor if asset fails to pass validation or there are any warngins"),
            ("DO_NOT_IMPORT", "Do Not Import", "Do not send asset to Unreal Editor.")
        ],
        default="ERRORS_ONLY"
    ) # type: ignore

    mesh_prefix: bpy.props.StringProperty(
        name="Mesh Prefix",
        description="Prefix used to denote static mesh assets.",
        default=config.get_setting("naming_conventions.mesh_prefix", "SM_"),
        update=make_setting_updater("naming_conventions.mesh_prefix", "mesh_prefix")
    ) # type: ignore

    texture_prefix: bpy.props.StringProperty(
        name="Texture Prefix",
        description="Prefix used to denote image texture files.",
        default=config.get_setting("naming_conventions.texture_prefix", "T_"),
        update=make_setting_updater("naming_conventions.texture_prefix", "texture_prefix")
    ) # type: ignore

    material_prefix: bpy.props.StringProperty(
        name="Master Material Prefix",
        description="Prefix used to denote master materials.",
        default=config.get_setting("naming_conventions.material_prefix", "M_"),
        update=make_setting_updater("naming_conventions.material_prefix", "material_prefix")
    ) # type: ignore

    material_instance_prefix: bpy.props.StringProperty(
        name="Material Instance Prefix",
        description="Prefix used to denote material instances.",
        default=config.get_setting("naming_conventions.material_instance_prefix", "MI_"),
        update=make_setting_updater("naming_conventions.material_instance_prefix", "material_instance_prefix")
    ) # type: ignore
    
    prop_small_tri_budget: bpy.props.IntProperty(
        name="Triangle Budget",
        description="Triangle budget for small props.",
        default=config.get_setting("asset_budgets.PROP_SMALL.max_triangles", 5000),
        update=make_setting_updater("asset_budgets.PROP_SMALL.max_triangles", "prop_small_tri_budget")
    ) # type: ignore

    prop_small_tex_budget: bpy.props.IntProperty(
        name="Tex Budget (px)",
        description="Image texture budget for small props.",
        default=config.get_setting("asset_budgets.PROP_SMALL.max_texture_size", 2048),
        update=make_setting_updater("asset_budgets.PROP_SMALL.max_texture_size", "prop_small_tex_budget")
    ) # type: ignore
    
    prop_hero_tri_budget: bpy.props.IntProperty(
        name="Triangle Budget",
        description="Triangle budget for hero props.",
        default=config.get_setting("asset_budgets.HERO_PROP.max_triangles", 5000),
        update=make_setting_updater("asset_budgets.HERO_PROP.max_triangles", "prop_hero_tri_budget")
    ) # type: ignore
    
    prop_hero_tex_budget: bpy.props.IntProperty(
        name="Tex Budget (px)",
        description="Image texture budget for hero props.",
        default=config.get_setting("asset_budgets.HERO_PROP.max_texture_size", 4096),
        update=make_setting_updater("asset_budgets.HERO_PROP.max_texture_size", "prop_hero_tex_budget")
    ) # type: ignore
    
    prop_modular_tri_budget: bpy.props.IntProperty(
        name="Triangle Budget",
        description="Triangle budget for modular props.",
        default=config.get_setting("asset_budgets.MODULAR.max_triangles", 5000),
        update=make_setting_updater("asset_budgets.MODULAR.max_triangles", "prop_modular_tri_budget")
    ) # type: ignore

    prop_modular_tex_budget: bpy.props.IntProperty(
        name="Tex Budget (px)",
        description="Image texture budget for modular props.",
        default=config.get_setting("asset_budgets.MODULAR.max_texture_size", 2048),
        update=make_setting_updater("asset_budgets.MODULAR.max_texture_size", "prop_modular_tex_budget")
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

        mesh_data: dict[str, Any] = mesh_metadata.generate_metadata(obj, export_dir, ue_project_path, ue_assets_dir, master_mat_path, settings.asset_type, settings.export_ext, bpy.context)
        mesh_data["validation"] = validate_asset.generate_validation_data(obj, settings.asset_type)

        try:
            mesh_exporter.export_mesh_metadata(data_export_path, mesh_data)
            mesh_exporter.export_active_mesh_fbx(object_export_path, mesh_data, settings.export_ext)

            if settings.import_strictness == "DO_NOT_IMPORT":
                pass
            elif settings.import_strictness == "ERRORS_AND_WARNINGS" and (mesh_data['validation']['warnings'] != [] or not mesh_data['validation']['passed']):
                raise RuntimeError(f"Asset failed validation checks. Errors: {mesh_data['validation']['errors']}. Warnings: {mesh_data['validation']['warnings']}")
            elif not mesh_data['validation']['passed']:
                raise RuntimeError(f"Asset failed validation checks. Errors: {mesh_data['validation']['errors']}")
            else:
                run_ue_import(mesh_data["source"]["normalized_name"], context)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
    
        self.report({"INFO"}, f"Exported: {object_export_path}")
        return {"FINISHED"}


class AF_OT_reset_default(bt.Operator):
    bl_idname: str  = "af.reset_default"
    bl_label: str   = "Reset settings to default"
    bl_options: set = {"REGISTER", "UNDO"}

    def execute(self, context: bt.Context):
        settings: AF_Settings = context.scene.af # type: ignore

        try:
            config.reset_default()
            
            settings.mesh_prefix = config.get_setting("naming_conventions.mesh_prefix", "SM_")
            settings.texture_prefix = config.get_setting("naming_conventions.texture_prefix", "T_")
            settings.material_prefix = config.get_setting("naming_conventions.material_prefix", "M_")
            settings.material_instance_prefix = config.get_setting("naming_conventions.material_instance_prefix", "MI_")

            settings.prop_small_tri_budget = config.get_setting("asset_budgets.prop_small_tri_budget", 5000)
            settings.prop_small_tex_budget = config.get_setting("asset_budgets.prop_small_tex_budget", 2048)
            settings.prop_hero_tri_budget = config.get_setting("asset_budgets.prop_hero_tri_budget", 50000)
            settings.prop_hero_tex_budget = config.get_setting("asset_budgets.prop_hero_tex_budget", 4096)
            settings.prop_modular_tri_budget = config.get_setting("asset_budgets.prop_modular_tri_budget", 2000)
            settings.prop_modular_tex_budget = config.get_setting("asset_budgets.prop_modular_tex_budget", 2048)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        self.report({"INFO"}, "Reset settings to default")
        return{"FINISHED"}



class AF_PT_panel(bt.Panel):
    bl_label       = "Asset Forge"
    bl_idname      = "AF_PT_panel"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "AssetForge"
    bl_order       = 0

    def draw(self, context):
        layout = self.layout
        assert layout is not None

        settings: AF_Settings = context.scene.af # type: ignore
        
        layout.use_property_split = True
        layout.use_property_decorate = True

        layout.prop(settings, "asset_type")
        layout.prop(settings, "export_ext")
        layout.prop(settings, "export_dir")
        layout.separator()
        layout.label(text="Unreal Engine Info:")
        layout.prop(settings, "ue_project_path")
        layout.prop(settings, "ue_master_material")
        layout.separator()
        layout.operator("af.export", text="Export Asset")

        
class AF_PT_Settings(bt.Panel):
    bl_label        = "Settings"
    bl_idname       = "AF_PT_settings"
    bl_space_type   = "VIEW_3D"
    bl_region_type  = "UI"
    bl_category     = "AssetForge"
    bl_order        = 1

    def draw(self, context):
        layout = self.layout
        assert layout is not None

        settings = context.scene.af # type: ignore

        layout.use_property_split = True
        layout.use_property_decorate = True

        layout.label(text="Unreal Engine Project Structure")
        layout.prop(settings, "assets_dir")
        layout.prop(settings, "materials_dir")
        layout.separator()
        layout.prop(settings, "import_strictness")
        layout.separator()
        layout.operator("af.reset_default", text="Reset Settings")


class AF_PT_Naming(bt.Panel):
    bl_label        = "Naming Structure"
    bl_idname       = "AF_PT_naming"
    bl_space_type   = "VIEW_3D"
    bl_region_type  = "UI"
    bl_category     = "AssetForge"
    bl_parent_id    = "AF_PT_settings"
    bl_options      = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        assert layout is not None

        settings = context.scene.af # type: ignore

        layout.use_property_split = True
        layout.use_property_decorate = True

        layout.prop(settings, "mesh_prefix")
        layout.prop(settings, "texture_prefix")
        layout.prop(settings, "material_prefix")
        layout.prop(settings, "material_instance_prefix")


class AF_PT_Budgets(bt.Panel):
    bl_label        = "Asset Budgets"
    bl_idname       = "AF_PT_budgets"
    bl_space_type   = "VIEW_3D"
    bl_region_type  = "UI"
    bl_category     = "AssetForge"
    bl_parent_id    = "AF_PT_settings"
    bl_options      = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        assert layout is not None

        settings = context.scene.af # type: ignore

        layout.use_property_split = True
        layout.use_property_decorate = True

        layout.label(text="Small Prop")
        layout.prop(settings, "prop_small_tri_budget")
        layout.prop(settings, "prop_small_tex_budget")
        layout.label(text="Hero Prop")
        layout.prop(settings, "prop_hero_tri_budget")
        layout.prop(settings, "prop_hero_tex_budget")
        layout.label(text="Modular Prop")
        layout.prop(settings, "prop_modular_tri_budget")
        layout.prop(settings, "prop_modular_tex_budget")
