"""第 5 章(下)配图的公共绘图函数：圆形节点、带箭头的连线、多行文字。"""
import math
from html import escape

from svglib import PALETTE, INK, SUB, GREY, SANS


def node(f, x, y, label, kind="white", r=22, size=17, bold=True):
    """圆形节点，居中写标签。"""
    bg, ink = PALETTE[kind]
    f.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{bg}" stroke="{ink}" stroke-width="2"/>')
    f.text(x, y + size * 0.35, str(label), size, ink if kind != "white" else INK, "700" if bold else None, "middle")


def _shorten(a, b, ra, rb):
    (x1, y1), (x2, y2) = a, b
    d = math.hypot(x2 - x1, y2 - y1) or 1
    ux, uy = (x2 - x1) / d, (y2 - y1) / d
    return x1 + ux * ra, y1 + uy * ra, x2 - ux * rb, y2 - uy * rb


def link(f, a, b, r=22, color=GREY, dash=False, curve=0, arrow=True, width=2):
    """从点 a 到点 b 的连线，端点缩进到圆边。curve≠0 时画成弯曲的二次曲线（正负决定弯向）。"""
    extra = ' stroke-dasharray="6 5"' if dash else ""
    tip = r + (3 if arrow else 0)
    if curve:
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1
        cx, cy = (a[0] + b[0]) / 2 - dy / d * curve, (a[1] + b[1]) / 2 + dx / d * curve
        x1, y1 = _shorten(a, (cx, cy), r, 0)[:2]
        x2, y2 = _shorten((cx, cy), b, 0, tip)[2:]
        path = f"M{x1:.1f} {y1:.1f}Q{cx:.1f} {cy:.1f} {x2:.1f} {y2:.1f}"
    else:
        x1, y1, x2, y2 = _shorten(a, b, r, tip)
        path = f"M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}"
    mk = f' marker-end="url(#{f._marker(color)})"' if arrow and not curve else ""
    f.parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{width}"{extra}{mk}/>')
    if arrow and curve:
        # 弯曲的线不用 marker（个别渲染器会把箭头压在节点下），直接画一个三角形箭头
        tx, ty = x2 - cx, y2 - cy
        n = math.hypot(tx, ty) or 1
        tx, ty = tx / n, ty / n
        L, W = 7 * width, 3.5 * width
        bx, by = x2 - tx * L, y2 - ty * L
        pts = f"{x2 + tx * 1.5:.1f},{y2 + ty * 1.5:.1f} {bx - ty * W:.1f},{by + tx * W:.1f} {bx + ty * W:.1f},{by - tx * W:.1f}"
        f.parts.append(f'<polygon points="{pts}" fill="{color}"/>')


def lines(f, x, y, rows, size=15, fill=INK, gap=None, maxw=None, mono=False):
    """从 (x,y) 起逐行写文字。"""
    gap = gap or round(size * 1.6)
    for i, s in enumerate(rows):
        f.text(x, y + i * gap, s, size, fill, maxw=maxw, mono=mono)


def tag(f, x, y, s, kind="blue", size=14):
    """贴在节点旁的小标签（如 dfn/low 值），居中。"""
    w = max(36, int(len(s) * size * 0.62) + 14)
    f.chip(x, y, w, size + 12, kind, s, size=size, mono=True)


def bounding(f, x, y, w, h, kind, label=None, size=15):
    """虚线分组框。"""
    f.rect(x, y, w, h, kind, dash=True, fill="none")
    if label:
        f.text(x + 12, y + 22, label, size, PALETTE[kind][1], "700")
