"""第 6 章后半（6.8 到 6.12，进阶篇）的配图。"""
from svglib import Fig, GREY, SUB, INK, PALETTE

BL, GR, OR, RD, PU, GY, WH = (PALETTE[k][1] for k in ("blue", "green", "orange", "red", "purple", "grey", "white"))


def circle(f, cx, cy, r, fill, stroke, sw=2):
    f.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def line(f, x1, y1, x2, y2, color=GREY, w=2, dash=False):
    d = ' stroke-dasharray="6 5"' if dash else ""
    f.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}"{d}/>')


def poly(f, pts, color=GREY, w=2, dash=False):
    d = ' stroke-dasharray="6 5"' if dash else ""
    s = " ".join(f"{x},{y}" for x, y in pts)
    f.parts.append(f'<polyline points="{s}" fill="none" stroke="{color}" stroke-width="{w}"{d}/>')


# ---------------------------------------------------------------- 6.8
def c6_08_matrix_fib():
    f = Fig("c6-08-matrix-fib", "斐波那契的转移矩阵与快速幂", "一步转移写成矩阵乘法，n 步转移就是矩阵的 n 次幂。", 570,
            "13 的二进制是 1101，所以只需要 3 次平方、2 次相乘，而不是 12 次乘法。")
    f.rect(32, 105, 936, 170, "blue")
    f.text(48, 137, "一步转移：从 (F(i), F(i-1)) 得到 (F(i+1), F(i))", 19, BL, "700")
    f.chip(170, 207, 120, 80, "white", "F(i+1)\nF(i)", 20, mono=True)
    f.text(255, 214, "=", 28, INK, "700", "middle")
    f.chip(370, 207, 120, 80, "orange", "1   1\n1   0", 22, mono=True, bold=True)
    f.text(470, 214, "×", 28, INK, "700", "middle")
    f.chip(570, 207, 120, 80, "white", "F(i)\nF(i-1)", 20, mono=True)
    f.text(660, 190, "第一行：F(i+1) = 1·F(i) + 1·F(i-1)", 16)
    f.text(660, 220, "第二行：F(i)   = 1·F(i) + 0·F(i-1)", 16)
    f.text(660, 250, "橙色的 M 不随 i 变化", 16, OR, "700")

    f.rect(32, 300, 936, 210, "green")
    f.text(48, 332, "快速幂：反复平方，按二进制位取用（以 M^13 为例）", 19, GR, "700")
    xs = [140, 340, 540, 740]
    names = ["M^1", "M^2", "M^4", "M^8"]
    bits = ["第 0 位 = 1，取", "第 1 位 = 0，不取", "第 2 位 = 1，取", "第 3 位 = 1，取"]
    used = [True, False, True, True]
    for i, x in enumerate(xs):
        f.chip(x, 392, 120, 56, "orange" if used[i] else "white", names[i], 22, bold=used[i])
        f.text(x, 444, bits[i], 15, INK if used[i] else GREY, anchor="middle")
        if i < 3:
            f.arrow(x + 62, 392, xs[i + 1] - 62, 392, GR)
            f.text((x + xs[i + 1]) / 2, 378, "平方", 15, GR, anchor="middle")
    f.text(500, 486, "M^13 = M^8 · M^4 · M^1", 19, OR, "700", "middle")
    return f.save()


