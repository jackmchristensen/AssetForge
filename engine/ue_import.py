from os.path import splitext
import unreal
import json
import re
import traceback
import tempfile
import os

from pathlib import Path
from typing import Any, cast

# Debug logging
def _debug_log(msg: str):
    log_path = os.path.join(tempfile.gettempdir(), "asset_forge_debug.log")
    with open(log_path, "a") as f:
        f.write(f"{msg}\n")


def _ensure_folder(path: str) -> None:
    unreal.EditorAssetLibrary.make_directory(path)


def _import_file(filepath: str, destination: str) -> list[str]:
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", filepath)
    task.set_editor_property("destination_path", destination)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)

    tasks = cast(unreal.Array, [task])
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    return list(task.get_editor_property("imported_object_paths") or [])


def _load_first(imported_paths: list[str]):
    for p in imported_paths:
        asset = unreal.load_asset(p)
        if asset:
            return asset
        
    return None


def _import_fbx(fbx_path: str, mesh_folder: str) -> unreal.StaticMesh:
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", fbx_path)
    task.set_editor_property("destination_path", mesh_folder)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)

    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_as_skeletal", False)
    ui.set_editor_property("import_mesh", True)
    ui.set_editor_property("import_materials", False)
    ui.set_editor_property("import_textures", False) 
    task.set_editor_property("options", ui)

    tasks = cast(unreal.Array, [task])
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

    imported_mesh_paths = list(task.get_editor_property("imported_object_paths") or [])
    mesh_asset = _load_first(imported_mesh_paths)

    if not isinstance(mesh_asset, unreal.StaticMesh):
        raise RuntimeError(f"Expected a StaticMesh import; got {type(mesh_asset)} from {imported_mesh_paths}")
    
    return mesh_asset


def _import_textures(manifest_data, texture_destination_folder: str) -> dict[str, unreal.Texture]:
    """Checks if a material parameter uses an image texture and imports the texture into Unreal project if it exists.
    
    Takes the JSON file containing material data and the destination folder as inputs.
    """

    texture_lookup_by_path: dict[str, unreal.Texture] = {}
    for mat in manifest_data.get("materials", []):
        params = mat.get("parameters", {})
        for _, slot in params.items():
            if not slot or slot.get("type") != "texture":
                continue

            tex_path = slot.get("path")
            p = Path(tex_path)
            # Possible for texture to not have a path. For example, if you are texture
            # painting in Blender you can save the texture in the Blender scene without
            # saving texture to disk.
            if not p.exists():
                unreal.log_warning(f"Texture missing on disk: {tex_path}")
                continue

            # Skip if texture already imported to Unreal Engine
            if tex_path in texture_lookup_by_path:
                continue

            imported_tex_paths = _import_file(tex_path, texture_destination_folder)
            tex_asset = _load_first(imported_tex_paths)

            if isinstance(tex_asset, unreal.Texture):
                original_name = slot.get("original_name", "")
                normalized_name = slot.get("normalized_name", "")
                if original_name != normalized_name:
                    _debug_log(f"Renaming image texture {original_name} to {normalized_name}")
                    new_name, _ = splitext(slot.get("normalized_name"))
                    new_path: str = texture_destination_folder + "/" + new_name
                    _debug_log(f"New path: {new_path}")
                    old_path: str = unreal.EditorAssetLibrary.get_path_name_for_loaded_asset(tex_asset)
                    unreal.EditorAssetLibrary.rename_asset(old_path, new_path)
                texture_lookup_by_path[tex_path] = tex_asset
            else:
                unreal.log_warning(f"Imported non-texture from {tex_path}: {imported_tex_paths}")
        
    return texture_lookup_by_path


def _populate_material_instance(mat_instance: unreal.MaterialInstanceConstant, mat_data: dict[str, Any], texture_lookup: dict[str, unreal.Texture]) -> None:
    """Populates a material instance with parameter values based on the material data from the JSON manifest."""

    parameters = mat_data.get("parameters", {})

    _debug_log(f"Populating material instance {mat_instance.get_name()} with parameters: {parameters}")

    for param_name, param_data in parameters.items():
        param_type = param_data.get("type")

        if param_type == "texture":
            tex_path = param_data.get("path")
            texture = texture_lookup.get(tex_path)

            switch_param = "Use" + param_name + "Texture"

            unreal.MaterialEditingLibrary.set_material_instance_static_switch_parameter_value(
                instance=mat_instance,
                parameter_name=unreal.Name(switch_param),
                value=True
            )
            
            unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                instance=mat_instance,
                parameter_name=unreal.Name(param_name),
                value=texture
            )


