import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty
import os
import json
import datetime


class AF_Settings(PropertyGroup):
    export_dir: StringProperty(
        name="Export Folder",
        description="Folder to export FBX files into",
        subtype="DIR_PATH",
        default="//Exports"
    )


# Returns mesh stats for mesh after modifiers are applied
# Creates and clears temporary mesh to evaluate mesh statistics 
def get_evaluated_mesh_stats(obj: bpy.types.Object, context) -> dict:
    depsgraph = context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    
    mesh_eval = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    
    try:
        verts = len(mesh_eval.vertices)
        edges = len(mesh_eval.edges)
        polys = len(mesh_eval.polygons)
        
        # Tri count always two less than vertex count per polygon
        tri_count = sum(len(p.vertices) - 2 for p in mesh_eval.polygons)
        return {"vertices": verts, "edges": edges, "faces": polys, "triangles": tri_count}
    finally:
        obj_eval.to_mesh_clear()


def get_active_object() -> bpy.types.Object:
    obj = bpy.context.active_object
    
    if obj is None or obj.type != 'MESH':
        raise RuntimeError("Please select a mesh to export.")
        
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    
    return obj


def export_active_mesh_fbx(export_path: str):
    obj = get_active_object()
    
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


def export_active_mesh_data(export_path: str, context):
    obj = get_active_object()
    stats = get_evaluated_mesh_stats(obj, context)
    
    os.makedirs(os.path.dirname(export_path), exist_ok=True)
    
    mesh_data = {
        "schema": "asset_forge.export",
        "schema_version": "0.1.0",
     
        "source": {
            "blend_file": bpy.data.filepath,
            "object_name": obj.name
        },
        
        "export": {
            "target": "unreal",
            "format": "fbx",
            "export_path": export_path,
            "export_dir": bpy.path.abspath(export_path),
            "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%dT:%H:%M:%SZ%z")
        },
        
        "mesh": {
            "name": obj.name,
            "stats": { **stats }
        }
    }
    
    with open(export_path, 'w') as f:
        json.dump(mesh_data, f)
    

class AF_OT_export(bpy.types.Operator):
    bl_idname = "af.export"
    bl_label = "Export Active Mesh (FBX)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.af
        export_dir = bpy.path.abspath(settings.export_dir)
        
        obj = bpy.context.active_object
        filename = f"{obj.name}.fbx"
        object_export_path = os.path.join(export_dir, filename)
        
        obj_data = f"{obj.name}.json"
        data_export_path = os.path.join(export_dir, obj_data)
       
        try:
            export_active_mesh_fbx(object_export_path)
            export_active_mesh_data(data_export_path, bpy.context)           
                
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        
        self.report({"INFO"}, f"Exported: {object_export_path}")
        return {"FINISHED"}


class AF_PT_panel(bpy.types.Panel):
    bl_label = "Asset Forge"
    bl_idname = "AF_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "AssetForge"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.af
        
        layout.prop(settings, "export_dir")
        layout.separator()
        layout.operator("af.export", text="Export Asset")