def c6_08_matrix_states():
    f = Fig("c6-08-matrix-states", "状态转移图与矩阵一一对应", "例：长度为 n、不含连续两个 1 的 01 串有多少个。", 530,
            "矩阵第 i 行第 j 列 = 从状态 j 走一步到状态 i 的方式数。")
    f.rect(32, 105, 450, 360, "blue")
    f.text(48, 137, "状态图", 19, BL, "700")
    circle(f, 140, 290, 52, "#ffffff", BL)
    circle(f, 360, 290, 52, "#ffffff", BL)
    f.text(140, 282, "A", 24, BL, "700", "middle")
    f.text(140, 308, "末位是 0", 14, SUB, anchor="middle")
    f.text(360, 282, "B", 24, BL, "700", "middle")
    f.text(360, 308, "末位是 1", 14, SUB, anchor="middle")
    f.path("M120 240 C90 170 190 170 160 240", BL)
    f.text(140, 178, "追加 0", 15, BL, anchor="middle")
    f.path("M192 268 C245 235 255 235 308 268", BL)
    f.text(250, 232, "追加 1", 15, BL, anchor="middle")
    f.path("M312 316 C255 350 245 350 192 316", BL)
    f.text(250, 372, "追加 0", 15, BL, anchor="middle")
    f.text(48, 430, "B 后面不能再追加 1，所以没有 B→B。", 16)

    f.rect(518, 105, 450, 360, "green")
    f.text(534, 137, "转移矩阵", 19, GR, "700")
    f.chip(660, 220, 130, 80, "white", "a'\nb'", 22, mono=True)
    f.text(740, 228, "=", 28, INK, "700", "middle")
    f.chip(830, 220, 120, 80, "orange", "1  1\n1  0", 22, mono=True, bold=True)
    f.text(534, 290, "a'、b' 是追加一个字符后以 0、1 结尾的串数。", 16)
    f.text(534, 320, "a' = a + b（A、B 后面都能追加 0）", 16, mono=False)
    f.text(534, 348, "b' = a（只有 A 后面能追加 1）", 16)
    f.text(534, 392, "初始 (a, b) = (1, 1)（长度 1），M^(n-1) 乘上去，", 16, GR, "700")
    f.text(534, 420, "a + b 就是长度为 n 的合法串数，结果是斐波那契数。", 16, GR, "700")
    return f.save()


# ---------------------------------------------------------------- 6.9
def c6_09_window():
    f = Fig("c6-09-window", "单调队列维护滑动窗口最大值", "dp[i] = a[i] + max(dp[i-k..i-1])，k = 3，现在计算 dp[6]。", 590,
            "队列里存下标，对应 dp 值从队首到队尾严格递减，队首永远是窗口最大值。")
    vals = [5, 3, 6, 2, 4, 1]
    x0, w = 90, 100
    f.text(48, 125, "dp 数组（下标 0 到 5 已算好，窗口是 [3, 5]）", 17, SUB)
    for i, v in enumerate(vals):
        in_win = 3 <= i <= 5
        f.chip(x0 + i * w + w / 2 - 10, 170, 80, 50, "green" if in_win else "white", f"dp[{i}]={v}", 16, bold=in_win)
    f.chip(x0 + 6 * w + w / 2 - 10, 170, 80, 50, "orange", "dp[6]=?", 16, bold=True)
    line(f, x0 + 3 * w + 10, 212, x0 + 6 * w - 10, 212, GR, 3)
    f.text(x0 + 4.5 * w - 10, 236, "窗口 [3, 5]", 15, GR, "700", "middle")

    steps = [
        ("处理前的队列", "(下标:dp)", [("2", "6"), ("4", "4"), ("5", "1")], "red", None),
        ("① 弹队首", "下标 2 < 6-3，已滑出窗口", [("4", "4"), ("5", "1")], "green", None),
        ("② 取队首", "dp[6] = a[6] + 4 = 6（设 a[6]=2）", [("4", "4"), ("5", "1")], "green", 0),
        ("③ 6 入队前先弹队尾", "1 ≤ 6、4 ≤ 6 都弹掉，再放入 6", [("6", "6")], "blue", None),
    ]
    y = 290
    for title, note, items, kind, hl in steps:
        f.text(48, y + 6, title, 17, PALETTE[kind][1], "700")
        f.text(48, y + 32, note, 14, SUB)
        for i, (idx, dv) in enumerate(items):
            f.chip(520 + i * 120, y + 12, 100, 44, "orange" if hl == i else "white", f"{idx}:{dv}", 17, mono=True, bold=hl == i)
            if i:
                f.arrow(520 + (i - 1) * 120 + 50, y + 12, 520 + i * 120 - 52, y + 12, GREY)
        y += 62
    f.text(520, 272, "队首", 14, GREY, anchor="middle")
    f.text(880, 272, "队尾方向 →", 14, GREY, anchor="end")
    return f.save()


