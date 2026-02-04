from . import naming
from . import validation_types as vt

def validate_mesh_materials(obj_data: vt.ValidationContext) -> list[str]:
    """Return true if object has materials"""

    if obj_data.obj.type == "MESH" and bool(obj_data.obj.data.materials):
        return []
    return ["validate_mesh_materials"]


def validate_file_names(obj_data: vt.ValidationContext) -> list[str]:
    messages: list[str] = []

    if not naming.validate_prefix("SM_", obj_data.obj.name):
        messages.append(f"Static mesh {obj_data.obj.name} does not start with the required prefix 'SM_'")

    for image in obj_data.images:
        if not naming.validate_prefix("T_", image.name):
            messages.append(f"Texture {image.name_full} does not start with the required prefix 'T_'")
    
    for mat in obj_data.materials:
        if not naming.validate_prefix("MI_", mat.name):
            messages.append(f"Material {mat.name} does not start with the required prefix 'MI_'")

    return messages