"""第 3 章（搜索）用到的配图。图名前缀 c3-。"""
import heapq
import math
from collections import deque

from svglib import Fig, GREY, SUB, INK, PALETTE


# ---------- 小工具 ----------
def line(f, x1, y1, x2, y2, color=GREY, w=2, dash=False):
    d = ' stroke-dasharray="6 5"' if dash else ""
    f.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}"{d}/>')


def circle(f, cx, cy, r, kind="white", w=2, fill=None, dash=False, opacity=None):
    bg, ink = PALETTE[kind]
    d = ' stroke-dasharray="7 5"' if dash else ""
    op = f' fill-opacity="{opacity}"' if opacity is not None else ""
    f.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill or bg}"{op} stroke="{ink}" stroke-width="{w}"{d}/>')


def cell(f, x, y, s, kind, label="", size=18, bold=False):
    f.rect(x, y, s, s, kind, r=4, opacity=".5")
    if label != "":
        f.text(x + s / 2, y + s / 2 + size * 0.35, label, size, PALETTE[kind][1] if bold else INK,
               "700" if bold else None, "middle")


# ---------- 3.1 DFS 与回溯 ----------
def perm_tree():
    f = Fig("c3-perm-tree", "全排列的递归树（n = 3）", "每下一层多选一个数；走到第 3 层就是一个完整排列。", 520,
            "绿色是第一条走到底的路径；叶子返回时 pop_back 撤销，回到父节点再试下一个数。")
    ys = [130, 235, 340, 445]
    xs1 = [190, 500, 810]
    pos = {(): (500, ys[0])}
    cols = {1: 230, 2: 500, 3: 770}
    for a in (1, 2, 3):
        pos[(a,)] = (cols[a], ys[1])
        others = [b for b in (1, 2, 3) if b != a]
        for k, b in enumerate(others):
            x2 = cols[a] + (-65 if k == 0 else 65)
            pos[(a, b)] = (x2, ys[2])
            c = [x for x in (1, 2, 3) if x not in (a, b)][0]
            pos[(a, b, c)] = (x2, ys[3])
    green = {(), (1,), (1, 2), (1, 2, 3)}
    for key, (x, y) in pos.items():
        if len(key) == 0:
            continue
        px, py = pos[key[:-1]]
        on = key in green
        line(f, px, py + 18, x, y - 18, PALETTE["green"][1] if on else GREY, 4 if on else 2)
    for key, (x, y) in pos.items():
        label = "[ ]" if not key else "".join(map(str, key)) if len(key) == 3 else "[" + ",".join(map(str, key)) + "]"
        kind = "green" if key in green else ("orange" if len(key) == 3 else "white")
        f.chip(x, y, 92, 36, kind, label, 16, bold=key in green)
    for i, t in enumerate(["第 0 层：还没选", "第 1 层", "第 2 层", "第 3 层：排列"]):
        pass
    f.text(32, 135, "深度 0", 15, SUB)
    f.text(32, 240, "深度 1", 15, SUB)
    f.text(32, 345, "深度 2", 15, SUB)
    f.text(32, 450, "深度 3", 15, SUB)
    return f.save()


def backtrack_steps():
    f = Fig("c3-backtrack-steps", "回溯的三步：选择、递归、撤销", "追踪 path 和 used 在前 6 步里的变化。", 540,
            "橙色行是撤销。撤销与选择严格对称，path 和 used 才能回到原样，才有机会试 [1, 3]。")
    heads = [("步骤", 32, 90), ("动作", 130, 220), ("path", 360, 260), ("used（已选的数）", 640, 330)]
    for t, x, w in heads:
        f.rect(x, 105, w, 40, "grey", r=6)
        f.text(x + 12, 132, t, 17, PALETTE["grey"][1], "700")
    rows = [
        ("1", "选 1，进入下一层", "[1]", "{1}", "blue"),
        ("2", "选 2，进入下一层", "[1, 2]", "{1, 2}", "blue"),
        ("3", "选 3，长度 = 3，输出", "[1, 2, 3]", "{1, 2, 3}", "green"),
        ("4", "撤销 3，回到上一层", "[1, 2]", "{1, 2}", "orange"),
        ("5", "撤销 2，回到上一层", "[1]", "{1}", "orange"),
        ("6", "换一个数：选 3", "[1, 3]", "{1, 3}", "blue"),
    ]
    for i, (s, act, path, used, kind) in enumerate(rows):
        y = 155 + i * 58
        for (t, x, w), val in zip(heads, (s, act, path, used)):
            f.rect(x, y, w, 48, kind, r=6)
            f.text(x + 12, y + 31, val, 17, INK, mono=(t in ("path", "used（已选的数）")))
    return f.save()


