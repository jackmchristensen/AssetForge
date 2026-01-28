import bpy
import bmesh

def validate_mesh_uv(obj: bpy.types.Object) -> bool:
    """Return true if object has UVs"""

    return obj.type == "MESH" and bool(obj.data.uv_layers)


def validate_mesh_manifold(obj: bpy.types.Object) -> bool:
    """Return true if object is manifold"""

    if obj.type != "MESH":
        return False
    
    prev_mode = obj.mode
    if prev_mode != "EDIT":
        bpy.ops.object.mode_set(mode="EDIT")

    try:
        # Use bmesh in order to edit selected mesh
        mesh: bmesh.types.BMesh = bmesh.from_edit_mesh(obj.data)

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

        return not has_nonmanifold
    finally:
        if prev_mode != "EDIT":
            bpy.ops.object.mode_set(mode=prev_mode)