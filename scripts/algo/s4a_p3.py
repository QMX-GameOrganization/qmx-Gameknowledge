"""4.5 LCA 倍增、4.6 树状数组 的配图。"""
from s4a_common import *

LTREE = [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (4, 7), (7, 8)]


def c405_table():
    f = Fig("c4-05-jump-table", "倍增表 up[k][v]：v 的第 2^k 个祖先", "每个节点只存 log n 个“跳板”，就能到达任意高度。", 600,
            "up[k][v] = up[k-1][ up[k-1][v] ]：先跳 2^(k-1) 步，再跳 2^(k-1) 步。")
    pos = {1: (200, 150), 2: (120, 240), 3: (300, 240), 4: (70, 330), 5: (170, 330), 6: (300, 330), 7: (70, 420), 8: (70, 510)}
    tree(f, pos, LTREE, {8: "orange"})
    rows = [("up[0]", "- 1 1 2 2 3 4 7"), ("up[1]", "- - - 1 1 1 2 4"), ("up[2]", "- - - - - - - 1")]
    table(f, 430, 110, [100] + [54] * 8, ["v"] + [str(i) for i in range(1, 9)],
          [[n] + v.split() for n, v in rows], 46, 17, mono_cols=(0,))
    f.text(430, 330, "“-”表示不存在（越过了根）。", 16, SUB)
    f.box(430, 360, 530, 150, "orange", "以 8 为例", ["up[0][8] = 7：爬 1 步", "up[1][8] = up[0][up[0][8]] = up[0][7] = 4：爬 2 步",
                                             "up[2][8] = up[1][up[1][8]] = up[1][4] = 1：爬 4 步"], 16)
    return f.save()


def c405_steps():
    f = Fig("c4-05-lca-steps", "倍增求 LCA(8, 6)", "先把深的一个跳到同一深度，再两个一起往上跳。", 560,
            "跳的原则：只有“跳完仍不相等”才真的跳，最后停在 LCA 的两个孩子上。")
    f.box(32, 105, 440, 120, "blue", "① 对齐深度", ["depth[8]=4，depth[6]=2，差 2", "2 的二进制是 10，用 up[1] 跳一步：8 → 4"], 16)
    f.box(32, 240, 440, 120, "green", "② 从大到小同时上跳", ["k=1：up[1][4]=up[1][6]=1，相同，不跳", "k=0：up[0][4]=2 ≠ up[0][6]=3，跳"], 16)
    f.box(32, 375, 440, 120, "orange", "③ 收尾", ["此时 u=2，v=3，父亲相同", "LCA = up[0][2] = 1"], 16)
    pos = {1: (760, 150), 2: (680, 240), 3: (860, 240), 4: (630, 330), 5: (730, 330), 6: (860, 330), 7: (630, 420), 8: (630, 510)}
    kinds = {8: "orange", 4: "orange", 2: "orange", 6: "purple", 3: "purple", 1: "green"}
    tree(f, pos, LTREE, kinds, {(7, 8), (4, 7), (2, 4), (3, 6)})
    return f.save()


def c406_structure():
    f = Fig("c4-06-bit-structure", "树状数组：c[i] 管理 (i - lowbit(i), i]", "每个 c[i] 覆盖的长度恰好是 i 的 lowbit。", 580,
            "lowbit(i) = i & -i，即 i 的二进制里最低位的 1 对应的数。")
    x0, w = 100, 100
    kinds = ["blue", "green", "orange", "purple"]
    for i in range(1, 9):
        lb = i & -i
        lv = lb.bit_length() - 1
        y = 396 - lv * 50
        lab = f"c{i}" if lb == 1 else f"c{i}: {i - lb + 1}~{i}"
        f.chip(x0 + (i - lb) * w + lb * w / 2, y + 18, lb * w - 8, 36, kinds[lv], lab, 16, bold=True)
    cells(f, x0, 450, [f"a{i}" for i in range(1, 9)], w, 40, None, 17)
    for i in range(1, 9):
        f.text(x0 + (i - 1) * w + w / 2, 515, format(i, "04b"), 15, SUB, anchor="middle", mono=True)
    for lv, t in enumerate(["lowbit 1", "lowbit 2", "lowbit 4", "lowbit 8"]):
        f.text(24, 420 - lv * 50, t, 13, PALETTE[kinds[lv]][1], "700")
    f.text(32, 130, "c[i] 存的是 a[i - lowbit(i) + 1 .. i] 的和。", 18, INK, "700")
    f.text(32, 162, "例：c6 管 a5~a6，c8 管 a1~a8，c7 只管 a7。", 17, INK)
    f.text(32, 194, "下方二进制是下标 i，最低位的 1 决定了它覆盖多长。", 17, SUB)
    return f.save()


