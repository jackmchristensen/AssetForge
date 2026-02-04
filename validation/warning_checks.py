import bpy

from . import naming
from . import validation_types as vt

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

    if not naming.validate_prefix("SM_", validation_data.obj.name):
        messages.append(f"Static mesh {validation_data.obj.name} does not start with the required prefix 'SM_'")

    for image in validation_data.images:
        if not naming.validate_prefix("T_", image.name):
            messages.append(f"Texture {image.name_full} does not start with the required prefix 'T_'")
    
    for mat in validation_data.materials:
        if not naming.validate_prefix("MI_", mat.name):
            messages.append(f"Material {mat.name} does not start with the required prefix 'MI_'")

    return messages