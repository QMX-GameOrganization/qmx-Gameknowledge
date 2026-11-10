"""第 2 章配图（下）：进阶篇——带权并查集、可撤销并查集、ST 表、左偏树。"""
from svglib import Fig, GREY, SUB, INK, PALETTE
from figures_s02_c0a import ln
from figures_s02_c2b import node, up


def wdsu():
    f = Fig("c2-wdsu", "带权并查集：边上记录到父亲的距离", "d[x] 表示 x 到 parent[x] 的距离；路径压缩时把路径上的距离累加起来。", 620,
            "压缩后 d[x] 变成 x 到根的总距离，查询任意两点的差只需看 d。")
    f.h = 650
    f.rect(32, 105, 440, 480, "blue")
    f.rect(500, 105, 468, 480, "green")
    f.text(48, 136, "压缩前：一条链", 18, PALETTE["blue"][1], "700")
    f.text(516, 136, "find(4) 之后：全部直连根 1", 18, PALETTE["green"][1], "700")
    ys, ds = [190, 300, 410, 520], [None, 1, 3, 2]
    for k in range(4):
        node(f, 230, ys[k], k + 1, "blue" if k == 0 else "white")
        if k:
            up(f, (230, ys[k]), (230, ys[k - 1]))
            f.text(248, (ys[k] + ys[k - 1]) / 2 + 5, f"d[{k + 1}] = {ds[k]}", 16, PALETTE["blue"][1], "700")
    node(f, 734, 190, 1, "green")
    xs, tot = [590, 734, 878], [1, 4, 6]
    for k in range(3):
        node(f, xs[k], 450, k + 2, "white")
        f.arrow(xs[k], 431, 734 + (xs[k] - 734) * 0.3, 212, PALETTE["green"][1])
        f.text(xs[k] + (12 if k == 1 else 0), 340, f"d[{k + 2}] = {tot[k]}", 16, PALETTE["green"][1], "700",
               "start" if k == 1 else "middle")
    f.text(516, 560, "d[4] = 2 + 3 + 1 = 6", 16, SUB)
    return f.save()


def rollback():
    f = Fig("c2-rollback", "可撤销并查集：用栈记录每次合并", "不做路径压缩，只按大小合并；每次合并记下“谁挂到了谁下面”。", 520,
            "撤销只需弹出栈顶并还原两个值，正好适合按时间线回退的离线题。")
    f.text(48, 128, "操作栈（栈顶在上）", 18, SUB, "700")
    recs = [("合并 3：把根 3 挂到根 1", "red"), ("合并 2：把根 4 挂到根 3", "blue"), ("合并 1：把根 2 挂到根 1", "blue")]
    for i, (s, k) in enumerate(recs):
        f.chip(250, 190 + i * 70, 400, 52, k, s, 17)
    f.text(250, 392, "栈底", 15, SUB, anchor="middle")
    f.text(250, 156, "栈顶", 15, PALETTE["red"][1], "700", "middle")
    f.arrow(470, 190, 560, 190, PALETTE["red"][1])
    f.rect(570, 140, 400, 330, "red")
    f.text(588, 174, "撤销栈顶（合并 3）要做两件事", 17, PALETTE["red"][1], "700", maxw=370)
    f.text(588, 214, "parent[3] = 3", 17, INK, mono=True)
    f.text(588, 248, "size[1] -= size[3]", 17, INK, mono=True)
    f.text(588, 296, "根 3 重新成为独立的根，", 16, INK)
    f.text(588, 322, "根 1 的集合大小恢复。", 16, INK)
    f.text(588, 372, "因为没有路径压缩，", 16, SUB)
    f.text(588, 398, "树的形状只被这一次合并改动过。", 16, SUB, maxw=370)
    return f.save()


