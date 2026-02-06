import bpy

from . import naming
from . import validation_types as vt
from .. import config

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


# TODO implement mesh types
# def validate_triangle_budget(validation_data: vt.ValidationContext) -> list[str]:
#     if validation_data.obj.type != "MESH":
#         return ["Error validating triangle budget. Asset is not a mesh."]
#
#     data = validation_data.obj.data
#     assert isinstance(data, bpy.types.Mesh)
#
#     triangle_count = sum(len(p.vertices) - 2 for p in data.polygons)
#     budget = config.get_setting("asset_budgets.PROP_SMALL.max_triangles", 5000)
#
#     if triangle_count > budget:
#         return [f"Mesh has {triangle_count} triangles, which exceeds the budget of {budget}."]
#
#     return []
