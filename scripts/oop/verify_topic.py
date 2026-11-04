"""校验新增专题的发布链接、配图和代码同步；不修改其他专题。"""
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
import argparse
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "src/content/docs/knowledge/面向对象串讲"


def main():
    """基于实际构建输出验证引用目标，避免把源文件存在误当成发布链接有效。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("build", type=Path)
    args = parser.parse_args()
    checked = 0
    for path in sorted(DOCS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        page = args.build / "knowledge/面向对象串讲" / path.stem / "index.html"
        assert page.is_file(), f"missing built page: {page}"
        base = f"/qmx-Gameknowledge/knowledge/面向对象串讲/{path.stem}/"
        for link in re.findall(r"\]\(([^)]+)\)", text):
            url = urlsplit(urljoin(base, link))
            if url.scheme or not url.path.startswith("/qmx-Gameknowledge/"):
                continue
            target = args.build / unquote(url.path.removeprefix("/qmx-Gameknowledge/"))
            if url.path.endswith("/"):
                target /= "index.html"
            assert target.is_file(), f"broken link in {path.name}: {link} -> {target}"
            checked += 1
    for svg in (ROOT / "public/assets/oop").glob("*.svg"):
        ET.parse(svg)
    for chapter, source, lang in [("18-battle-lab.md", "battle.cpp", "cpp")]:
        text = (DOCS / chapter).read_text(encoding="utf-8")
        expected = (ROOT / "public/examples/oop" / source).read_text(encoding="utf-8").strip()
        assert f"```{lang}\n{expected}\n```" in text, f"example drift: {source}"
    pages = sorted(DOCS.glob("[0-9][0-9]-*.md"))
    assert [int(p.name[:2]) for p in pages] == list(range(20)), "chapter sequence must be 00 through 19"
    for current, following in zip(pages, pages[1:]):
        assert f"../{following.stem}/" in current.read_text(encoding="utf-8"), f"missing next-chapter link: {current.name}"
    print(f"PASS: {len(pages)+1} pages, {len(list((ROOT / 'public/assets/oop').glob('*.svg')))} valid SVGs, {checked} local links, 1 synchronized example; chapter order 00-19 verified")


if __name__ == "__main__":
    main()
