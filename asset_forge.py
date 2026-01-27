import json
import os
import bpy

from .metadata import statistics


class AF_Settings(bpy.types.PropertyGroup):
    export_dir: bpy.props.StringProperty(
        name="Export Folder",
        description="Folder to export FBX files into",
        subtype="DIR_PATH",
        default="//Exports",
    )  # type: ignore


def get_active_object() -> bpy.types.Object:
    obj = bpy.context.active_object

    if obj is None or obj.type != "MESH":
        raise RuntimeError("Please select a mesh to export.")

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    return obj


def export_active_mesh_fbx(export_path: str):
    obj = get_active_object()

    os.makedirs(os.path.dirname(export_path), exist_ok=True)

    bpy.ops.export_scene.fbx(
        filepath=export_path,
        use_selection=True,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_ALL",
        object_types={"MESH"},
        use_mesh_modifiers=True,
        add_leaf_bones=False,
        bake_anim=False,
        axis_forward="-Y",
        axis_up="Z",
    )


def export_mesh_metadata(export_path: str, mesh_data: dict):
    os.makedirs(os.path.dirname(export_path), exist_ok=True)

    with open(export_path, "w") as f:
        json.dump(mesh_data, f)


class AF_OT_export(bpy.types.Operator):
    bl_idname = "af.export"
    bl_label = "Export Active Mesh (FBX)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.af
        export_dir = bpy.path.abspath(settings.export_dir)

        obj = bpy.context.active_object
        filename = f"{obj.name}.fbx"
        object_export_path = os.path.join(export_dir, filename)

        obj_data = f"{obj.name}.json"
        data_export_path = os.path.join(export_dir, obj_data)

        mesh_data = statistics.generate_metadata(obj, data_export_path, bpy.context)

        try:
            export_active_mesh_fbx(object_export_path)
            export_mesh_metadata(data_export_path, mesh_data)

        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        self.report({"INFO"}, f"Exported: {object_export_path}")
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
