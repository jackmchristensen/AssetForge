import bpy
import os
import json

from typing import Any
from .. import config

def export_active_mesh_fbx(export_path: str, manifest: dict[str, Any] | None, export_ext: str) -> None:
    """Exports current active mesh as fbx. Creates export directory if 
    one doesn't already exist.
    """

    os.makedirs(os.path.dirname(export_path), exist_ok=True)

    if export_ext == "obj":
        bpy.ops.wm.obj_export(
            filepath=export_path,
            export_selected_objects=True,
            apply_modifiers=True,
            export_animation=False,
            apply_transform=True,
            export_materials=False,
            forward_axis=config.get_setting("export.obj_axis_forward", default='NEGATIVE_Y'),
            up_axis=config.get_setting("export.obj_axis_up", default='Z')
        )
    elif export_ext == "fbx":
        bpy.ops.export_scene.fbx(
            filepath=export_path,
            use_selection=True,
            apply_unit_scale=True,
            apply_scale_options="FBX_SCALE_ALL",
            object_types={"MESH"},
            use_mesh_modifiers=True,
            add_leaf_bones=False,
            bake_anim=False,
            axis_forward=config.get_setting("export.fbx_axis_forward", default="-Y"),
            axis_up=config.get_setting("export.fbx_axis_up", default="Z"),
        )

    if manifest is not None:
        mesh = manifest.get("source", {})
        export = manifest.get("export", {})
        if mesh.get("object_name", "") != mesh.get("normalized_name", ""):
            export_dir = export.get("export_dir", "")
            original_file = f"{export_dir}/{mesh.get("object_name", "")}"
            os.rename(f"{original_file}.fbx", f"{export_dir}/{mesh.get("normalized_name", "")}.{export_ext}")
            os.rename(f"{original_file}.json", f"{export_dir}/{mesh.get("normalized_name", "")}.json")


def export_mesh_metadata(export_path: str, mesh_data: dict[str, Any]) -> None:
    """Exports metadata as JSON file. Creates export directory if
    one doesn't currently exist.
    """

    os.makedirs(os.path.dirname(export_path), exist_ok=True)

    with open(export_path, "w") as f:
        json.dump(mesh_data, f)
