"""第 5 章 5.1~5.6 的配图。"""
import math
from svglib import Fig, GREY, SUB, INK, PALETTE

BG = "#f6f8fc"
GRID = "#c5cfdf"
GREEN = PALETTE["green"][1]
BLUE = PALETTE["blue"][1]
ORANGE = PALETTE["orange"][1]
RED = PALETTE["red"][1]
PURPLE = PALETTE["purple"][1]


def node(f, p, label, kind="white", r=22, size=18):
    bg, ink = PALETTE[kind]
    f.parts.append(f'<circle cx="{p[0]}" cy="{p[1]}" r="{r}" fill="{bg}" stroke="{ink}" stroke-width="2"/>')
    f.text(p[0], p[1] + size * 0.35, str(label), size, INK, "700", "middle")


def edge(f, p, q, w=None, directed=False, color=GREY, width=2, dash=False, r=22, bend=0,
         lpos=0.5, lshift=(0, 0), lsize=15, lcolor=None):
    """画一条边(可带箭头、弯曲、权值标签)。p、q 是两端节点的圆心。"""
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    a = (p[0] + ux * r, p[1] + uy * r)
    b = (q[0] - ux * (r + (3 if directed else 0)), q[1] - uy * (r + (3 if directed else 0)))
    mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    extra = ' stroke-dasharray="6 5"' if dash else ""
    mk = f' marker-end="url(#{f._marker(color)})"' if directed else ""
    if bend:
        c = (mid[0] + nx * bend * 2, mid[1] + ny * bend * 2)
        d = f"M{a[0]:.1f} {a[1]:.1f}Q{c[0]:.1f} {c[1]:.1f} {b[0]:.1f} {b[1]:.1f}"
        lx, ly = mid[0] + nx * bend, mid[1] + ny * bend
    else:
        d = f"M{a[0]:.1f} {a[1]:.1f}L{b[0]:.1f} {b[1]:.1f}"
        lx, ly = p[0] + dx * lpos, p[1] + dy * lpos
    f.parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{extra}{mk}/>')
    if w is not None:
        s = str(w)
        tw = max(22, len(s) * lsize * 0.6 + 12)
        lx += lshift[0]
        ly += lshift[1]
        f.parts.append(f'<rect x="{lx - tw / 2:.1f}" y="{ly - 11:.1f}" width="{tw:.1f}" height="22" rx="6" fill="{BG}"/>')
        f.text(round(lx, 1), round(ly + 5, 1), s, lsize, lcolor or color, "700", "middle")


def cell(f, x, y, w, h, s, fill="#ffffff", bold=False, mono=True, size=15, color=INK, stroke=GRID):
    f.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}"/>')
    f.text(round(x + w / 2, 1), round(y + h / 2 + size * 0.35, 1), s, size, color, "700" if bold else None,
           "middle", mono, maxw=w - 4)


HL = "#d9f0e4"   # 高亮(变化)格
HL2 = "#fff2df"  # 次高亮
HEAD = "#eaf2ff"


# ---------------------------------------------------------------- 5.1
def adj_storage():
    f = Fig("c5-01-adj-storage", "图的两种存储:邻接表与链式前向星",
            "同一张有向带权图:左边是图,右边是邻接表,下面是链式前向星。", 710,
            "前向星用头插法,遍历顺序与输入顺序相反;vector 邻接表保持输入顺序。")
    P = {1: (80, 250), 2: (250, 160), 3: (250, 340)}
    edge(f, P[1], P[2], 5, True, BLUE, bend=-24, lshift=(0, 0))
    edge(f, P[1], P[2], 1, True, BLUE, bend=24)
    edge(f, P[1], P[3], 7, True, GREEN, bend=18)
    edge(f, P[3], P[1], 2, True, ORANGE, bend=18)
    for k, p in P.items():
        node(f, p, k, "white")
    f.text(32, 118, "图(n=3, m=4)", 17, SUB, "700")
    f.text(32, 410, "输入顺序:1→2(5) 1→3(7) 1→2(1) 3→1(2)", 15, SUB)
    # 邻接表
    f.rect(360, 105, 608, 250, "grey")
    f.text(376, 135, "邻接表  vector<pair<int,int>> g[u]", 18, PALETTE["grey"][1], "700")
    rows = {1: ["(2,5)", "(3,7)", "(2,1)"], 2: [], 3: ["(1,2)"]}
    for i, u in enumerate((1, 2, 3)):
        y = 190 + i * 55
        f.chip(410, y, 70, 38, "white", f"g[{u}]", 16, mono=True, bold=True)
        x = 480
        if not rows[u]:
            f.text(x + 14, y + 6, "空(没有出边)", 15, SUB)
        for item in rows[u]:
            f.arrow(x + 2, y, x + 28, y, GREY)
            f.chip(x + 70, y, 76, 38, "blue", item, 16, mono=True)
            x += 100
    f.text(376, 340, "(v, w) 表示一条指向 v、权为 w 的边", 15, SUB)
    # 前向星
    f.rect(32, 440, 936, 215, "orange")
    f.text(48, 470, "链式前向星  head[u] 指向 u 最近加入的出边,nxt[e] 指向同一起点的上一条", 18, ORANGE, "700")
    x0, y0, cw, ch = 48, 490, 70, 32
    for r_, (name, vals) in enumerate([("边号 e", [1, 2, 3, 4]), ("to[e]", [2, 3, 2, 1]),
                                      ("wt[e]", [5, 7, 1, 2]), ("nxt[e]", [0, 1, 2, 0])]):
        cell(f, x0, y0 + r_ * ch, 90, ch, name, HEAD, True, False, 14)
        for c_, v in enumerate(vals):
            cell(f, x0 + 90 + c_ * cw, y0 + r_ * ch, cw, ch, str(v), "#ffffff" if r_ else HEAD, r_ == 0)
    hx = 470
    for r_, (name, v) in enumerate([("head[1]", 3), ("head[2]", 0), ("head[3]", 4)]):
        cell(f, hx, y0 + r_ * ch, 90, ch, name, HEAD, True, False, 14)
        cell(f, hx + 90, y0 + r_ * ch, 60, ch, str(v), "#ffffff")
    f.text(hx, y0 + 3 * ch + 22, "0 表示没有边了", 14, SUB)
    f.text(650, 512, "遍历 1 的出边:", 16, ORANGE, "700")
    f.text(650, 540, "e = head[1] = 3  →  2(权1)", 15, mono=True)
    f.text(650, 566, "e = nxt[3]  = 2  →  3(权7)", 15, mono=True)
    f.text(650, 592, "e = nxt[2]  = 1  →  2(权5)", 15, mono=True, maxw=316)
    return f.save()