def c6_09_residue():
    f = Fig("c6-09-residue", "多重背包：按余数分组，每组一个滑动窗口", "体积 w = 3，数量 c = 2：dp[j] 只和 j、j-3、j-6 这三个同余位置有关。", 470,
            "组内下标 u，g[u] = dp[r+u·w] - u·v；新 dp = u·v + max(g[u-c..u])。")
    f.text(48, 128, "按 j mod 3 分成 3 组（每行一组）：", 17, SUB)
    for r in range(3):
        y = 175 + r * 75
        f.text(80, y + 6, f"r = {r}", 17, PALETTE[["blue", "green", "orange"][r]][1], "700")
        for u in range(4):
            j = r + 3 * u
            hl = r == 1 and 1 <= u <= 3
            cur = r == 1 and u == 3
            kind = "orange" if cur else ("green" if hl else "white")
            f.chip(230 + u * 130, y, 100, 50, kind, f"dp[{j}]", 17, mono=True, bold=hl)
            f.text(230 + u * 130, y + 40, f"u = {u}", 13, GREY, anchor="middle")
    f.rect(298, 220, 384, 60, "green", dash=True, fill="none")
    f.text(760, 232, "当前 j = 10（u = 3）", 16, OR, "700")
    f.text(760, 258, "窗口 u ∈ [1, 3]", 16, GR, "700")
    f.text(760, 284, "即 dp[4]、dp[7]、dp[10]", 16)
    f.text(760, 310, "最多取 2 个物品", 16)
    return f.save()


# ---------------------------------------------------------------- 6.10
def _plot(f, x0, y0, sx, sy):
    return lambda X, Y: (x0 + X * sx, y0 - Y * sy)


def c6_10_hull():
    f = Fig("c6-10-hull", "把转移变成「找最低的切线」", "点 (X_j, Y_j) 是候选决策，斜率为 S[i] 的直线向上平移，第一个碰到的点最优。", 560,
            "只有下凸壳上的点可能成为最优决策，其余点可以直接丢掉。")
    p = _plot(f, 90, 480, 85, 32)
    line(f, 70, 480, 640, 480, GREY, 2)
    line(f, 90, 500, 90, 130, GREY, 2)
    f.text(640, 505, "X_j = 2·S[j]", 15, SUB, anchor="end")
    f.text(104, 128, "Y_j = dp[j] + S[j]²", 15, SUB)
    hull = [(0, 10), (1, 6), (2, 3.5), (3.5, 2.5), (5, 3.2)]
    others = [(0.8, 8.2), (1.7, 6.3), (2.8, 5.0), (4.1, 4.6), (4.7, 6.0)]
    poly(f, [p(*h) for h in hull], BL, 3)
    for x, y in others:
        cx, cy = p(x, y)
        circle(f, cx, cy, 7, "#eef1f6", GREY)
    for k, (x, y) in enumerate(hull):
        cx, cy = p(x, y)
        circle(f, cx, cy, 8, "#eaf2ff" if k != 3 else "#fff2df", BL if k != 3 else OR, 3)
    # 切线：斜率 0.2，过 (3.5, 2.5)
    a, b = p(0.3, 2.5 + 0.2 * (0.3 - 3.5)), p(5.8, 2.5 + 0.2 * (5.8 - 3.5))
    line(f, a[0], a[1], b[0], b[1], OR, 2.5, True)
    cx, cy = p(3.5, 2.5)
    f.text(cx - 6, cy + 32, "最优决策 j*", 16, OR, "700", "middle")
    f.text(b[0], b[1] + 26, "斜率 S[i]", 15, OR, "700", "end")

    f.rect(660, 105, 308, 395, "blue")
    f.text(676, 138, "怎么用", 19, BL, "700")
    rows = ["凸壳上相邻线段的斜率", "从左到右依次变大。", "", "斜率 S[i] 递增时，", "最优点只会向右移，", "队首斜率 ≤ S[i] 的点", "可以永久弹出。", "", "新点 i 加入队尾前，", "先弹掉不在凸壳上的点。"]
    for i, s in enumerate(rows):
        f.text(676, 172 + i * 28, s, 16)
    return f.save()


