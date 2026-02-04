import unreal
import json
import re

from pathlib import Path
from typing import cast

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
                texture_lookup_by_path[tex_path] = tex_asset
            else:
                unreal.log_warning(f"Imported non-texture from {tex_path}: {imported_tex_paths}")
        
    return texture_lookup_by_path


def ingest_asset(json_path: str) -> None:
    """Imports asset and image textures to Unreal Editor and creates material instances if materials
    are assigned in Blender and a master material is selected.

    Does not use FBX default import settings so only the mesh gets imported automatically. Other assets 
    get imported manually.
    """
    
    manifest_path = Path(json_path)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {json_path}.")
    
    data = json.loads(manifest_path.read_text())

    asset_name = data["source"]["object_name"]
    fbx_path = data["export"]["export_path"]

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

    # TODO create material instances
    parent_mat = unreal.load_asset(MASTER_MAT_PATH)


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
