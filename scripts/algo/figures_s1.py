"""第 1 章 基础算法 配图（图名前缀 c1-）。"""
from svglib import Fig, GREY, SUB, INK, PALETTE


def cells(f, x0, y, vals, w=60, h=40, kinds=None, size=18, idx=None):
    """一行方格；idx 给出时在上方标下标。返回每格中心 x。"""
    xs = []
    for i, v in enumerate(vals):
        cx = x0 + i * w + w / 2
        xs.append(cx)
        f.chip(cx, y + h / 2, w - 6, h, (kinds[i] if kinds else "white"), str(v), size)
        if idx is not None:
            f.text(cx, y - 6, str(idx + i), 13, SUB, anchor="middle")
    return xs


def groups_row(f, y, groups, kind, cw=56, gap=24, h=38):
    """一行若干组方格，整体水平居中。"""
    n = sum(len(g) for g in groups)
    total = n * cw + (len(groups) - 1) * gap
    x = 500 - total / 2
    for g in groups:
        for v in g:
            f.chip(x + cw / 2, y + h / 2, cw - 6, h, kind, str(v), 18)
            x += cw
        x += gap


def merge_tree():
    f = Fig("c1-merge-tree", "归并排序：先拆到单个元素，再两两合并", "拆分 3 层，合并 3 层，每层的总工作量都是 n。", 560,
            "一共 log n 层，每层合并耗时 O(n)，所以总复杂度 O(n log n)。")
    rows = [
        ("拆分", [[6, 2, 5, 1, 8, 3, 7, 4]], "grey"),
        ("", [[6, 2, 5, 1], [8, 3, 7, 4]], "grey"),
        ("", [[6, 2], [5, 1], [8, 3], [7, 4]], "grey"),
        ("单个元素", [[6], [2], [5], [1], [8], [3], [7], [4]], "white"),
        ("合并", [[2, 6], [1, 5], [3, 8], [4, 7]], "blue"),
        ("", [[1, 2, 5, 6], [3, 4, 7, 8]], "blue"),
        ("", [[1, 2, 3, 4, 5, 6, 7, 8]], "green"),
    ]
    y = 108
    for label, g, kind in rows:
        if label:
            f.text(32, y + 26, label, 16, PALETTE["blue"][1] if label != "单个元素" else SUB, "700")
        groups_row(f, y, g, kind)
        y += 60
    return f.save()


def merge_count():
    f = Fig("c1-merge-count", "合并时数逆序对：右边的数先出队，就和左边剩下的每个数构成逆序", "左 [3,5,8]，右 [2,4,9]，共 5 个逆序对。", 560,
            "每次右侧元素先出队，累加左侧剩余个数；每对元素只会在它们第一次处于不同半区的那次合并里被数到一次。")
    f.text(60, 125, "左半（已排序）", 16, PALETTE["blue"][1], "700")
    cells(f, 60, 140, [3, 5, 8], kinds=["blue"] * 3)
    f.text(560, 125, "右半（已排序）", 16, PALETTE["green"][1], "700")
    cells(f, 560, 140, [2, 4, 9], kinds=["green"] * 3)
    f.rect(32, 215, 936, 245, "grey")
    f.text(48, 245, "步骤", 16, SUB, "700")
    f.text(130, 245, "比较", 16, SUB, "700")
    f.text(300, 245, "谁出队", 16, SUB, "700")
    f.text(470, 245, "本步新增逆序对", 16, SUB, "700")
    f.text(760, 245, "累计", 16, SUB, "700")
    steps = [("1", "3 与 2", "右 2", "左剩 3,5,8 → +3", "3"), ("2", "3 与 4", "左 3", "+0", "3"),
             ("3", "5 与 4", "右 4", "左剩 5,8 → +2", "5"), ("4", "5 与 9", "左 5", "+0", "5"),
             ("5", "8 与 9", "左 8", "+0", "5"), ("6", "只剩 9", "右 9", "+0", "5")]
    for i, (a, b, c, d, e) in enumerate(steps):
        y = 275 + i * 29
        f.text(56, y, a, 16)
        f.text(130, y, b, 16)
        f.text(300, y, c, 16, PALETTE["green"][1] if c.startswith("右") else PALETTE["blue"][1], "700")
        f.text(470, y, d, 16)
        f.text(775, y, e, 16, INK, "700")
    f.text(48, 500, "合并结果：", 16, SUB, "700")
    cells(f, 150, 478, [2, 3, 4, 5, 8, 9], w=56, h=36, kinds=["green", "blue", "green", "blue", "blue", "green"])
    return f.save()


