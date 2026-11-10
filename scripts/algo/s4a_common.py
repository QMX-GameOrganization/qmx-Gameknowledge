"""第 4 章 4.1~4.8 配图的公共绘制函数（节点、边、数组格子、表格）。"""
from svglib import Fig, PALETTE, INK, SUB, GREY

R = 20
HOT = "#8c5315"


def edge(f, x1, y1, x2, y2, color=GREY, w=2, dash=False):
    d = ' stroke-dasharray="6 5"' if dash else ""
    f.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}"{d}/>')


def node(f, x, y, label, kind="blue", r=R, size=17):
    bg, ink = PALETTE[kind]
    f.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{bg}" stroke="{ink}" stroke-width="2"/>')
    f.text(x, round(y + size * 0.35, 1), str(label), size, ink, "700", "middle")


def tree(f, pos, edges, kinds=None, hot=(), r=R, size=17, dashed=()):
    """pos: {标签: (x, y)}；edges: [(父, 子)]；kinds: {标签: 颜色名}；hot: 需要高亮的边集合。"""
    kinds = kinds or {}
    for p, c in edges:
        (x1, y1), (x2, y2) = pos[p], pos[c]
        if (p, c) in hot:
            edge(f, x1, y1, x2, y2, HOT, 4)
        else:
            edge(f, x1, y1, x2, y2, GREY, 2, (p, c) in dashed)
    for k, (x, y) in pos.items():
        node(f, x, y, k, kinds.get(k, "blue"), r, size)


def cells(f, x, y, vals, w=60, h=44, kinds=None, size=18, index_from=None):
    """一排数组格子；kinds 为每格颜色名列表；index_from 不为空时在格子上方标下标。"""
    for i, v in enumerate(vals):
        k = kinds[i] if kinds else "white"
        f.rect(x + i * w, y, w, h, k, r=6, opacity=".6")
        f.text(x + i * w + w / 2, round(y + h / 2 + size * 0.35, 1), str(v), size, INK, "700", "middle")
        if index_from is not None:
            f.text(x + i * w + w / 2, y - 8, str(index_from + i), 13, SUB, anchor="middle")


def brace(f, x1, x2, y, label, kind="blue", size=15):
    """格子下方的横线标注。"""
    ink = PALETTE[kind][1]
    f.parts.append(f'<path d="M{x1} {y - 6}V{y}H{x2}V{y - 6}" fill="none" stroke="{ink}" stroke-width="2"/>')
    f.text((x1 + x2) / 2, y + 22, label, size, ink, "700", "middle", maxw=max(x2 - x1 + 40, 120))


def table(f, x, y, widths, header, rows, row_h=40, size=16, mono_cols=()):
    """简单表格：列宽 widths，第一行为表头；偶数行加浅色底。"""
    tot = sum(widths)
    f.rect(x, y, tot, row_h, "grey", r=6, opacity=".5")
    cx = x
    for wd, h in zip(widths, header):
        f.text(cx + 12, y + row_h / 2 + size * 0.35, h, size, PALETTE["grey"][1], "700", maxw=wd - 16)
        cx += wd
    for i, row in enumerate(rows):
        ry = y + row_h * (i + 1)
        if i % 2 == 1:
            f.rect(x, ry, tot, row_h, "grey", r=0, opacity="0", fill="#f0f3f9")
        cx = x
        for j, (wd, s) in enumerate(zip(widths, row)):
            f.text(cx + 12, round(ry + row_h / 2 + size * 0.35, 1), s, size, INK, mono=j in mono_cols, maxw=wd - 16)
            cx += wd
