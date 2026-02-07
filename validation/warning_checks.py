import bpy

from typing import Any

from . import naming
from . import validation_types as vt
from .. import config

def _get_evaluated_mesh_stats(obj: bpy.types.Object, context: bpy.types.Context) -> dict[str, int]:
    """Return mesh statistics after all modifiers are evaluated.

    A temporary evaluated mesh is created to compute statistics and is
    cleared before returning.
    """

    depsgraph: Any = context.evaluated_depsgraph_get()
    obj_eval: bpy.types.Object = obj.evaluated_get(depsgraph)

    mesh_eval: bpy.types.Mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

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


def validate_mesh_materials(validation_data: vt.ValidationContext) -> list[str]:
    """Return true if object has materials"""

    obj = validation_data.obj
    
    if obj.type != "MESH":
        return ["Error validating materials. Asset is not a mesh."]
   
    data = obj.data
    assert isinstance(data, bpy.types.Mesh)

    if bool(data.materials):
        return[]
    
    return ["Mesh does not have any assigned materials."]


def validate_file_names(validation_data: vt.ValidationContext) -> list[str]:
    messages: list[str] = []

    if not naming.validate_prefix(config.get_setting("naming_conventions.mesh_prefix", "SM_"), validation_data.obj.name):
        messages.append(f"Static mesh {validation_data.obj.name} does not start with the required prefix '{config.get_setting("naming_conventions.mesh_prefix", "SM_")}'")

    for image in validation_data.images:
        if not naming.validate_prefix(config.get_setting("naming_conventions.texture_prefix", "T_"), image.name):
            messages.append(f"Texture {image.name_full} does not start with the required prefix '{config.get_setting("naming_conventions.texture_prefix", "T_")}'")
    
    for mat in validation_data.materials:
        if not naming.validate_prefix(config.get_setting("naming_conventions.material_instance_prefix", "MI_"), mat.name):
            messages.append(f"Material {mat.name} does not start with the required prefix '{config.get_setting("naming_conventions.material_instance_prefix", "MI_")}'")
    return messages


def validate_triangle_budget(validation_data: vt.ValidationContext) -> list[str]:
    if validation_data.obj.type != "MESH":
        return ["Error validating triangle budget. Asset is not a mesh."]

    data = validation_data.obj.data
    assert isinstance(data, bpy.types.Mesh)

    evalutaed_stats: dict[str, Any] = _get_evaluated_mesh_stats(validation_data.obj, bpy.context)

    budget = config.get_setting(f"asset_budgets.{validation_data.obj_type}.max_triangles", None)
    assert budget is not None, f"No triangle budget set for asset type {validation_data.obj_type}"

    if evalutaed_stats["triangles"] > budget:
        return [f"Mesh has {evalutaed_stats['triangles']} triangles, which exceeds the budget of {budget} for asset type {validation_data.obj_type}."]

    return []


def validate_texture_aspect_ratio(validation_data: vt.ValidationContext) -> list[str]:
    messages: list[str] = []

    for image in validation_data.images:
        if image.size[0] != image.size[1]:
            messages.append(f"Image texture {image.name_full} does not have a square aspect ratio. {image.name_full} aspect ratio is {image.size[0] / image.size[1]}.")

    return messages


def validate_texture_size(validation_data: vt.ValidationContext) -> list[str]:
    messages: list[str] = []
    budget: int = config.get_setting(f"asset_budgets.{validation_data.obj_type}.max_texture_size")

    for image in validation_data.images:
        if image.size[0] > budget:
            messages.append(f"Image texture {image.name_full} has size of {image.size[0]}px, which exceeds the budget of {budget}px for asset type {validation_data.obj_type}.")

    return messages