def bs_template():
    f = Fig("c1-bs-template", "找第一个 ≥ 5 的位置：区间 [lo, hi) 不断减半", "a = [1,3,3,5,7,9,11]，答案是下标 3。", 520,
            "mid 处的值 ≥ 5 时答案不会在 mid 右边（hi = mid）；< 5 时答案一定在 mid 右边（lo = mid + 1）。")
    a = [1, 3, 3, 5, 7, 9, 11]
    rows = [(0, 7, 3, "a[3]=5 ≥ 5 → hi = 3"), (0, 3, 1, "a[1]=3 < 5 → lo = 2"),
            (2, 3, 2, "a[2]=3 < 5 → lo = 3"), (3, 3, None, "lo = hi = 3，答案 3")]
    x0, w = 330, 66
    for r, (lo, hi, mid, note) in enumerate(rows):
        y = 125 + r * 88
        kinds = []
        for i in range(7):
            if mid == i:
                kinds.append("orange")
            elif lo <= i < hi:
                kinds.append("blue")
            elif mid is None and i == lo:
                kinds.append("green")
            else:
                kinds.append("grey")
        cells(f, x0, y, a, w=w, kinds=kinds, idx=0 if r == 0 else None)
        f.text(32, y + 20, f"lo={lo}  hi={hi}", 16, INK, "700", mono=True)
        f.text(32, y + 44, note, 14, SUB, maxw=290)
        if mid is not None:
            f.text(x0 + mid * w + w / 2, y + 62, "mid", 14, PALETTE["orange"][1], "700", "middle")
    return f.save()


def bs_answer():
    f = Fig("c1-bs-answer", "二分答案：答案落在“假…假真…真”的分界线上", "check(x) 随 x 单调变化时，就能在答案的取值范围上二分。", 470,
            "先确认单调性，再决定找第一个“真”还是最后一个“真”。")
    xs = range(1, 11)
    f.text(32, 120, "求最小的可行值（如：最小化最大段和）", 17, PALETTE["blue"][1], "700")
    kinds = ["red"] * 4 + ["green"] * 6
    cells(f, 50, 140, ["假"] * 4 + ["真"] * 6, w=90, kinds=kinds, idx=1)
    f.arrow(455, 222, 455, 186, PALETTE["green"][1])
    f.text(455, 244, "第一个真 = 答案", 15, PALETTE["green"][1], "700", "middle")
    f.text(32, 280, "求最大的可行值（如：最大化最小间距）", 17, PALETTE["orange"][1], "700")
    kinds = ["green"] * 6 + ["red"] * 4
    cells(f, 50, 300, ["真"] * 6 + ["假"] * 4, w=90, kinds=kinds, idx=1)
    f.arrow(545, 382, 545, 346, PALETTE["green"][1])
    f.text(545, 404, "最后一个真 = 答案", 15, PALETTE["green"][1], "700", "middle")
    return f.save()


def prefix_1d():
    f = Fig("c1-prefix-1d", "一维前缀和：区间和 = 两个前缀和相减", "查询 a[2..4] 的和，只需要 s[4] - s[1]。", 420,
            "s[i] = a[1] + … + a[i]，s[0] = 0。预处理 O(n)，每次查询 O(1)。")
    a = [3, 1, 4, 1, 5, 9]
    s = [0, 3, 4, 8, 9, 14, 23]
    f.text(32, 140, "a", 18, INK, "700", mono=True)
    cells(f, 250, 120, a, w=80, kinds=["grey", "orange", "orange", "orange", "grey", "grey"], idx=1)
    f.text(32, 250, "s", 18, INK, "700", mono=True)
    cells(f, 170, 230, s, w=80,
          kinds=["grey", "red", "grey", "grey", "green", "grey", "grey"])
    for i in range(7):
        f.text(210 + 80 * i, 224, f"s[{i}]", 13, SUB, anchor="middle", mono=True)
    f.text(500, 330, "sum(2..4) = s[4] - s[1] = 9 - 3 = 6", 20, INK, "700", "middle", mono=True)
    f.text(500, 362, "= a[2] + a[3] + a[4] = 1 + 4 + 1", 17, SUB, anchor="middle", mono=True)
    return f.save()


