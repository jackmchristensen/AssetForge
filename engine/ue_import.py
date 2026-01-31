import unreal
import json
from pathlib import Path

def _ensure_folder(path: str) -> None:
    unreal.EditorAssetLibrary.make_directory(path)


def _import_file(filepath: str, destination: str) -> list[str]:
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", filepath)
    task.set_editor_property("destination_path", destination)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return list(task.get_editor_property("imported_object_paths") or [])


def _load_first(imported_paths: list[str]):
    for p in imported_paths:
        asset = unreal.load_asset(p)
        if asset:
            return asset
        
    return None


def _import_fbx(fbx_path: str, mesh_folder: str) -> unreal.StaticMesh:
    imported_mesh_paths = _import_file(fbx_path, mesh_folder)
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
        for parameters in mat.get("parameters"):
            slot = mat.get(parameters)
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
                texture_lookup_by_path[tex_path] = tex_asset
            else:
                unreal.log_warning(f"Imported non-texture from {tex_path}: {imported_tex_paths}")
        
    return texture_lookup_by_path


def ingest_asset(json_path: str) -> None:
    manifest_path = Path(json_path)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {json_path}.")
    
    data = json.loads(manifest_path.read_text())

    asset_name = data["source"]["object_name"]
    fbx_path = data["export"]["export_path"]

    if not Path(fbx_path).exists():
        raise FileNotFoundError(f"FBX not found: {fbx_path}")

    ue_config = data.get("unreal", {})
    DEST_ROOT = ue_config.get("ue_assets_dir", "/Game/Assets/")
    MASTER_MAT_PATH = ue_config.get("ue_master_material", "")

    base_folder = f"{DEST_ROOT}/{asset_name}"
    mesh_folder = f"{base_folder}/Mesh"
    tex_folder  = f"{base_folder}/Textures"
    mat_folder  = f"{base_folder}/Materials"

    _ensure_folder(mesh_folder)
    _ensure_folder(tex_folder)
    _ensure_folder(mat_folder)

    parent_mat = unreal.load_asset(MASTER_MAT_PATH)
    
    mesh_asset = _import_fbx(fbx_path, mesh_folder)

    unreal.EditorAssetLibrary.save_loaded_asset(mesh_asset)
    unreal.log(f"[Ingest] Done: {asset_name} -> {base_folder}")

    texture_lookup_by_path: dict[str, unreal.Texture] = _import_textures(data, tex_folder)

    # TODO create material instances