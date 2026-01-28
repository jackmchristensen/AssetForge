import bpy
import bmesh

from typing import Any, Callable, Literal
from dataclasses import dataclass

Severity = Literal["error", "warning"]

@dataclass(frozen=True)
class ValidationRule:
    code: str
    message: str
    severity: Severity
    check: Callable[[bpy.types.Object], bool]


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


def generate_validation_data(obj: bpy.types.Object) -> dict[str, Any]:
    rules: list[ValidationRule] = [
        ValidationRule(
            code="MISSING_UV",
            message="No UV map found.",
            severity="error",
            check=validate_mesh_uv
        ),
        ValidationRule(
            code="NON_MANIFOLD",
            message="Mesh has non-manifold geometry.",
            severity="error",
            check=validate_mesh_manifold
        )
    ]

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    for r in rules:
        passed = r.check(obj)
        if passed:
            continue

        item = {"code": r.code, "message": r.message}
        if r.severity == "error":
            errors.append(item)
        else:
            warnings.append(item)

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
    