DAG = {1: (70, 260), 2: (210, 150), 3: (210, 370), 4: (360, 210), 5: (360, 370), 6: (490, 290)}
DAG_E = [(1, 2, 3), (1, 3, 2), (2, 4, 4), (3, 4, 6), (3, 5, 3), (4, 6, 2), (5, 6, 4)]


def topo_steps():
    f = Fig("c5-01-topo-steps", "Kahn 算法:反复取出入度为 0 的点", "每取出一个点,就删掉它的出边,让后继的入度减 1。", 560,
            "取出顺序就是一个合法的拓扑序。若最后取出的点数少于 n,说明图里有环。")
    indeg = {1: 0, 2: 1, 3: 1, 4: 2, 5: 1, 6: 2}
    for u, v, _ in DAG_E:
        edge(f, DAG[u], DAG[v], None, True, GREY)
    for k, p in DAG.items():
        node(f, p, k, "green" if indeg[k] == 0 else "white")
    below = {1: 38, 2: 40, 3: 38, 4: -40, 5: 38, 6: 38}
    for k, p in DAG.items():
        f.text(p[0], p[1] + below[k] + (0 if below[k] > 0 else 6), f"入度 {indeg[k]}", 14, SUB, anchor="middle")
    f.text(32, 118, "有向无环图(绿色:起始入度为 0)", 17, SUB, "700")
    x0, y0 = 560, 125
    cols = [("取出", 62), ("入度 d1…d6", 150), ("队列", 196)]
    x = x0
    for name, w in cols:
        cell(f, x, y0, w, 36, name, HEAD, True, False, 14)
        x += w
    rows = [("—", "0 1 1 2 1 2", "[1]"), ("1", "- 0 0 2 1 2", "[2, 3]"), ("2", "- - 0 1 1 2", "[3]"),
            ("3", "- - - 0 0 2", "[4, 5]"), ("4", "- - - - 0 1", "[5]"), ("5", "- - - - - 0", "[6]"),
            ("6", "- - - - - -", "[ ]")]
    for i, row in enumerate(rows):
        x = x0
        for j, (name, w) in enumerate(cols):
            fill = "#ffffff"
            if j == 2 and i in (1, 3, 5):
                fill = HL
            cell(f, x, y0 + 36 + i * 38, w, 38, row[j], fill, j == 0)
            x += w
    f.text(x0, y0 + 36 + 7 * 38 + 30, "拓扑序:1 2 3 4 5 6", 18, GREEN, "700")
    f.text(x0, y0 + 36 + 7 * 38 + 58, "绿色格:这一步有新的点入度变为 0,入队", 14, SUB)
    return f.save()


