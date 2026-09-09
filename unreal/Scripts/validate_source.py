#!/usr/bin/env python3
"""Standard-library source contracts only. Does NOT compile C++, run UHT or UE.

Machine-readable JSON goes to stdout. Exit 0 means these limited checks passed;
Unreal runtime validation remains not_run regardless of the source-check result.
"""

import ast
import json
import os
import re
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
CHECKS = []


def check(name, condition, detail=""):
    CHECKS.append({"name": name, "ok": bool(condition), "detail": detail})


def main():
    project = json.loads((PROJECT / "Shenjin.uproject").read_text())
    check("target_engine", project.get("EngineAssociation") == "5.6", "Declared target only; no compatibility claim")
    scripts = PROJECT / "Scripts"
    for path in sorted(scripts.glob("*.py")):
        try:
            ast.parse(path.read_text(), filename=str(path))
            check("python_syntax:" + path.name, True)
        except SyntaxError as error:
            check("python_syntax:" + path.name, False, str(error))
    module = PROJECT / "Source" / "Shenjin"
    for path in sorted(module.glob("*.h")):
        content = path.read_text()
        if "UCLASS()" in content:
            includes = re.findall(r'^#include "([^"]+)"', content, flags=re.M)
            check("generated_header_last:" + path.name,
                  bool(includes) and includes[-1] == path.stem + ".generated.h")
    importer = ast.parse((scripts / "prepare_animation.py").read_text())
    specs_node = next(node.value for node in importer.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == "SPECS" for target in node.targets))
    specs = ast.literal_eval(specs_node)
    # Exercise the real normalization function in isolation, without faking Unreal.
    label_node = next(node for node in importer.body if isinstance(node, ast.FunctionDef) and node.name == "clip_label")
    namespace = {"re": re}
    exec(compile(ast.Module(body=[label_node], type_ignores=[]), "clip_label", "exec"), namespace)
    normalize = namespace["clip_label"]
    manifest_path = ROOT / "art" / "exports" / "animation-manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    check("animation_manifest_present", bool(manifest))
    for character, spec in specs.items():
        source = (module / ("ShenjinCharacter.cpp" if character == "Hero" else "ShenjinSentinel.cpp")).read_text()
        load = re.search(r'ShenjinAnimation::Load\([^;]+AnimationClips\)', source, flags=re.S)
        declared = re.findall(r'TEXT\("([^"]+)"\)', load.group(0)) if load else []
        check("required_clips:" + character, declared == [character, *spec["clips"]], str(declared))
        check("source_fbx:" + character, (ROOT / "art" / "exports" / spec["file"]).is_file(), spec["file"])
        round_trip = manifest.get("verification", {}).get("round_trip", {}).get(spec["file"], {})
        imported = round_trip.get("clips", {})
        check("fbx_round_trip_contract:" + character, set(imported) == set(spec["clips"])
              and all(normalize(item.get("imported_action", ""), character, spec["clips"]) == clip
                      and abs(item.get("duration_seconds", -1) - spec["clips"][clip]) < 0.001
                      for clip, item in imported.items()), "Blender report contract; not an Unreal import")
        bones = manifest.get("assets", {}).get(character.lower(), {}).get("bones", [])
        check("weapon_bone_contract:" + character, "WeaponSocket" in bones and "WeaponTip" in bones)
        for clip in spec["clips"]:
            examples = [clip, f"{character}_{clip}", f"{character}_SK_{character}Rig_{clip}_001"]
            check("clip_name:" + character + "/" + clip,
                  all(normalize(name, character, spec["clips"]) == clip for name in examples))
        check("reject_ambiguous:" + character,
              normalize(f"{character}_Idle_Walk", character, spec["clips"]) is None
              and normalize(f"{character}_Idle_Broken", character, spec["clips"]) is None
              and normalize("UnrelatedAnimation", character, spec["clips"]) is None)
        header = (module / ("ShenjinCharacter.h" if character == "Hero" else "ShenjinSentinel.h")).read_text()
        check("gc_owned_clips:" + character,
              bool(re.search(r'UPROPERTY\(\)\s+TMap<FName, TObjectPtr<UAnimSequence>> AnimationClips', header)))
    hero_header = (module / "ShenjinCharacter.h").read_text()
    boss_header = (module / "ShenjinSentinel.h").read_text()
    for name, expected, content in [("BaseAttackDuration", 0.55, hero_header),
                                     ("AttackImpactTime", 0.20, hero_header),
                                     ("DodgeDuration", 0.32, hero_header),
                                     ("SlamDuration", 0.30, boss_header),
                                     ("SlamImpactTime", 0.30, boss_header)]:
        match = re.search(rf'{name}\s*=\s*([0-9.]+)f', content)
        check("timing:" + name, match and abs(float(match.group(1)) - expected) < 0.0001)
    helper = (module / "ShenjinAnimation.h").read_text()
    check("deterministic_runtime_asset_folder", '/Game/Shenjin/Characters/%s' in helper and '%s_SK' in helper)
    check("single_node_transition_guard", 'Current != Desired || bRestart' in helper and 'AnimationSingleNode' in helper)
    check("skeleton_compatibility_guard", 'Animation->GetSkeleton() != Asset->GetSkeleton()' in helper)
    config = (PROJECT / "Config" / "DefaultGame.ini").read_text()
    for folder in ("/Game/Shenjin", "/Engine/BasicShapes"):
        check("cook_directory:" + folder, f'+DirectoriesToAlwaysCook=(Path="{folder}")' in config)
    check("default_map", 'GameDefaultMap=/Game/Shenjin/Maps/LostTemple' in (PROJECT / "Config" / "DefaultEngine.ini").read_text())
    engine = os.environ.get("SHENJIN_UE_ROOT")
    result = {"schema_version": 1, "kind": "source_contract_validation", "ok": all(item["ok"] for item in CHECKS),
              "checks": CHECKS, "engine_directory_configured": bool(engine and Path(engine).is_dir()),
              "unreal_validation": {"cpp_compile": "not_run", "uht": "not_run", "editor_import": "not_run",
                                    "pie": "not_run", "packaged_build": "not_run"},
              "limitation": "Text, Python syntax, normalization and file-presence checks do not establish Unreal compatibility."}
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
