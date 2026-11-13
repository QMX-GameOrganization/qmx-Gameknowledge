from pathlib import Path
import json
import re
import sys


root = Path(sys.argv[1]).resolve()
index = root / "目录.md"
static = root / "03-封装/04-静态成员与扩展方法.md"
capstone = root / "06-通向Unity/01-综合练习方块人.md"
final = root / "06-通向Unity/04-完整小游戏验收.md"
unity_runtime = root / "00-先认识Unity/00-主线项目与Unity运行逻辑.md"

checks = {
    "index_exists": index.exists(),
    "dungeon_goal": index.exists() and "方块地牢" in index.read_text(encoding="utf-8"),
    "unity_runtime_page": unity_runtime.exists(),
    "static_game_math": static.exists() and "public static class GameMath" in static.read_text(encoding="utf-8"),
    "static_reuse_contract": static.exists() and "不需要 `new GameMath()`" in static.read_text(encoding="utf-8"),
    "capstone_milestone": capstone.exists() and "主线里程碑一" in capstone.read_text(encoding="utf-8"),
    "final_acceptance": final.exists() and "可玩验收清单" in final.read_text(encoding="utf-8"),
}

missing_links = []
for page in (index, static, capstone, final, unity_runtime):
    if not page.exists():
        continue
    for reference in re.findall(r"\]\(([^)#]+)", page.read_text(encoding="utf-8")):
        if reference.startswith(("http://", "https://", "/qmx-Gameknowledge/")):
            continue
        candidate = page.parent / reference.rstrip("/\\")
        if candidate.is_dir():
            candidate /= "目录.md"
        if candidate.suffix != ".md":
            candidate = candidate.with_suffix(".md")
        if not candidate.exists() and reference.endswith(("/", "\\")):
            # Starlight links to a markdown page with a route-style trailing slash.
            candidate = page.parent / (reference.rstrip("/\\") + ".md")
        if not candidate.exists():
            missing_links.append(f"{page.name} -> {reference}")

checks["local_links_resolve"] = not missing_links
result = {
    "root": str(root),
    "checks": checks,
    "missing_links": missing_links,
    "passed": all(checks.values()) and not missing_links,
}
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(0 if result["passed"] else 1)