def dag_dp():
    f = Fig("c5-01-dag-dp", "DAG 上的最长路:按拓扑序递推", "dp[v] = max(dp[u] + w),u 是 v 的前驱;每个 dp[u] 在使用时已经定型。", 540,
            "绿色粗线是一条最长路径 1→3→4→6,长度 10。")
    best = {(1, 3), (3, 4), (4, 6)}
    for u, v, w in DAG_E:
        hi = (u, v) in best
        edge(f, DAG[u], DAG[v], w, True, GREEN if hi else GREY, width=4 if hi else 2, lpos=0.45)
    dp = {1: 0, 2: 3, 3: 2, 4: 8, 5: 5, 6: 10}
    for k, p in DAG.items():
        node(f, p, k, "green" if k in (1, 3, 4, 6) else "white")
    off = {1: (0, 44), 2: (0, -42), 3: (0, 44), 4: (0, -42), 5: (0, 44), 6: (0, 44)}
    for k, p in DAG.items():
        f.text(p[0] + off[k][0], p[1] + off[k][1] + (0 if off[k][1] > 0 else 6), f"dp={dp[k]}", 16, ORANGE, "700", "middle")
    f.rect(590, 105, 378, 380, "grey")
    f.text(606, 137, "按拓扑序 1,2,3,4,5,6 计算", 17, PALETTE["grey"][1], "700")
    lines = [(0, "dp[1] = 0(没有前驱)"), (0, "dp[2] = dp[1] + 3 = 3"), (0, "dp[3] = dp[1] + 2 = 2"),
             (0, "dp[4] = max(dp[2] + 4, dp[3] + 6)"), (1, "= max(7, 8) = 8"),
             (0, "dp[5] = dp[3] + 3 = 5"), (0, "dp[6] = max(dp[4] + 2, dp[5] + 4)"), (1, "= max(10, 9) = 10")]
    for i, (ind, s) in enumerate(lines):
        f.text(606 + ind * 56, 175 + i * 32, s, 15, mono=True, maxw=350 - ind * 56)
    f.text(606, 455, "拓扑序保证:算 dp[v] 时所有前驱都已算完", 14, SUB, maxw=350)
    return f.save()


# ---------------------------------------------------------------- 5.2
def relax():
    f = Fig("c5-02-relax", "松弛(relaxation):用一条边尝试改进距离", "核心判断只有一句:dist[u] + w 是否小于 dist[v]。", 590,
            "各种最短路算法的区别,只在于按什么顺序做松弛、做多少次。")
    for x0, kind, title in ((32, "green", "松弛成功"), (518, "orange", "松弛失败")):
        f.rect(x0, 105, 450, 270, kind)
        f.text(x0 + 16, 137, title, 19, PALETTE[kind][1], "700")
    # 成功
    u, v = (110, 260), (390, 260)
    edge(f, u, v, 4, True, GREEN, width=3, lshift=(0, -24), lsize=17)
    node(f, u, "u", "white")
    node(f, v, "v", "white")
    f.text(110, 312, "dist[u] = 3", 16, INK, "700", "middle")
    f.text(390, 312, "dist[v] = 9", 16, INK, "700", "middle")
    f.text(48, 345, "3 + 4 = 7 < 9,更新 dist[v] = 7", 17, GREEN, "700")
    # 失败
    u2, v2 = (596, 260), (876, 260)
    edge(f, u2, v2, 4, True, ORANGE, width=3, lshift=(0, -24), lsize=17)
    node(f, u2, "u", "white")
    node(f, v2, "v", "white")
    f.text(596, 312, "dist[u] = 3", 16, INK, "700", "middle")
    f.text(876, 312, "dist[v] = 5", 16, INK, "700", "middle")
    f.text(534, 345, "3 + 4 = 7 ≥ 5,不更新", 17, ORANGE, "700")
    f.rect(32, 400, 936, 110, "blue")
    f.text(48, 432, "收敛条件", 19, BLUE, "700")
    f.text(48, 464, "当所有边都不能再松弛时,对每条边 (u, v, w) 都有 dist[v] ≤ dist[u] + w,", 17)
    f.text(48, 490, "此时 dist 就是最短距离。松弛时 dist[u] 若是 INF 要先跳过,免得溢出。", 17)
    return f.save()


UG = {1: (60, 260), 2: (190, 150), 3: (190, 370), 4: (340, 260), 5: (450, 370)}
UG_E = [(1, 2, 2), (1, 3, 5), (2, 3, 1), (2, 4, 4), (3, 4, 1), (3, 5, 6), (4, 5, 2)]