def prefix_2d():
    f = Fig("c1-prefix-2d", "二维前缀和：整块减去两条边，再加回重复减去的角", "求右下角 (3,3)–(6,6) 的子矩阵和。", 560,
            "S[i][j] 表示左上角 (1,1) 到 (i,j) 的矩形和，预处理时用同样的容斥。")
    cw = 52
    x0, y0 = 60, 120
    for r in range(6):
        for c in range(6):
            if r >= 2 and c >= 2:
                k = "green"
            elif r < 2 and c >= 2:
                k = "orange"
            elif r >= 2 and c < 2:
                k = "orange"
            else:
                k = "blue"
            f.rect(x0 + c * cw, y0 + r * cw, cw - 2, cw - 2, k, r=6, opacity=".6")
            f.text(x0 + c * cw + cw / 2 - 1, y0 + r * cw + 33, f"{r + 1},{c + 1}", 13, SUB, anchor="middle")
    lx = 420
    legend = [("green", "目标：行 3–6，列 3–6"), ("orange", "S[2][6] 与 S[6][2]：各减一次"),
              ("blue", "S[2][2]：被减了两次，加回一次")]
    for i, (k, t) in enumerate(legend):
        y = 135 + i * 46
        f.rect(lx, y, 30, 30, k, r=6, opacity=".6")
        f.text(lx + 44, y + 22, t, 17, INK, maxw=480)
    f.text(lx, 320, "ans = S[x2][y2] - S[x1-1][y2]", 17, INK, "700", mono=True)
    f.text(lx + 56, 350, "- S[x2][y1-1] + S[x1-1][y1-1]", 17, INK, "700", mono=True)
    f.text(lx, 400, "代入 (3,3)–(6,6)：", 17, SUB)
    f.text(lx, 430, "S[6][6] - S[2][6] - S[6][2] + S[2][2]", 17, INK, "700", mono=True)
    return f.save()


def diff_array():
    f = Fig("c1-diff", "差分：区间加变成两个端点的修改", "对 a[2..4] 全部加 3：d[2] += 3，d[5] -= 3，再做前缀和还原。", 440,
            "差分是前缀和的逆运算：区间 [l, r] 加 v 等价于 d[l] += v，d[r+1] -= v。")
    f.text(32, 150, "d", 18, INK, "700", mono=True)
    cells(f, 100, 130, [0, 3, 0, 0, -3, 0], w=90, kinds=["grey", "orange", "grey", "grey", "red", "grey"], idx=1)
    f.text(660, 154, "d[2] += 3，d[5] -= 3", 16, SUB, maxw=320)
    for i in range(6):
        f.arrow(145 + i * 90, 178, 145 + i * 90, 238, GREY, dash=True)
    f.text(120, 215, "做前缀和", 15, SUB)
    f.text(32, 280, "a", 18, INK, "700", mono=True)
    cells(f, 100, 260, [0, 3, 3, 3, 0, 0], w=90, kinds=["grey", "green", "green", "green", "grey", "grey"], idx=1)
    f.text(32, 360, "d[2] 的 +3 一路传到右边，d[5] 的 -3 在第 5 位把它抵消，", 16, INK)
    f.text(32, 386, "所以只有 a[2..4] 增加了 3。", 16, INK)
    return f.save()


def two_pointer():
    f = Fig("c1-two-pointer", "滑动窗口：r 向右扩张，满足条件后 l 向右收缩", "求和 ≥ 7 的最短连续子数组，a = [2,3,1,2,4,3]。", 480,
            "l 和 r 都只会向右移动，各走不超过 n 步，总复杂度 O(n)。")
    a = [2, 3, 1, 2, 4, 3]
    states = [(0, 3, 8, "窗口 [0,3] 和 8 ≥ 7，记长度 4"), (2, 4, 7, "收缩后 [2,4] 和 7 ≥ 7，记长度 3"),
              (4, 5, 7, "再向右 [4,5] 和 7 ≥ 7，记长度 2（最优）")]
    x0, w = 90, 80
    for k, (l, r, s, note) in enumerate(states):
        y = 125 + k * 112
        kinds = ["orange" if l <= i <= r else "grey" for i in range(6)]
        cells(f, x0, y, a, w=w, kinds=kinds, idx=0 if k == 0 else None)
        f.text(x0 + l * w + w / 2, y + 62, "l", 15, PALETTE["blue"][1], "700", "middle")
        f.text(x0 + r * w + w / 2, y + 62, "r", 15, PALETTE["green"][1], "700", "middle")
        f.text(600, y + 26, note, 16, INK, maxw=380)
    return f.save()


