"""第 6 章 6.1~6.7(动态规划上半)的配图。"""
from svglib import Fig, GREY, SUB, INK, PALETTE

B, G, O, R, P, K, W = "blue", "green", "orange", "red", "purple", "grey", "white"


def ink(kind):
    return PALETTE[kind][1]


def table(f, x0, y0, cw, ch, rows, kinds=None, size=16, hdr_rows=0, hdr_cols=0, mono=False):
    """画一张表。rows 是二维字符串;kinds 是 {(r,c): kind};第一行/列可作表头。"""
    kinds = kinds or {}
    for r, row in enumerate(rows):
        for c, s in enumerate(row):
            if s is None:
                continue
            head = r < hdr_rows or c < hdr_cols
            kind = kinds.get((r, c), K if head else W)
            f.chip(x0 + c * cw + cw / 2, y0 + r * ch + ch / 2, cw - 4, ch - 4, kind, str(s), size, mono=mono,
                   bold=head or (r, c) in kinds)


# ------------------------------------------------------------ 6.1
def fib_tree():
    f = Fig("c6-01-fib-tree", "朴素递归的 fib(5):同一个子问题被反复计算", "每个节点是一次函数调用,颜色深的节点在树里出现不止一次。", 600,
            "fib(3) 算了 2 次,fib(2) 算了 3 次;n 每加 1,重复的部分近似翻倍。")
    nodes = []  # (n, depth, x)
    leaf = [0]

    def build(n, d):
        if n < 2:
            x = leaf[0]; leaf[0] += 1
            nodes.append([n, d, x, None, None]); return len(nodes) - 1
        a = build(n - 1, d + 1); b = build(n - 2, d + 1)
        nodes.append([n, d, (nodes[a][2] + nodes[b][2]) / 2, a, b]); return len(nodes) - 1

    build(5, 0)
    sx = 112
    X = lambda x: 80 + x * sx
    Y = lambda d: 150 + d * 92
    for n, d, x, a, b in nodes:
        for c in (a, b):
            if c is not None:
                f.arrow(X(x), Y(d) + 18, X(nodes[c][2]), Y(nodes[c][1]) - 20, GREY)
    for n, d, x, a, b in nodes:
        kind = {2: R, 3: O}.get(n, K if n < 2 else B)
        f.chip(X(x), Y(d), 76, 38, kind, f"fib({n})", 16, bold=n in (2, 3))
    f.chip(880, 150, 150, 36, R, "fib(2) × 3 次", 15, bold=True)
    f.chip(880, 200, 150, 36, O, "fib(3) × 2 次", 15, bold=True)
    return f.save()


def design_steps():
    f = Fig("c6-01-design", "设计一个 DP 的四步", "以「网格最小路径和」为例,每一步都要写清楚。", 460,
            "写代码之前,先把这四件事用一句话写下来。")
    steps = [("① 状态", "dp[i][j]", "从左上角走到 (i,j)\n的最小路径和", B),
             ("② 转移", "dp[i][j] =\nmin(上, 左) + g[i][j]", "最后一步只可能\n来自上方或左方", G),
             ("③ 边界", "dp[0][0] = g[0][0]", "第一行、第一列\n只有一个来源", O),
             ("④ 顺序", "i、j 从小到大", "算 (i,j) 时,\n上方和左方已经算好", P)]
    for i, (head, code, note, kind) in enumerate(steps):
        x = 32 + i * 243
        f.rect(x, 110, 222, 270, kind)
        f.text(x + 14, 144, head, 21, ink(kind), "700")
        f.chip(x + 111, 215, 194, 76, W, code, 15, mono=True)
        for k, line in enumerate(note.split("\n")):
            f.text(x + 14, 306 + k * 26, line, 15, INK, maxw=196)
        if i < 3:
            f.arrow(x + 224, 245, x + 241, 245, GREY)
    f.text(32, 410, "答案:dp[n-1][m-1]。状态定义决定了转移怎么写,所以第一步最重要。", 17, INK)
    return f.save()


def grid_dp():
    f = Fig("c6-01-grid", "最小路径和:格子与 dp 表", "左边是原始网格,右边是 dp 表,绿色格子是最优路径经过的位置,橙色是下面要算的格子。", 480,
            "dp[1][1] = min(dp[0][1], dp[1][0]) + 5 = min(4, 2) + 5 = 7。")
    g = [[1, 3, 1], [1, 5, 1], [4, 2, 1]]
    dp = [[1, 4, 5], [2, 7, 6], [6, 8, 7]]
    path = {(0, 0), (0, 1), (0, 2), (1, 2), (2, 2)}
    f.text(60, 128, "网格 g", 19, ink(B), "700")
    f.text(420, 128, "dp 表", 19, ink(G), "700")
    for r in range(3):
        for c in range(3):
            f.chip(100 + c * 100, 190 + r * 90, 90, 80, B if (r, c) in path else W, str(g[r][c]), 24, bold=(r, c) in path)
            kind = O if (r, c) == (1, 1) else (G if (r, c) in path else W)
            f.chip(470 + c * 100, 190 + r * 90, 90, 80, kind, str(dp[r][c]), 24, bold=kind != W)
    f.arrow(350, 280, 405, 280, GREY)
    f.text(378, 262, "逐格", 14, SUB, anchor="middle")
    f.rect(740, 150, 230, 250, O)
    f.text(756, 184, "算 dp[1][1]", 18, ink(O), "700")
    f.text(756, 218, "上方 dp[0][1] = 4", 16, INK)
    f.text(756, 248, "左方 dp[1][0] = 2", 16, INK)
    f.text(756, 286, "取较小的 2,再加 5", 16, INK)
    f.text(756, 330, "dp[1][1] = 7", 20, ink(O), "700")
    return f.save()


