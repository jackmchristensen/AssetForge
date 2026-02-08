import bpy
import os
import json

from typing import Any
from .. import config

def export_active_mesh_fbx(export_path: str, manifest: dict[str, Any] | None) -> None:
    """Exports current active mesh as fbx. Creates export directory if 
    one doesn't already exist.
    """

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
        axis_forward=config.get_setting("export.fbx_axis_forward", default="-Y"),
        axis_up=config.get_setting("export.fbx_axis_up", default="Z"),
    )

    if manifest is not None:
        mesh = manifest.get("source", {})
        export = manifest.get("export", {})
        if mesh.get("name", "") != mesh.get("normalized_name", ""):
            original_path = export.get("export_path", "")
            export_dir = export.get("export_dir", "")
            os.rename(original_path, export_dir + "/" + mesh.get("normalized_name", "") + ".fbx")


def export_mesh_metadata(export_path: str, mesh_data: dict[str, Any]) -> None:
    """Exports metadata as JSON file. Creates export directory if
    one doesn't currently exist.
    """

    os.makedirs(os.path.dirname(export_path), exist_ok=True)

    with open(export_path, "w") as f:
        json.dump(mesh_data, f)
