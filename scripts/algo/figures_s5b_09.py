"""5.9 网络流 的配图：残量网络与反向边、Dinic 分层、最小割。"""
from svglib import Fig, PALETTE, INK, SUB
from s5b_helpers import node, link, lines

GREEN, RED, GREY, BLUE = PALETTE["green"][1], PALETTE["red"][1], PALETTE["grey"][1], PALETTE["blue"][1]


def mid(a, b, t=0.5, dy=0):
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t + dy


def elab(f, a, b, s, dy=0, t=0.5):
    x, y = mid(a, b, t, dy)
    f.chip(x, y, max(40, len(s) * 10 + 14), 24, "white", s, size=14, mono=True)


def residual():
    f = Fig("c5-09-residual", "残量网络：每条边拆成“还能推多少”和“能退回多少”", "反向边让后面的增广路可以撤销之前走歪的决定。", 570,
            "两条增广路合起来，等价于 s→a→t 和 s→b→t 各一单位，反向边上的流量互相抵消。")
    f.h = 600
    f.rect(32, 105, 468, 170, "blue")
    f.text(48, 135, "原网络：u→v 容量 5，已流 3", 17, BLUE, "700")
    u, v = (110, 215), (400, 215)
    link(f, u, v)
    elab(f, u, v, "3/5")
    node(f, *u, "u")
    node(f, *v, "v")
    f.rect(518, 105, 450, 170, "green")
    f.text(534, 135, "残量网络：两条有向边", 17, GREEN, "700")
    u2, v2 = (590, 215), (880, 215)
    link(f, u2, v2, curve=-26, color=GREEN)
    link(f, v2, u2, curve=-26, color=RED, dash=True)
    f.text(735, 178, "正向：还能推 2", 15, GREEN, "700", "middle")
    f.text(735, 262, "反向：能退回 3", 15, RED, "700", "middle")
    node(f, *u2, "u")
    node(f, *v2, "v")
    f.arrow(500, 190, 518, 190, GREY)
    pts = {"s": (90, 420), "a": (240, 360), "b": (240, 480), "t": (390, 420)}
    for ox, title, kind, col in [(0, "第一条增广路：s→a→b→t", "blue", BLUE), (518, "残量网络里再找：s→b→a→t", "green", GREEN)]:
        f.rect(32 if ox == 0 else 518, 295, 468 if ox == 0 else 450, 245, kind)
        f.text(48 if ox == 0 else 534, 325, title, 17, col, "700")
        P = {k: (x + ox, y) for k, (x, y) in pts.items()}
        if ox == 0:
            for a, b in [("s", "a"), ("a", "t"), ("s", "b"), ("b", "t")]:
                link(f, P[a], P[b])
            link(f, P["a"], P["b"], color=GREEN, width=3)
            link(f, P["s"], P["a"], color=GREEN, width=3)
            link(f, P["b"], P["t"], color=GREEN, width=3)
        else:
            link(f, P["s"], P["b"], color=RED, width=3)
            link(f, P["b"], P["a"], color=RED, width=3, dash=True)
            link(f, P["a"], P["t"], color=RED, width=3)
            f.text(P["a"][0] - 14, 428, "反向边 b→a", 15, RED, "700", "end")
        for k, p in P.items():
            node(f, *p, k)
    return f.save()


def dinic_level():
    f = Fig("c5-09-dinic-level", "Dinic：先分层，再只沿“层数加 1”的边推流", "每条边的标注是 已流量/容量，灰色虚线是不走的边。", 520,
            "两轮推流共 5，每轮之后用残量网络重新分层；反向边略去未画。")
    f.rect(32, 105, 468, 370, "blue")
    f.text(48, 137, "第 1 轮：BFS 分层，推流 4", 18, BLUE, "700")
    f.rect(518, 105, 450, 370, "green")
    f.text(534, 137, "第 2 轮：重新分层，推流 1", 18, GREEN, "700")
    P1 = {1: (100, 300), 2: (240, 210), 3: (240, 390), 4: (380, 300)}
    P2 = {k: (x + 486, y) for k, (x, y) in P1.items()}
    lv1, lv2 = {1: 0, 2: 1, 3: 1, 4: 2}, {1: 0, 2: 1, 3: 2, 4: 3}
    for P, lv in ((P1, lv1), (P2, lv2)):
        for k, p in P.items():
            node(f, *p, k, "orange" if k in (1, 4) else "white")
            f.text(p[0], p[1] - 32 if k == 2 else p[1] + 44, f"层 {lv[k]}", 14, SUB, anchor="middle")
    for a, b, s in [(1, 2, "2/3"), (2, 4, "2/2"), (1, 3, "2/2"), (3, 4, "2/3")]:
        link(f, P1[a], P1[b], color=GREEN, width=3)
        elab(f, P1[a], P1[b], s)
    link(f, P1[2], P1[3], color="#9aa5b5", dash=True)
    elab(f, P1[2], P1[3], "0/1")
    f.text(278, 305, "同层，不走", 13, SUB)
    for a, b in [(1, 2), (2, 3), (3, 4)]:        # 第 1 轮后这三条边都还剩 1
        link(f, P2[a], P2[b], color=RED, width=3)
        elab(f, P2[a], P2[b], "余1")
    for a, b in [(1, 3), (2, 4)]:
        link(f, P2[a], P2[b], color="#9aa5b5", dash=True)
        elab(f, P2[a], P2[b], "满")
    return f.save()


def mincut():
    f = Fig("c5-09-mincut", "最小割：最大流结束后，从 s 在残量网络里能到的点就是 S 侧", "边的标注是 已流量/容量。", 560,
            "割边必为满边，容量之和等于最大流 4。")
    f.h = 590
    P = {"s": (110, 310), "a": (320, 200), "b": (320, 420), "t": (530, 310)}
    f.rect(32, 105, 600, 420, "blue")
    for a, b, s, cut in [("s", "a", "2/3", 0), ("a", "t", "2/2", 1), ("s", "b", "2/2", 1), ("b", "t", "2/3", 0)]:
        link(f, P[a], P[b], color=RED if cut else GREY, width=3 if cut else 2)
        elab(f, P[a], P[b], s)
    for k, p in P.items():
        node(f, *p, k, "green" if k in "sa" else "orange")
    f.text(48, 140, "绿色：S 侧   橙色：T 侧   红色粗线：割边", 16, SUB)
    f.rect(650, 105, 318, 420, "grey")
    f.text(666, 137, "怎么得到割", 19, GREY, "700")
    lines(f, 666, 172, [
        "① 跑完最大流，流量为 4。",
        "② 从 s 沿“剩余容量>0”的",
        "边走：s→a 还剩 1，到 a。",
        "③ a→t、s→b 已满，停下。",
        "④ S = {s, a}，T = {b, t}。",
        "⑤ S 到 T 的原边：",
        "a→t（2）和 s→b（2），",
        "容量和 4 = 最大流。",
    ], 14, gap=30, maxw=290)
    return f.save()


def build_all():
    return residual() + dinic_level() + mincut()
