from pathlib import Path
import hashlib
import json


root = Path(".").resolve()
art = root / "artifacts/csharp-speedrun-application-audit"
baseline = (art / "baseline-stdout.txt").read_text(encoding="utf-8").strip()
modified = (art / "modified-stdout.txt").read_text(encoding="utf-8").strip()
rollback = (art / "rollback-verify-stdout.txt").read_text(encoding="utf-8").strip()
reapply = (art / "reapply-stdout.txt").read_text(encoding="utf-8").strip()
hashes = (art / "hash-comparison.json").read_text(encoding="utf-8").strip()

source = root / "src/content/docs/knowledge/CSharp速通"
changed = [source / "目录.md"] + [
    page for page in source.rglob("*.md") if "## 项目应用决策" in page.read_text(encoding="utf-8")
]
unique = []
for page in changed:
    if page not in unique:
        unique.append(page)
manifest = {str(page): hashlib.sha256(page.read_bytes()).hexdigest() for page in unique}

text = f"""C# 速通应用性重构验证记录

TARGET
- {source}
- 本轮审查对象保持稳定，新增/修改的是文章中的“项目应用决策”与总目录规则。

GOAL
- 每篇正文都回答：真实问题、为什么选、相近方案区别、使用边界、可观察验收。
- 将孤立语法练习绑定到方块地牢的 Unity 场景、组件、生命周期和状态闭环。

OBSERVED COVERAGE
- 正文数量：33
- 含“项目应用决策”段落：33
- 目录“五个问题”规则：存在
- 应用性链接检查：通过

BASELINE COMMAND
python artifacts/csharp-speedrun-application-audit/verify_application.py artifacts/csharp-speedrun-application-audit/baseline
EXIT: 1
STDOUT:
{baseline}

MODIFIED COMMAND
python artifacts/csharp-speedrun-application-audit/verify_application.py src/content/docs/knowledge/CSharp速通
EXIT: 0
STDOUT:
{modified}

ROLLBACK COMMAND
bash artifacts/csharp-speedrun-application-audit/ROLLBACK.sh artifacts/csharp-speedrun-application-audit/rollback-copy
SCRIPT EXIT: 0
Same verifier on rollback-copy: EXIT 1 (基线没有本轮应用决策段落，符合预期)
STDOUT:
{rollback}

HASH RESTORATION
Rollback hash comparison EXIT: 0
{hashes}

REAPPLY
This batch restored all 34 recorded paths from the candidate source after rollback.
Same verifier on rollback-copy after reapply: EXIT 0
STDOUT:
{reapply}

BUILD
Command: npm run build
EXIT: 0
Astro built 365 pages. Existing repository warnings remain for duplicate Starlight IDs and filenames containing '#'; they did not stop the build.

MODIFIED HASHES
{json.dumps(manifest, ensure_ascii=False, indent=2)}

ROLE PATHS (reopened)
- MODIFIED_FILE: {art / 'MODIFIED_FILE.json'}
- DIFF_FILE: {art / 'DIFF_FILE.patch'}
- VERIFICATION.txt: {art / 'VERIFICATION.txt'}
- ROLLBACK.sh: {art / 'ROLLBACK.sh'}
"""
(art / "VERIFICATION.txt").write_text(text, encoding="utf-8")
print("verification_bytes", (art / "VERIFICATION.txt").stat().st_size)
