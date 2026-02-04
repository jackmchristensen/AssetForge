import bpy
import bmesh

from . import validation_types as vt

def validate_mesh_uv(obj_data: vt.ValidationContext) -> list[str]:
    """Return true if object has UVs"""

    if obj_data.obj.type == "MESH" and bool(obj_data.obj.data.uv_layers):
        return []
    return ["validate_mesh_uv"]


def validate_mesh_manifold(obj_data: vt.ValidationContext) -> list[str]:
    """Return true if object is manifold"""

    if obj_data.obj.type != "MESH":
        return ["validate_mesh_manifold"]
    
    prev_mode = obj_data.obj.mode
    if prev_mode != "EDIT":
        bpy.ops.object.mode_set(mode="EDIT")

    try:
        # Use bmesh in order to edit selected mesh
        mesh: bmesh.types.BMesh = bmesh.from_edit_mesh(obj_data.obj.data)

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
        return ["validate_mesh_manifold"]
    finally:
        if prev_mode != "EDIT":
            bpy.ops.object.mode_set(mode=prev_mode)