def dijkstra_steps():
    f = Fig("c5-02-dijkstra-steps", "Dijkstra 逐步执行", "每次取出堆里 dist 最小的点,用它的边去松弛邻居;被取出的点距离不再改变。", 630,
            "堆里残留的过期元素 (5,点3)、(6,点4)、(9,点5) 取出时发现 d > dist[u],直接跳过。")
    final = {1: 0, 2: 2, 3: 3, 4: 4, 5: 6}
    for u, v, w in UG_E:
        edge(f, UG[u], UG[v], w, False, GREY, lpos=0.5)
    for k, p in UG.items():
        node(f, p, k, "white")
    f.text(32, 118, "无向图,起点为 1", 17, SUB, "700")
    x0, y0 = 520, 125
    cw = [112, 64, 64, 64, 64, 64]
    heads = ["", "dist[1]", "dist[2]", "dist[3]", "dist[4]", "dist[5]"]
    x = x0
    for w, h in zip(cw, heads):
        cell(f, x, y0, w, 36, h, HEAD, True, False, 13)
        x += w
    rows = [("初始", ["0", "∞", "∞", "∞", "∞"], set()),
            ("取出 1 (0)", ["0", "2", "5", "∞", "∞"], {1, 2}),
            ("取出 2 (2)", ["0", "2", "3", "6", "∞"], {2, 3}),
            ("取出 3 (3)", ["0", "2", "3", "4", "9"], {3, 4}),
            ("取出 4 (4)", ["0", "2", "3", "4", "6"], {4}),
            ("取出 5 (6)", ["0", "2", "3", "4", "6"], set())]
    for i, (name, vals, changed) in enumerate(rows):
        y = y0 + 36 + i * 40
        cell(f, x0, y, cw[0], 40, name, "#ffffff", True, False, 14)
        for j, v in enumerate(vals):
            fill = HL if j in changed else "#ffffff"
            cell(f, x0 + cw[0] + j * 64, y, 64, 40, v, fill, j in changed)
    f.text(x0, y0 + 36 + 6 * 40 + 28, "绿色格:本步被松弛更新", 14, SUB)
    f.text(x0, y0 + 36 + 6 * 40 + 56, "最终:0 2 3 4 6", 18, GREEN, "700")
    f.rect(520, 470, 448, 90, "grey")
    f.text(534, 498, "堆中元素是 (距离, 点)。", 15)
    f.text(534, 524, "点 5 先后以 9、6 入堆,取出 9 时早已过期。", 15)
    f.text(534, 548, "这就是代码里 if (d > dist[u]) continue; 的用处。", 15)
    return f.save()


def floyd_idea():
    f = Fig("c5-02-floyd", "Floyd:允许使用的中转点逐个增加", "d[i][j] = min(d[i][j], d[i][k] + d[k][j]),k 必须在最外层循环。", 650,
            "第 k 轮结束后,d[i][j] 是只经过编号 ≤ k 的点作中转时的最短距离。")
    P = {1: (80, 200), 2: (230, 130), 3: (230, 290)}
    edge(f, P[1], P[2], 4, True, BLUE, lshift=(-6, -8))
    edge(f, P[2], P[3], 1, True, BLUE, lshift=(14, 0))
    edge(f, P[1], P[3], 6, True, BLUE, lshift=(-14, 8))
    for k, p in P.items():
        node(f, p, k)
    # 3->1 画成下方弧线,避免与 1->3 重叠
    edge(f, (230, 290), (80, 200), 2, True, ORANGE, bend=-34, lshift=(0, 0))
    f.text(32, 118, "三个点的小图", 17, SUB, "700")
    f.text(32, 355, "边:1→2(4) 2→3(1) 1→3(6) 3→1(2)", 14, SUB)
    mats = [("初始", [[0, 4, 6], [None, 0, 1], [2, None, 0]], set()),
            ("k=1 之后", [[0, 4, 6], [None, 0, 1], [2, 6, 0]], {(2, 1)}),
            ("k=2 之后", [[0, 4, 5], [None, 0, 1], [2, 6, 0]], {(0, 2)}),
            ("k=3 之后", [[0, 4, 5], [3, 0, 1], [2, 6, 0]], {(1, 0)})]
    bx = [330, 480, 630, 780]
    for (title, M, ch), x in zip(mats, bx):
        f.text(x + 66, 135, title, 16, INK, "700", "middle")
        for i in range(3):
            for j in range(3):
                v = M[i][j]
                cell(f, x + j * 44, 150 + i * 44, 44, 44, "∞" if v is None else str(v),
                     HL if (i, j) in ch else "#ffffff", (i, j) in ch)
    notes = [("", ""), ("经过点 1:", "d[3][2] = d[3][1] + d[1][2] = 2 + 4 = 6"),
             ("经过点 2:", "d[1][3] = min(6, d[1][2] + d[2][3]) = 5"),
             ("经过点 3:", "d[2][1] = d[2][3] + d[3][1] = 1 + 2 = 3")]
    for i in range(1, 4):
        f.text(330, 330 + (i - 1) * 56, notes[i][0], 16, BLUE, "700")
        f.text(330, 330 + (i - 1) * 56 + 26, notes[i][1], 15, mono=True, maxw=620)
    f.rect(32, 520, 936, 60, "orange")
    f.text(48, 557, "如果把 k 放到内层,当前轮用到的 d[i][k] 还没经过前面的中转点,会漏掉路径。", 16)
    return f.save()


# ---------------------------------------------------------------- 5.3
MG = {1: (70, 260), 5: (330, 150), 3: (250, 320), 4: (440, 290), 2: (260, 450)}
MG_E = [(1, 3, 1), (3, 5, 2), (1, 5, 3), (2, 4, 4), (3, 4, 5), (2, 3, 6), (1, 2, 7), (4, 5, 8)]


