from pathlib import Path
import json
import sys

root = Path(sys.argv[1]).resolve()
pages = sorted(root.rglob("*.md"))
practice_pages = sorted(root.rglob("*主线实践*.md"))
experimental_sections = [
    str(page.relative_to(root))
    for page in pages
    if "## 动手试试" in page.read_text(encoding="utf-8")
    and "**代码归属**：`【实验代码】`" not in page.read_text(encoding="utf-8")
]
mainline_sections = [
    str(page.relative_to(root))
    for page in practice_pages
    if "**代码归属**：`【主线代码】`" not in page.read_text(encoding="utf-8")
    or "Assets/Speedrun/Game/" not in page.read_text(encoding="utf-8")
]
old_refs = [
    str(page.relative_to(root))
    for page in pages
    if "扩展-主线支撑" in page.read_text(encoding="utf-8")
]
index_text = (root / "目录.md").read_text(encoding="utf-8") if (root / "目录.md").exists() else ""
checks = {
    "ownership_rules": "## 代码归属规则" in index_text,
    "seven_mainline_practice_pages": len(practice_pages) == 7,
    "experimental_sections_marked": not experimental_sections,
    "mainline_code_marked": not mainline_sections,
    "no_old_folder_refs": not old_refs,
}
result = {
    "root": str(root),
    "practice_page_count": len(practice_pages),
    "experimental_sections_missing_mark": experimental_sections,
    "mainline_pages_missing_code_mark": mainline_sections,
    "old_folder_refs": old_refs,
    "checks": checks,
    "passed": all(checks.values()),
}
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(0 if result["passed"] else 1)
