import bpy
import os
import json

from typing import Any

def export_active_mesh_fbx(export_path: str) -> None:
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
        axis_forward="-Y",
        axis_up="Z",
    )


def export_mesh_metadata(export_path: str, mesh_data: dict[str, Any]) -> None:
    """Exports metadata as JSON file. Creates export directory if
    one doesn't currently exist.
    """

    os.makedirs(os.path.dirname(export_path), exist_ok=True)

    with open(export_path, "w") as f:
        json.dump(mesh_data, f)