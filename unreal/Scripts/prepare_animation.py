"""UE 5.6 Editor: import original rigs/clips with deterministic runtime names.

Existing assets are never overwritten. Incomplete existing sets require manual
review; new sets use unique staging folders and strict clip/skeleton validation.
This script requires Unreal and has not been executed against an installed UE.
"""

import json
import re
import uuid
from pathlib import Path

import unreal


PROJECT = Path(unreal.Paths.project_dir()).resolve()
EXPORTS = PROJECT.parent / "art" / "exports"
CHARACTER_FOLDER = "/Game/Shenjin/Characters"
SPECS = {
    "Hero": {"file": "hero-rigged.fbx", "height": (130, 270), "clips": {
        "Idle": 2.0, "Walk": 0.8, "Thrust": 0.55, "Dodge": 0.32, "Hit": 0.35, "Death": 1.4}},
    "Sentinel": {"file": "sentinel-rigged.fbx", "height": (400, 850), "clips": {
        "Idle": 2.4, "Walk": 1.2, "Windup": 1.1, "Slam": 0.3, "Recover": 1.05,
        "Hit": 0.4, "Death": 1.8}},
}


def clip_label(asset_name, character, expected):
    """Recognize delimited FBX names, never select an arbitrary first take.

    FBX may prefix Character_SK / CharacterRig and suffix a take with a numeric
    index. Match an exact known token, accepting only known wrapper tokens.
    Multiple known clips or unknown semantic suffixes are rejected.
    """
    tokens = [token.lower() for token in re.split(r"[^A-Za-z0-9]+", asset_name) if token]
    aliases = {name.lower(): name for name in expected}
    matched = [aliases[token] for token in tokens if token in aliases]
    wrappers = {character.lower(), character.lower() + "rig", "rig", "sk", "anim", "animation", "take"}
    unknown = [token for token in tokens if token not in aliases and token not in wrappers and not token.isdigit()]
    if len(matched) != 1 or unknown:
        return None
    return matched[0]


def required_paths(character, spec):
    folder = f"{CHARACTER_FOLDER}/{character}"
    return {"mesh": f"{folder}/{character}_SK", "skeleton": f"{folder}/{character}_Skeleton",
            **{clip: f"{folder}/{character}_{clip}" for clip in spec["clips"]}}


def load_checked(path, expected_type):
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        return None
    asset = unreal.load_asset(path)
    if not isinstance(asset, expected_type):
        raise RuntimeError(f"Existing asset has wrong type; preserved for manual review: {path}")
    return asset


def validate_set(character, spec, paths):
    mesh = load_checked(paths["mesh"], unreal.SkeletalMesh)
    skeleton = load_checked(paths["skeleton"], unreal.Skeleton)
    if not mesh or not skeleton or mesh.get_editor_property("skeleton") != skeleton:
        raise RuntimeError(f"{character}: missing or mismatched mesh/skeleton")
    height = mesh.get_imported_bounds().box_extent.z * 2.0
    if not spec["height"][0] <= height <= spec["height"][1]:
        raise RuntimeError(f"{character}: height {height:.2f} cm is outside {spec['height']}; verify FBX units")
    clips = {}
    for clip, seconds in spec["clips"].items():
        asset = load_checked(paths[clip], unreal.AnimSequence)
        if not asset or asset.get_editor_property("skeleton") != skeleton:
            raise RuntimeError(f"{character}/{clip}: missing animation or mismatched skeleton")
        length = asset.get_play_length()
        if abs(length - seconds) > max(0.055, seconds * 0.05):
            raise RuntimeError(f"{character}/{clip}: {length:.4f}s does not match {seconds}s contract")
        clips[clip] = {"asset": paths[clip], "seconds": length}
    return {"mesh": paths["mesh"], "skeleton": paths["skeleton"], "height_cm": height, "clips": clips}


def publish(asset, target, expected_type):
    existing = load_checked(target, expected_type)
    if existing:
        raise RuntimeError(f"Destination appeared during import; preserved: {target}")
    if not unreal.EditorAssetLibrary.rename_asset(asset.get_path_name(), target):
        raise RuntimeError(f"Could not rename {asset.get_path_name()} to {target}")
    return unreal.load_asset(target)