def c6_10_pop():
    f = Fig("c6-10-pop", "维护凸壳的两个弹出规则", "队尾弹出用三点的斜率比较，队首弹出用查询斜率比较。", 625,
            "写成交叉相乘的形式，避免除法和浮点误差；乘积可能超过 long long，用 __int128。")
    f.rect(32, 105, 456, 250, "green")
    f.text(48, 135, "加入新点 c：b 在 a、c 连线下方 → 保留", 17, GR, "700")
    p1 = _plot(f, 90, 330, 100, 24)
    pts = [(0, 6), (1.5, 2), (3, 3.5)]
    poly(f, [p1(*q) for q in pts], GR, 3)
    for n, q in zip("abc", pts):
        cx, cy = p1(*q)
        circle(f, cx, cy, 8, "#e8f7f1", GR, 3)
        f.text(cx, cy - 16, n, 17, GR, "700", "middle")
    f.text(48, 340, "slope(a,b) < slope(b,c)：向下凸", 15, SUB)

    f.rect(512, 105, 456, 250, "red")
    f.text(528, 135, "b 在 a、c 连线上方或线上 → 弹出 b", 17, RD, "700")
    p2 = _plot(f, 570, 330, 100, 30)
    pts2 = [(0, 2.5), (1.5, 5), (3, 5.5)]
    poly(f, [p2(*q) for q in pts2], RD, 3)
    ca, cc = p2(*pts2[0]), p2(*pts2[2])
    line(f, ca[0], ca[1], cc[0], cc[1], GREY, 2, True)
    for n, q in zip("abc", pts2):
        cx, cy = p2(*q)
        circle(f, cx, cy, 8, "#fdecec", RD, 3)
        f.text(cx, cy - 16, n, 17, RD, "700", "middle")
    f.text(48, 372, "弹队尾的条件：(Yb-Ya)·(Xc-Xb) ≥ (Yc-Yb)·(Xb-Xa)，即 slope(a,b) ≥ slope(b,c)。", 16)

    f.rect(32, 400, 936, 170, "blue")
    f.text(48, 430, "弹队首：队首两点的斜率 ≤ 查询斜率 S[i]，说明队首以后不再最优（S 递增）", 17, BL, "700")
    xs = [130, 330, 530, 730]
    for i, x in enumerate(xs):
        f.chip(x, 500, 90, 44, "orange" if i == 2 else ("grey" if i < 2 else "white"), f"q{i}", 18, bold=i == 2)
    for i, s in enumerate(["斜率 1", "斜率 3", "斜率 5"]):
        f.arrow(xs[i] + 48, 500, xs[i + 1] - 48, 500, GREY)
        f.text((xs[i] + xs[i + 1]) / 2, 486, s, 15, SUB, anchor="middle")
    f.text(48, 556, "S[i] = 4：1 ≤ 4 弹 q0，3 ≤ 4 弹 q1，5 > 4 停止，q2 是最优决策。", 16)
    return f.save()


def c6_10_lichao():
    f = Fig("c6-10-lichao", "Li Chao 树：插入一条直线", "每个节点保存一条在区间中点处最优的直线，另一条最多只会在一侧更优。", 575,
            "插入、查询都是 O(log V)，直线可以任意顺序加入，查询 x 也可以任意顺序。")
    f.rect(32, 105, 480, 400, "blue")
    f.text(48, 135, "x ∈ [1, 8]，求最小值", 18, BL, "700")
    p = _plot(f, 60, 460, 50, 34)
    line(f, 50, 460, 490, 460, GREY, 2)
    A = [(1, 6.5), (8, 3)]       # 直线 A: y = 7 - 0.5x
    B = [(1, 2.4), (8, 5.2)]     # 直线 B: y = 2 + 0.4x
    poly(f, [p(*q) for q in A], RD, 3)
    poly(f, [p(*q) for q in B], GR, 3)
    f.text(p(1, 6.5)[0] + 6, p(1, 6.5)[1] - 12, "新直线 A", 16, RD, "700")
    f.text(p(8, 5.2)[0] - 4, p(8, 5.2)[1] - 12, "已有直线 B", 16, GR, "700", "end")
    mx = p(4, 0)[0]
    line(f, mx, 205, mx, 460, GREY, 1.5, True)
    f.text(mx, 480, "mid = 4", 15, SUB, anchor="middle")
    f.text(48, 160, "mid 处 B 更低，B 留在节点；", 15)
    f.text(48, 184, "A 只在右端更低，只需放进右子树。", 15)

    f.rect(540, 105, 428, 400, "green")
    f.text(556, 135, "线段树结构", 18, GR, "700")
    f.chip(754, 195, 150, 60, "orange", "[1, 8]\n存 B", 16, bold=True)
    f.chip(650, 340, 130, 56, "white", "[1, 4]\n空", 16)
    f.chip(860, 340, 130, 56, "red", "[5, 8]\n存 A", 16, bold=True)
    f.arrow(730, 228, 665, 310, GREY)
    f.arrow(780, 228, 845, 310, RD)
    f.text(556, 430, "递归规则：在 mid 处比较并交换，", 15)
    f.text(556, 456, "较差的那条直线只在左端更优就进左子树，", 15)
    f.text(556, 482, "只在右端更优就进右子树，都不优则丢弃。", 15)
    return f.save()