def subset_tree():
    f = Fig("c3-subset-tree", "子集的搜索树：下一个数只能往后选", "n = 3。每个节点本身就是一个答案。", 500,
            "规定下标递增后，{1,2} 不会再以 {2,1} 的形式出现，共 2³ = 8 个节点。")
    P = {"{ }": (500, 135), "{1}": (230, 235), "{2}": (500, 235), "{3}": (770, 235),
         "{1,2}": (140, 335), "{1,3}": (320, 335), "{2,3}": (500, 335), "{1,2,3}": (140, 435)}
    edges = [("{ }", "{1}"), ("{ }", "{2}"), ("{ }", "{3}"), ("{1}", "{1,2}"), ("{1}", "{1,3}"),
             ("{2}", "{2,3}"), ("{1,2}", "{1,2,3}")]
    for a, b in edges:
        line(f, P[a][0], P[a][1] + 18, P[b][0], P[b][1] - 18)
    for k, (x, y) in P.items():
        kind = "orange" if k in ("{1,2}", "{1,3}", "{2,3}") else "blue"
        f.chip(x, y, 104, 36, kind, k, 16, mono=True)
    f.rect(620, 300, 350, 150, "green")
    f.text(636, 332, "组合 C(3,2)", 19, PALETTE["green"][1], "700")
    f.text(636, 362, "只收深度为 2 的节点（橙色）：", 16)
    f.text(636, 390, "{1,2}  {1,3}  {2,3}", 17, INK, "700", mono=True)
    f.text(636, 420, "到了深度 2 就不用再往下走了。", 16)
    return f.save()


def nqueens():
    f = Fig("c3-nqueens", "N 皇后：逐行放置，三个数组判冲突", "左：一个皇后攻击到的格子。右：4 皇后的第一个解。", 520,
            "同列 c 相同；主对角线 r − c 相同；副对角线 r + c 相同。")
    S = 70

    def board(x0, y0, queens, attacked=()):
        for r in range(4):
            for c in range(4):
                base = "grey" if (r + c) % 2 == 0 else "white"
                if (r, c) in attacked:
                    base = "red"
                f.rect(x0 + c * S, y0 + r * S, S, S, base, r=0, opacity=".4")
        for r, c in queens:
            circle(f, x0 + c * S + S / 2, y0 + r * S + S / 2, 24, "blue", fill="#eaf2ff", w=3)
            f.text(x0 + c * S + S / 2, y0 + r * S + S / 2 + 8, "Q", 22, PALETTE["blue"][1], "700", "middle")
        for i in range(4):
            f.text(x0 - 14, y0 + i * S + S / 2 + 5, str(i), 14, SUB, anchor="middle")
            f.text(x0 + i * S + S / 2, y0 - 8, str(i), 14, SUB, anchor="middle")

    q = (0, 1)
    att = set()
    for r in range(4):
        for c in range(4):
            if (r, c) != q and (c == q[1] or r - c == q[0] - q[1] or r + c == q[0] + q[1] or r == q[0]):
                att.add((r, c))
    board(70, 130, [q], att)
    f.text(70, 440, "(0,1) 的皇后攻击红色格子：", 16)
    f.text(70, 468, "同列 c = 1；主对角线 r − c = −1；副对角线 r + c = 1", 15, SUB)
    sol = [(0, 1), (1, 3), (2, 0), (3, 2)]
    board(560, 130, sol)
    f.text(560, 440, "解：pos = [1, 3, 0, 2]（每行皇后所在的列）", 16)
    f.text(560, 468, "每行恰好一个，所以搜索深度就是行号。", 15, SUB)
    return f.save()


# ---------- 3.2 BFS ----------
MAZE = ["S.#..", ".##.#", "....#", "#.##.", "...T."]


def _bfs_maze():
    R, C = len(MAZE), len(MAZE[0])
    dist = [[-1] * C for _ in range(R)]
    frm = {}
    q = deque()
    for i in range(R):
        for j in range(C):
            if MAZE[i][j] == "S":
                dist[i][j] = 0
                q.append((i, j))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < R and 0 <= ny < C and MAZE[nx][ny] != "#" and dist[nx][ny] == -1:
                dist[nx][ny] = dist[x][y] + 1
                frm[(nx, ny)] = (x, y)
                q.append((nx, ny))
    return dist, frm


