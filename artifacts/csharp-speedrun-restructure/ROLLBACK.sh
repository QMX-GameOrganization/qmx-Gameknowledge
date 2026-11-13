#!/usr/bin/env sh
set -eu

TARGET=${1:?usage: ROLLBACK.sh <target-csharp-speedrun-copy>}
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BASELINE="$SCRIPT_DIR/baseline"
ADDED="$SCRIPT_DIR/candidate-only.txt"

python - "$TARGET" "$BASELINE" "$ADDED" <<'PY'
from pathlib import Path
import shutil
import sys

target = Path(sys.argv[1]).resolve()
baseline = Path(sys.argv[2]).resolve()
added = Path(sys.argv[3]).resolve()
if not target.is_dir() or not baseline.is_dir():
    raise SystemExit("target and sibling baseline directories are required")

for source in baseline.rglob("*"):
    if source.is_file():
        relative = source.relative_to(baseline)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

if added.exists():
    for line in added.read_text(encoding="utf-8").splitlines():
        relative = line.strip()
        if relative:
            candidate = target / Path(relative)
            if candidate.is_file():
                candidate.unlink()
for candidate in sorted(target.rglob("*"), reverse=True):
    if candidate.is_dir() and not any(candidate.iterdir()):
        candidate.rmdir()
PY
