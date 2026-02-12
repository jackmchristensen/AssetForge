import bpy
import bmesh

from . import validation_types as vt
from .. import config
from typing import Tuple
from mathutils import Vector

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


def _eval_object_bounds_local(obj: bpy.types.Object) -> Tuple[Vector, Vector] | None:
    """Returns (min_v, max_v) of the evaluated mesh in object space.

    Works even if modifiers are present.
    """

    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)

    if obj_eval.type != "MESH":
        return None

    mesh = obj_eval.to_mesh(preserve_all_data_layers=False)
    try:
        if not mesh.vertices:
            return None

        min_v = Vector((float("inf"), float("inf"), float("inf")))
        max_v = Vector((float("-inf"), float("-inf"), float("-inf")))

        for v in mesh.vertices:
            co = v.co 
            min_v.x = min(min_v.x, co.x)
            min_v.y = min(min_v.y, co.y)
            min_v.z = min(min_v.z, co.z)
            max_v.x = max(max_v.x, co.x)
            max_v.y = max(max_v.y, co.y)
            max_v.z = max(max_v.z, co.z)

        return min_v, max_v
    finally:
        obj_eval.to_mesh_clear()


def _is_multiple(x: float, unit: float = 0.1, eps: float = 1e-5) -> bool:
    if unit == 0:
        return False

    n = x / unit
    return abs(n - round(n)) <= eps


def validate_modular(validation_data: vt.ValidationContext) -> list[str]:
    if validation_data.obj_type != "MODULAR":
        return []

    messages: list[str] = []
    unit: float = config.get_setting("modular_mesh_units.unit", 0.1)
    eps: float = config.get_setting("modular_mesh_units.eps", 1e-5)

    bounds = _eval_object_bounds_local(validation_data.obj)

    assert bounds is not None
    min_v, max_v = bounds
    size = max_v - min_v

    if not _is_multiple(size.x, unit, eps):
        messages.append(f"Width is not a multiple of {unit}")
    if not _is_multiple(size.y, unit, eps):
        messages.append(f"Depth is not a multiple of {unit}")
    if not _is_multiple(size.z, unit, eps):
        messages.append(f"Height is not a multiple of {unit}")

    pivot_ok: bool = (
        abs(min_v.x) <= eps and
        abs(min_v.y) <= eps and
        abs(min_v.z) <= eps
    )

    if not pivot_ok:
        messages.append("Pivot not aligned to corner")

    return messages
