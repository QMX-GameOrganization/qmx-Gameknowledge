"""4.8 树形 DP 入门 的配图。"""
from s4a_common import *


def c408_order():
    f = Fig("c4-08-dp-order", "树形 DP：先算孩子，再算父亲", "没有上司的舞会：f1[u] 表示 u 去，f0[u] 表示 u 不去，子树内的最大快乐值。", 600,
            "孩子的状态都算好后才能算父亲，所以按后序（回溯时）计算。")
    pos = {1: (500, 150), 2: (300, 260), 3: (700, 260), 4: (200, 370), 5: (400, 370), 6: (700, 370)}
    tree(f, pos, [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6)])
    info = {1: ("r=5", "f1=14 f0=12", 1), 2: ("r=3", "f1=3 f0=8", -1), 3: ("r=4", "f1=4 f0=1", 1),
            4: ("r=2", "f1=2 f0=0", -1), 5: ("r=6", "f1=6 f0=0", 1), 6: ("r=1", "f1=1 f0=0", 1)}
    for k, (a, b, side) in info.items():
        x, y = pos[k]
        y -= 16 if k == 1 else 0
        if side > 0:
            f.text(x + 30, y - 2, a, 14, SUB)
            f.text(x + 30, y + 16, b, 14, PALETTE["blue"][1], "700")
        else:
            f.text(x - 30, y - 2, a, 14, SUB, anchor="end")
            f.text(x - 30, y + 16, b, 14, PALETTE["blue"][1], "700", "end")
    f.text(32, 130, "r[u]：快乐值；直接上下级不能同去。", 16, SUB)
    f.text(32, 160, "计算顺序：4、5、2、6、3、1。", 16, SUB)
    for i, s in enumerate(["f1[u] = r[u] + Σ f0[孩子]", "f0[u] = Σ max(f0[孩子], f1[孩子])",
                           "答案 = max(f1[1], f0[1]) = max(14, 12) = 14"]):
        f.text(32, 470 + i * 34, s, 18, INK, "700" if i == 2 else None, mono=i < 2, maxw=930)
    return f.save()


def c408_knap():
    f = Fig("c4-08-tree-knapsack", "树上背包：把孩子的数组合并进父亲", "dp[u][j]：在 u 的子树里选 j 个点（u 必选）能得到的最大价值。", 480,
            "合并是一次“最大加卷积”；总复杂度 O(n·m)，因为每对点只在它们的 LCA 处配对一次。")
    f.text(32, 160, "dp[u]（已合并）", 17, SUB, "700")
    cells(f, 300, 135, [0, 5, 9], 70, 44, ["blue"] * 3, 18, 0)
    f.text(32, 262, "dp[v]（新孩子）", 17, SUB, "700")
    cells(f, 300, 237, [0, 4], 70, 44, ["green"] * 2, 18, 0)
    f.text(32, 392, "合并后的 dp[u]", 17, SUB, "700")
    cells(f, 300, 367, [0, 5, 9, 13], 70, 44, ["orange"] * 4, 18, 0)
    f.arrow(280, 318, 280, 360, GREY)
    f.text(300, 336, "new[k] = max( dp[u][i] + dp[v][k-i] )", 15, SUB)
    for i, s in enumerate(["new[0] = 0 + 0 = 0", "new[1] = max(5+0, 0+4) = 5", "new[2] = max(9+0, 5+4) = 9",
                           "new[3] = 9 + 4 = 13"]):
        f.text(620, 160 + i * 34, s, 16, INK, mono=True, maxw=350)
    return f.save()


def build_all():
    w = []
    for fn in (c408_order, c408_knap):
        w += fn()
    return w
