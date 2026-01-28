import bpy

from typing import Any, Callable, Literal
from dataclasses import dataclass
from . import error_checks, warning_checks

Severity = Literal["error", "warning"]

@dataclass(frozen=True)
class ValidationRule:
    code: str
    message: str
    severity: Severity
    check: Callable[[bpy.types.Object], bool]


def generate_validation_data(obj: bpy.types.Object) -> dict[str, Any]:
    """Validates mesh and returns any errors or warnings.
    
    Mesh can pass with warnings but will fail to pass if any errors are found.
    """

    rules: list[ValidationRule] = [
        ValidationRule(
            code="MISSING_UV",
            message="No UV map found.",
            severity="error",
            check=error_checks.validate_mesh_uv
        ),
        ValidationRule(
            code="NON_MANIFOLD",
            message="Mesh has non-manifold geometry.",
            severity="error",
            check=error_checks.validate_mesh_manifold
        ),
        ValidationRule(
            code="MISSING_MATERIALS",
            message="Mesh has no materials assigned to it.",
            severity="warning",
            check=warning_checks.validate_mesh_materials
        )
    ]

    error_items: list[dict[str, Any]] = []
    warning_items: list[dict[str, Any]] = []

    for r in rules:
        passed = r.check(obj)
        if passed:
            continue

        item = {"code": r.code, "message": r.message}
        if r.severity == "error":
            error_items.append(item)
        else:
            warning_items.append(item)

    return {
        "passed": len(error_items) == 0,
        "errors": error_items,
        "warnings": warning_items,
    }
    