def bfs_layers():
    dist, frm = _bfs_maze()
    f = Fig("c3-bfs-layers", "BFS 一层一层向外扩", "格子里的数字是从 S 出发的最少步数，同一步数的格子颜色相同。", 580,
            "第一次到达某格时的步数就是它的最短距离，所以入队时就可以标记 dist。")
    S = 80
    x0, y0 = 50, 120
    layer_kind = ["green", "blue", "purple", "orange", "grey", "blue", "purple", "green", "orange"]
    path = set()
    p = (4, 3)
    while p in frm:
        path.add(p)
        p = frm[p]
    path.add(p)
    for i in range(5):
        for j in range(5):
            x, y = x0 + j * S, y0 + i * S
            ch = MAZE[i][j]
            if ch == "#":
                f.rect(x, y, S, S, "grey", r=4, fill="#66758d")
            else:
                d = dist[i][j]
                label = "S" if ch == "S" else "T" if ch == "T" else str(d)
                cell(f, x, y, S, layer_kind[d % len(layer_kind)] if d >= 0 else "white", label, 22, bold=(ch in "ST" or (i, j) in path))
                if (i, j) in path:
                    f.rect(x + 3, y + 3, S - 6, S - 6, "red", r=4, fill="none", opacity="1")
    f.rect(500, 120, 470, 400, "grey")
    f.text(520, 152, "队列里发生了什么", 19, PALETTE["grey"][1], "700")
    layers = {}
    for i in range(5):
        for j in range(5):
            if dist[i][j] >= 0:
                layers.setdefault(dist[i][j], []).append((i, j))
    for d in range(0, 4):
        cells = " ".join(f"({a},{b})" for a, b in layers[d])
        f.text(520, 190 + d * 48, f"第 {d} 步：{cells}", 15 if len(cells) < 36 else 14, INK, mono=True, maxw=440)
    f.text(520, 190 + 4 * 48, f"……第 {dist[4][3]} 步到达 T", 16, SUB)
    f.text(520, 440, "红框：从 T 沿 from[] 倒着走回 S，", 16)
    f.text(520, 468, "再反转，就是一条最短路径。", 16)
    f.text(520, 496, "队列中任何时刻只有相邻两层的格子。", 16, PALETTE["blue"][1], "700")
    return f.save()


def multi_bfs():
    f = Fig("c3-multi-bfs", "多源 BFS：所有源点同时出发", "求每个格子到最近的 0 的距离。", 500,
            "等价于加一个超级源点连向所有 0，只扩展一次，复杂度仍是 O(格子数)。")
    a = [[0, 0, 0], [0, 1, 0], [1, 1, 1]]
    dist = [[0, 0, 0], [0, 1, 0], [1, 2, 1]]
    S = 90
    for (x0, title, data, mode) in ((70, "初始：所有 0 同时入队", a, "src"), (560, "结果：到最近 0 的距离", dist, "res")):
        f.text(x0, 130, title, 18, PALETTE["blue"][1], "700")
        for i in range(3):
            for j in range(3):
                v = data[i][j]
                if mode == "src":
                    kind = "green" if v == 0 else "white"
                else:
                    kind = ["green", "blue", "orange"][v]
                cell(f, x0 + j * S, 150 + i * S, S, kind, str(v), 28, bold=True)
    f.arrow(375, 285, 545, 285, PALETTE["blue"][1])
    f.text(460, 265, "一层层扩", 16, SUB, anchor="middle")
    f.text(70, 450, "绿色是距离 0 的源点；蓝色走 1 步到达；橙色走 2 步到达。", 16)
    return f.save()


# ---------- 3.3 剪枝 ----------
def prune_array():
    f = Fig("c3-prune-array", "组合总和 II：排序后的两种剪枝", "候选数排序为 1 1 2 5 6 7 10，目标 8，在第一层从左到右尝试。", 505,
            "排序让重复的数相邻、让大数集中在右边，这两个剪枝都依赖它。")
    vals = [1, 1, 2, 5, 6, 7, 10]
    notes = [("试", "green"), ("跳过\n与前一个相同", "orange"), ("试", "green"), ("试", "green"),
             ("试", "green"), ("试", "green"), ("10 > 8\n停止", "red")]
    for i, (v, (n, kind)) in enumerate(zip(vals, notes)):
        cx = 100 + i * 130
        f.chip(cx, 170, 90, 56, kind, str(v), 24, bold=True)
        f.chip(cx, 260, 110, 62, "white", n, 15)
        f.arrow(cx, 200, cx, 227, GREY)
    f.rect(32, 330, 470, 110, "orange")
    f.text(48, 362, "去重剪枝", 19, PALETTE["orange"][1], "700")
    f.text(48, 392, "i > start 且 a[i] == a[i-1]：", 16, mono=True)
    f.text(48, 420, "同一层里，相同的数只让第一个出场。", 16)
    f.rect(520, 330, 450, 110, "red")
    f.text(536, 362, "可行性剪枝", 19, PALETTE["red"][1], "700")
    f.text(536, 392, "a[i] > rest 时 break：", 16, mono=True)
    f.text(536, 420, "排序后右边更大，整层都不用再看。", 16)
    return f.save()


