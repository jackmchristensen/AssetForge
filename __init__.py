bl_info = {
  "name": "Asset Forge",
  "author": "Jack Christensen",
  "version": (0, 1, 0),
  "blender": (5, 0, 1),
  "location": "View3D > Sidebar > AssetForge",
  "description": "Export bridge from Blender to Unreal Engine",
  "category": "3D View"
}

_needs_reload = "asset_forge" in locals()

import bpy

from . import config

from .export import (
    mesh_exporter,
    mesh_metadata
)
from .validation import (
    error_checks,
    validate_asset,
    warning_checks,
    naming,
    validation_types
)
from . import (
    asset_forge
)

if _needs_reload:
    import importlib
    config = importlib.reload(config)
    config.reload_settings()
    asset_forge = importlib.reload(asset_forge)
    mesh_metadata = importlib.reload(mesh_metadata)
    mesh_exporter = importlib.reload(mesh_exporter)
    validate_asset = importlib.reload(validate_asset)
    error_checks = importlib.reload(error_checks)
    warning_checks = importlib.reload(warning_checks)
    naming = importlib.reload(naming)
    validation_types = importlib.reload(validation_types)

classes = (asset_forge.AF_OT_export, asset_forge.AF_PT_panel, asset_forge.AF_Settings, asset_forge.AF_PT_Settings)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.af = bpy.props.PointerProperty(type=asset_forge.AF_Settings) # type: ignore


def unregister():
    del bpy.types.Scene.af # type: ignore
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