def rolling():
    f = Fig("c6-01-rolling", "滚动数组:一维 dp 代替二维表", "处理第 i 行时,dp[j] 在被覆盖之前存的是上一行的值。", 600,
            "g = {{1,3,1},{1,5,1},{4,2,1}},下面演示处理第 1 行(g 的值为 1 5 1)。")
    rows = [("处理前(上一行的结果)", ["1", "4", "5"], None),
            ("j=0:dp[0] += 1", ["2", "4", "5"], 0),
            ("j=1:dp[1] = min(4, 左边 2) + 5", ["2", "7", "5"], 1),
            ("j=2:dp[2] = min(5, 左边 7) + 1", ["2", "7", "6"], 2)]
    for i, (label, vals, hot) in enumerate(rows):
        y = 150 + i * 92
        f.text(40, y + 8, label, 17, INK, "700" if hot is not None else None, maxw=420)
        for c, v in enumerate(vals):
            f.chip(640 + c * 100, y, 90, 56, O if c == hot else (K if hot is None else W), v, 22, bold=c == hot)
        if i < 3:
            f.arrow(685, y + 32, 685, y + 60, GREY)
    f.text(40, 520, "同一个数组原地更新:dp[j] 的旧值是「从上方来」,dp[j-1] 的新值是「从左方来」。", 16, INK)
    return f.save()


# ------------------------------------------------------------ 6.2
def lis_n2():
    f = Fig("c6-02-lis-n2", "LIS 的 O(n²) 做法", "dp[i] = 以 a[i] 结尾的最长严格递增子序列长度。", 470,
            "dp[6] = 4 来自 7 之前最优的结尾 7(dp=3) + 1;还原时沿着前驱往回找。")
    a = [10, 9, 2, 5, 3, 7, 101, 18]
    dp = [1, 1, 1, 2, 2, 3, 4, 4]
    hot = {2, 3, 5, 6}
    f.text(40, 136, "下标 i", 15, SUB)
    f.text(40, 206, "a[i]", 17, INK, "700")
    f.text(40, 296, "dp[i]", 17, ink(G), "700")
    for i in range(8):
        x = 190 + i * 95
        f.text(x, 136, str(i), 15, SUB, anchor="middle")
        f.chip(x, 200, 82, 54, O if i in hot else W, str(a[i]), 22, bold=i in hot)
        f.chip(x, 290, 82, 54, G if i in hot else W, str(dp[i]), 22, bold=i in hot)
    for i, j in [(2, 3), (3, 5), (5, 6)]:
        xi, xj = 190 + i * 95, 190 + j * 95
        f.path(f"M{xi} 172C{xi} 142 {xj} 142 {xj} 172", ink(O))
    f.text(40, 372, "橙色是一条最长序列 2 → 5 → 7 → 101;弧线表示「接在谁后面」。", 16, INK)
    f.text(40, 404, "转移:dp[i] = max(dp[j] + 1),其中 j < i 且 a[j] < a[i];没有这样的 j 就是 1。", 16, INK)
    return f.save()


def lis_tail():
    f = Fig("c6-02-lis-tail", "LIS 的 O(n log n) 做法:维护 tail 数组", "tail[k] = 长度为 k+1 的递增子序列里,结尾元素的最小值。", 560,
            "tail 始终有序,所以每个新元素用 lower_bound 二分;最终长度就是 LIS 长度 4。")
    a = [10, 9, 2, 5, 3, 7, 101, 18]
    tails = [[10], [9], [2], [2, 5], [2, 3], [2, 3, 7], [2, 3, 7, 101], [2, 3, 7, 18]]
    pos = [0, 0, 0, 1, 1, 2, 3, 3]
    f.text(40, 132, "读入", 16, SUB)
    f.text(180, 132, "tail 数组(橙色是本次写入的位置)", 16, SUB)
    f.text(720, 132, "动作", 16, SUB)
    for i, x in enumerate(a):
        y = 172 + i * 46
        f.chip(70, y, 64, 36, B, str(x), 17, bold=True)
        for c in range(4):
            if c < len(tails[i]):
                f.chip(220 + c * 80, y, 72, 36, O if c == pos[i] else W, str(tails[i][c]), 17, bold=c == pos[i])
        new = len(tails[i]) > (len(tails[i - 1]) if i else 0)
        f.text(720, y + 6, "追加到末尾" if new else "替换第 %d 个" % (pos[i] + 1), 16, INK)
    return f.save()