def sparse_table():
    f = Fig("c2-sparse-table", "ST 表：st[j][i] = 从 i 开始长度 2^j 的区间最小值", "a = [3, 1, 4, 1, 5, 9, 2, 6]，查询区间 [1, 6] 的最小值。", 560,
            "区间长 6，k = floor(log2(6)) = 2，答案 = min(st[2][1], st[2][3]) = 1。两段重叠不影响取最小值。")
    a = [3, 1, 4, 1, 5, 9, 2, 6]
    st = [a]
    for j in range(1, 4):
        prev = st[-1]
        st.append([min(prev[i], prev[i + (1 << (j - 1))]) for i in range(len(a) - (1 << j) + 1)])
    x0, cw = 170, 96
    for i in range(8):
        f.text(x0 + i * cw + cw / 2, 118, f"i={i}", 15, SUB, anchor="middle")
    for j in range(4):
        y = 130 + j * 62
        f.text(32, y + 31, f"j={j}（长 {1 << j}）", 16, SUB, "700")
        for i, v in enumerate(st[j]):
            hot = j == 2 and i in (1, 3)
            f.rect(x0 + i * cw + 3, y, cw - 6, 48, "orange" if hot else "blue", r=8)
            f.text(x0 + i * cw + cw / 2, y + 32, str(v), 20, INK, "700" if hot else None, "middle")
    f.rect(x0 + 1 * cw + 3, 400, 4 * cw - 6, 22, "orange", r=6)
    f.text(x0 + 1 * cw + 12, 417, "st[2][1] 覆盖 [1, 4]", 14, INK)
    f.rect(x0 + 3 * cw + 3, 430, 4 * cw - 6, 22, "green", r=6)
    f.text(x0 + 3 * cw + 12, 447, "st[2][3] 覆盖 [3, 6]", 14, INK)
    f.text(32, 490, "查询区间 [1, 6] 被这两段盖满，中间的 [3, 4] 重叠。", 16, INK)
    return f.save()


def leftist_merge():
    f = Fig("c2-leftist-merge", "左偏树合并：沿右链合并，必要时交换左右子树", "dist 表示到最近空位置的距离（空节点为 0，叶子为 1）；要求左儿子的 dist 不小于右儿子。", 560,
            "右链长度只有 O(log n)，所以合并是 O(log n)。")
    def nd(x, y, v, d, kind="blue"):
        f.chip(x, y, 62, 46, kind, f"{v}\nd={d}", 14)
    def edge(a, b):
        ln(f, a[0], a[1] + 23, b[0], b[1] - 23)
    f.text(130, 128, "堆 A", 17, SUB, "700", "middle")
    f.text(400, 128, "堆 B", 17, SUB, "700", "middle")
    f.text(780, 128, "合并后", 17, SUB, "700", "middle")
    A = {1: (130, 190), 6: (130, 290)}
    B = {2: (400, 190), 7: (350, 290), 8: (450, 290)}
    R = {1: (780, 190), 2: (700, 300), 6: (860, 300), 7: (650, 410), 8: (750, 410)}
    edge(A[1], A[6]); edge(B[2], B[7]); edge(B[2], B[8])
    edge(R[1], R[2]); edge(R[1], R[6]); edge(R[2], R[7]); edge(R[2], R[8])
    for k, d in ((1, 1), (6, 1)):
        nd(*A[k], k, d, "blue")
    for k, d in ((2, 2), (7, 1), (8, 1)):
        nd(*B[k], k, d, "green")
    for k, d in ((1, 2), (2, 2), (6, 1), (7, 1), (8, 1)):
        nd(*R[k], k, d, "orange" if k == 1 else "green" if k in (2, 7, 8) else "blue")
    f.text(265, 205, "+", 30, SUB, "700", "middle")
    f.arrow(500, 250, 600, 250, GREY)
    f.text(32, 470, "1 比 2 小，1 当根；把 B 并进 1 的右子树。此时右子树 dist = 2，大于左子树 6 的 dist = 1，", 15, INK)
    f.text(32, 496, "违反左偏性质，于是交换左右子树：2 变成左儿子，6 变成右儿子，1 的 dist 更新为右儿子 dist + 1 = 2。", 15, INK)
    return f.save()


def build_all():
    w = []
    for fn in (wdsu, rollback, sparse_table, leftist_merge):
        w += fn()
    return w
