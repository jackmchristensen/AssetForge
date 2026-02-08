import bpy
import datetime
import os

from bpy import types as bt
from typing import Any
from ..validation import naming

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
    assert tree is not None

    shader = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"))
    return shader


def _classify_shader_input(sock: bt.NodeSocket) -> dict[str, Any]:
    """Returns material input data.
    
    Returns constant value if no nodes are used.
    If image texture is used returns image's path and color space.
    If another node is used returns 'complex' type and no other data.
    """

    if not sock.is_linked:
        if isinstance(sock, bt.NodeSocketColor) or isinstance(sock, bt.NodeSocketVector):
            val = list(sock.default_value)[:3]
        elif isinstance(sock, bt.NodeSocketFloat) or isinstance(sock, bt.NodeSocketFloatFactor):
            val = sock.default_value
        return { "type": "constant", "value": val }
    
    links = sock.links
    assert links is not None
    from_node = links[0].from_node
    assert isinstance(from_node, bt.Node)

    if isinstance(from_node, bt.ShaderNodeTexImage):
        image = from_node.image
        assert image is not None

        new_name: str = naming.normalize_texture_name(image.name)

        colorspace = image.colorspace_settings
        assert colorspace is not None

        return {
            "type": "texture",
            "path": bpy.path.abspath(image.filepath),
            "original_name": image.name_full,
            "normalized_name": new_name,
            "color_space": colorspace.name
        }
    
    if isinstance(from_node, bt.ShaderNodeNormalMap):
        color_input = from_node.inputs.get("Color")
        if color_input and color_input.is_linked:
            links = color_input.links
            assert links is not None

            tex_node = links[0].from_node
            assert tex_node is not None
            
            if isinstance(tex_node, bt.ShaderNodeTexImage):
                image = tex_node.image
                assert image is not None

                new_name: str = naming.normalize_texture_name(image.name)

                colorspace = image.colorspace_settings
                assert colorspace is not None

                return {
                    "type": "texture",
                    "usage": "normal",
                    "path": bpy.path.abspath(image.filepath),
                    "original_name": image.name_full,
                    "normalized_name": new_name,
                    "color_space": colorspace.name
                }

    return { "type": "complex" }


def get_material_data(obj: bt.Object) -> list[dict[str, Any]]:
    materials: list[dict[str, Any]] = []

    for mat in obj.material_slots:
        next_material = mat.material
        assert next_material is not None

        shader = _get_shader_connected_to_output(next_material)

        base_color          = shader.inputs.get("Base Color")
        assert base_color is not None
        roughness           = shader.inputs.get("Roughness")
        assert roughness is not None
        metallic            = shader.inputs.get("Metallic")
        assert metallic is not None
        normal              = shader.inputs.get("Normal")
        assert normal is not None
        emission_color      = shader.inputs.get("Emission Color")
        assert emission_color is not None
        alpha               = shader.inputs.get("Alpha")
        assert alpha is not None

        mat_data: dict[str, Any] = { "name": next_material.name }
        mat_data["normalized_name"] = naming.normalize_material_instance_name(next_material.name)

        parameters: dict[str, Any] = {}

        parameters["base_color"]      = _classify_shader_input(base_color)
        parameters["roughness"]       = _classify_shader_input(roughness)
        parameters["metallic"]        = _classify_shader_input(metallic)
        parameters["normal"]          = _classify_shader_input(normal)
        parameters["emission_color"]  = _classify_shader_input(emission_color)
        parameters["alpha"]           = _classify_shader_input(alpha)

        mat_data["parameters"] = parameters

        materials.append(mat_data)
        

    return materials


def generate_metadata(obj: bt.Object, export_dir: str, ue_project_path: str, 
                      ue_assets_dir: str, material_path: str, asset_type: str, 
                      context: bt.Context) -> dict[str, Any]:
    """Generate export metadata for a Blender object.

    Builds a JSON-serializable metadata dictionary containing source
    information, export settings, and evaluated mesh statistics.
    """

    assert obj is not None
    obj_data = obj.data
    assert isinstance(obj_data, bt.Mesh)
    normalized_obj_name = naming.normalize_mesh_name(obj.name)

    filename: str = f"{normalized_obj_name}.fbx"
    export_path: str = os.path.join(export_dir, filename)

    stats: dict[str, int] = get_evaluated_mesh_stats(obj, context)
    
    materials: list[dict[str, Any]] = get_material_data(obj) 

    return {
        "schema": "asset_forge.export",
        "schema_version": "0.1.0",
        "source": {
            "blend_file": bpy.data.filepath, 
            "object_name": obj.name,
            "normalized_name": normalized_obj_name,
            "asset_type": asset_type
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
        "unreal": {
            "unreal_project_path": ue_project_path,
            "ue_assets_directory": ue_assets_dir,
            "ue_master_material": material_path
        },
        "mesh": {
            "name": obj.name,
            "material_count": len(materials),
            "stats": {
                "original": {
                    "vertices": len(obj_data.vertices),
                    "edges": len(obj_data.edges),
                    "faces": len(obj_data.polygons),
                    "triangles": sum(len(p.vertices) - 2 for p in obj_data.polygons)
                },
                "evaluated": stats
            }
        },
        "materials": materials
    }