def c406_path():
    f = Fig("c4-06-query-update", "查询和修改都只走 log n 步", "查询时下标不断减去 lowbit；修改时不断加上 lowbit。", 480,
            "两条路径各至多 log n 个节点。")
    f.rect(32, 100, 450, 340, "blue")
    f.text(48, 132, "query(7)：i -= lowbit(i)", 19, PALETTE["blue"][1], "700")
    for k, (x, lab, rg) in enumerate([(120, "i=7 (111)", "c7 = a7"), (260, "i=6 (110)", "c6 = a5~a6"), (400, "i=4 (100)", "c4 = a1~a4")]):
        f.chip(x, 200, 120, 46, "white", lab, 16)
        f.chip(x, 280, 120, 46, "green", rg, 16)
        if k < 2:
            f.arrow(x + 62, 200, x + 78, 200, PALETTE["blue"][1])
    f.text(48, 355, "i=4 再减 lowbit 得 0，结束。", 16, SUB)
    f.text(48, 390, "sum(7) = c7 + c6 + c4 = a1~a7", 18, INK, "700")
    f.rect(518, 100, 450, 340, "orange")
    f.text(534, 132, "update(3, d)：i += lowbit(i)", 19, PALETTE["orange"][1], "700")
    for k, (x, lab, rg) in enumerate([(606, "i=3 (011)", "c3 += d"), (746, "i=4 (100)", "c4 += d"), (886, "i=8 (1000)", "c8 += d")]):
        f.chip(x, 200, 120, 46, "white", lab, 16)
        f.chip(x, 280, 120, 46, "red", rg, 16)
        if k < 2:
            f.arrow(x + 62, 200, x + 78, 200, PALETTE["orange"][1])
    f.text(534, 355, "i=8 再加 lowbit 得 16 > n，结束。", 16, SUB)
    f.text(534, 390, "覆盖 a3 的 c3、c4、c8 都被更新。", 18, INK, "700")
    return f.save()


def c406_diff():
    f = Fig("c4-06-diff", "区间加：转成差分数组的两次单点修改", "给 [3, 6] 都加 2，只需改 d[3] 和 d[7]。", 560,
            "d[i] = a[i] - a[i-1]；a[i] 等于 d 的前缀和，所以“区间加、单点查”用树状数组维护 d。")
    x0, w = 190, 70
    a0, d, a1 = [0] * 8, [0, 0, 2, 0, 0, 0, -2, 0], [0, 0, 2, 2, 2, 2, 0, 0]
    f.text(32, 172, "原数组 a", 17, SUB, "700")
    cells(f, x0, 150, a0, w, 44, None, 18, 1)
    f.text(32, 292, "差分 d", 17, SUB, "700")
    cells(f, x0, 270, d, w, 44, ["white", "white", "orange", "white", "white", "white", "red", "white"], 18, 1)
    f.text(x0 + 8 * w + 14, 288, "d[3] += 2", 16, PALETTE["orange"][1], "700")
    f.text(x0 + 8 * w + 14, 314, "d[7] -= 2", 16, PALETTE["red"][1], "700")
    f.text(32, 412, "新数组 a", 17, SUB, "700")
    cells(f, x0, 390, a1, w, 44, ["white", "white", "green", "green", "green", "green", "white", "white"], 18, 1)
    f.arrow(x0 + 4 * w, 200, x0 + 4 * w, 262, GREY)
    f.arrow(x0 + 4 * w, 320, x0 + 4 * w, 382, GREY)
    f.text(x0 + 4 * w + 12, 236, "区间加 → 两个端点", 15, SUB)
    f.text(x0 + 4 * w + 12, 358, "前缀和还原出 a", 15, SUB)
    f.text(32, 490, "区间求和：sum(1..x) = (x+1) * Σd[i] - Σ i*d[i]（i 从 1 到 x），用两个树状数组分别维护 d[i] 和 i*d[i]。", 16, INK, maxw=940)
    return f.save()


def build_all():
    w = []
    for fn in (c405_table, c405_steps, c406_structure, c406_path, c406_diff):
        w += fn()
    return w
