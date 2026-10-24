#!/usr/bin/env bash
set -euo pipefail
TARGET=${1:?usage: ROLLBACK.sh <modified-notes-directory>}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASELINE="$SCRIPT_DIR/baseline/开端.md"
[ -d "$TARGET" ] || { echo "target directory not found: $TARGET" >&2; exit 2; }
[ -f "$BASELINE" ] || { echo "baseline not found: $BASELINE" >&2; exit 2; }
rm -rf "$TARGET/00-导读" "$TARGET/01-实体与组件" "$TARGET/02-拓扑与连接" "$TARGET/03-传送带" "$TARGET/04-输入与输出" "$TARGET/05-生产与处理" "$TARGET/06-系统与时序" "$TARGET/07-性能与存档" "$TARGET/08-Unity ECS映射" "$TARGET/09-实践路线"
cp "$BASELINE" "$TARGET/开端.md"
printf 'restored=%s\n' "$TARGET"