def cut_property():
    f = Fig("c5-03-cut", "两条性质:切割性质与环性质", "它们解释了 Kruskal 和 Prim 为什么贪心是对的。", 550,
            "切割性质管\"选哪条\",环性质管\"丢哪条\"。")
    f.rect(32, 105, 470, 380, "blue")
    f.text(48, 137, "切割性质", 19, BLUE, "700")
    f.text(48, 165, "把点分成 S 和 V\\S 两部分,横跨两部分的边里", 15, maxw=440)
    f.text(48, 188, "最小的一条必在某棵最小生成树里。", 15, maxw=440)
    f.parts.append(f'<ellipse cx="150" cy="340" rx="90" ry="100" fill="#ffffff" fill-opacity=".7" stroke="{BLUE}" stroke-dasharray="6 5"/>')
    f.parts.append(f'<ellipse cx="390" cy="340" rx="90" ry="100" fill="#ffffff" fill-opacity=".7" stroke="{ORANGE}" stroke-dasharray="6 5"/>')
    A = [(120, 290), (160, 380), (190, 310)]
    B = [(350, 290), (420, 310), (380, 390)]
    for p, n in zip(A, "abc"):
        node(f, p, n, "blue", 18, 16)
    for p, n in zip(B, "xyz"):
        node(f, p, n, "orange", 18, 16)
    edge(f, A[0], A[2], 2, False, GREY, r=18)
    edge(f, B[0], B[1], 6, False, GREY, r=18)
    edge(f, A[2], B[0], 3, False, GREEN, 4, r=18, lpos=0.5, lshift=(0, -14))
    edge(f, A[2], B[1], 7, False, RED, 2, True, r=18, lpos=0.45, lshift=(0, 12))
    edge(f, A[1], B[2], 5, False, RED, 2, True, r=18, lshift=(0, 12))
    f.text(150, 460, "S", 17, BLUE, "700", "middle")
    f.text(390, 460, "V \\ S", 17, ORANGE, "700", "middle")
    f.text(270, 226, "横跨的边:3、5、7,最小的 3 一定可选", 14, GREEN, "700", "middle", maxw=300)
    f.rect(518, 105, 450, 380, "red")
    f.text(534, 137, "环性质", 19, RED, "700")
    f.text(534, 165, "一个环里权最大的边", 15)
    f.text(534, 188, "(且唯一最大时)不在任何最小生成树里。", 15)
    C = {"a": (640, 300), "b": (800, 300), "c": (870, 400), "d": (720, 440)}
    cyc = [("a", "b", 2, GREY), ("b", "c", 4, GREY), ("c", "d", 5, GREY), ("d", "a", 9, RED)]
    for u, v, w, c in cyc:
        edge(f, C[u], C[v], w, False, c, 4 if c == RED else 2, c == RED, r=18)
    for k, p in C.items():
        node(f, p, k, "white", 18, 16)
    f.text(534, 238, "环 a-b-c-d 中最大边是 d-a(9),", 14, RED, "700")
    f.text(534, 260, "剩下三条已经把四个点连通,丢掉它不吃亏。", 14, RED, "700")
    return f.save()


def kruskal_steps():
    f = Fig("c5-03-kruskal-steps", "Kruskal:边按权从小到大,不成环就选", "用并查集判断一条边的两端是否已经连通。", 600,
            "选够 n-1 = 4 条边即可停止,总权 1+2+4+5 = 12。")
    chosen = {(1, 3), (3, 5), (2, 4), (3, 4)}
    for u, v, w in MG_E:
        if (u, v) in chosen:
            edge(f, MG[u], MG[v], w, False, GREEN, 4)
        elif (u, v) == (1, 5):
            edge(f, MG[u], MG[v], w, False, RED, 2, True)
        else:
            edge(f, MG[u], MG[v], w, False, GREY, 2, True)
    for k, p in MG.items():
        node(f, p, k)
    f.text(32, 118, "绿色:选中  红色虚线:成环被拒  灰色虚线:没有检查", 14, SUB)
    x0, y0 = 540, 125
    cols = [("边", 70), ("权", 46), ("操作", 100), ("连通块", 212)]
    x = x0
    for name, w in cols:
        cell(f, x, y0, w, 36, name, HEAD, True, False, 14)
        x += w
    rows = [("1-3", "1", "选", "{1,3} {2} {4} {5}", HL), ("3-5", "2", "选", "{1,3,5} {2} {4}", HL),
            ("1-5", "3", "成环,跳过", "不变", "#fdecec"), ("2-4", "4", "选", "{1,3,5} {2,4}", HL),
            ("3-4", "5", "选", "{1,2,3,4,5}", HL), ("2-3…", "6…", "已选够,停止", "", "#eef1f6")]
    for i, r in enumerate(rows):
        x = x0
        for j, (name, w) in enumerate(cols):
            cell(f, x, y0 + 36 + i * 40, w, 40, r[j], r[4] if j == 2 else "#ffffff", j == 2, j == 0 or j == 1, 14 if j == 3 else 15)
            x += w
    f.text(x0, y0 + 36 + 6 * 40 + 30, "判断成环:find(u) == find(v)", 15, mono=True)
    f.text(x0, y0 + 36 + 6 * 40 + 58, "选边后合并:fa[find(u)] = find(v)", 15, mono=True)
    return f.save()


