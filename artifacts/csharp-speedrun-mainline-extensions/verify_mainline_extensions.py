from pathlib import Path
import json
import re
import sys

root = Path(sys.argv[1]).resolve()
extensions = sorted(root.rglob("扩展-主线支撑/*.md"))
original_markers = [
    root / "00-先认识Unity/00-主线项目与Unity运行逻辑.md",
    root / "00-先认识Unity/01-游戏是怎么跑起来的.md",
    root / "00-先认识Unity/02-场景物体与组件.md",
    root / "00-先认识Unity/03-脚本就是组件.md",
    root / "00-先认识Unity/04-在Unity里学CSharp.md",
    root / "01-入门/05-位运算.md",
    root / "02-基础/01-枚举.md",
    root / "02-基础/03-值类型和引用类型.md",
    root / "03-封装/03-属性与索引器.md",
    root / "03-封装/04-静态成员与扩展方法.md",
    root / "04-继承与多态/03-多态抽象类接口.md",
    root / "05-进阶/01-泛型与集合.md",
    root / "05-进阶/02-委托与事件.md",
    root / "06-通向Unity/01-综合练习方块人.md",
]
missing_extension_labels = [
    str(p.relative_to(root))
    for p in extensions
    if "【主线支撑】" not in p.read_text(encoding="utf-8")
]
missing_original_markers = [
    str(p.relative_to(root))
    for p in original_markers
    if not p.exists() or "本篇主线标记" not in p.read_text(encoding="utf-8")
]
missing_links = []
for page in [root / "目录.md", *extensions, *original_markers]:
    if not page.exists():
        continue
    source = page.read_text(encoding="utf-8")
    source = re.sub(r"```[\s\S]*?```", "", source)
    source = re.sub(r"`[^`]*`", "", source)
    for reference in re.findall(r"\]\(([^)#]+)", source):
        if reference.startswith(("http://", "https://", "/qmx-Gameknowledge/")):
            continue
        raw = reference.rstrip("/\\")
        candidates = [page.parent / raw]
        if raw.startswith("../"):
            candidates.append(page.parent / raw[3:])
        valid = []
        for candidate in candidates:
            if candidate.is_dir():
                candidate /= "目录.md"
            if candidate.suffix != ".md":
                candidate = candidate.with_suffix(".md")
            valid.append(candidate)
        if not any(candidate.exists() for candidate in valid):
            missing_links.append(f"{page.name} -> {reference}")

checks = {
    "seven_extension_pages": len(extensions) == 7,
    "extension_labels": not missing_extension_labels,
    "original_markers": not missing_original_markers,
    "links": not missing_links,
}
result = {
    "root": str(root),
    "extension_count": len(extensions),
    "missing_extension_labels": missing_extension_labels,
    "missing_original_markers": missing_original_markers,
    "missing_links": missing_links,
    "checks": checks,
    "passed": all(checks.values()),
}
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(0 if result["passed"] else 1)