def lcs_table():
    s, t = "ABCBDAB", "BDCABA"
    n, m = len(s), len(t)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if s[i - 1] == t[j - 1] else max(dp[i - 1][j], dp[i][j - 1])
    i, j, path, picked = n, m, {(n, m)}, []
    while i > 0 and j > 0:
        if s[i - 1] == t[j - 1]:
            picked.append((i, j)); i -= 1; j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
        path.add((i, j))
    res = "".join(s[i - 1] for i, _ in reversed(picked))
    f = Fig("c6-02-lcs", "LCS 表:s = ABCBDAB,t = BDCABA", "dp[i][j] 是 s 前 i 个字符与 t 前 j 个字符的最长公共子序列长度;从右下角回溯。", 640,
            f"橙色格子是回溯路径上字符相同的位置,依次取出得到公共子序列 {res}(长度 {dp[n][m]})。")
    rows = [["", ""] + list(t)] + [[""] + [str(x) for x in dp[0]]]
    rows[1][0] = ""
    rows = [["", ""] + list(t), ["", "0"] + ["0"] * m]
    for i in range(1, n + 1):
        rows.append([s[i - 1]] + [str(x) for x in dp[i]])
    kinds = {}
    for (i, j) in path:
        kinds[(i + 1, j + 1)] = G
    for (i, j) in picked:
        kinds[(i + 1, j + 1)] = O
    table(f, 200, 104, 80, 52, rows, kinds, 20, hdr_rows=1, hdr_cols=1)
    f.text(40, 138, "t →", 16, SUB)
    f.text(40, 190, "s ↓", 16, SUB)
    f.text(40, 300, "相同:左上 + 1", 15, ink(O), "700")
    f.text(40, 328, "不同:取上、左较大者", 15, INK)
    return f.save()


def edit_table():
    s, t = "horse", "ros"
    n, m = len(s), len(t)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1): d[i][0] = i
    for j in range(m + 1): d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = d[i - 1][j - 1] if s[i - 1] == t[j - 1] else 1 + min(d[i - 1][j - 1], d[i - 1][j], d[i][j - 1])
    f = Fig("c6-02-edit", "编辑距离:horse → ros", "dp[i][j] 是 s 前 i 个字符变成 t 前 j 个字符的最少操作数。", 590,
            "相同则继承左上角;不同则取三个方向的最小值 + 1,三个方向对应替换、删除、插入。")
    rows = [["", ""] + list(t)] + [[""] + [str(x) for x in d[0]]]
    rows = [["", ""] + list(t), ["", "0", "1", "2", "3"]]
    for i in range(1, n + 1):
        rows.append([s[i - 1]] + [str(x) for x in d[i]])
    kinds = {(6, 4): G, (3, 2): O, (3, 3): B}
    table(f, 70, 112, 84, 58, rows, kinds, 21, hdr_rows=1, hdr_cols=1)
    f.box(560, 112, 410, 160, B, "三种操作对应三个方向", [
        "左上 dp[i-1][j-1]:替换(相同则免费)", "上方 dp[i-1][j]:删除 s[i-1]", "左方 dp[i][j-1]:插入 t[j-1]"], 15)
    f.box(560, 292, 410, 130, O, "橙色:dp[2][1](ho → r)", [
        "o≠r,取 min(dp[1][0], dp[1][1], dp[2][0]) + 1", "= min(1, 1, 2) + 1 = 2"], 15)
    f.box(560, 440, 410, 100, B, "蓝色:dp[2][2](ho → ro)", [
        "o = o,字符相同,直接继承左上角 dp[1][1] = 1"], 15)
    return f.save()



# ------------------------------------------------------------ 6.3
def knap_table():
    w, v, C = [1, 3, 4, 5], [1, 4, 5, 7], 7
    dp = [[0] * (C + 1) for _ in range(5)]
    for i in range(1, 5):
        for j in range(C + 1):
            dp[i][j] = dp[i - 1][j]
            if j >= w[i - 1]:
                dp[i][j] = max(dp[i][j], dp[i - 1][j - w[i - 1]] + v[i - 1])
    f = Fig("c6-03-table", "01 背包的二维表", "dp[i][j] = 只考虑前 i 件物品、容量为 j 时的最大价值。物品 (重量, 价值):(1,1) (3,4) (4,5) (5,7)。", 520,
            "dp[3][7] = max(不选第 3 件 = dp[2][7] = 5, 选第 3 件 = dp[2][3] + 5 = 9) = 9。")
    rows = [["i\\j"] + [str(j) for j in range(C + 1)]]
    for i in range(5):
        rows.append([str(i)] + [str(x) for x in dp[i]])
    kinds = {(4, 8): O, (3, 8): B, (3, 4): B}
    table(f, 40, 108, 66, 54, rows, kinds, 20, hdr_rows=1, hdr_cols=1)
    f.rect(660, 108, 310, 270, G)
    f.text(676, 142, "两种选择", 19, ink(G), "700")
    f.text(676, 176, "不选第 i 件:dp[i-1][j]", 16, INK)
    f.text(676, 206, "选第 i 件:", 16, INK)
    f.text(676, 232, "dp[i-1][j-w] + v", 16, INK)
    f.text(676, 278, "橙色 = 本格(i=3, j=7)", 15, ink(O), "700")
    f.text(676, 306, "蓝色 = 它依赖的两格:", 15, ink(B), "700")
    f.text(676, 334, "正上方 5,和 j-4 列的 4", 15, INK)
    return f.save()