def divide_maxsub():
    f = Fig("c1-divide-maxsub", "分治求最大子段和：最优段在左半、右半，或跨过中点", "a = [-2,1,-3,4,-1,2,1,-5,4]，答案 6。", 470,
            "跨中点的最优段 = 左半以 mid 结尾的最大后缀 + 右半以 mid+1 开头的最大前缀，O(n) 求出。")
    a = [-2, 1, -3, 4, -1, 2, 1, -5, 4]
    x0, w = 50, 100
    cells(f, x0, 130, a, w=w, kinds=["blue"] * 5 + ["green"] * 4, idx=0)
    f.path(f"M{x0 + 5 * w} 112L{x0 + 5 * w} 200", PALETTE["red"][1], dash=True)
    f.text(x0 + 5 * w, 106, "mid | mid+1", 14, PALETTE["red"][1], "700", "middle")
    bars = [("左半最优：4（下标 3）", x0 + 3 * w + 8, x0 + 4 * w - 8, "blue", 235),
            ("右半最优：4（下标 8）", x0 + 8 * w + 8, x0 + 9 * w - 8, "green", 235),
            ("跨中点：4 + (-1) + 2 + 1 = 6", x0 + 3 * w + 8, x0 + 7 * w - 8, "orange", 300)]
    for t, xa, xb, k, y in bars:
        f.rect(xa, y, xb - xa, 16, k, r=6, opacity="1")
    f.text(x0 + 3 * w + 8, 276, "左半最优：4", 15, PALETTE["blue"][1], "700")
    f.text(x0 + 6 * w, 276, "右半最优：4", 15, PALETTE["green"][1], "700")
    f.text(x0 + 3 * w + 8, 345, "跨中点：4 + (-1) + 2 + 1 = 6（取三者最大）", 16, PALETTE["orange"][1], "700")
    return f.save()


def greedy_interval():
    f = Fig("c1-greedy-interval", "区间调度：每次选结束最早且与已选不冲突的区间", "10 个区间，按右端点排序后依次检查，选出 3 个。", 540,
            "选 [1,4]；下一个起点 ≥ 4 的最早结束区间是 [5,7]；再选起点 ≥ 7 的 [8,11]。")
    iv = [(1, 4), (3, 5), (0, 6), (5, 7), (3, 9), (5, 9), (6, 10), (8, 11), (8, 12), (2, 14)]
    chosen = {(1, 4), (5, 7), (8, 11)}
    x0, sc = 70, 60
    for t in range(0, 15, 2):
        f.text(x0 + t * sc, 112, str(t), 14, SUB, anchor="middle")
    for i, (l, r) in enumerate(iv):
        y = 124 + i * 34
        k = "green" if (l, r) in chosen else "grey"
        f.rect(x0 + l * sc, y, (r - l) * sc, 24, k, r=6, opacity="1" if k == "green" else ".5")
        f.text(x0 + l * sc + 8, y + 18, f"[{l},{r}]", 14, PALETTE[k][1], "700" if k == "green" else None)
    for t in (4, 7, 11):
        f.path(f"M{x0 + t * sc} 120L{x0 + t * sc} 470", PALETTE["green"][1], dash=True)
    return f.save()


def quickselect():
    f = Fig("c1-quickselect", "快速选择：只进入包含第 k 小的那一段", "a = [7,2,9,4,1,8,3,6]，求第 3 小，答案 3。", 510,
            "每轮平均丢掉一半元素，期望总代价 n + n/2 + n/4 + … = O(n)。")
    groups_row(f, 125, [[2, 1, 3], [4], [7, 9, 8, 6]], "grey", cw=56, gap=30)
    f.text(32, 112, "第 1 轮 基准 4", 16, PALETTE["blue"][1], "700")
    f.text(300, 190, "< 4：3 个", 15, PALETTE["blue"][1], "700", "middle")
    f.text(500, 190, "= 4", 15, SUB, anchor="middle")
    f.text(750, 190, "> 4：4 个", 15, SUB, anchor="middle")
    f.text(32, 232, "k = 3 ≤ 3，只留下左段", 16, INK)
    groups_row(f, 285, [[1], [2], [3]], "grey", cw=56, gap=30)
    f.text(32, 272, "第 2 轮 基准 2", 16, PALETTE["blue"][1], "700")
    f.text(32, 350, "左段只有 1 个、等于 2 的有 1 个，合计 2 < 3，所以答案在右段，且是右段的第 1 小", 16, INK)
    f.rect(430, 385, 140, 46, "green")
    f.text(500, 416, "答案 3", 20, PALETTE["green"][1], "700", "middle")
    return f.save()


