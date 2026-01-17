bl_info = {
  "name": "Asset Forge",
  "author": "Jack Christensen",
  "version": (0, 1, 0),
  "blender": (5, 0, 1),
  "location": "View3D > Sidebar > BtoU",
  "description": "Export bridge from Blender to Unreal Engine",
  "category": "3D View",
}

import bpy
import os

def export_active_mesh_fbx(export_path: str):
    obj = bpy.context.active_object
    
    if obj is None or obj.type != 'MESH':
        raise RuntimeError("Please select the mesh to export.")
        
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    os.makedirs(os.path.dirname(export_path), exist_ok=True)
    
    bpy.ops.export_scene.fbx(
        filepath=export_path,
        use_selection=True,
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',
        object_types={'MESH'},
        use_mesh_modifiers=True,
        add_leaf_bones=False,
        bake_anim=False,
        axis_forward='-Y',
        axis_up='Z'
    )


class AF_OT_export(bpy.types.Operator):
    bl_idname = "af.export"
    bl_label = "Export Active Mesh (FBX)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        export_dir = bpy.path.abspath("//Exports")
        filename = "test1.fbx"
        export_path = os.path.join(export_dir, filename)
        
        try:
            export_active_mesh_fbx(export_path)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        
        self.report({"INFO"}, f"Exported: {export_path}")
        print("Exported:", export_path)
        return {"FINISHED"}


class AF_PT_panel(bpy.types.Panel):
    bl_label = "Asset Forge"
    bl_idname = "AF_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AssetForge"

    def draw(self, context):
        layout = self.layout
        
        layout.label(text="Blender to Unreal Engine Bridge")
        layout.operator("af.export", text="Export Asset")
        

classes = (AF_OT_export, AF_PT_panel)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()