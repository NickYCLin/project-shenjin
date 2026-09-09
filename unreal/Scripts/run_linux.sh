#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$script_dir/.." && pwd)"
project_file="$project_dir/Shenjin.uproject"
action="${1:-editor}"
case "$action" in
  validate) exec python3 "$script_dir/validate_source.py" ;;
  build|prepare|prepare-animation|editor) ;;
  *) echo "Usage: $0 {validate|build|prepare|prepare-animation|editor}" >&2; exit 2 ;;
esac
if [[ -z "${SHENJIN_UE_ROOT:-}" || ! -d "${SHENJIN_UE_ROOT:-}" ]]; then
  echo "Unreal Engine installation not found. Set SHENJIN_UE_ROOT to an existing UE 5.6 directory." >&2
  echo "No build, Editor import, PIE, or packaging has run. Source checks: $0 validate" >&2
  exit 3
fi
editor="$SHENJIN_UE_ROOT/Engine/Binaries/Linux/UnrealEditor"
builder="$SHENJIN_UE_ROOT/Engine/Build/BatchFiles/Linux/Build.sh"
required="$editor"
if [[ "$action" == build ]]; then required="$builder"; fi
if [[ ! -f "$required" || ! -x "$required" ]]; then
  echo "Missing executable: $required. Point SHENJIN_UE_ROOT at a complete Linux UE 5.6 installation." >&2
  exit 3
fi
case "$action" in
  build)
    exec "$builder" ShenjinEditor Linux Development "$project_file" -WaitMutex -NoHotReloadFromIDE
    ;;
  prepare|prepare-animation)
    prepare_script="$script_dir/prepare_project.py"
    if [[ "$action" == prepare-animation ]]; then prepare_script="$script_dir/prepare_animation.py"; fi
    exec "$editor" "$project_file" "-ExecutePythonScript=$prepare_script" -unattended -nop4 -nosplash
    ;;
  editor) exec "$editor" "$project_file" ;;
esac