def knap_order():
    f = Fig("c6-03-order", "一维背包:内层循环为什么要倒序", "只有一件物品 (重量 2,价值 3),容量 6。同一份代码,仅循环方向不同。", 560,
            "倒序时 dp[j-w] 还是上一件物品之后的旧值;正序时已被本轮更新,同一件物品被重复使用。")
    for k, (head, kind, vals, note, lab) in enumerate([
        ("倒序 j = 6 → 2(01 背包)", G, ["0", "0", "3", "3", "3", "3", "3"], "每个 dp[j] 读到的 dp[j-2] 都是本轮之前的值,物品最多放 1 件。", "正确"),
        ("正序 j = 2 → 6(完全背包)", R, ["0", "0", "3", "3", "6", "6", "9"], "dp[4] 读到的 dp[2] 已经是 3,等于放了第二件;dp[6] = 9 放了 3 件。", "放进了多件")]):
        y = 112 + k * 210
        f.rect(32, y, 936, 190, kind)
        f.text(48, y + 34, head, 19, ink(kind), "700")
        for j in range(7):
            f.text(150 + j * 96, y + 70, "j=%d" % j, 14, SUB, anchor="middle")
            f.chip(150 + j * 96, y + 108, 84, 46, W, vals[j], 21, bold=True)
        f.text(48, y + 170, note, 15, INK)
        f.chip(890, y + 34, 130, 34, kind, lab, 15, bold=True)
    return f.save()


def knap_split():
    f = Fig("c6-03-split", "多重背包的二进制拆分", "一种物品有 13 件,拆成 1、2、4、6 四组,当作 4 件 01 背包物品。", 520,
            "任何 0~13 的件数都能由这四组的某个子集凑出,物品数从 13 降到 4;一般是 O(log c)。")
    for i, (n, kind) in enumerate([(1, B), (2, G), (4, O), (6, P)]):
        f.chip(160 + i * 200, 160, 150, 56, kind, "一组 %d 件" % n, 19, bold=True)
    f.text(60, 232, "拆法:1, 2, 4, ... 依次取,最后剩下的余数 6 单独成组(13 - 1 - 2 - 4 = 6)。", 16, INK)
    f.text(60, 278, "凑出任意件数的例子:", 17, ink(G), "700")
    ex = [("5", "1 + 4"), ("7", "1 + 6"), ("11", "1 + 4 + 6"), ("13", "1 + 2 + 4 + 6")]
    for i, (n, how) in enumerate(ex):
        f.rect(85 + i * 200, 312, 150, 56, W)
        f.text(160 + i * 200, 337, n + " 件", 17, INK, "700", "middle")
        f.text(160 + i * 200, 360, how, 15, SUB, anchor="middle")
    f.text(60, 430, "注意:最后一组要取余数 6,不能取 8;取 8 会凑出超过 13 件的情况。", 16, ink(R), "700")
    return f.save()


# ------------------------------------------------------------ 6.4
def _stone_dp(a):
    n = len(a)
    pre = [0]
    for x in a:
        pre.append(pre[-1] + x)
    dp = [[0] * n for _ in range(n)]
    for ln in range(2, n + 1):
        for l in range(n - ln + 1):
            r = l + ln - 1
            dp[l][r] = min(dp[l][k] + dp[k + 1][r] for k in range(l, r)) + pre[r + 1] - pre[l]
    return dp, pre