def prim_steps():
    f = Fig("c5-03-prim-steps", "Prim:从一个点出发,每次拉进最近的点", "树外的点记录\"连到树的最便宜的边\",每轮取最小的那个。", 600,
            "与 Kruskal 得到同一棵树(总权 12),但选边顺序不同。")
    order = {(1, 3): 1, (3, 5): 2, (3, 4): 3, (2, 4): 4}
    for u, v, w in MG_E:
        if (u, v) in order:
            edge(f, MG[u], MG[v], w, False, GREEN, 4)
        else:
            edge(f, MG[u], MG[v], w, False, GREY, 2, True)
    for k, p in MG.items():
        node(f, p, k, "green" if k == 1 else "white")
    # 选边序号
    for (u, v), n in order.items():
        mx = (MG[u][0] + MG[v][0]) / 2
        my = (MG[u][1] + MG[v][1]) / 2
        f.parts.append(f'<circle cx="{mx + 16:.0f}" cy="{my + 22:.0f}" r="11" fill="{GREEN}"/>')
        f.text(round(mx + 16), round(my + 27), str(n), 14, "#ffffff", "700", "middle")
    f.text(32, 118, "绿色圆点:第几轮选中的边;起点为 1", 14, SUB)
    x0, y0 = 540, 125
    cols = [("轮", 40), ("加入", 56), ("选边", 70), ("树外各点的 key(2,3,4,5)", 262)]
    x = x0
    for name, w in cols:
        cell(f, x, y0, w, 36, name, HEAD, True, False, 13)
        x += w
    rows = [("0", "1", "—", "key: ∞  1  ∞  3  → 2:7 3:1 5:3"),
            ("1", "3", "1-3 (1)", "2:6  4:5  5:2"),
            ("2", "5", "3-5 (2)", "2:6  4:5"),
            ("3", "4", "3-4 (5)", "2:4"),
            ("4", "2", "2-4 (4)", "(树已完成)")]
    rows[0] = ("0", "1", "—", "2:7  3:1  5:3")
    for i, r in enumerate(rows):
        x = x0
        for j, (name, w) in enumerate(cols):
            cell(f, x, y0 + 36 + i * 44, w, 44, r[j], HL if j == 2 and i else "#ffffff", j == 1, j != 3 or True, 14)
            x += w
    f.text(x0, y0 + 36 + 5 * 44 + 30, "key[v] = v 连到树内点的最小边权", 15)
    f.text(x0, y0 + 36 + 5 * 44 + 56, "加入新点后,用它的边刷新树外点的 key", 15)
    return f.save()


# ---------------------------------------------------------------- 5.4
def bfs_color():
    f = Fig("c5-04-bfs-color", "BFS 染色:同一层的点颜色相同", "相邻的点染成不同颜色;若发现相邻点颜色相同,就不是二分图。", 560,
            "二分图的两部分,恰好是 BFS 层号的奇数层与偶数层(每个连通分量内)。")
    L = {1: (90, 300), 2: (290, 190), 4: (290, 410), 3: (520, 190), 5: (520, 410), 6: (740, 410)}
    E = [(1, 2), (1, 4), (2, 3), (4, 3), (4, 5), (5, 6)]
    col = {1: "blue", 2: "orange", 4: "orange", 3: "blue", 5: "blue", 6: "orange"}
    for i, x in enumerate((90, 290, 520, 740)):
        f.text(x, 120 + (0 if i < 3 else 0), f"第 {i} 层", 16, SUB, "700", "middle")
    for u, v in E:
        edge(f, L[u], L[v], None, False, GREY)
    for k, p in L.items():
        node(f, p, k, col[k])
    f.rect(32, 450, 936, 50, "grey")
    f.text(48, 482, "蓝色 = 颜色 0,橙色 = 颜色 1。染色规则:color[v] = color[u] ^ 1;遇到已染色的邻居,检查颜色是否不同。", 15, maxw=900)
    f.text(800, 270, "结果:{1,3,5} 与 {2,4,6}", 15, GREEN, "700", "middle", maxw=190)
    f.text(800, 296, "两部分之间才有边", 15, GREEN, "700", "middle", maxw=190)
    return f.save()


def odd_cycle():
    f = Fig("c5-04-odd-cycle", "奇环:二染色一定失败", "沿着环交替染色,绕回起点时,奇数长度的环会让起点颜色冲突。", 560,
            "二分图 ⇔ 图中没有奇数长度的环。")
    # 4 环
    f.rect(32, 105, 450, 330, "green")
    f.text(48, 137, "偶环(4 个点):可以", 19, GREEN, "700")
    C4 = {1: (140, 230), 2: (300, 230), 3: (300, 370), 4: (140, 370)}
    for u, v in ((1, 2), (2, 3), (3, 4), (4, 1)):
        edge(f, C4[u], C4[v], None, False, GREY, 2)
    for k, c in zip(C4, ("blue", "orange", "blue", "orange")):
        node(f, C4[k], k, c)
    f.text(48, 415, "颜色依次 0,1,0,1,回到起点正好对上。", 15)
    # 3 环
    f.rect(518, 105, 450, 330, "red")
    f.text(534, 137, "奇环(3 个点):冲突", 19, RED, "700")
    C3 = {1: (640, 360), 2: (820, 360), 3: (730, 200)}
    edge(f, C3[1], C3[2], None, False, RED, 4, True)
    edge(f, C3[1], C3[3], None, False, GREY, 2)
    edge(f, C3[2], C3[3], None, False, GREY, 2)
    node(f, C3[1], 1, "blue")
    node(f, C3[3], 3, "orange")
    node(f, C3[2], 2, "blue")
    f.text(730, 410, "1 与 2 都被染成颜色 0,但它们相邻", 14, RED, "700", "middle", maxw=400)
    f.rect(32, 450, 936, 50, "grey")
    f.text(48, 482, "冲突边出现在 BFS 同一层的两个点之间(或 DFS 的返回边上),它们和公共祖先构成一个奇环。", 15, maxw=900)
    return f.save()


