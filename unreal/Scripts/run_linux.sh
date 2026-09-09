#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "$script_dir/.." && pwd)"
project_file="$project_dir/Shenjin.uproject"
: "${SHENJIN_UE_ROOT:?Set SHENJIN_UE_ROOT to your Unreal Engine 5.6 installation directory}"
editor="$SHENJIN_UE_ROOT/Engine/Binaries/Linux/UnrealEditor"

case "${1:-editor}" in
  build)
    exec "$SHENJIN_UE_ROOT/Engine/Build/BatchFiles/Linux/Build.sh" \
      ShenjinEditor Linux Development "$project_file" -WaitMutex -NoHotReloadFromIDE
    ;;
  prepare)
    exec "$editor" "$project_file" \
      "-ExecutePythonScript=$script_dir/prepare_project.py" -unattended -nop4 -nosplash
    ;;
  editor)
    exec "$editor" "$project_file"
    ;;
  *)
    echo "Usage: $0 {build|prepare|editor}" >&2
    exit 2
    ;;
esac