def import_character(character, spec):
    paths = required_paths(character, spec)
    mesh = load_checked(paths["mesh"], unreal.SkeletalMesh)
    skeleton = load_checked(paths["skeleton"], unreal.Skeleton)
    existing_clips = {clip: load_checked(paths[clip], unreal.AnimSequence) for clip in spec["clips"]}
    if mesh and skeleton and all(existing_clips.values()):
        return {"status": "kept", **validate_set(character, spec, paths)}
    if mesh or skeleton or any(existing_clips.values()):
        raise RuntimeError(f"{character}: incomplete existing asset set; preserved for manual review. "
                           "Move or repair the complete character folder in Editor before retrying.")
    source = EXPORTS / spec["file"]
    if not source.is_file():
        raise RuntimeError(f"Missing {source}; generate the Blender character animation exports first")

    stage = f"{CHARACTER_FOLDER}/{character}/_Import/{uuid.uuid4().hex[:12]}"
    options = unreal.FbxImportUI()
    for key, value in {
        "automated_import_should_detect_type": False,
        "mesh_type_to_import": unreal.FBXImportType.FBXIT_SKELETAL_MESH,
        "import_mesh": True, "import_as_skeletal": True,
        "import_animations": True, "import_materials": True, "import_textures": False,
        "create_physics_asset": False, "override_full_name": True,
    }.items():
        options.set_editor_property(key, value)
    for property_name in ("skeletal_mesh_import_data", "anim_sequence_import_data"):
        data = options.get_editor_property(property_name)
        for key, value in {"convert_scene": True, "convert_scene_unit": True,
                           "force_front_x_axis": False, "import_uniform_scale": 1.0}.items():
            data.set_editor_property(key, value)
    options.get_editor_property("anim_sequence_import_data").set_editor_property("use_default_sample_rate", False)
    task = unreal.AssetImportTask()
    for key, value in {
        "filename": str(source), "destination_path": stage, "destination_name": f"{character}_SK",
        "replace_existing": False, "automated": True, "save": False,
        "factory": unreal.FbxFactory(), "options": options,
    }.items():
        task.set_editor_property(key, value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    # Registry enumeration covers animation-only outputs omitted by some task lists.
    assets = [unreal.load_asset(path) for path in unreal.EditorAssetLibrary.list_assets(stage, recursive=True)]
    imported_meshes = [asset for asset in assets if isinstance(asset, unreal.SkeletalMesh)]
    sequences = [asset for asset in assets if isinstance(asset, unreal.AnimSequence)]
    matches = {clip: [] for clip in spec["clips"]}
    for asset in sequences:
        label = clip_label(asset.get_name(), character, spec["clips"])
        if label is None:
            raise RuntimeError(f"Unrecognized or ambiguous FBX take: {asset.get_name()}; assets retained in {stage}")
        matches[label].append(asset)
    if any(len(found) != 1 for found in matches.values()):
        raise RuntimeError(f"{character}: expected exactly one animation per clip; got "
                           f"{ {clip: [asset.get_name() for asset in found] for clip, found in matches.items()} }; {stage}")
    if len(imported_meshes) != 1:
        raise RuntimeError(f"{character}: expected one combined SkeletalMesh, got {len(imported_meshes)}; {stage}")
    mesh = imported_meshes[0]
    source_skeleton = mesh.get_editor_property("skeleton")
    if not source_skeleton:
        raise RuntimeError(f"{character}: importer skeleton mismatch; {stage}")
    height = mesh.get_imported_bounds().box_extent.z * 2.0
    if not spec["height"][0] <= height <= spec["height"][1]:
        raise RuntimeError(f"{character}: unexpected imported height {height:.2f} cm; {stage}")
    # Verify complete incoming set before publishing any canonical assets.
    for clip, found in matches.items():
        asset = found[0]
        if asset.get_editor_property("skeleton") != source_skeleton:
            raise RuntimeError(f"{character}/{clip}: imported skeleton mismatch; {stage}")
        if abs(asset.get_play_length() - spec["clips"][clip]) > max(0.055, spec["clips"][clip] * 0.05):
            raise RuntimeError(f"{character}/{clip}: unexpected imported clip duration; {stage}")
    skeleton = publish(source_skeleton, paths["skeleton"], unreal.Skeleton)
    mesh = publish(mesh, paths["mesh"], unreal.SkeletalMesh)
    for clip, found in matches.items():
        publish(found[0], paths[clip], unreal.AnimSequence)
    report = validate_set(character, spec, paths)
    if not unreal.EditorAssetLibrary.save_directory(f"{CHARACTER_FOLDER}/{character}", only_if_is_dirty=True, recursive=True):
        raise RuntimeError(f"Could not save {character} assets")
    # Staging holds source materials. Keep it for review; never delete user assets
    # or redirectors automatically.
    return {"status": "imported", "staging": stage, **report}


def main():
    saved = PROJECT / "Saved"
    saved.mkdir(parents=True, exist_ok=True)
    report_path = saved / "prepare-animation-report.json"
    report = {"ok": False, "engine": unreal.SystemLibrary.get_engine_version(), "characters": {}}
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        raise RuntimeError("Save edited Content assets before importing character animation")
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor.get_editor_world()
    cvar = "Interchange.FeatureFlags.Import.FBX"
    previous = unreal.SystemLibrary.get_console_variable_int_value(cvar)
    unreal.SystemLibrary.execute_console_command(world, f"{cvar} 0")
    try:
        for character, spec in SPECS.items():
            report["characters"][character] = import_character(character, spec)
        report["ok"] = True
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        unreal.SystemLibrary.execute_console_command(world, f"{cvar} {previous}")
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    unreal.log("SHENJIN_ANIMATION_PREPARE_OK: character rigs and all clips validated and saved")


if __name__ == "__main__":
    main()