# ---------------------------------------------------------------- 6.11
def c6_11_knuth():
    f = Fig("c6-11-knuth", "Knuth 优化：决策点被左、下两格夹住", "f[l][r] 的最优分割点 opt[l][r] 满足 opt[l][r-1] ≤ opt[l][r] ≤ opt[l+1][r]。", 600,
            "固定区间长度后，所有区间的枚举范围首尾相接，总共只有 O(n) 次，整张表 O(n²)。")
    n = 6
    cw, x0, y0 = 60, 120, 150
    f.text(x0 + 3 * cw, 120, "右端点 r", 15, SUB, anchor="middle")
    f.text(48, y0 + 3 * cw, "左端点 l", 15, SUB)
    for r in range(1, n + 1):
        f.text(x0 + (r - 1) * cw + cw / 2, 150 - 4, str(r), 15, SUB, anchor="middle")
    for l in range(1, n + 1):
        f.text(x0 - 14, y0 + (l - 1) * cw + cw / 2 + 5, str(l), 15, SUB, anchor="end")
        for r in range(l, n + 1):
            kind = "white"
            label = f"{l},{r}"
            if (l, r) == (2, 5):
                kind = "orange"
            elif (l, r) == (2, 4):
                kind = "blue"
            elif (l, r) == (3, 5):
                kind = "green"
            f.chip(x0 + (r - 1) * cw + cw / 2, y0 + (l - 1) * cw + cw / 2, cw - 6, cw - 8, kind, label, 16, mono=True)
    f.text(x0, y0 + n * cw + 30, "格子里的 l,r 表示 opt[l][r]，只画 l ≤ r 的一半", 15, SUB)
    f.rect(600, 150, 368, 330, "orange")
    f.text(616, 182, "怎么读这张表", 19, OR, "700")
    for i, (s, c) in enumerate([("橙色：要计算的 opt[2][5]", OR), ("蓝色：左边一格 opt[2][4]，下界", BL), ("绿色：下边一格 opt[3][5]，上界", GR),
                               ("", INK), ("于是枚举 k 只需", INK), ("从 opt[2][4] 到 opt[3][5]。", INK), ("", INK), ("按区间长度从小到大算，", INK), ("左、下两格一定已经算好。", INK)]):
        f.text(616, 218 + i * 28, s, 16, c, "700" if c != INK else None)
    return f.save()


def c6_11_dc():
    f = Fig("c6-11-dc", "决策单调性的分治：取中点，一分为二", "solve(l, r, optl, optr)：求 dp[mid] 的最优决策 bk，左半边只看 [optl, bk]，右半边只看 [bk, optr]。", 560,
            "每一层所有节点的决策区间加起来只有 O(n) 个，一共 log n 层，一层 DP 总共 O(n log n)。")
    nodes = {
        (0, 0): (500, 178, "i ∈ [1, 8]\nk ∈ [0, 7]\nmid=4 → bk=2"),
        (1, 0): (270, 312, "i ∈ [1, 3]\nk ∈ [0, 2]\nmid=2 → bk=1"),
        (1, 1): (730, 312, "i ∈ [5, 8]\nk ∈ [2, 7]\nmid=6 → bk=4"),
        (2, 0): (140, 446, "i = 1\nk ∈ [0, 1]"),
        (2, 1): (370, 446, "i = 3\nk ∈ [1, 2]"),
        (2, 2): (610, 446, "i = 5\nk ∈ [2, 4]"),
        (2, 3): (850, 446, "i ∈ [7, 8]\nk ∈ [4, 7]"),
    }
    edges = [((0, 0), (1, 0)), ((0, 0), (1, 1)), ((1, 0), (2, 0)), ((1, 0), (2, 1)), ((1, 1), (2, 2)), ((1, 1), (2, 3))]
    for a, b in edges:
        xa, ya, _ = nodes[a]
        xb, yb, _ = nodes[b]
        f.arrow(xa, ya + 40, xb, yb - 42, GREY)
    kinds = {0: "orange", 1: "blue", 2: "green"}
    for (lv, _), (x, y, s) in nodes.items():
        f.chip(x, y, 200, 76, kinds[lv], s, 15, mono=True)
    f.text(48, 118, "上层的 bk 把 k 的范围一分为二；左右两半的范围只在 bk 处重叠。", 16, SUB)
    return f.save()


