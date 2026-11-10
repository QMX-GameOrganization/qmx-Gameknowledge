"""5.7 强连通分量与割点、桥 的配图。"""
from svglib import Fig, PALETTE, INK, SUB
from s5b_helpers import node, link, lines, tag, bounding

RED = PALETTE["red"][1]


def tarjan_trace():
    f = Fig("c5-07-tarjan-trace", "Tarjan 在一张小图上的执行过程", "圆旁的标签是 dfn/low，红色虚线是回到栈内的边。", 560,
            "先弹出的分量编号小：SCC 1 = {4,5,6}，SCC 2 = {1,2,3}。")
    f.rect(32, 105, 570, 400, "blue")
    P = {1: (100, 250), 2: (210, 170), 3: (210, 340), 4: (380, 340), 5: (470, 260), 6: (470, 430)}
    bounding(f, 52, 125, 220, 285, "green", "SCC 2")
    bounding(f, 335, 200, 250, 285, "orange", "SCC 1")
    for a, b in [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6)]:
        link(f, P[a], P[b])
    link(f, P[3], P[1], color=RED, dash=True, curve=-28)
    link(f, P[6], P[4], color=RED, dash=True, curve=-28)
    for k, (x, y) in P.items():
        node(f, x, y, k, "white")
    for k, s, dx, dy in [(1, "1/1", 0, -45), (2, "2/1", -52, -6), (3, "3/1", 0, 42), (4, "4/4", -15, -42),
                         (5, "5/4", 62, 0), (6, "6/4", 62, 0)]:
        tag(f, P[k][0] + dx, P[k][1] + dy, s, "grey")
    f.rect(620, 105, 348, 400, "grey")
    f.text(636, 137, "执行过程", 19, PALETTE["grey"][1], "700")
    lines(f, 636, 172, [
        "① 1→2→3：dfn 依次为 1、2、3",
        "② 3→1：1 在栈内，",
        "    low[3] = dfn[1] = 1",
        "③ 3→4→5→6：dfn 为 4、5、6",
        "④ 6→4：4 在栈内，",
        "    low[6] = dfn[4] = 4",
        "⑤ 回溯到 5、4：low 都是 4",
        "⑥ 4：dfn = low，弹栈 6、5、4，",
        "    得到 SCC 1",
        "⑦ 回溯到 3、2：low 都是 1",
        "⑧ 1：dfn = low，弹栈 3、2、1，",
        "    得到 SCC 2",
    ], 14, gap=26, maxw=316)
    return f.save()


def condense():
    f = Fig("c5-07-condense", "缩点：每个强连通分量缩成一个点，结果是 DAG", "点权累加，再按分量编号从小到大做 DP。", 520,
            "边 u→v 跨分量时 comp[u] > comp[v]，所以编号从小到大就是从汇到源。")
    bounding(f, 40, 110, 200, 150, "green", "SCC 2")
    bounding(f, 40, 290, 200, 150, "orange", "SCC 1")
    A = {1: (80, 205), 2: (140, 155), 3: (200, 205)}
    B = {4: (140, 335), 5: (200, 385), 6: (80, 385)}
    for pts in (A, B):
        ks = list(pts)
        for i in range(3):
            link(f, pts[ks[i]], pts[ks[(i + 1) % 3]], r=17)
    for k, (x, y) in {**A, **B}.items():
        node(f, x, y, k, "white", r=17, size=15)
    link(f, A[3], B[4], r=17, color=PALETTE["grey"][1])
    f.arrow(280, 275, 470, 275, PALETTE["grey"][1])
    f.text(375, 262, "缩点", 17, SUB, anchor="middle")
    f.chip(700, 180, 220, 76, "green", "SCC 2\n权值 3+2+1 = 6", 17, bold=True)
    f.chip(700, 370, 220, 76, "orange", "SCC 1\n权值 4+5+6 = 15", 17, bold=True)
    f.arrow(700, 220, 700, 330, PALETTE["grey"][1])
    f.text(716, 282, "只有这一条边", 15, SUB)
    f.text(700, 462, "dp[1] = 15，dp[2] = 6 + dp[1] = 21", 18, INK, "700", "middle")
    return f.save()


def bridge_cut():
    f = Fig("c5-07-bridge-cut", "桥和割点：用 low 判断子树能不能绕回去", "圆旁标签是 dfn/low；红边是桥，橙色点是割点。", 560,
            "无向图的 DFS 只有树边和回边，没有横叉边。")
    P = {1: (100, 300), 2: (200, 200), 3: (300, 300), 4: (480, 300), 5: (580, 200), 6: (680, 300)}
    for a, b in [(1, 2), (2, 3), (1, 3), (4, 5), (5, 6), (4, 6)]:
        link(f, P[a], P[b], arrow=False)
    link(f, P[3], P[4], arrow=False, color=RED, width=5)
    f.text(390, 285, "桥", 17, RED, "700", "middle")
    for k, (x, y) in P.items():
        node(f, x, y, k, "orange" if k in (3, 4) else "white")
    for k, s, dy in [(1, "1/1", 45), (2, "2/1", -45), (3, "3/1", 45), (4, "4/4", 45), (5, "5/4", -45), (6, "6/4", 45)]:
        tag(f, P[k][0], P[k][1] + dy, s, "grey")
    f.rect(32, 385, 936, 115, "grey")
    lines(f, 48, 417, [
        "桥 3-4：low[4] = 4 > dfn[3] = 3，4 的子树出不去，删掉这条边图就断开。",
        "割点 3：孩子 4 满足 low[4] ≥ dfn[3]。割点 4：孩子 5 满足 low[5] ≥ dfn[4]。",
        "点 2 不是割点：孩子 3 的 low[3] = 1 < dfn[2] = 2，能绕回 1。",
    ], 16, gap=30, maxw=900)
    return f.save()


def build_all():
    return tarjan_trace() + condense() + bridge_cut()