def interval_order():
    a = [3, 4, 5, 2, 1]
    dp, pre = _stone_dp(a)
    f = Fig("c6-04-order", "区间 DP 的填表顺序:按区间长度", "石子 3 4 5 2 1,dp[l][r] = 把第 l 到 r 堆合并成一堆的最小代价。", 590,
            "dp[0][4] 依赖更短的区间 dp[0][k] 与 dp[k+1][4],所以必须先填完所有较短的区间。")
    n = 5
    rows = [["l \\ r"] + [str(r) for r in range(n)]]
    kinds = {}
    colors = {1: K, 2: B, 3: G, 4: O, 5: P}
    for l in range(n):
        row = [str(l)]
        for r in range(n):
            if r < l:
                row.append(None)
            else:
                row.append(str(dp[l][r]))
                kinds[(l + 1, r + 1)] = colors[r - l + 1]
        rows.append(row)
    kinds[(1, 2)] = R
    kinds[(3, 5)] = R
    table(f, 40, 112, 84, 62, rows, kinds, 21, hdr_rows=1, hdr_cols=1)
    for i, (ln, kd) in enumerate([(1, K), (2, B), (3, G), (4, O), (5, P)]):
        f.chip(680, 134 + i * 62, 120, 34, kd, "长度 %d" % ln, 16, bold=True)
        if i < 4:
            f.arrow(680, 153 + i * 62, 680, 177 + i * 62, GREY)
    f.rect(780, 112, 190, 300, R)
    f.text(794, 146, "dp[0][4] 的", 16, ink(R), "700")
    f.text(794, 170, "最优分割", 16, ink(R), "700")
    f.text(794, 206, "k = 1:", 15, INK)
    f.text(794, 234, "dp[0][1] = 7", 15, INK)
    f.text(794, 262, "+ dp[2][4] = 11", 15, INK)
    f.text(794, 290, "+ 区间和 15", 15, INK)
    f.text(794, 328, "= 33", 20, ink(R), "700")
    f.text(794, 366, "红色格子是这两项", 14, SUB)
    return f.save()


def interval_split():
    a = [3, 4, 5, 2, 1]
    dp, pre = _stone_dp(a)
    f = Fig("c6-04-split", "枚举最后一次合并的位置 k", "区间 [0,4] 的最后一次合并,把前后两段各自合并好的两堆合到一起。", 610,
            "总代价 = 左段最小代价 + 右段最小代价 + 整段重量和 15;四种 k 里取最小。")
    best = min(range(4), key=lambda k: dp[0][k] + dp[k + 1][4])
    for k in range(4):
        y = 110 + k * 92
        hot = k == best
        f.rect(32, y, 936, 80, G if hot else W)
        f.text(48, y + 32, "k = %d" % k, 18, ink(G if hot else K), "700")
        for i in range(5):
            f.chip(170 + i * 62, y + 40, 54, 44, B if i <= k else O, str(a[i]), 18)
        f.text(500, y + 32, "左 dp[0][%d] = %d" % (k, dp[0][k]), 16, INK)
        f.text(500, y + 62, "右 dp[%d][4] = %d" % (k + 1, dp[k + 1][4]), 16, INK)
        f.text(720, y + 46, "= %d" % (dp[0][k] + dp[k + 1][4]), 22, (ink(G) if hot else INK), "700")
        if hot:
            f.chip(880, y + 40, 70, 34, G, "最小", 15, bold=True)
    f.text(32, 540, "dp[0][4] = 18 + 15 = 33。蓝色是左段,橙色是右段。", 17, INK, "700")
    return f.save()


def balloon():
    f = Fig("c6-04-balloon", "戳气球:枚举「最后一个被戳」的气球", "nums = 3 1 5 8,两端补上虚拟的 1。区间 (l, r) 表示开区间,l 和 r 本身不戳。", 590,
            "k 最后被戳时,它左右的邻居一定是 l 和 r,左右两段互不影响,于是可以拆成两个独立子问题。")
    a = [1, 3, 1, 5, 8, 1]
    for i, x in enumerate(a):
        kind = O if i == 3 else (B if i in (0, 5) else W)
        f.text(130 + i * 148, 136, "下标 %d" % i, 14, SUB, anchor="middle")
        f.chip(130 + i * 148, 180, 100, 60, kind, str(x), 24, bold=kind != W)
    f.text(130, 268, "l", 18, ink(B), "700", "middle")
    f.text(130 + 3 * 148, 268, "k", 18, ink(O), "700", "middle")
    f.text(130 + 5 * 148, 268, "r", 18, ink(B), "700", "middle")
    f.path("M130 285C130 330 574 330 574 288", ink(G))
    f.text(352, 346, "dp[0][3]:只戳 3 1 5 之间的 3、1", 15, ink(G), "700", "middle")
    f.path("M574 285C574 330 870 330 870 288", ink(P))
    f.text(722, 346, "dp[3][5]:只戳 8", 15, ink(P), "700", "middle")
    f.rect(32, 420, 936, 90, O)
    f.text(48, 452, "dp[l][r] = max( dp[l][k] + dp[k][r] + a[l] × a[k] × a[r] )", 18, INK, mono=True)
    f.text(48, 486, "此例 k = 3:最后戳 5,得 1 × 5 × 1 = 5,加上左右两段各自的最大值。", 16, INK)
    return f.save()