# ---------------------------------------------------------------- 6.12
def c6_12_lcs_bits():
    f = Fig("c6-12-lcs-bits", "把 LCS 的一整行压成一个二进制数", "S = ABCB，依次追加 T 的字符 B、C、B，f[j] = LCS(S 前 j 个字符, 当前 T)。", 545,
            "相邻 f 值只相差 0 或 1，所以差分序列是 m 位的 01 串；mask 里 1 的个数就是 LCS 长度。")
    S = "ABCB"
    rows = [("T = (空)", [0, 0, 0, 0, 0]), ("T = B", [0, 0, 1, 1, 1]), ("T = BC", [0, 0, 1, 2, 2]), ("T = BCB", [0, 0, 1, 2, 3])]
    x0 = 230
    f.text(48, 135, "S 的前 j 个字符", 15, SUB)
    for j in range(5):
        f.text(x0 + j * 90, 135, ("j=0" if j == 0 else f"j={j} {S[j-1]}"), 15, SUB, anchor="middle")
    f.text(x0 + 5 * 90 + 30, 135, "差分 mask", 15, OR, "700", anchor="middle")
    for r, (name, fv) in enumerate(rows):
        y = 190 + r * 66
        f.text(48, y + 6, name, 17, INK, "700")
        for j, v in enumerate(fv):
            f.chip(x0 + j * 90, y, 70, 46, "white", str(v), 20, mono=True)
        bits = "".join(str(fv[j] - fv[j - 1]) for j in range(1, 5))
        f.chip(x0 + 5 * 90 + 30, y, 130, 46, "orange", bits, 20, mono=True, bold=True)
    f.text(48, 480, "mask 的第 j-1 位 = f[j] - f[j-1]。BCB 之后 mask = 0111，三个 1，LCS = 3。", 16, OR, "700")
    return f.save()