def ternary():
    f = Fig("c1-ternary", "三分：比较两个三等分点，丢掉较差一侧的三分之一", "单峰函数求最大值：f(m1) < f(m2) 时，最大值不在 [l, m1] 内。", 460,
            "每轮区间缩到原来的 2/3，需要 O(log 区间长度) 轮；函数必须严格单峰。")
    pts = []
    for i in range(0, 101):
        x = 100 + 8 * i
        t = (x - 620) / 520
        pts.append(f"{x},{380 - 240 * (1 - t * t):.1f}")
    l, r = 100, 900
    m1, m2 = l + (r - l) / 3, l + 2 * (r - l) / 3
    f.rect(l, 110, m1 - l, 270, "red", r=0, opacity=".15")
    f.parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{PALETTE["blue"][1]}" stroke-width="3"/>')
    def y_of(x):
        t = (x - 620) / 520
        return 380 - 240 * (1 - t * t)
    for x, name in ((l, "l"), (m1, "m1"), (m2, "m2"), (r, "r")):
        if x != l:
            f.path(f"M{x} 380L{x} {y_of(x):.1f}", GREY, dash=True)
        f.text(x, 404, name, 16, INK, "700", "middle")
    f.text((l + m1) / 2, 140, "丢弃", 17, PALETTE["red"][1], "700", "middle")
    return f.save()


def cdq():
    f = Fig("c1-cdq", "CDQ 分治：先算左右内部，再统计左半对右半的贡献", "把“前面的元素影响后面的元素”转成一次跨区间的批量处理。", 520,
            "跨区间统计时左右两半各自按另一维排序，用双指针加数据结构完成，总复杂度 O(n log n · log n)。")
    cells(f, 100, 120, ["1", "2", "3", "4", "5", "6", "7", "8"], w=100, kinds=["blue"] * 4 + ["green"] * 4)
    f.box(100, 215, 380, 70, "blue", "solve(l, mid)", ["左半内部的贡献，递归"], size=15)
    f.box(520, 215, 380, 70, "green", "solve(mid+1, r)", ["右半内部的贡献，递归"], size=15)
    f.box(220, 340, 560, 90, "orange", "左半 → 右半 的贡献", ["左半元素只能影响右半元素（时间或下标在前）", "在这一层一次性算完，不再往下递归"], size=15)
    f.arrow(290, 285, 400, 338, PALETTE["blue"][1])
    f.arrow(710, 285, 600, 338, PALETTE["green"][1])
    return f.save()


def mo_order():
    f = Fig("c1-mo-order", "莫队：按左端点所在块排序，块内按右端点升序", "n = 16，块长 4；右端点在同一块内只增不减。", 520,
            "总移动量约 O(n√n)：每块内 r 最多走 n 步，l 每次最多走一个块长。")
    cells(f, 100, 120, [str(i) for i in range(16)], w=50, h=36, kinds=["blue"] * 4 + ["green"] * 4 + ["orange"] * 4 + ["purple"] * 4, size=15)
    qs = [("q1", 0, 6, "blue"), ("q2", 2, 9, "blue"), ("q3", 3, 13, "blue"), ("q4", 5, 8, "green"), ("q5", 6, 14, "green")]
    for i, (n, l, r, k) in enumerate(qs):
        y = 195 + i * 44
        f.rect(100 + l * 50 + 3, y, (r - l + 1) * 50 - 6, 26, k, r=6, opacity="1")
        f.text(86, y + 19, n, 15, INK, "700", "end")
    f.text(960, 215, "块 0 内按 r 升序：6 → 9 → 13", 15, PALETTE["blue"][1], "700", "end")
    f.text(960, 347, "块 1 内按 r 升序：8 → 14", 15, PALETTE["green"][1], "700", "end")
    f.text(32, 450, "处理顺序 q1, q2, q3 | q4, q5：r 在块内一路向右，不会来回跑。", 17, INK)
    return f.save()


def build_all():
    w = []
    for fn in (merge_tree, merge_count, bs_template, bs_answer, prefix_1d, prefix_2d, diff_array, two_pointer,
               divide_maxsub, greedy_interval, quickselect, ternary, cdq, mo_order):
        w += fn()
    return w