def prune_tree():
    f = Fig("c3-prune-tree", "最优性剪枝：整棵子树被一刀切掉", "0-1 背包的 DFS：上界追不上当前最优，就不再往下搜。", 540,
            "上界用“可拆分背包”估计：把剩余容量按性价比从高到低装，最后一件按比例取。")
    P = {"r": (500, 130), "a": (260, 230), "b": (740, 230), "a1": (140, 330), "a2": (380, 330),
         "b1": (620, 330), "b2": (860, 330)}
    for a, b in (("r", "a"), ("r", "b"), ("a", "a1"), ("a", "a2"), ("b", "b1"), ("b", "b2")):
        line(f, P[a][0], P[a][1] + 18, P[b][0], P[b][1] - 18)
    f.chip(*P["r"], 150, 36, "blue", "拿 / 不拿 第 1 件", 15)
    f.chip(*P["a"], 150, 36, "blue", "拿，value=60", 15)
    f.chip(*P["b"], 190, 36, "red", "不拿，上界 58 ≤ 最优 61", 14)
    f.chip(*P["a1"], 120, 36, "green", "继续搜", 15)
    f.chip(*P["a2"], 120, 36, "green", "继续搜", 15)
    for k in ("b1", "b2"):
        f.chip(*P[k], 120, 36, "grey", "不再展开", 15)
    # 被切掉的子树
    f.text(500, 410, "红色节点：上界 ≤ 当前最优，整棵子树（灰色）不可能更好，直接返回。", 17, PALETTE["red"][1], "700", "middle")
    f.text(500, 446, "实测 26 件物品：无剪枝约 1455 万个节点，有剪枝只要 109 个。", 17, INK, None, "middle")
    return f.save()


# ---------- 3.4 记忆化搜索 ----------
def memo_fib():
    f = Fig("c3-memo-fib", "斐波那契：重复子问题与记忆化", "左：fib(5) 的递归树，共 15 次调用。右：记忆化后 6 个状态各算一次。", 540,
            "橙色是被重复计算的状态：fib(3) 算了 2 次，fib(2) 算了 3 次。")
    leaves = [0]

    def build(n):
        if n <= 1:
            node = {"n": n, "ch": [], "slot": leaves[0]}
            leaves[0] += 1
            return node
        ch = [build(n - 1), build(n - 2)]
        return {"n": n, "ch": ch, "slot": sum(c["slot"] for c in ch) / 2}

    root = build(5)
    L = leaves[0]
    W, X0 = 520, 30
    cnt = {}

    def count(nd):
        cnt[nd["n"]] = cnt.get(nd["n"], 0) + 1
        for c in nd["ch"]:
            count(c)

    count(root)

    def draw(nd, depth, parent=None):
        x = X0 + (nd["slot"] + 0.5) * W / L
        y = 140 + depth * 72
        if parent:
            line(f, parent[0], parent[1] + 15, x, y - 15)
        kind = "orange" if cnt[nd["n"]] > 1 and nd["n"] >= 2 else ("grey" if nd["n"] <= 1 else "blue")
        pts = [(x, y, nd["n"], kind)]
        for c in nd["ch"]:
            pts += draw(c, depth + 1, (x, y))
        return pts

    pts = draw(root, 0)
    for x, y, n, kind in pts:
        f.chip(x, y, 54, 30, kind, f"f({n})", 14)
    f.text(32, 500, "15 次调用：f(0)×3、f(1)×5、f(2)×3、f(3)×2、f(4)×1、f(5)×1", 15, SUB)
    # 右：记忆化 DAG（链）
    f.rect(590, 105, 385, 380, "green")
    f.text(606, 137, "记忆化后：每个状态只算一次", 18, PALETTE["green"][1], "700")
    xs = [645 + i * 64 for i in range(6)]
    for i, n in enumerate([5, 4, 3, 2, 1, 0]):
        f.chip(xs[i], 280, 46, 30, "orange" if n in (2, 3) else ("grey" if n <= 1 else "blue"), f"f({n})", 13)
    for i in range(5):                                  # f(n) 依赖 f(n-1)：下方实线弧
        a, b = xs[i], xs[i + 1]
        f.path(f"M{a} 297Q{(a + b) / 2} 340 {b} 297", PALETTE["green"][1])
    for i in range(4):                                  # f(n) 依赖 f(n-2)：上方虚线弧
        a, b = xs[i], xs[i + 2]
        f.path(f"M{a} 263Q{(a + b) / 2} 190 {b} 263", PALETTE["green"][1], dash=True)
    f.text(606, 400, "实线：f(n) 依赖 f(n−1)", 15)
    f.text(606, 426, "虚线：f(n) 依赖 f(n−2)", 15)
    f.text(606, 458, "fib(40)：3.3 亿次调用 → 79 次", 16, PALETTE["green"][1], "700")
    return f.save()