def c6_12_plug_profile():
    f = Fig("c6-12-plug-profile", "插头 DP：轮廓线与括号表示", "逐格处理，轮廓线上记录「哪些位置有路径穿过边界」，用括号区分它们属于哪条路径的哪一端。", 600,
            "状态 = m+1 个位置，每个位置 3 种取值：0 无插头，1 左括号，2 右括号。")
    cs, gx, gy = 90, 60, 150
    for r in range(3):
        for c in range(4):
            done = r == 0 or (r == 1 and c < 2)
            cur = (r, c) == (1, 2)
            kind = "orange" if cur else ("blue" if done else "white")
            f.rect(gx + c * cs, gy + r * cs, cs, cs, kind, r=4, opacity=".5")
    f.text(gx + 2 * cs + cs / 2, gy + 1 * cs + cs / 2 + 6, "当前格", 16, OR, "700", "middle")
    f.text(gx + 1.0 * cs, gy - 10, "已处理（浅蓝）", 15, BL, "700", "middle")
    poly(f, [(gx, gy + 2 * cs), (gx + 2 * cs, gy + 2 * cs), (gx + 2 * cs, gy + cs), (gx + 4 * cs, gy + cs), (gx + 4 * cs, gy)], RD, 3, True)
    f.text(gx + 4 * cs + 14, gy + cs - 4, "轮廓线", 16, RD, "700")
    # 插头：下标 0..4
    px = [gx + 0.5 * cs, gx + 1.5 * cs, gx + 2 * cs, gx + 2.5 * cs, gx + 3.5 * cs]
    stubs = [("v", px[0], gy + 2 * cs, "(", 1), ("v", px[1], gy + 2 * cs, ")", 2), ("h", px[2], gy + 1.5 * cs, "·", 0),
             ("v", px[3], gy + cs, "(", 1), ("v", px[4], gy + cs, ")", 2)]
    for k, (t, x, y, s, code) in enumerate(stubs):
        if code:
            if t == "v":
                line(f, x, y - 14, x, y + 20, OR, 5)
            else:
                line(f, x - 20, y, x + 14, y, OR, 5)
    lab_y = gy + 3 * cs + 28
    for k in range(5):
        x = px[k] if k != 2 else gx + 2 * cs - 4
        f.text(x, lab_y, str(k), 15, SUB, anchor="middle")
        f.text(x, lab_y + 30, stubs[k][3], 24, OR if stubs[k][4] else GREY, "700", "middle", mono=True)
    f.text(60, lab_y + 62, "下标 0..4 对应的状态：1 2 0 1 2", 16, INK, "700")
    f.rect(500, 130, 468, 400, "green")
    f.text(516, 162, "读法", 19, GR, "700")
    lines = ["下标 0、1：已处理格子向下伸出的插头。", "下标 2（= j）：当前格左边来的插头。", "下标 3（= j+1）：当前格上边来的插头。",
             "下标 4：上一行向右侧列伸下来的插头。", "", "配对的括号是同一条路径的两个端点：", "(0,1) 是一对，(3,4) 是一对。", "", "换行时整体左移一个位置，",
             "最右边的插头必须是 0。"]
    for i, s in enumerate(lines):
        f.text(516, 200 + i * 29, s, 16)
    return f.save()


def c6_12_plug_cases():
    f = Fig("c6-12-plug-cases", "插头 DP：一个格子的六种转移", "a 是左插头，b 是上插头，括号序列里只有这两位和它们的配对对象会变化。", 725,
            "只有 a=1,b=2 会形成回路，且必须发生在最后一个空格，否则丢弃。")
    panels = [
        ("a=0, b=0", "新开路径", "· ·  →  ( )", "向下、向右各伸出一个插头", "blue"),
        ("a 或 b 为 c", "延伸", "c ·  →  · c  或  c ·", "继续向下或向右", "blue"),
        ("a=1, b=1", "两个左括号相接", "( ( … ) )  →  · · ( … )", "b 的配对右括号改成左括号", "green"),
        ("a=2, b=2", "两个右括号相接", "( ( ) )  →  ( ) · ·", "a 的配对左括号改成右括号", "green"),
        ("a=2, b=1", "不同路径相接", "( ) ( )  →  ( · · )", "两端自动配成一对，其余不变", "orange"),
        ("a=1, b=2", "同一路径首尾相接", "( )  →  闭合成回路", "只允许在最后一个空格", "red"),
    ]
    for i, (cond, title, seq, note, kind) in enumerate(panels):
        col, row = i % 2, i // 2
        x, y = 32 + col * 476, 105 + row * 190
        f.rect(x, y, 460, 172, kind)
        ink = PALETTE[kind][1]
        f.text(x + 16, y + 32, cond, 19, ink, "700", mono=False)
        f.text(x + 160, y + 32, title, 17, INK)
        f.chip(x + 80, y + 112, 60, 60, "white", "格", 17)
        if "a=0" not in cond:
            line(f, x + 30, y + 112, x + 50, y + 112, ink, 5)        # 左插头
        if "b=0" not in cond:
            line(f, x + 80, y + 66, x + 80, y + 82, ink, 5)           # 上插头
        f.text(x + 150, y + 104, seq, 16, INK, mono=True, maxw=300)
        f.text(x + 150, y + 138, note, 15, SUB, maxw=300)
    return f.save()


def build_all():
    w = []
    for fn in (c6_08_matrix_fib, c6_08_matrix_states, c6_09_window, c6_09_residue, c6_10_hull, c6_10_pop,
               c6_10_lichao, c6_11_knuth, c6_11_dc, c6_12_lcs_bits, c6_12_plug_profile, c6_12_plug_cases):
        w += fn()
    return w
