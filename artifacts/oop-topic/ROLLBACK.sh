#!/bin/sh
# 恢复新增目录页的空白基线；仅用于目标副本，不删除整个专题。
set -eu
[ "$#" -eq 1 ] || { printf "%s\n" "usage: ROLLBACK.sh TARGET_COPY" >&2; exit 2; }
[ -f "$1" ] || { printf "%s\n" "target copy must exist" >&2; exit 2; }
: > "$1"