def memo_state():
    f = Fig("c3-memo-state", "记忆化只计算“用得到”的状态", "背包例题 dfs(i, c) 的备忘表：4 件物品，容量 8。", 545,
            "格子里是 dfs(i, c) 的值；“·”表示这个状态从未被访问。")
    n, cap = 4, 8
    w, v = [2, 3, 4, 5], [3, 4, 5, 8]
    memo = {}

    def dfs(i, c):
        if i == n:
            return 0
        if (i, c) in memo:
            return memo[(i, c)]
        r = dfs(i + 1, c)
        if c >= w[i]:
            r = max(r, dfs(i + 1, c - w[i]) + v[i])
        memo[(i, c)] = r
        return r

    ans = dfs(0, cap)
    S = 62
    x0, y0 = 120, 150
    f.text(x0 - 90, y0 - 18, "i＼c", 15, SUB)
    for c in range(cap + 1):
        f.text(x0 + c * S + S / 2, y0 - 18, str(c), 15, SUB, anchor="middle")
    for i in range(n + 1):
        f.text(x0 - 50, y0 + i * 52 + 32, f"i={i}", 15, SUB)
        for c in range(cap + 1):
            x, y = x0 + c * S, y0 + i * 52
            if i == n:
                f.rect(x, y, S - 4, 46, "grey", r=4, opacity=".5")
                f.text(x + (S - 4) / 2, y + 30, "0", 16, SUB, anchor="middle")
            elif (i, c) in memo:
                hit = (i, c) == (0, cap)
                f.rect(x, y, S - 4, 46, "green" if hit else "blue", r=4, opacity=".6")
                f.text(x + (S - 4) / 2, y + 30, str(memo[(i, c)]), 18, INK, "700", "middle")
            else:
                f.rect(x, y, S - 4, 46, "white", r=4, opacity=".3")
                f.text(x + (S - 4) / 2, y + 30, "·", 18, GREY, anchor="middle")
    visited = len(memo)
    f.text(32, 450, f"共 {n * (cap + 1)} 个状态，实际只计算了 {visited} 个；答案 dfs(0, 8) = {ans}（绿色）。", 17, INK, "700")
    f.text(32, 478, "最后一行 i=4 是边界，直接返回 0，不进备忘表。", 15, SUB)
    return f.save()


# ---------- 3.5 0-1 BFS 与双向 BFS ----------
def bfs01_deque():
    f = Fig("c3-01bfs-deque", "0-1 BFS：用双端队列代替优先队列", "边权只有 0 和 1 时，队列里始终只有距离 d 和 d+1 两种值。", 470,
            "出队后松弛邻居：权 0 放队头（同层），权 1 放队尾（下一层）。")
    vals = [2, 2, 2, 3, 3, 3]
    x0 = 250
    for i, d in enumerate(vals):
        f.rect(x0 + i * 80, 230, 74, 56, "blue" if d == 2 else "orange", r=6)
        f.text(x0 + i * 80 + 37, 266, f"d={d}", 18, INK, "700", "middle")
    f.text(x0 - 20, 215, "队头", 15, SUB, anchor="end")
    f.text(x0 + 6 * 80 + 8, 215, "队尾", 15, SUB)
    f.arrow(x0 - 8, 258, x0 - 110, 258, PALETTE["grey"][1])
    f.text(x0 - 118, 300, "pop_front：取出当前最小的", 15, SUB)
    f.arrow(x0 - 110, 160, x0 + 30, 220, PALETTE["blue"][1])
    f.text(32, 150, "权 0：push_front（距离不变）", 16, PALETTE["blue"][1], "700")
    f.arrow(x0 + 6 * 80 + 100, 160, x0 + 6 * 80 - 20, 220, PALETTE["orange"][1])
    f.text(x0 + 6 * 80 - 20, 150, "权 1：push_back（距离 +1）", 16, PALETTE["orange"][1], "700")
    f.rect(32, 340, 936, 90, "grey")
    f.text(48, 372, "为什么对：每个点出队时距离最小，且队列从头到尾距离单调不降。", 17)
    f.text(48, 404, "每次松弛最多入队一次，总复杂度 O(V + E)，比 Dijkstra 少一个 log。", 17)
    return f.save()


def bidir():
    f = Fig("c3-bidir", "双向 BFS：两个小圆代替一个大圆", "状态数随半径指数增长，半径减半省得非常多。", 500,
            "八数码最难局面（31 步）实测：普通 BFS 出队 181440 个状态，双向 BFS 只有 12452 个。")
    f.rect(32, 105, 460, 330, "blue")
    f.text(48, 137, "单向 BFS", 19, PALETTE["blue"][1], "700")
    circle(f, 160, 300, 110, "blue", fill="#eaf2ff")
    f.text(160, 290, "S", 20, INK, "700", "middle")
    circle(f, 270, 300, 6, "red", fill="#a33a3a")
    f.text(278, 285, "T", 18, PALETTE["red"][1], "700")
    f.text(48, 425, "半径 d：约 b^d 个状态", 16, INK)
    f.rect(508, 105, 460, 330, "green")
    f.text(524, 137, "双向 BFS", 19, PALETTE["green"][1], "700")
    circle(f, 640, 300, 55, "green", fill="#e8f7f1")
    circle(f, 750, 300, 55, "green", fill="#e8f7f1")
    f.text(640, 308, "S", 20, INK, "700", "middle")
    f.text(750, 308, "T", 20, INK, "700", "middle")
    f.text(695, 240, "相遇", 15, SUB, anchor="middle")
    f.arrow(695, 246, 695, 290, GREY)
    f.text(524, 425, "两个半径 d/2：约 2·b^(d/2) 个状态", 16, INK)
    return f.save()