# ------------------------------------------------------------ 6.5
def party_tree():
    f = Fig("c6-05-party", "没有上司的舞会:每个结点两个状态", "7 个人快乐值都是 1。括号里是 (dp[u][0], dp[u][1]) = (不选 u, 选 u) 时子树的最大快乐值。", 600,
            "根 5:不选 = max(2,1) + max(2,1) = 4;选 = 1 + 2 + 2 = 5。答案 max(4, 5) = 5。")
    pos = {5: (500, 150), 4: (280, 280), 3: (720, 280), 6: (170, 410), 7: (390, 410), 1: (610, 410), 2: (830, 410)}
    val = {5: "(4, 5)", 4: "(2, 1)", 3: "(2, 1)", 6: "(0, 1)", 7: "(0, 1)", 1: "(0, 1)", 2: "(0, 1)"}
    edges = [(5, 4), (5, 3), (4, 6), (4, 7), (3, 1), (3, 2)]
    for a, b in edges:
        f.arrow(pos[a][0], pos[a][1] + 28, pos[b][0], pos[b][1] - 30, GREY)
    for u, (x, y) in pos.items():
        kind = O if u == 5 else (B if u in (3, 4) else G)
        f.chip(x, y, 120, 56, kind, "人 %d\n%s" % (u, val[u]), 16, bold=True)
    f.text(32, 530, "叶子:不选 0,选 1。 内部结点:不选时孩子可选可不选,选时孩子必须不选。", 16, INK)
    return f.save()


def tree_order():
    f = Fig("c6-05-order", "树形 DP 的计算顺序:后序", "先递归到叶子,回溯时才计算 dp[u];此时 u 的所有孩子都已经算完。", 580,
            "编号是 dp 被算出的先后顺序。dfs(u) 里先 dfs 每个孩子,再用孩子的结果更新 dp[u]。")
    pos = {5: (500, 150), 4: (280, 270), 3: (720, 270), 6: (170, 390), 7: (390, 390), 1: (610, 390), 2: (830, 390)}
    order = {6: 1, 7: 2, 4: 3, 1: 4, 2: 5, 3: 6, 5: 7}
    edges = [(5, 4), (5, 3), (4, 6), (4, 7), (3, 1), (3, 2)]
    for a, b in edges:
        f.arrow(pos[b][0], pos[b][1] - 30, pos[a][0], pos[a][1] + 28, ink(G))
    for u, (x, y) in pos.items():
        f.chip(x, y, 110, 52, O if u == 5 else W, "人 %d" % u, 17)
        f.chip(x + 62, y - 26, 40, 30, G, "%d" % order[u], 16, bold=True)
    f.text(32, 460, "箭头方向:孩子的结果传给父亲。", 16, ink(G), "700")
    f.text(32, 496, "对应代码:for (int v : son[u]) { dfs(v); dp[u][..] += ... }", 16, INK, mono=True)
    return f.save()


def tree_knap():
    f = Fig("c6-05-knap", "树上背包:把孩子的表合并进父亲", "dp[u][j] = 在 u 的子树里选 j 个点(必须含 u)的最大学分。合并孩子 v 的方式和分组背包一样。", 600,
            "j 倒序枚举,k 是分给 v 的名额(至少 1,选了 v 才能选 v 下面的点);所有合并加起来总体 O(n²)。")
    f.text(60, 128, "合并前 dp[u]", 18, ink(B), "700")
    f.text(380, 128, "孩子 dp[v]", 18, ink(G), "700")
    f.text(700, 128, "合并后 dp[u]", 18, ink(O), "700")
    t1 = [("j=1", "2")]
    t2 = [("k=1", "3"), ("k=2", "5")]
    t3 = [("j=1", "2"), ("j=2", "5"), ("j=3", "7")]
    for i, (a, b) in enumerate(t1):
        f.chip(100, 190 + i * 62, 70, 48, K, a, 16, bold=True); f.chip(180, 190 + i * 62, 90, 48, W, b, 21, bold=True)
    for i, (a, b) in enumerate(t2):
        f.chip(420, 190 + i * 62, 70, 48, K, a, 16, bold=True); f.chip(500, 190 + i * 62, 90, 48, W, b, 21, bold=True)
    for i, (a, b) in enumerate(t3):
        f.chip(740, 190 + i * 62, 70, 48, K, a, 16, bold=True); f.chip(820, 190 + i * 62, 90, 48, O, b, 21, bold=True)
    f.arrow(290, 214, 330, 214, GREY); f.arrow(610, 214, 650, 214, GREY)
    f.rect(32, 400, 936, 130, G)
    f.text(48, 434, "u 的学分 2,v 的学分 3,v 的孩子学分 2(选它必须先选 v)。", 16, INK)
    f.text(48, 466, "dp[u][2] = dp[u][1] + dp[v][1] = 2 + 3 = 5", 17, INK, mono=True)
    f.text(48, 498, "dp[u][3] = dp[u][1] + dp[v][2] = 2 + 5 = 7", 17, INK, mono=True)
    return f.save()



