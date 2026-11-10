"""5.10 欧拉路径与回路 的配图：存在条件、Hierholzer 过程。"""
from svglib import Fig, PALETTE, INK, SUB
from s5b_helpers import node, link, lines, tag

GREEN, RED, GREY, BLUE, ORANGE = (PALETTE[k][1] for k in ("green", "red", "grey", "blue", "orange"))


def _mini(f, ox, oy, pts, edges, directed, marks=None):
    P = {k: (ox + x, oy + y) for k, (x, y) in pts.items()}
    for a, b in edges:
        link(f, P[a], P[b], r=16, arrow=directed)
    for k, p in P.items():
        node(f, *p, k, "orange" if marks and k in marks else "white", r=16, size=15)
    return P


def conditions():
    f = Fig("c5-10-conditions", "欧拉回路与欧拉路径：看度数就能判断", "前提是所有有边的点互相连通；孤立点不影响。", 560,
            "橙色点是路径的起点或终点。")
    f.h = 585
    cells = [
        (32, 105, 468, "无向图 · 欧拉回路", "green", "每个点度数为偶数", ["起点任选", "最后回到起点"],
         {1: (50, 140), 2: (115, 75), 3: (180, 140)}, [(1, 2), (2, 3), (3, 1)], False, None),
        (518, 105, 450, "无向图 · 欧拉路径", "blue", "恰有两个奇度点", ["必须从奇度点出发", "在另一个奇度点结束"],
         {1: (40, 150), 2: (95, 85), 3: (150, 150), 4: (225, 100)}, [(1, 2), (2, 3), (3, 1), (3, 4)], False, {3, 4}),
        (32, 325, 468, "有向图 · 欧拉回路", "green", "每个点入度 = 出度", ["起点任选", "最后回到起点"],
         {1: (50, 140), 2: (115, 75), 3: (180, 140)}, [(1, 2), (2, 3), (3, 1)], True, None),
        (518, 325, 450, "有向图 · 欧拉路径", "blue", "起点 出-入=1，终点 入-出=1", ["其余点入度 = 出度"],
         {1: (40, 150), 2: (95, 85), 3: (150, 150), 4: (225, 100)}, [(1, 2), (2, 3), (3, 1), (3, 4)], True, {3, 4}),
    ]
    for ox, oy, w, title, kind, cond, notes, pts, edges, directed, marks in cells:
        f.rect(ox, oy, w, 200, kind)
        f.text(ox + 16, oy + 32, title, 18, PALETTE[kind][1], "700")
        _mini(f, ox, oy + 20, pts, edges, directed, marks)
        f.text(ox + 16 + (230 if w == 468 else 255), oy + 85, cond, 15 if len(cond) < 14 else 13, INK, "700",
               maxw=w - 260)
        lines(f, ox + 16 + (230 if w == 468 else 255), oy + 120, notes, 14, gap=26, maxw=w - 260)
    return f.save()


def hierholzer():
    f = Fig("c5-10-hierholzer", "Hierholzer：走进死胡同再回溯，遇到没走完的点就接上一个圈", "无向图，6 条边，从 1 出发。", 560,
            "回溯入栈序列反过来，就是一条欧拉回路。")
    f.h = 590
    P = {1: (190, 215), 2: (190, 440), 3: (370, 330), 4: (550, 215), 5: (550, 440)}
    f.rect(32, 105, 600, 420, "blue")
    seq1 = [(1, 2), (2, 3), (3, 1)]
    seq2 = [(3, 4), (4, 5), (5, 3)]
    for i, (a, b) in enumerate(seq1 + seq2, 1):
        link(f, P[a], P[b], color=BLUE if i <= 3 else ORANGE, width=3)
        x, y = (P[a][0] + P[b][0]) / 2, (P[a][1] + P[b][1]) / 2
        f.chip(x, y, 28, 26, "white", str(i), size=15, bold=True)
    for k, p in P.items():
        node(f, *p, k, "orange" if k == 3 else "white")
    f.text(48, 140, "边上的数字是实际走过的先后；蓝色：先走的路，橙色：回溯后接上的圈", 15, SUB)
    f.rect(650, 105, 318, 420, "grey")
    f.text(666, 137, "过程", 19, GREY, "700")
    lines(f, 666, 172, [
        "甲 1→2→3→1 走进死胡同，",
        "   1 先入栈。",
        "乙 回溯到 3，3 还有没走的",
        "   边，走 3→4→5→3。",
        "丙 圈走完，3、5、4 依次入栈。",
        "丁 继续回溯，3、2、1 入栈。",
        "入栈序列：1 3 5 4 3 2 1",
        "反转：1 2 3 4 5 3 1",
    ], 14, gap=30, maxw=294)
    return f.save()


def build_all():
    return conditions() + hierholzer()
