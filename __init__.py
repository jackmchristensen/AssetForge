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

if _needs_reload:
        import importlib
        asset_forge = importlib.reload(asset_forge)

import bpy
from . import (
    asset_forge
)

classes = (asset_forge.AF_OT_export, asset_forge.AF_PT_panel, asset_forge.AF_Settings)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    bpy.types.Scene.af = bpy.props.PointerProperty(type=asset_forge.AF_Settings)


def unregister():
    del bpy.types.Scene.af
    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
