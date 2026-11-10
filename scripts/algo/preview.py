"""把 SVG 渲染成 PNG 供目检（需要 cairosvg；预览时才替换字体，不改源文件）。
用法：python3 scripts/algo/preview.py <输出目录> [图名...]"""
import sys
from pathlib import Path

import cairosvg

SRC = Path(__file__).resolve().parents[2] / "public/assets/algo"


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    for n in sys.argv[2:] or [p.stem for p in sorted(SRC.glob("*.svg"))]:
        s = (SRC / f"{n}.svg").read_text(encoding="utf-8")
        s = s.replace("Microsoft YaHei, Noto Sans CJK SC, sans-serif", "Noto Sans CJK SC")
        s = s.replace("Consolas, Menlo, Noto Sans Mono CJK SC, monospace", "Noto Sans CJK SC")
        cairosvg.svg2png(bytestring=s.encode("utf-8"), write_to=str(out / f"{n}.png"), scale=1)
        print(n)


if __name__ == "__main__":
    main()