# ---------- 3.6 A* 与 IDA* ----------
ASTAR_MAP = [
    "..........",
    "..........",
    "....####..",
    "....#.....",
    "S...#....T",
    "....#.....",
    "....####..",
    "..........",
]


def _expanded(useH):
    R, C = len(ASTAR_MAP), len(ASTAR_MAP[0])
    s = t = None
    for i in range(R):
        for j in range(C):
            if ASTAR_MAP[i][j] == "S":
                s = (i, j)
            if ASTAR_MAP[i][j] == "T":
                t = (i, j)
    h = lambda x, y: abs(x - t[0]) + abs(y - t[1]) if useH else 0
    dist = [[10 ** 9] * C for _ in range(R)]
    dist[s[0]][s[1]] = 0
    pq = [(h(*s), s[0], s[1])]
    seen = []
    while pq:
        fv, x, y = heapq.heappop(pq)
        if fv > dist[x][y] + h(x, y):
            continue
        seen.append((x, y))
        if (x, y) == t:
            return seen, dist[x][y]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < R and 0 <= ny < C and ASTAR_MAP[nx][ny] != "#" and dist[x][y] + 1 < dist[nx][ny]:
                dist[nx][ny] = dist[x][y] + 1
                heapq.heappush(pq, (dist[nx][ny] + h(nx, ny), nx, ny))
    return seen, -1


def astar_grid():
    f = Fig("c3-astar", "A*：让搜索朝着终点的方向走", "有颜色的格子是被扩展（出队）的格子。同一张图，最短步数都是 15。", 595,
            "f = g + h：g 是已走步数，h 是到终点的估计（曼哈顿距离），堆按 f 从小到大取。")
    S = 40
    for x0, title, useH in ((40, "无启发（Dijkstra）", False), (540, "A*（h = 曼哈顿距离）", True)):
        seen, d = _expanded(useH)
        sset = set(seen)
        f.text(x0, 125, f"{title}：扩展 {len(seen)} 个格子", 18, PALETTE["blue"][1] if not useH else PALETTE["green"][1], "700")
        for i in range(8):
            for j in range(10):
                x, y = x0 + j * S, 145 + i * S
                ch = ASTAR_MAP[i][j]
                if ch == "#":
                    f.rect(x, y, S, S, "grey", r=2, fill="#66758d")
                elif ch in "ST":
                    cell(f, x, y, S, "red", ch, 18, bold=True)
                elif (i, j) in sset:
                    cell(f, x, y, S, "green" if useH else "blue", "", 14)
                else:
                    cell(f, x, y, S, "white", "", 14)
    f.text(40, 498, "两者都保证最优，但 A* 只扩展了更少的格子；", 16)
    f.text(40, 524, "h 越接近真实距离（又不高估），省得越多。", 16)
    return f.save()


GOALPOS = {1: (0, 0), 2: (0, 1), 3: (0, 2), 4: (1, 0), 5: (1, 1), 6: (1, 2), 7: (2, 0), 8: (2, 1)}


