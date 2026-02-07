import bpy

from typing import Any
from . import error_checks, warning_checks
from . import validation_types as vt

def _build_context(obj: bpy.types.Object, asset_type: str) -> vt.ValidationContext:
    mats = [slot.material for slot in obj.material_slots if slot.material]
    mats = list(dict.fromkeys(mats))

    images = []
    for m in mats:
        if not m.use_nodes or not m.node_tree:
            continue
        for node in m.node_tree.nodes:
            if isinstance(node, bpy.types.ShaderNodeTexImage):
                images.append(node.image)

    images = list(dict.fromkeys(images))

    return vt.ValidationContext(obj, asset_type, mats, images)


def generate_validation_data(obj: bpy.types.Object, asset_type: str) -> dict[str, Any]:
    """Validates mesh and returns any errors or warnings.
    
    Mesh can pass with warnings but will fail to pass if any errors are found.
    """

    obj_data: vt.ValidationContext = _build_context(obj, asset_type)

    rules: list[vt.ValidationRule] = [
        vt.ValidationRule(
            code="MISSING_UV",
            severity="error",
            check=error_checks.validate_mesh_uv # type: ignore
        ),
        vt.ValidationRule(
            code="NON_MANIFOLD",
            severity="error",
            check=error_checks.validate_mesh_manifold # type: ignore
        ),
        vt.ValidationRule(
            code="MISSING_MATERIALS",
            severity="warning",
            check=warning_checks.validate_mesh_materials # type: ignore
        ),
        vt.ValidationRule(
            code="BAD_NAME",
            severity="warning",
            check=warning_checks.validate_file_names # type: ignore
        ),
        vt.ValidationRule(
            code="OVER_TRIANGLE_BUDGET",
            severity="warning",
            check=warning_checks.validate_triangle_budget # type: ignore
        ),
        vt.ValidationRule(
            code="TEXTURE_NOT_SQUARE",
            severity="warning",
            check=warning_checks.validate_texture_aspect_ratio # type: ignore
        ),
        vt.ValidationRule(
            code="OVER_TEXTURE_BUDGET",
            severity="warning",
            check=warning_checks.validate_texture_size # type: ignore
        ),
    ]

    error_items: list[dict[str, Any]] = []
    warning_items: list[dict[str, Any]] = []

    for r in rules:
        message = r.check(obj_data) # type: ignore
        if message == []:
            continue

        item = {"code": r.code, "message": message}
        if r.severity == "error":
            error_items.append(item)
        else:
            warning_items.append(item)

    return {
        "passed": len(error_items) == 0,
        "errors": error_items,
        "warnings": warning_items,
    }
    
