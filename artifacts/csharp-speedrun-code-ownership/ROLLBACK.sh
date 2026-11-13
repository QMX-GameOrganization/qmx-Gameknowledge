#!/usr/bin/env sh
set -eu

TARGET=${1:?usage: ROLLBACK.sh <target-csharp-speedrun-copy>}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASELINE="$SCRIPT_DIR/baseline"

python - "$TARGET" "$BASELINE" <<'PY'
from pathlib import Path
import shutil
import sys

target = Path(sys.argv[1]).resolve()
baseline = Path(sys.argv[2]).resolve()
if not target.is_dir() or not baseline.is_dir():
    raise SystemExit("target and sibling baseline directories are required")
for source in baseline.rglob("*"):
    if source.is_file():
        destination = target / source.relative_to(baseline)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
PY
