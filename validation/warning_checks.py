import bpy

def validate_mesh_materials(obj: bpy.types.Object) -> bool:
    """Return true if object has materials"""

    return obj.type == "MESH" and bool(obj.data.materials)