"""5.12 次短路、k 短路与最小环 的配图。"""
from svglib import Fig, PALETTE, INK, SUB
from s5b_helpers import node, link, lines
from figures_s5b_09 import elab

GREEN, RED, GREY, BLUE, ORANGE = (PALETTE[k][1] for k in ("green", "red", "grey", "blue", "orange"))


def second():
    f = Fig("c5-12-second", "严格次短路：每个点记两个值，最短 d1 和严格更长的最短 d2", "无向图，求 1 到 4，边可以重复走。", 540,
            "d2 可以来自“走到邻点再折返”，所以图里没有第二条简单路径时也可能有次短路。")
    f.h = 575
    P = {1: (120, 270), 2: (330, 180), 3: (330, 360), 4: (540, 270)}
    f.rect(32, 105, 590, 400, "blue")
    for a, b, w, col in [(1, 2, 2, GREEN), (2, 4, 3, GREEN), (1, 3, 4, ORANGE), (3, 4, 2, ORANGE)]:
        link(f, P[a], P[b], arrow=False, color=col, width=4)
    for a, b, w, col in [(1, 2, 2, GREEN), (2, 4, 3, GREEN), (1, 3, 4, ORANGE), (3, 4, 2, ORANGE)]:
        elab(f, P[a], P[b], str(w))      # 先画线再画权值，权值不会被线盖住
    for k, p in P.items():
        node(f, *p, k)
    f.text(48, 140, "绿色：最短 1-2-4 = 5   橙色：次短 1-3-4 = 6", 15, SUB)
    f.rect(640, 105, 328, 400, "grey")
    f.text(656, 137, "各点的 (d1, d2)", 19, GREY, "700")
    rows = [("1", "0", "4", "1-2-1"), ("2", "2", "6", "1-2-1-2"), ("3", "4", "7", "1-2-4-3"), ("4", "5", "6", "1-3-4")]
    f.text(656, 175, "点", 14, SUB)
    f.text(710, 175, "d1", 14, SUB)
    f.text(770, 175, "d2", 14, SUB)
    f.text(830, 175, "d2 的走法", 14, SUB)
    for i, (v, a, b, w) in enumerate(rows):
        y = 210 + i * 42
        f.text(656, y, v, 17, INK, "700")
        f.text(710, y, a, 17, GREEN, "700")
        f.text(770, y, b, 17, ORANGE, "700")
        f.text(830, y, w, 14, INK, mono=True)
    lines(f, 656, 410, ["松弛 nd = d + w：", "nd < d1 → 旧 d1 降为 d2", "d1 < nd < d2 → 更新 d2"], 14, gap=26, maxw=300)
    return f.save()


def kth():
    f = Fig("c5-12-kth", "k 短路（A*）：用反图最短距离 h 当估价，f = g + h", "有向图，求 1 到 4 的前 3 短路径（允许重复经过点）。", 540,
            "每个点最多出队 k 次；第 j 次出队的终点对应第 j 短路径。")
    f.h = 575
    P = {1: (90, 280), 2: (250, 180), 3: (250, 390), 4: (410, 280)}
    f.rect(32, 105, 460, 400, "blue")
    for a, b, w, dy in [(1, 2, 1, 0), (1, 3, 2, 0), (2, 4, 3, 0), (3, 4, 1, 0), (2, 3, 1, 0)]:
        link(f, P[a], P[b])
        elab(f, P[a], P[b], str(w))
    h = {1: 3, 2: 2, 3: 1, 4: 0}
    for k, p in P.items():
        node(f, *p, k, "orange" if k in (1, 4) else "white")
        if k == 2:
            f.text(p[0] - 32, p[1] + 5, f"h={h[k]}", 14, SUB, anchor="end")
        else:
            f.text(p[0], p[1] + 42, f"h={h[k]}", 14, SUB, anchor="middle")
    f.text(48, 140, "h 来自在反图上从 4 出发的 Dijkstra", 15, SUB)
    f.rect(510, 105, 458, 400, "grey")
    f.text(526, 137, "出队顺序 (f, g, 点)", 19, GREY, "700")
    steps = [("1", "(3, 0, 1)", "展开 2、3"), ("2", "(3, 1, 2)", "展开 4、3"), ("3", "(3, 2, 3)", "展开 4"),
             ("4", "(3, 2, 3)", "展开 4"), ("5", "(3, 3, 4)", "第 1 短 = 3"), ("6", "(3, 3, 4)", "第 2 短 = 3"),
             ("7", "(4, 4, 4)", "第 3 短 = 4")]
    for i, (n, t, s) in enumerate(steps):
        y = 178 + i * 40
        f.text(526, y, n, 15, SUB)
        f.text(556, y, t, 16, INK, mono=True)
        f.text(700, y, s, 16, GREEN if "短" in s else INK, "700" if "短" in s else None)
    return f.save()


def mincycle():
    f = Fig("c5-12-mincycle", "Floyd 求最小环：环上编号最大的点是 k", "在 d 还没把 k 当中转点之前，枚举 i、j 与 k 围成的环。", 540,
            "环长 = d[i][j] + w[i][k] + w[k][j]，要求 i ≠ j 且都小于 k。")
    f.h = 575
    P = {1: (140, 210), 2: (380, 210), 3: (380, 400), 4: (140, 400)}
    f.rect(32, 105, 520, 400, "blue")
    for a, b, w, hot in [(1, 2, 2, 1), (2, 3, 2, 1), (3, 4, 1, 1), (4, 1, 1, 1), (1, 3, 5, 0)]:
        link(f, P[a], P[b], arrow=False, color=RED if hot else GREY, width=4 if hot else 2)
        elab(f, P[a], P[b], str(w), t=0.5 if (a, b) != (1, 3) else 0.3)
    for k, p in P.items():
        node(f, *p, k, "orange" if k == 4 else "white")
    f.text(48, 140, "红色：最小环 1-2-3-4-1，长度 6", 15, SUB)
    f.rect(570, 105, 398, 400, "grey")
    f.text(586, 137, "k = 4 时", 19, GREY, "700")
    lines(f, 586, 175, [
        "此时 d 只用了点 1、2、3 作中转：",
        "d[1][3] = min(5, 2+2) = 4",
        "取 i=1，j=3：",
        "环长 = 4 + w[1][4] + w[4][3]",
        "       = 4 + 1 + 1 = 6",
        "k = 3 时，i=1，j=2：",
        "环长 = 2 + 5 + 2 = 9",
        "全局取最小值 6。",
    ], 14, gap=32, maxw=370)
    return f.save()


def build_all():
    return second() + kth() + mincycle()