def _ida_rounds(s):
    board = [int(c) for c in s]

    def h():
        return sum(abs(i // 3 - GOALPOS[b][0]) + abs(i % 3 - GOALPOS[b][1]) for i, b in enumerate(board) if b)

    nodes = [0]

    def dfs(z, g, limit, last):
        nodes[0] += 1
        hv = h()
        if g + hv > limit:
            return g + hv
        if hv == 0:
            return -1
        nl = 10 ** 9
        for d, (dx, dy) in enumerate(((1, 0), (-1, 0), (0, 1), (0, -1))):
            if last != -1 and d == (last ^ 1):
                continue
            x, y = z // 3 + dx, z % 3 + dy
            if not (0 <= x < 3 and 0 <= y < 3):
                continue
            nz = x * 3 + y
            board[z], board[nz] = board[nz], board[z]
            r = dfs(nz, g + 1, limit, d)
            board[z], board[nz] = board[nz], board[z]
            if r == -1:
                return -1
            nl = min(nl, r)
        return nl

    z = board.index(0)
    limit = h()
    rounds = []
    while True:
        nodes[0] = 0
        r = dfs(z, 0, limit, -1)
        rounds.append((limit, nodes[0]))
        if r == -1:
            return rounds
        limit = r


def idastar_rounds():
    rounds = _ida_rounds("724506831")
    f = Fig("c3-idastar-rounds", "IDA*：逐轮放宽 f 的上限", "八数码起点 724506831。每一轮是一次受 f = g + h ≤ limit 约束的深度优先搜索。",
            210 + 52 * len(rounds),
            "搜不到就把上限放宽到“刚好超出的最小 f”，下一轮再来，内存只需要一条路径。")
    mx = max(n for _, n in rounds)
    for i, (lim, n) in enumerate(rounds):
        y = 115 + i * 52
        f.text(32, y + 28, f"第 {i + 1} 轮  limit = {lim}", 17, INK, "700")
        w = max(8, int(520 * math.log(n + 1) / math.log(mx + 1)))
        last = i == len(rounds) - 1
        f.rect(300, y, w, 38, "green" if last else "blue", r=6)
        f.text(300 + w + 12, y + 26, f"{n} 个节点" + ("  找到解" if last else ""), 16, INK)
    f.text(32, 135 + 52 * len(rounds), "条形长度按节点数取对数画；limit 就是当前轮的最优步数下界，找到解时它等于最少步数。", 15, SUB)
    return f.save()


# ---------- 3.7 舞蹈链 ----------
def dlx_matrix():
    f = Fig("c3-dlx-matrix", "精确覆盖：选出若干行，使每一列恰好有一个 1", "Knuth 论文中的小例子：6 个集合 A–F，覆盖元素 1–7。", 550,
            "解是 B、D、F：每一列的 1 恰好出现一次。")
    sets = {"A": {1, 4, 7}, "B": {1, 4}, "C": {4, 5, 7}, "D": {3, 5, 6}, "E": {2, 3, 6, 7}, "F": {2, 7}}
    S = 56
    x0, y0 = 150, 150
    f.text(x0 - 90, y0 - 20, "集合＼元素", 15, SUB)
    for c in range(1, 8):
        f.text(x0 + (c - 1) * S + S / 2, y0 - 20, str(c), 17, SUB, "700", "middle")
    for r, (name, st) in enumerate(sets.items()):
        pick = name in "BDF"
        f.text(x0 - 50, y0 + r * S + 34, name, 20, PALETTE["green"][1] if pick else INK, "700", "middle")
        for c in range(1, 8):
            x, y = x0 + (c - 1) * S, y0 + r * S
            on = c in st
            kind = ("green" if pick else "blue") if on else "white"
            f.rect(x, y, S - 4, S - 4, kind, r=4, opacity=".6" if on else ".25")
            if on:
                f.text(x + (S - 4) / 2, y + 34, "1", 20, INK, "700", "middle")
    f.rect(580, 130, 390, 330, "grey")
    f.text(596, 162, "搜索的思路", 19, PALETTE["grey"][1], "700")
    for i, t in enumerate(["1. 选 1 的个数最少的列（分支最少）", "2. 逐行试：选中该行，", "    删去它覆盖的所有列，", "    以及与它冲突的所有行",
                           "3. 列全部删完 = 找到解", "4. 失败就按相反顺序恢复，换下一行"]):
        f.text(596, 198 + i * 32, t, 16, INK)
    return f.save()


def dlx_remove():
    f = Fig("c3-dlx-remove", "舞蹈链的核心：删除与恢复只改两个指针", "双向链表删除一个结点后，被删结点自己仍记得原来的左右邻居。", 530,
            "cover 和 uncover 严格按相反顺序执行，链表就能原样跳回来。")

    def row(y, title, removed):
        f.text(32, y - 85, title, 18, PALETTE["blue"][1], "700")
        xs = [160, 500, 840]
        for x, n in zip(xs, "ABC"):
            f.chip(x, y, 110, 46, "orange" if (removed and n == "B") else "blue", n, 20, bold=True)
        if not removed:
            f.arrow(222, y - 8, 438, y - 8, PALETTE["blue"][1]); f.arrow(438, y + 8, 222, y + 8, PALETTE["blue"][1])
            f.arrow(562, y - 8, 778, y - 8, PALETTE["blue"][1]); f.arrow(778, y + 8, 562, y + 8, PALETTE["blue"][1])
        else:
            f.path("M215 " + str(y - 24) + "Q500 " + str(y - 90) + " 785 " + str(y - 24), PALETTE["green"][1])
            f.path("M785 " + str(y + 24) + "Q500 " + str(y + 90) + " 215 " + str(y + 24), PALETTE["green"][1])
            f.text(500, y - 66, "R[A] = C", 15, PALETTE["green"][1], "700", "middle")
            f.text(500, y + 80, "L[C] = A", 15, PALETTE["green"][1], "700", "middle")
            f.arrow(445, y - 6, 380, y - 6, PALETTE["orange"][1], dash=True)
            f.arrow(555, y + 6, 620, y + 6, PALETTE["orange"][1], dash=True)
            f.text(380, y + 32, "L[B] 仍是 A", 14, PALETTE["orange"][1], anchor="end")
            f.text(620, y + 32, "R[B] 仍是 C", 14, PALETTE["orange"][1])
    row(205, "删除前：A ⇄ B ⇄ C", False)
    row(405, "删除 B：A ⇄ C 直接相连，B 的指针（虚线）还指着 A 和 C", True)
    return f.save()


# ---------- 3.8 模拟退火与爬山 ----------
def _fx(x):
    return x * math.sin(5 * x) + 0.3 * x


def sa_landscape():
    f = Fig("c3-sa-landscape", "爬山会卡在局部最高点，退火能翻过山谷", "f(x) = x·sin(5x) + 0.3x，x ∈ [0, 10]。", 520,
            "爬山只接受更好的解；退火以概率 exp(Δ/T) 接受变差的解，所以有机会越过山谷。")
    X0, X1, Y0, Y1 = 60, 940, 130, 440
    lo, hi = min(_fx(i / 200) for i in range(2001)), max(_fx(i / 200) for i in range(2001))

    def px(x):
        return X0 + (X1 - X0) * x / 10

    def py(y):
        return Y1 - (Y1 - Y0) * (y - lo) / (hi - lo)

    pts = " ".join(f"{px(i / 100):.1f},{py(_fx(i / 100)):.1f}" for i in range(1001))
    line(f, X0, Y1, X1, Y1, GREY, 1)
    f.parts.append(f'<polyline points="{pts}" fill="none" stroke="{PALETTE["blue"][1]}" stroke-width="2.5"/>')
    # 局部最高：x≈4.5 附近；全局最高 9.1163
    best = max((i / 1000 for i in range(10001)), key=_fx)
    loc = max((i / 1000 for i in range(3500, 5000)), key=_fx)
    x_start = 3.4
    circle(f, px(best), py(_fx(best)), 7, "green", fill="#176951")
    f.text(px(best) + 12, py(_fx(best)) + 5, "全局最大", 15, PALETTE["green"][1], "700")
    circle(f, px(loc), py(_fx(loc)), 7, "red", fill="#a33a3a")
    f.text(px(loc) - 16, py(_fx(loc)) - 26, "爬山停在这里", 15, PALETTE["red"][1], "700", "end")
    circle(f, px(x_start), py(_fx(x_start)), 6, "orange", fill="#8c5315")
    f.text(px(x_start), py(_fx(x_start)) + 24, "起点", 15, PALETTE["orange"][1], "700", "middle")
    f.path(f"M{px(x_start) + 8} {py(_fx(x_start)) - 6}Q{px(4.0)} {py(_fx(loc)) - 30} {px(loc) - 8} {py(_fx(loc)) - 6}", PALETTE["red"][1])
    f.path(f"M{px(loc) + 8} {py(_fx(loc)) - 8}Q{(px(loc) + px(best)) / 2} {Y0 - 12} {px(best) - 8} {py(_fx(best)) - 8}", PALETTE["green"][1], dash=True)
    f.text(60, 150, "红色实线：爬山一路向上，停在局部最高点", 15, PALETTE["red"][1], "700")
    f.text(60, 178, "绿色虚线：退火偶尔接受更差的解，越过山谷", 15, PALETTE["green"][1], "700")
    f.text(32, 478, "200 次随机起点实测：爬山找到全局最大 30 次，模拟退火 200 次。", 17, INK, "700")
    return f.save()


def sa_accept():
    f = Fig("c3-sa-accept", "接受变差解的概率 exp(−Δ/T)", "Δ 是解变差的幅度，T 是温度。温度高时什么都敢接受，温度低时几乎只接受更好的。", 500,
            "降温方式：每轮 T ← T × 0.995 之类的几何衰减，先广泛探索，再逐渐收敛。")
    X0, X1, Y0, Y1 = 90, 920, 130, 400
    line(f, X0, Y1, X1, Y1, GREY, 1)
    line(f, X0, Y0, X0, Y1, GREY, 1)
    f.text(X0 - 12, Y0 + 5, "1", 15, SUB, anchor="end")
    f.text(X0 - 12, Y1 + 5, "0", 15, SUB, anchor="end")
    for k in range(0, 6):
        x = X0 + (X1 - X0) * k / 5
        f.text(x, Y1 + 24, str(k), 15, SUB, anchor="middle")
    f.text(X1, Y1 + 46, "Δ（变差的幅度）", 15, SUB, anchor="end")
    f.text(X0 + 8, Y0 - 8, "接受概率", 15, SUB)
    for T, kind in ((5.0, "green"), (2.0, "blue"), (1.0, "orange"), (0.3, "red")):
        pts = " ".join(f"{X0 + (X1 - X0) * d / 5:.1f},{Y1 - (Y1 - Y0) * math.exp(-d / T):.1f}" for d in [i / 20 for i in range(101)])
        f.parts.append(f'<polyline points="{pts}" fill="none" stroke="{PALETTE[kind][1]}" stroke-width="2.5"/>')
    for i, (T, kind) in enumerate(((5.0, "green"), (2.0, "blue"), (1.0, "orange"), (0.3, "red"))):
        f.rect(640 + (i % 2) * 150, 150 + (i // 2) * 40, 140, 32, kind, r=6)
        f.text(710 + (i % 2) * 150, 172 + (i // 2) * 40, f"T = {T}", 16, PALETTE[kind][1], "700", "middle")
    return f.save()


def build_all():
    w = []
    for fn in (perm_tree, backtrack_steps, subset_tree, nqueens, bfs_layers, multi_bfs, prune_array, prune_tree,
               memo_fib, memo_state, bfs01_deque, bidir, astar_grid, idastar_rounds, dlx_matrix, dlx_remove,
               sa_landscape, sa_accept):
        w += fn()
    return w
