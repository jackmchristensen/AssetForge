import bpy
import bmesh

from . import validation_types as vt

def validate_mesh_uv(validation_data: vt.ValidationContext) -> list[str]:
    """Return true if object has UVs"""

    obj = validation_data.obj
    
    if obj.type != "MESH":
        return ["Error validating UVs. Asset is not a mesh."]
    
    data = obj.data
    assert isinstance(data, bpy.types.Mesh)

    if validation_data.obj.type == "MESH" and bool(data.uv_layers):
        return []
    return ["Asset is missing UVs."]


def validate_mesh_manifold(validation_data: vt.ValidationContext) -> list[str]:
    """Return true if object is manifold"""

    if validation_data.obj.type != "MESH":
        return ["Error checking if asset is manifold. Asset is not a mesh."]
    
    prev_mode = validation_data.obj.mode
    if prev_mode != "EDIT":
        bpy.ops.object.mode_set(mode="EDIT")

    try:
        # Use bmesh in order to edit selected mesh
        data = validation_data.obj.data
        assert isinstance(data, bpy.types.Mesh)

        mesh: bmesh.types.BMesh = bmesh.from_edit_mesh(data)

        # Make sure nothing in mesh is selected before finding non-
        # manifold geometry
        for v in mesh.verts:
            v.select = False
        for e in mesh.edges:
            e.select = False
        for f in mesh.faces:
            f.select = False
        
        bpy.ops.mesh.select_non_manifold()

        has_nonmanifold: bool = any(v.select for v in mesh.verts) or any(e.select for e in mesh.edges)

        if not has_nonmanifold:
            return []
        return ["Mesh is not manifold"]
    finally:
        if prev_mode != "EDIT":
            bpy.ops.object.mode_set(mode=prev_mode)