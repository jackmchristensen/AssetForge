import bpy
import datetime

from bpy import types as bt
from typing import Any
from ..validation import validate_mesh


def get_evaluated_mesh_stats(obj: bt.Object, context: bt.Context) -> dict[str, int]:
    """Return mesh statistics after all modifiers are evaluated.

    A temporary evaluated mesh is created to compute statistics and is
    cleared before returning.
    """

    depsgraph: Any = context.evaluated_depsgraph_get()
    obj_eval: bt.Object = obj.evaluated_get(depsgraph)

    mesh_eval: bt.Mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

    try:
        verts: int = len(mesh_eval.vertices)
        edges: int = len(mesh_eval.edges)
        polys: int = len(mesh_eval.polygons)

        # Tri count always two less than vertex count per polygon
        tri_count: int = sum(len(p.vertices) - 2 for p in mesh_eval.polygons)
        return {
            "vertices": verts,
            "edges": edges,
            "faces": polys,
            "triangles": tri_count,
        }
    finally:
        obj_eval.to_mesh_clear()


def generate_metadata(obj: bt.Object, export_path: str, context: bt.Context) -> dict[str, Any]:
    """Generate export metadata for a Blender object.

    Builds a JSON-serializable metadata dictionary containing source
    information, export settings, and evaluated mesh statistics.
    """

    stats: dict[str, int] = get_evaluated_mesh_stats(obj, context)

    return {
        "schema": "asset_forge.export",
        "schema_version": "0.1.0",
        "source": {"blend_file": bpy.data.filepath, "object_name": obj.name},
        "export": {
            "target": "unreal",
            "format": "fbx",
            "export_path": export_path,
            "export_dir": bpy.path.abspath(export_path),
            "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).strftime(
                "%Y-%m-%dT:%H:%M:%SZ%z"
            ),
        },
        "mesh": {"name": obj.name, "stats": stats}
    }