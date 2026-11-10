"""算法学习专栏配图的绘制工具：沿用 C# 速通专栏的配色、字体与浅色底，输出自包含 SVG。"""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "public/assets/algo"

# (填充色, 描边与标题色)，与 scripts/oop/generate_figures.py 的三色保持一致，另加红、紫、灰。
PALETTE = {
    "blue": ("#eaf2ff", "#285caa"), "green": ("#e8f7f1", "#176951"), "orange": ("#fff2df", "#8c5315"),
    "red": ("#fdecec", "#a33a3a"), "purple": ("#f0ecfb", "#5b3fa0"), "grey": ("#eef1f6", "#495b73"),
    "white": ("#ffffff", "#66758d"),
}
INK, SUB, GREY = "#23364e", "#495b73", "#66758d"
SANS = "Microsoft YaHei, Noto Sans CJK SC, sans-serif"
MONO = "Consolas, Menlo, Noto Sans Mono CJK SC, monospace"


def text_width(s, size, mono=False):
    """粗略估算文字宽度：中日韩字符按一个字号，拉丁字符按 0.56（等宽 0.6）个字号。"""
    return sum(size if ord(c) > 0x2E80 or c in "，。：；（）、「」“”→…" else size * (0.6 if mono else 0.56) for c in s)


class Fig:
    def __init__(self, name, title, sub, height, footer=""):
        self.name, self.title, self.sub, self.h, self.footer = name, title, sub, height, footer
        self.parts, self.markers, self.warnings = [], {}, []

    def _check(self, s, size, mono, x, anchor, maxw):
        w = text_width(s, size, mono)
        left = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
        if maxw and w > maxw or left < 8 or left + w > 992:
            self.warnings.append(f"{self.name}: 文字可能溢出 ({w:.0f}px) {s!r}")

    def text(self, x, y, s, size=17, fill=INK, weight=None, anchor="start", mono=False, maxw=None):
        self._check(s, size, mono, x, anchor, maxw)
        attrs = f' font-weight="{weight}"' if weight else ""
        attrs += f' text-anchor="{anchor}"' if anchor != "start" else ""
        attrs += f' font-family="{MONO}"' if mono else ""
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}"{attrs}>{escape(s)}</text>')

    def rect(self, x, y, w, h, kind="blue", r=12, dash=False, opacity=".3", fill=None):
        bg, ink = PALETTE[kind]
        d = ' stroke-dasharray="7 5" stroke-opacity="1"' if dash else f' stroke-opacity="{opacity}"'
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill or bg}" stroke="{ink}"{d}/>')

    def box(self, x, y, w, h, kind, head=None, lines=(), size=17, mono=False):
        """带标题和若干行说明的卡片；文字宽度超出卡片会在生成时告警。"""
        self.rect(x, y, w, h, kind)
        ink = PALETTE[kind][1]
        top = y + 30
        if head:
            self.text(x + 14, top, head, 19, ink, "700", maxw=w - 28)
            top += 28
        for i, line in enumerate(lines):
            self.text(x + 14, top + i * 25, line, size, INK, mono=mono, maxw=w - 28)

    def chip(self, cx, cy, w, h, kind, s, size=16, mono=False, bold=False):
        """居中文字的小块，可用多行（用 \\n 分隔）。"""
        self.rect(cx - w / 2, cy - h / 2, w, h, kind, r=8)
        rows = s.split("\n")
        y0 = cy - (len(rows) - 1) * size * 0.65 + size * 0.35
        for i, row in enumerate(rows):
            self.text(cx, round(y0 + i * size * 1.3, 1), row, size, PALETTE[kind][1] if bold else INK,
                      "700" if bold else None, "middle", mono, maxw=w - 8)

    def _marker(self, color):
        mid = "m" + color.strip("#")
        if mid not in self.markers:
            self.markers[mid] = (f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                                 f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10" fill="{color}"/></marker>')
        return mid

    def arrow(self, x1, y1, x2, y2, color=GREY, dash=False):
        self.path(f"M{x1} {y1}L{x2} {y2}", color, dash)

    def path(self, d, color=GREY, dash=False):
        extra = ' stroke-dasharray="6 5"' if dash else ""
        self.parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"{extra} marker-end="url(#{self._marker(color)})"/>')

    def save(self):
        OUT.mkdir(parents=True, exist_ok=True)
        head = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{self.h}" viewBox="0 0 1000 {self.h}" role="img" aria-labelledby="title desc">',
            f'<title id="title">{escape(self.title)}</title><desc id="desc">{escape(self.sub + "。" + self.footer)}</desc>',
            "<defs>" + "".join(self.markers.values()) + "</defs>",
            f'<rect width="1000" height="{self.h}" rx="18" fill="#f6f8fc"/>',
            f'<g font-family="{SANS}">',
            f'<text x="32" y="44" font-size="27" font-weight="700" fill="#15263e">{escape(self.title)}</text>',
            f'<text x="32" y="77" font-size="17" fill="{SUB}">{escape(self.sub)}</text>',
        ]
        foot = [f'<text x="32" y="{self.h - 20}" font-size="16" fill="{SUB}">{escape(self.footer)}</text>'] if self.footer else []
        (OUT / f"{self.name}.svg").write_text("\n".join(head + self.parts + foot + ["</g></svg>"]), encoding="utf-8")
        return self.warnings