# ------------------------------------------------------------ 6.6
def mask_basics():
    f = Fig("c6-06-mask", "用一个整数表示集合", "n 个元素的集合 {0, 2, 3} 对应二进制 01101:第 i 位为 1 表示 i 在集合里。", 600,
            "n 个元素共有 2^n 个集合,mask 从 0 到 2^n - 1 恰好各出现一次,正好作为 DP 的下标。")
    bits = [1, 0, 1, 1, 0]
    for i in range(5):
        x = 780 - i * 120
        f.text(x, 140, "第 %d 位" % i, 15, SUB, anchor="middle")
        f.chip(x, 190, 90, 56, O if bits[i] else W, str(bits[i]), 26, bold=bits[i] == 1)
        f.text(x, 236, "元素 %d" % i, 14, ink(O) if bits[i] else SUB, anchor="middle")
    f.text(60, 196, "mask =", 20, INK, "700")
    f.text(60, 226, "(十进制 13)", 14, SUB)
    ops = [("i 是否在集合里", "mask >> i & 1", B), ("加入元素 i", "mask | (1 << i)", G),
           ("删除元素 i", "mask & ~(1 << i)", R), ("全集 / 补集", "full = (1<<n)-1;  full ^ mask", P),
           ("元素个数", "__builtin_popcount(mask)", O), ("枚举非空子集", "for (s = mask; s; s = (s-1) & mask)", K)]
    for i, (name, code, kind) in enumerate(ops):
        x = 32 + (i % 2) * 476
        y = 290 + (i // 2) * 82
        f.rect(x, y, 460, 70, kind)
        f.text(x + 14, y + 28, name, 17, ink(kind), "700")
        f.text(x + 14, y + 56, code, 15, INK, mono=True, maxw=430)
    return f.save()


def tsp_states():
    INF = 10 ** 9
    d = [[0, 10, 15, 20], [10, 0, 35, 25], [15, 35, 0, 30], [20, 25, 30, 0]]
    n = 4
    dp = [[INF] * n for _ in range(1 << n)]
    dp[1][0] = 0
    for mask in range(1 << n):
        for i in range(n):
            if dp[mask][i] >= INF:
                continue
            for j in range(n):
                if not mask >> j & 1:
                    dp[mask | 1 << j][j] = min(dp[mask | 1 << j][j], dp[mask][i] + d[i][j])
    f = Fig("c6-06-tsp", "TSP 的状态:dp[mask][i]", "mask 是已访问的城市集合,i 是当前所在城市。4 个城市,从 0 出发。", 690,
            "距离矩阵 d 的四行:{0,10,15,20}  {10,0,35,25}  {15,35,0,30}  {20,25,30,0}。")
    layers = [[1], [3, 5, 9], [7, 11, 13], [15]]
    names = ["已访问 1 个", "已访问 2 个", "已访问 3 个", "已访问 4 个"]
    pos = {}
    for c, masks in enumerate(layers):
        x = 110 + c * 260
        f.text(x, 120, names[c], 16, SUB, "700", "middle")
        k = 0
        for m in masks:
            for i in range(n):
                if m >> i & 1 and dp[m][i] < INF:
                    y = 170 + k * 68
                    pos[(m, i)] = (x, y)
                    label = format(m, "04b") + " @" + str(i)
                    f.chip(x, y, 150, 50, [B, G, O, P][c], "%s\n= %d" % (label, dp[m][i]), 14, mono=False)
                    k += 1
    for (m, i), (x, y) in pos.items():
        for j in range(n):
            if not m >> j & 1 and (m | 1 << j, j) in pos and dp[m][i] + d[i][j] == dp[m | 1 << j][j]:
                x2, y2 = pos[(m | 1 << j, j)]
                f.arrow(x + 76, y, x2 - 78, y2, GREY)
    best = min(dp[15][i] + d[i][0] for i in range(1, n))
    f.text(32, 612, "只画出了「真正取到最小值」的转移。", 16, INK)
    f.text(32, 644, "最后一层再加回到 0 的路程:70+10 = 80,65+15 = 80,75+20 = 95,取最小得 %d。" % best, 16, INK, "700")
    return f.save()


def domino_columns():
    f = Fig("c6-06-domino", "铺骨牌:逐列转移,s 和 t 都是行集合", "n = 4 行。s = 从左边伸进本列的横牌所占的行,t = 本列伸向右边的横牌所占的行。", 560,
            "本列剩下的空格只能放竖牌,所以每一段连续空格的长度必须是偶数;s 与 t 还不能重叠。")
    cw, ch = 76, 54
    for k, (title, kind, s_rows, t_rows, ok) in enumerate([
            ("合法:s = {0},t = {3}", G, [0], [3], True), ("不合法:s = {0},t = {}", R, [0], [], False)]):
        x0 = 60 + k * 470
        f.text(x0, 130, title, 18, ink(kind), "700")
        for c, name in enumerate(["第 i-1 列", "第 i 列", "第 i+1 列"]):
            f.text(x0 + c * cw + cw / 2, 164, name, 13, SUB, anchor="middle")
        for r in range(4):
            for c in range(3):
                f.rect(x0 + c * cw, 176 + r * ch, cw, ch, K, r=4, opacity="1")
        for r in s_rows:
            f.rect(x0 + 4, 176 + r * ch + 6, cw * 2 - 8, ch - 12, B, r=10)
            f.text(x0 + cw, 176 + r * ch + 34, "横牌 s", 14, ink(B), "700", "middle")
        for r in t_rows:
            f.rect(x0 + cw + 4, 176 + r * ch + 6, cw * 2 - 8, ch - 12, O, r=10)
            f.text(x0 + cw * 2, 176 + r * ch + 34, "横牌 t", 14, ink(O), "700", "middle")
        if ok:
            f.rect(x0 + cw + 6, 176 + 1 * ch + 4, cw - 12, ch * 2 - 8, G, r=10)
            f.text(x0 + cw * 1.5, 176 + 2 * ch + 6, "竖牌", 14, ink(G), "700", "middle")
            f.text(x0, 440, "空格 = 行 1、2,长度 2(偶数),", 16, INK)
            f.text(x0, 468, "刚好放一张竖牌。", 16, INK)
        else:
            for r in (1, 2, 3):
                f.text(x0 + cw * 1.5, 176 + r * ch + 34, "?", 20, ink(R), "700", "middle")
            f.text(x0, 440, "空格 = 行 1、2、3,长度 3(奇数),", 16, INK)
            f.text(x0, 468, "竖牌凑不齐,这个转移不成立。", 16, ink(R), "700")
    return f.save()


# ------------------------------------------------------------ 6.7
def digit_tree():
    f = Fig("c6-07-tree", "数位 DP 的搜索树:n = 253", "从高位到低位逐位填数。只有「贴着上界」的那一条链需要继续展开,其余分支都是自由的。", 560,
            "自由分支的结果只取决于「还剩几位、上一位是什么」,可以直接查 memo;整棵树只有 3 层有效展开。")
    levels = [("百位", [("0 ~ 1", False), ("2", True)]), ("十位", [("0 ~ 4", False), ("5", True)]), ("个位", [("0 ~ 2", False), ("3", True)])]
    tx = 480
    for i, (name, opts) in enumerate(levels):
        y = 150 + i * 130
        f.text(40, y + 6, name, 19, INK, "700")
        free, tight = opts
        f.chip(tx - 150, y, 150, 52, B, free[0], 19, bold=True)
        f.chip(tx + 50, y, 90, 52, O, tight[0], 22, bold=True)
        f.text(tx - 150, y - 38, "自由(limit = 否)", 13, ink(B), anchor="middle")
        f.text(tx + 50, y - 38, "贴上界(limit = 是)", 13, ink(O), anchor="middle")
        if i < 2:
            f.arrow(tx + 50, y + 28, tx + 50, y + 78, ink(O))
    notes = ["自由:后两位任意,直接 memo[2][...]", "自由:后一位任意,直接 memo[1][...]", "自由:后面没有位了,直接计 1"]
    for i, t in enumerate(notes):
        f.text(640, 156 + i * 130, t, 15, INK, maxw=330)
    f.text(640, 186, "贴上界:继续展开十位", 15, ink(O), "700")
    f.text(640, 316, "贴上界:继续展开个位", 15, ink(O), "700")
    f.text(640, 446, "贴上界:253 本身,结束", 15, ink(O), "700")
    return f.save()


def digit_state():
    f = Fig("c6-07-state", "数位 DP 的状态:pos、limit、lead", "n = 253 时,几个前缀对应的 limit 与 lead。", 600,
            "limit 一旦变成否就不会再变回来;lead 一旦变成否也一样。memo 只保存 limit 为否(且 lead 为否)的状态。")
    heads = ["已填前缀", "limit", "lead", "含义"]
    xs = [60, 300, 430, 560]
    for h, x in zip(heads, xs):
        f.text(x, 130, h, 17, SUB, "700")
    rows = [("2 5 3", "是", "否", "每一位都等于上界对应位:已经填满,只此一个数", O),
            ("2 5 _", "是", "否", "前两位都贴着 2、5:下一位最大只能到 3", O),
            ("2 4 _", "否", "否", "十位 4 < 5,已经比 253 小:下一位可以填 0~9", B),
            ("1 _ _", "否", "否", "百位 1 < 2:后两位随便填,可以查 memo", B),
            ("0 0 7", "否", "是→否", "前两位是前导零(lead = 是),填 7 之后 lead 变成否", G)]
    for i, (pre, lim, lead, note, kind) in enumerate(rows):
        y = 164 + i * 64
        f.rect(32, y - 8, 936, 56, kind)
        f.text(60, y + 24, pre, 20, INK, "700", mono=True)
        f.text(300, y + 24, lim, 18, ink(kind), "700")
        f.text(430, y + 24, lead, 18, ink(kind), "700")
        f.text(560, y + 24, note, 15, INK, maxw=396)
    f.rect(32, 496, 936, 40, K)
    f.text(48, 523, "pos:还剩几位;pre:上一位数字(按题目需要);limit:是否贴着上界;lead:是否仍是前导零", 15, INK, maxw=900)
    return f.save()


def build_all():
    out = []
    for fn in (fib_tree, design_steps, grid_dp, rolling, lis_n2, lis_tail, lcs_table, edit_table,
               knap_table, knap_order, knap_split, interval_order, interval_split, balloon, party_tree, tree_order, tree_knap,
               mask_basics, tsp_states, domino_columns, digit_tree, digit_state):
        out += fn()
    return out
