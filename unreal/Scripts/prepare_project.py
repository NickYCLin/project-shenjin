"""Run inside Unreal Editor after building ShenjinEditor (UE 5.6 target).

Imports missing original FBX files and creates the prototype material/map.
Existing assets are preserved unless SHENJIN_REIMPORT=1 is explicitly set.
No Unreal Editor installation was available during initial source development.
"""

import json
import os
from pathlib import Path

import unreal


PROJECT = Path(unreal.Paths.project_dir()).resolve()
EXPORTS = PROJECT.parent / "art" / "exports"
MESH_FOLDER = "/Game/Shenjin/Meshes"
MATERIAL_FOLDER = "/Game/Shenjin/Materials"
MAP_PATH = "/Game/Shenjin/Maps/LostTemple"
REIMPORT = os.environ.get("SHENJIN_REIMPORT") == "1"


def ensure_material():
    path = MATERIAL_FOLDER + "/M_Prototype"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        return
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_Prototype", MATERIAL_FOLDER, unreal.Material, unreal.MaterialFactoryNew()
    )
    if not material:
        raise RuntimeError("Could not create the prototype material")
    library = unreal.MaterialEditingLibrary
    tint = library.create_material_expression(
        material, unreal.MaterialExpressionVectorParameter, -400, 0
    )
    tint.set_editor_property("parameter_name", "Tint")
    tint.set_editor_property("default_value", unreal.LinearColor(0.8, 0.55, 0.2, 1.0))
    library.connect_material_property(tint, "", unreal.MaterialProperty.MP_BASE_COLOR)
    glow = library.create_material_expression(material, unreal.MaterialExpressionMultiply, -180, 160)
    glow.set_editor_property("const_b", 0.15)
    library.connect_material_expressions(tint, "", glow, "A")
    library.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    library.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_loaded_asset(material):
        raise RuntimeError("Could not save M_Prototype")


def check_dimensions(mesh, name):
    bounds = mesh.get_bounding_box()
    extent = bounds.max - bounds.min
    dimensions = {"x": extent.x, "y": extent.y, "z": extent.z}
    # UE units are centimeters. Catch accidental 100x scaling before gameplay.
    expected_heights = {"hero": (130, 270), "sentinel": (400, 850), "spear": (180, 330)}
    if name in expected_heights:
        low, high = expected_heights[name]
        if not low <= extent.z <= high:
            raise RuntimeError(
                f"{name}: unexpected height {extent.z:.2f} cm (expected {low}-{high}). "
                "Check FBX meter metadata and convert_scene_unit; do not apply another 100x scale."
            )
    elif not 3000 <= extent.x <= 20000:
        raise RuntimeError(f"temple: unexpected width {extent.x:.2f} cm; check FBX units")
    return dimensions


def import_mesh(name):
    asset_path = f"{MESH_FOLDER}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(asset_path) and not REIMPORT:
        mesh = unreal.load_asset(asset_path)
        if not isinstance(mesh, unreal.StaticMesh):
            raise RuntimeError(f"Existing asset is not a StaticMesh: {asset_path}")
        return {"status": "kept", "dimensions_cm": check_dimensions(mesh, name)}
    source = EXPORTS / f"{name}.fbx"
    if not source.is_file():
        unreal.log_warning(f"Missing {source}; runtime will use the engine shape fallback")
        return {"status": "missing; fallback"}

    options = unreal.FbxImportUI()
    options.set_editor_property("automated_import_should_detect_type", False)
    options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_as_skeletal", False)
    options.set_editor_property("import_animations", False)
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_textures", False)
    data = options.get_editor_property("static_mesh_import_data")
    data.set_editor_property("combine_meshes", True)
    data.set_editor_property("convert_scene", True)
    data.set_editor_property("convert_scene_unit", True)
    data.set_editor_property("force_front_x_axis", False)
    data.set_editor_property("import_uniform_scale", 1.0)
    data.set_editor_property("transform_vertex_to_absolute", True)
    data.set_editor_property("auto_generate_collision", False)
    data.set_editor_property("generate_lightmap_u_vs", False)

    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(source))
    task.set_editor_property("destination_path", MESH_FOLDER)
    task.set_editor_property("destination_name", name)
    task.set_editor_property("replace_existing", REIMPORT)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", False)
    task.set_editor_property("factory", unreal.FbxFactory())
    task.set_editor_property("options", options)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = unreal.load_asset(asset_path)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError(f"Import did not create {asset_path}: {task.imported_object_paths}")
    dimensions = check_dimensions(mesh, name)
    if not unreal.EditorAssetLibrary.save_directory(MESH_FOLDER, only_if_is_dirty=True, recursive=True):
        raise RuntimeError(f"Could not save {MESH_FOLDER}")
    unreal.log(f"Shenjin: imported {name} ({dimensions} cm)")
    return {"status": "imported", "dimensions_cm": dimensions}


def main():
    if unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages():
        raise RuntimeError("Save your edited levels before preparing LostTemple; level switching discards unsaved work")
    mode = unreal.load_class(None, "/Script/Shenjin.ShenjinGameMode")
    if not mode:
        raise RuntimeError("Build ShenjinEditor first; native ShenjinGameMode was not found")
    ensure_material()
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor.get_editor_world()
    cvar = "Interchange.FeatureFlags.Import.FBX"
    previous = unreal.SystemLibrary.get_console_variable_int_value(cvar)
    # Use the documented legacy FbxImportUI options consistently across engines.
    unreal.SystemLibrary.execute_console_command(world, f"{cvar} 0")
    try:
        report = {name: import_mesh(name) for name in ("temple", "hero", "sentinel", "spear")}
    finally:
        unreal.SystemLibrary.execute_console_command(world, f"{cvar} {previous}")

    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP_PATH):
        succeeded = levels.load_level(MAP_PATH)
    else:
        succeeded = levels.new_level(MAP_PATH)
    if not succeeded:
        raise RuntimeError(f"Could not open or create {MAP_PATH}")
    world = editor.get_editor_world()
    world.get_world_settings().set_editor_property("default_game_mode", mode)
    if not levels.save_current_level():
        raise RuntimeError("Could not save LostTemple")
    # The arena and lighting are created by StartPlay, so the edit viewport is blank.
    saved = PROJECT / "Saved"
    saved.mkdir(parents=True, exist_ok=True)
    (saved / "prepare-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    unreal.log("SHENJIN_PREPARE_OK: open LostTemple and press Play. Arena appears at runtime.")


if __name__ == "__main__":
    main()
