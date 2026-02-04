import bpy

from typing import Callable, Literal
from dataclasses import dataclass

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