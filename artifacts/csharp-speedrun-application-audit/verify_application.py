from pathlib import Path
import json
import re
import sys


root = Path(sys.argv[1]).resolve()
pages = sorted(p for p in root.rglob("*.md") if p.name != "目录.md")
missing_sections = [str(p.relative_to(root)) for p in pages if "## 项目应用决策" not in p.read_text(encoding="utf-8")]
index = root / "目录.md"
index_text = index.read_text(encoding="utf-8") if index.exists() else ""
missing_links = []
for page in [index, *pages]:
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
        # The site links are route-relative: a single ../ points to the
        # neighbouring article route, while the source files live together.
        if raw.startswith("../"):
            candidates.append(page.parent / raw[3:])
        resolved = []
        for candidate in candidates:
            if candidate.is_dir():
                candidate /= "目录.md"
            if candidate.suffix != ".md":
                candidate = candidate.with_suffix(".md")
            if not candidate.exists() and reference.endswith(("/", "\\")):
                candidate = candidate.parent / (candidate.name + ".md")
            resolved.append(candidate)
        if not any(candidate.exists() for candidate in resolved):
            missing_links.append(f"{page.name} -> {reference}")

checks = {
    "all_pages_have_application_decision": not missing_sections and bool(pages),
    "index_has_five_question_rubric": "## 每篇文章必须回答的五个问题" in index_text,
    "application_links_resolve": not missing_links,
}
result = {
    "root": str(root),
    "page_count": len(pages),
    "missing_sections": missing_sections,
    "missing_links": missing_links,
    "checks": checks,
    "passed": all(checks.values()),
}
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(0 if result["passed"] else 1)
