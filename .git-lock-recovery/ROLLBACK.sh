#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then echo "usage: $0 TARGET_COPY" >&2; exit 2; fi
target=$1
base="$(dirname "$target")/BASELINE.index.lock"
[ -f "$base" ] || { echo "missing baseline: $base" >&2; exit 3; }
cp "$base" "$target"