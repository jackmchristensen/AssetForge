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

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(task)
    return list(task.get_editor_property("imported_object_paths") or [])


def _load_first(imported_paths: list[str]):
    for p in imported_paths:
        asset = unreal.load_asset(p)
        if asset:
            return asset
        
    return None


def _import_fbx(fbx_path: str, mesh_folder: str):
    imported_mesh_paths = _import_file(fbx_path, mesh_folder)
    mesh_asset = _load_first(imported_mesh_paths)

    if not isinstance(mesh_asset, unreal.StaticMesh):
        raise RuntimeError(f"Expected a StaticMesh import; got {type(mesh_asset)} from {imported_mesh_paths}")
    
    return mesh_asset


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

    # TODO import textures
    # TODO create material instances