def _create_material_instance(mat_instance_name: str, mat_path: str, mat_master: unreal.Material) -> unreal.MaterialInstanceConstant:
    """Checks if material instance exists and creates a material instance from the master material if it doesn't.

    Returns the material instance.
    """

    if unreal.load_asset(f"{mat_path}/{mat_instance_name}") is not None:
        _debug_log(f"Material instance already exists, loading: {mat_path}/{mat_instance_name}")
        return unreal.load_asset(f"{mat_path}/{mat_instance_name}")

    factory = unreal.MaterialInstanceConstantFactoryNew()
    _debug_log(f"Material instance factory created: {factory}")

    material_instance = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name=mat_instance_name,
        package_path=mat_path,
        asset_class=unreal.MaterialInstanceConstant, # type: ignore
        factory=factory
    )
    _debug_log(f"Material instance created: {material_instance}")

    if material_instance is None:
        raise RuntimeError(f"Failed to create material instance: {mat_instance_name} at {mat_path}")

    material_instance.set_editor_property("parent", mat_master)
    
    return material_instance


def ingest_asset(json_path: str) -> None:
    """Imports asset and image textures to Unreal Editor and creates material instances if materials
    are assigned in Blender and a master material is selected.

    Does not use FBX default import settings so only the mesh gets imported automatically. Other assets 
    get imported manually.
    """
   
    _debug_log("Starting UE import.")
    manifest_path = Path(json_path)
    if not manifest_path.exists():
        _debug_log(f"Manifest not found at {manifest_path}")
        raise FileNotFoundError(f"Manifest not found: {json_path}.")
    
    data = json.loads(manifest_path.read_text())

    asset_name = data["source"]["normalized_name"]
    fbx_path = data["export"]["export_path"]
    _debug_log(f"Object path: {fbx_path}")
    # fbx_path += f"/{asset_name}.fbx"

    if not Path(fbx_path).exists():
        raise FileNotFoundError(f"FBX not found: {fbx_path}")

    ue_config = data.get("unreal", {})
    DEST_ROOT = ue_config.get("ue_assets_directory", "/Game/Assets")
    MASTER_MAT_PATH = ue_config.get("ue_master_material", "")

    base_folder = f"{DEST_ROOT}/{asset_name}"
    mesh_folder = f"{base_folder}/Mesh"
    tex_folder  = f"{base_folder}/Textures"
    mat_folder  = f"{base_folder}/Materials"

    _ensure_folder(mesh_folder)
    _ensure_folder(tex_folder)
    _ensure_folder(mat_folder)
    
    mesh_asset = _import_fbx(fbx_path, mesh_folder)

    unreal.EditorAssetLibrary.save_loaded_asset(mesh_asset)
    unreal.log(f"[Ingest] Done: {asset_name} -> {base_folder}")

    texture_lookup_by_path: dict[str, unreal.Texture] = _import_textures(data, tex_folder)

    material_data = data.get("materials", [])
    _debug_log(f"Material data: {material_data}")
    _debug_log(f"Master material path: {MASTER_MAT_PATH}")
    master_mat = unreal.load_asset(MASTER_MAT_PATH)
    _debug_log(f"Loaded master material: {master_mat}")
    _debug_log(f"Asset material folder: {mat_folder}")

    for index, mat in enumerate(material_data):
        try:
            mat_name = mat.get("normalized_name", "MaterialInstance")
            _debug_log(f"Creating material instance: {mat_name}")

            mat_instance = _create_material_instance(mat_name, mat_folder, master_mat)
            _debug_log(f"Created: {mat_instance}")

            _populate_material_instance(mat_instance, mat, texture_lookup_by_path)

            unreal.EditorAssetLibrary.save_loaded_asset(mat_instance)
            unreal.log(f"[Ingest] Created material instance: {mat_name}")

            # For some reason, materials need to be both added and set for multiple materials 
            # to be assigned.
            if index > 0:
                mesh_asset.add_material(mat_instance)
            mesh_asset.set_material(index, mat_instance)
            _debug_log(f"Set material {mat_name} to mesh {mesh_asset.get_name()} at slot {index}")

            unreal.EditorAssetLibrary.save_loaded_asset(mesh_asset)
            _debug_log(f"Added material instance to mesh: {mat_name} -> {mesh_asset.get_name()}")
        except Exception as e:
            _debug_log(f"ERROR creating material {mat_name}: {e}")
            _debug_log(traceback.format_exc())


def get_cli_value(name: str) -> str | None:
    cmd = unreal.SystemLibrary.get_command_line()
    m = re.search(rf'(?:^|\s)-{re.escape(name)}=(?:"([^"]+)"|(\S+))', cmd)
    if not m:
        return None
    return m.group(1) or m.group(2)


def main() -> int:
    manifest_path = get_cli_value("manifest")
    if not manifest_path:
        unreal.log_error("Missing required argument: -manifest=/absolute/path/to/file.json")
        return 2

    unreal.log(f"[AssetForge] manifest: {manifest_path}")

    ingest_asset(manifest_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
