import bpy
import datetime
import os

from bpy import types as bt
from typing import Any

def get_evaluated_mesh_stats(obj: bt.Object, context: bt.Context) -> dict[str, int]:
    """Return mesh statistics after all modifiers are evaluated.

    A temporary evaluated mesh is created to compute statistics and is
    cleared before returning.
    """

    depsgraph: Any = context.evaluated_depsgraph_get()
    obj_eval: bt.Object = obj.evaluated_get(depsgraph)

    mesh_eval: bt.Mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

    try:
        verts: int = len(mesh_eval.vertices)
        edges: int = len(mesh_eval.edges)
        polys: int = len(mesh_eval.polygons)

        # Tri count always two less than vertex count per polygon
        tri_count: int = sum(len(p.vertices) - 2 for p in mesh_eval.polygons)
        return {
            "vertices": verts,
            "edges": edges,
            "faces": polys,
            "triangles": tri_count,
        }
    finally:
        obj_eval.to_mesh_clear()


def _get_shader_connected_to_output(mat: bt.Material):
    """Returns Principled BSDF node.
    
    Currently returns first found Principled BSDF node
    
    TODO Check if Principled BSDF node is connected to output node. Return nothing if not or doesn't exist.
    """
    tree = mat.node_tree
    shader = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"))
    return shader


def _classify_shader_input(sock: bt.NodeSocket) -> dict[str, Any]:
    """Returns material input data.
    
    Returns constant value if no nodes are used.
    If image texture is used returns image's path and color space.
    If another node is used returns 'complex' type and no other data.
    
    TODO Normal map image texture special case (includes intermediary node)
    """

    if not sock.is_linked:
        try:
            val = list(sock.default_value)[:3]
        except TypeError:
            val = sock.default_value
        return { "type": "constant", "value": val }
    
    from_node = sock.links[0].from_node

    if from_node.type == "TEX_IMAGE" and from_node.image:
        image = from_node.image
        return {
            "type": "texture",
            "path": bpy.path.abspath(image.filepath),
            "color_space": image.colorspace_settings.name
        }
    
    return { "type": "complex" }



def get_material_data(obj: bt.Object) -> list[dict[str, Any]]:
    materials: list[dict[str, Any]] = []

    for mat in obj.material_slots:
        shader = _get_shader_connected_to_output(mat.material)

        base_color          = shader.inputs.get("Base Color")
        roughness           = shader.inputs.get("Roughness")
        metallic            = shader.inputs.get("Metallic")
        normal              = shader.inputs.get("Normal")
        emission_color      = shader.inputs.get("Emission Color")
        alpha               = shader.inputs.get("Alpha")

        mat_data: dict[str, Any] = { "name": mat.material.name }

        mat_data["base_color"]      = _classify_shader_input(base_color)
        mat_data["roughness"]       = _classify_shader_input(roughness)
        mat_data["metallic"]        = _classify_shader_input(metallic)
        mat_data["normal"]          = _classify_shader_input(normal)
        mat_data["emission_color"]  = _classify_shader_input(emission_color)
        mat_data["alpha"]           = _classify_shader_input(alpha)

        materials.append(mat_data)
        

    return materials


def generate_metadata(obj: bt.Object, export_dir: str, context: bt.Context) -> dict[str, Any]:
    """Generate export metadata for a Blender object.

    Builds a JSON-serializable metadata dictionary containing source
    information, export settings, and evaluated mesh statistics.
    """

    filename: str = f"{obj.name}.fbx"
    export_path: str = os.path.join(export_dir, filename)

    stats: dict[str, int] = get_evaluated_mesh_stats(obj, context)
    
    materials: list[dict[str, Any]] = get_material_data(obj) 

    return {
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
            "export_dir": export_dir,
            "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).strftime(
                "%Y-%m-%dT:%H:%M:%SZ%z"
            ),
        },
        "mesh": {
            "name": obj.name,
            "material_count": len(materials),
            "stats": {
                "original": {
                    "vertices": len(obj.data.vertices),
                    "edges": len(obj.data.edges),
                    "faces": len(obj.data.polygons),
                    "triangles": sum(len(p.vertices) - 2 for p in obj.data.polygons)
                },
                "evaluated": stats
            }
        },
        "materials": materials
    }