# ---------------------------------------------------------------- 5.5
SG = {1: (70, 300), 2: (210, 170), 3: (210, 430), 4: (370, 300), 5: (490, 300)}
SG_E = [(1, 2, 5), (1, 3, 2), (3, 2, -1), (2, 4, 3), (3, 4, 6), (4, 5, 1)]


def spfa_queue():
    f = Fig("c5-05-spfa-queue", "SPFA 的队列变化", "只有距离刚变小的点才需要重新入队;一个点可能多次进出队列。", 640,
            "点 2、4、5 各入队两次:第一次拿到的不是最终距离,后来被更短的路改写。")
    for u, v, w in SG_E:
        edge(f, SG[u], SG[v], w, True, ORANGE if w < 0 else GREY, 3 if w < 0 else 2, lpos=0.5)
    for k, p in SG.items():
        node(f, p, k)
    f.text(32, 118, "有向图,起点 1,含一条负边 3→2", 17, SUB, "700")
    x0, y0 = 530, 125
    cw = [66, 108] + [48] * 5
    heads = ["取出", "队列(之后)", "d1", "d2", "d3", "d4", "d5"]
    x = x0
    for w, h in zip(cw, heads):
        cell(f, x, y0, w, 34, h, HEAD, True, False, 13)
        x += w
    rows = [("—", "[1]", ["0", "∞", "∞", "∞", "∞"], set()),
            ("1", "[2, 3]", ["0", "5", "2", "∞", "∞"], {1, 2}),
            ("2", "[3, 4]", ["0", "5", "2", "8", "∞"], {3}),
            ("3", "[4, 2]", ["0", "1", "2", "8", "∞"], {1}),
            ("4", "[2, 5]", ["0", "1", "2", "8", "9"], {4}),
            ("2", "[5, 4]", ["0", "1", "2", "4", "9"], {3}),
            ("5", "[4]", ["0", "1", "2", "4", "9"], set()),
            ("4", "[5]", ["0", "1", "2", "4", "5"], {4}),
            ("5", "[ ]", ["0", "1", "2", "4", "5"], set())]
    for i, (a, b, vals, ch) in enumerate(rows):
        y = y0 + 34 + i * 38
        cell(f, x0, y, cw[0], 38, a, "#ffffff", True)
        cell(f, x0 + cw[0], y, cw[1], 38, b, "#ffffff", False, True, 14)
        for j, v in enumerate(vals):
            cell(f, x0 + cw[0] + cw[1] + j * 48, y, 48, 38, v, HL if j in ch else "#ffffff", j in ch)
    f.text(x0, y0 + 34 + 9 * 38 + 28, "最终:0 1 2 4 5", 16, GREEN, "700")
    f.text(x0, y0 + 34 + 9 * 38 + 54, "绿色格:本步被更新", 14, SUB)
    return f.save()


def neg_cycle():
    f = Fig("c5-05-neg-cycle", "用路径边数检测负环", "len[v] 记录当前最短路径含多少条边;最短路径最多 n-1 条边,超出就说明在绕圈。", 560,
            "这里 n = 4。第二次更新点 2 时,len[2] = 4 ≥ n,报告负环。")
    P = {1: (80, 270), 2: (260, 170), 3: (460, 170), 4: (360, 380)}
    edge(f, P[1], P[2], 1, True, GREY)
    edge(f, P[2], P[3], -1, True, RED, 3)
    edge(f, P[3], P[4], -1, True, RED, 3)
    edge(f, P[4], P[2], 1, True, RED, 3)
    for k, p in P.items():
        node(f, p, k)
    f.text(32, 118, "环 2→3→4→2 的权和 = -1 + -1 + 1 = -1", 17, RED, "700")
    x0, y0 = 560, 140
    cw = [90, 120, 110, 88]
    for x, (w, h) in zip((x0, x0 + 90, x0 + 210, x0 + 320), zip(cw, ["绕圈次数", "dist[2]", "len[2]", "判断"])):
        cell(f, x, y0, w, 34, h, HEAD, True, False, 14)
    data = [("第 0 圈", "1", "1", "继续"), ("第 1 圈", "0", "4", "4 ≥ 4,停止")]
    for i, r in enumerate(data):
        for x, w, v in zip((x0, x0 + 90, x0 + 210, x0 + 320), cw, r):
            cell(f, x, y0 + 34 + i * 40, w, 40, v, "#fdecec" if i == 1 else "#ffffff", i == 1, False, 14)
    f.text(560, 290, "每绕一圈:dist 减 1,len 加 3。", 16)
    f.text(560, 318, "没有负环时,最短路径是简单路径,", 16)
    f.text(560, 344, "len 不会达到 n。", 16)
    f.rect(32, 430, 936, 60, "orange")
    f.text(48, 467, "也可以统计每个点的入队次数,超过 n 次判负环;边数法更早发现。", 16)
    return f.save()


