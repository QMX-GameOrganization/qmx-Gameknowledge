#!/usr/bin/env sh
set -eu

TARGET=${1:?usage: ROLLBACK.sh <target-csharp-speedrun-copy>}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASELINE="$SCRIPT_DIR/baseline"
PATHS="$SCRIPT_DIR/paths.txt"

python - "$TARGET" "$BASELINE" "$PATHS" <<'PY'
from pathlib import Path
import shutil
import sys

target = Path(sys.argv[1]).resolve()
baseline = Path(sys.argv[2]).resolve()
paths = Path(sys.argv[3]).resolve()
if not target.is_dir() or not baseline.is_dir() or not paths.is_file():
    raise SystemExit("target, sibling baseline, and paths file are required")
for line in paths.read_text(encoding="utf-8").splitlines():
    relative = line.strip()
    if not relative:
        continue
    source = baseline / Path(relative)
    destination = target / Path(relative)
    if not source.is_file():
        raise SystemExit(f"missing baseline file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
PY
