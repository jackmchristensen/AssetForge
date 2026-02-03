import bpy

from typing import Any, Callable, Literal
from dataclasses import dataclass
from . import error_checks, warning_checks

Severity = Literal["error", "warning"]

@dataclass(frozen=True)
class ValidationContext:
    obj: bpy.types.Object
    materials: list[bpy.types.Material]
    images: list[bpy.types.Image]

@dataclass(frozen=True)
class ValidationRule:
    code: str
    severity: Severity
    check: Callable[[bpy.types.Object], list[str]]


def _build_context(obj: bpy.types.Object) -> ValidationContext:
    mats = [slot.material for slot in obj.material_slots if slot.material]
    mats = list(dict.fromkeys(mats))

    images = []
    for m in mats:
        if not m.use_nodes or not m.node_tree:
            continue
        for node in m.node_tree.nodes:
            if node.type == "TEX_IMAGE" and node.image:
                images.append(node.image)

    images = list(dict.fromkeys(images))

    return ValidationContext(obj, mats, images)


def generate_validation_data(obj: bpy.types.Object) -> dict[str, Any]:
    """Validates mesh and returns any errors or warnings.
    
    Mesh can pass with warnings but will fail to pass if any errors are found.
    """

    obj_data: ValidationContext = _build_context(obj)

    rules: list[ValidationRule] = [
        ValidationRule(
            code="MISSING_UV",
            severity="error",
            check=error_checks.validate_mesh_uv
        ),
        ValidationRule(
            code="NON_MANIFOLD",
            severity="error",
            check=error_checks.validate_mesh_manifold
        ),
        ValidationRule(
            code="MISSING_MATERIALS",
            severity="warning",
            check=warning_checks.validate_mesh_materials
        ),
        ValidationRule(
            code="BAD_NAME",
            severity="warning",
            check=warning_checks.validate_file_names
        )
    ]

    error_items: list[dict[str, Any]] = []
    warning_items: list[dict[str, Any]] = []

    for r in rules:
        message = r.check(obj_data)
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
    