# ---------------------------------------------------------------- 5.6
def diff_graph():
    f = Fig("c5-06-diff-graph", "差分约束:不等式 ⇒ 边,解不等式组 ⇒ 最短路", "x_j - x_i ≤ c 等价于 x_j ≤ x_i + c,正是松弛的形式。", 640,
            "超源点 0 向每个点连权 0 的边,保证所有点都能被到达。")
    f.rect(32, 105, 450, 260, "blue")
    f.text(48, 137, "不等式组", 19, BLUE, "700")
    for i, s in enumerate(["x2 - x1 ≤ 3   →  边 1→2,权 3", "x3 - x2 ≤ -2  →  边 2→3,权 -2",
                           "x3 - x1 ≤ 4   →  边 1→3,权 4", "x1 - x3 ≤ 0   →  边 3→1,权 0"]):
        f.text(48, 178 + i * 34, s, 15, mono=True, maxw=420)
    f.text(48, 330, "规则:x_j - x_i ≤ c  ⇒  边 i→j,权 c", 16, BLUE, "700")
    P = {0: (570, 300), 1: (700, 190), 2: (860, 190), 3: (780, 400)}
    for j in (1, 2, 3):
        edge(f, P[0], P[j], 0, True, PURPLE, 1.5, True, lsize=13, lpos=0.5)
    edge(f, P[1], P[2], 3, True, GREY)
    edge(f, P[2], P[3], -2, True, GREY)
    edge(f, P[1], P[3], 4, True, GREY, bend=16)
    edge(f, P[3], P[1], 0, True, GREY, bend=16)
    for k, p in P.items():
        node(f, p, k, "purple" if k == 0 else "white")
    f.text(520, 118, "约束图(紫色虚线:超源点)", 16, SUB, "700")
    f.rect(32, 385, 450, 185, "green")
    f.text(48, 417, "从 0 出发的最短路", 19, GREEN, "700")
    f.text(48, 450, "dist[1] = -2   (路径 0→2→3→1)", 15)
    f.text(48, 478, "dist[2] = 0,   dist[3] = -2", 15)
    f.text(48, 510, "取 x = (-2, 0, -2),逐条检查:", 15, GREEN, "700")
    f.text(48, 538, "2 ≤ 3,  -2 ≤ -2,  0 ≤ 4,  0 ≤ 0  全部成立", 15)
    return f.save()


def diff_cycle():
    f = Fig("c5-06-diff-nosol", "负环 ⇒ 无解", "环上的不等式相加,得到 0 ≤ 负数。", 480,
            "判断有没有解,就是判断约束图里有没有负环。")
    f.rect(32, 105, 450, 330, "red")
    f.text(48, 137, "一个无解的例子", 19, RED, "700")
    f.text(48, 172, "x2 - x1 ≤ -1", 17, mono=True)
    f.text(48, 202, "x1 - x2 ≤  0", 17, mono=True)
    f.text(48, 245, "两式相加:0 ≤ -1,矛盾。", 17, RED, "700")
    A, B = (140, 350), (380, 350)
    edge(f, (140, 336), (380, 336), -1, True, RED, 2, r=17, lshift=(0, -16))
    edge(f, (380, 364), (140, 364), 0, True, RED, 2, r=17, lshift=(0, 16))
    node(f, A, 1)
    node(f, B, 2)
    f.text(260, 420, "环权 = -1 + 0 = -1 < 0", 15, RED, "700", "middle")
    f.rect(518, 105, 450, 330, "blue")
    f.text(534, 137, "为什么 ≤ 对应最短路", 19, BLUE, "700")
    for i, s in enumerate(["最短路满足 dist[j] ≤ dist[i] + c,", "和约束 x_j ≤ x_i + c 完全一致,",
                           "所以 dist 本身就是一组解。", "", "若约束是 x_j - x_i ≥ c,", "改成边 i→j 权 c 求最长路,",
                           "此时图中出现正环 ⇒ 无解。"]):
        f.text(534, 175 + i * 30, s, 16)
    return f.save()


def build_all():
    w = []
    for fn in (adj_storage, topo_steps, dag_dp, relax, dijkstra_steps, floyd_idea, cut_property,
               kruskal_steps, prim_steps, bfs_color, odd_cycle, spfa_queue, neg_cycle, diff_graph, diff_cycle):
        w += fn()
    return w


if __name__ == "__main__":
    for x in build_all():
        print(x)
