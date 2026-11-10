"""第 4 章进阶篇（4.9 到 4.14）的配图。"""
from html import escape
from svglib import Fig, GREY, SUB, INK, PALETTE

RED_FILL, RED_INK = "#d9534f", "#a33a3a"
BLACK_FILL = "#23364e"


def line(f, x1, y1, x2, y2, color=GREY, w=2, dash=False, op=1):
    extra = ' stroke-dasharray="6 5"' if dash else ""
    f.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}" '
                   f'stroke-opacity="{op}"{extra}/>')


def circ(f, x, y, label, kind="blue", r=22, size=17, sub=None, fill=None, stroke=None, tc=None, dash=False):
    bg, ink = PALETTE[kind]
    d = ' stroke-dasharray="4 3"' if dash else ""
    f.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill or bg}" stroke="{stroke or ink}" stroke-width="2"{d}/>')
    f.text(x, y + size * 0.35, str(label), size, tc or INK, "700", "middle")
    if sub:
        f.text(x, y + r + 16, sub, 13, SUB, anchor="middle")


def rb(f, x, y, label, red, r=21):
    """红黑树结点：红结点红底白字，黑结点深色底白字。"""
    circ(f, x, y, label, fill=RED_FILL if red else BLACK_FILL, stroke=RED_INK if red else "#0f1c2e",
         tc="#ffffff", r=r)


def tri(f, cx, apex, w, h, label, kind="grey"):
    bg, ink = PALETTE[kind]
    f.parts.append(f'<polygon points="{cx},{apex} {cx - w / 2},{apex + h} {cx + w / 2},{apex + h}" fill="{bg}" '
                   f'stroke="{ink}" stroke-opacity=".6" stroke-width="1.5"/>')
    f.text(cx, apex + h - 12, label, 17, ink, "700", "middle")


def big_arrow(f, x1, y, x2, label=None):
    f.arrow(x1, y, x2, y, PALETTE["grey"][1])
    if label:
        f.text((x1 + x2) / 2, y - 12, label, 15, SUB, anchor="middle")


def fig_rotate():
    f = Fig("c4-09-rotate", "旋转：改变形状，不改变中序", "右旋 rotR(y)：y 的左孩子 x 升到上面，x 的右子树 B 转给 y。", 470,
            "左旋是镜像操作。无论怎么转，中序始终是 A x B y C，所以二叉搜索树的性质不会被破坏。")
    # 旋转前
    f.text(230, 118, "旋转前：y 左边偏高", 17, SUB, anchor="middle")
    line(f, 230, 160, 140, 240); line(f, 230, 160, 320, 240)
    line(f, 140, 240, 80, 320); line(f, 140, 240, 200, 320)
    circ(f, 230, 160, "y", "orange"); circ(f, 140, 240, "x", "blue")
    tri(f, 80, 320, 70, 80, "A"); tri(f, 200, 320, 70, 80, "B"); tri(f, 320, 240, 70, 80, "C")
    big_arrow(f, 400, 240, 560, "rotR(y)")
    # 旋转后
    f.text(730, 118, "旋转后：x 做根，两边平衡", 17, SUB, anchor="middle")
    line(f, 730, 160, 640, 240); line(f, 730, 160, 820, 240)
    line(f, 820, 240, 760, 320); line(f, 820, 240, 880, 320)
    circ(f, 730, 160, "x", "blue"); circ(f, 820, 240, "y", "orange")
    tri(f, 640, 240, 70, 80, "A"); tri(f, 760, 320, 70, 80, "B"); tri(f, 880, 320, 70, 80, "C")
    return f.save()


def _avl_panel(f, ox, oy, title, op, before, after, bf):
    """画一个 AVL 失衡情形：before/after 是 [(相对x, 相对y, 标号)]，边按同一列表前缀给出。"""
    f.rect(ox, oy, 470, 235, "grey", r=12)
    f.text(ox + 16, oy + 30, title, 18, PALETTE["blue"][1], "700")
    f.text(ox + 16, oy + 56, op, 15, SUB)
    for nodes, edges, dx in ((before[0], before[1], 25), (after[0], after[1], 285)):
        for a, b in edges:
            line(f, ox + dx + nodes[a][0], oy + nodes[a][1], ox + dx + nodes[b][0], oy + nodes[b][1])
        for k, (x, y, lab, kd) in nodes.items():
            circ(f, ox + dx + x, oy + y, lab, kd, r=20)
    f.arrow(ox + 215, oy + 150, ox + 262, oy + 150, GREY)
    f.text(ox + 40, oy + 224, bf, 14, PALETTE["red"][1], "700")


def fig_avl_cases():
    f = Fig("c4-09-avl-cases", "AVL 失衡的四种情形", "先找最低的失衡结点（红色），再看重的一侧和重孙在哪边：LL、RR、LR、RL。", 640,
            "单旋解决 LL 和 RR，双旋解决 LR 和 RL；每次插入最多修复一处，删除可能沿路径多处修复。")
    # (节点: 编号 -> (x, y, 标号, 颜色)), 边
    ll = ({1: (90, 90, "3", "red"), 2: (50, 140, "2", "blue"), 3: (10, 190, "1", "blue")}, [(1, 2), (2, 3)])
    ll2 = ({1: (90, 140, "2", "blue"), 2: (50, 190, "1", "blue"), 3: (130, 190, "3", "orange")}, [(1, 2), (1, 3)])
    _avl_panel(f, 20, 100, "LL（左左）", "插入点在左孩子的左边：对 3 右旋", ll, ll2, "3 的平衡因子 = +2")
    rr = ({1: (10, 90, "1", "red"), 2: (50, 140, "2", "blue"), 3: (90, 190, "3", "blue")}, [(1, 2), (2, 3)])
    rr2 = ({1: (90, 140, "2", "blue"), 2: (50, 190, "1", "orange"), 3: (130, 190, "3", "blue")}, [(1, 2), (1, 3)])
    _avl_panel(f, 510, 100, "RR（右右）", "插入点在右孩子的右边：对 1 左旋", rr, rr2, "1 的平衡因子 = -2")
    lr = ({1: (90, 90, "3", "red"), 2: (40, 140, "1", "blue"), 3: (80, 190, "2", "blue")}, [(1, 2), (2, 3)])
    lr2 = ({1: (90, 140, "2", "blue"), 2: (50, 190, "1", "orange"), 3: (130, 190, "3", "blue")}, [(1, 2), (1, 3)])
    _avl_panel(f, 20, 360, "LR（左右）", "先对 1 左旋变成 LL，再对 3 右旋", lr, lr2, "3 的平衡因子 = +2")
    rl = ({1: (10, 90, "1", "red"), 2: (60, 140, "3", "blue"), 3: (30, 190, "2", "blue")}, [(1, 2), (2, 3)])
    rl2 = ({1: (90, 140, "2", "blue"), 2: (50, 190, "1", "orange"), 3: (130, 190, "3", "blue")}, [(1, 2), (1, 3)])
    _avl_panel(f, 510, 360, "RL（右左）", "先对 3 右旋变成 RR，再对 1 左旋", rl, rl2, "1 的平衡因子 = -2")
    return f.save()


def fig_rb_example():
    f = Fig("c4-09-rb-example", "一棵合法的红黑树", "红色结点不相邻，每条根到空位置的路径上都恰好有 2 个黑结点（黑高 = 2）。", 470,
            "空指针（NIL）按黑色计。树高不超过 2·log2(n+1)，所以查找、插入、删除都是 O(log n)。")
    pos = {8: (330, 150), 4: (180, 250), 12: (480, 250), 2: (100, 350), 6: (260, 350), 10: (400, 350), 14: (560, 350)}
    for a, b in [(8, 4), (8, 12), (4, 2), (4, 6), (12, 10), (12, 14)]:
        line(f, *pos[a], *pos[b])
    red = {4, 10, 14}
    for k, (x, y) in pos.items():
        rb(f, x, y, k, k in red)
    f.rect(660, 110, 312, 290, "blue")
    f.text(676, 142, "红黑树的 4 条性质", 19, PALETTE["blue"][1], "700")
    rows = ["1  每个结点非红即黑", "2  根结点是黑色", "3  红结点的孩子都是黑色", "4  从任一结点到它下面的空位置，",
            "    经过的黑结点数都相同"]
    for i, s in enumerate(rows):
        f.text(676, 182 + i * 34, s, 16, INK, maxw=290)
    f.text(676, 372, "新插入的结点先染红", 16, RED_INK, "700")
    return f.save()


def _rb_row(f, y0, title, op, before, after):
    f.text(24, y0, title, 19, PALETTE["blue"][1], "700")
    f.text(24, y0 + 236, op, 15, SUB, maxw=950)
    for ox, (nodes, edges) in ((130, before), (590, after)):
        for a, b in edges:
            line(f, ox + nodes[a][0], y0 + nodes[a][1], ox + nodes[b][0], y0 + nodes[b][1])
        for k, (x, y, lab, red) in nodes.items():
            rb(f, ox + x, y0 + y, lab, red)
    f.arrow(410, y0 + 110, 540, y0 + 110, GREY)


def fig_rb_insert():
    f = Fig("c4-09-rb-insert", "红黑树插入修复的三种情形", "新结点 z 是红色，父亲 p 也是红色时违反性质 3；看叔叔 u（祖父 g 的另一个孩子）的颜色。", 940,
            "情形 1 只染色，可能把问题上移到 g；情形 2、3 至多旋转两次就结束。图中只画了父亲在左边的情况，右边镜像处理。")
    g, p, u, z = "g", "p", "u", "z"
    # 情形 1：叔叔红
    b1 = ({1: (90, 60, g, False), 2: (40, 120, p, True), 3: (140, 120, u, True), 4: (0, 180, z, True)}, [(1, 2), (1, 3), (2, 4)])
    a1 = ({1: (90, 60, g, True), 2: (40, 120, p, False), 3: (140, 120, u, False), 4: (0, 180, z, True)}, [(1, 2), (1, 3), (2, 4)])
    _rb_row(f, 135,"情形 1：叔叔 u 是红色", "p、u 染黑，g 染红；再把 g 当作新的 z，继续向上检查（g 是根就直接染黑）。", b1, a1)
    # 情形 2：叔叔黑，z 是右孩子
    b2 = ({1: (90, 60, g, False), 2: (40, 120, p, True), 3: (140, 120, u, False), 4: (80, 180, z, True)}, [(1, 2), (1, 3), (2, 4)])
    a2 = ({1: (90, 60, g, False), 2: (40, 120, z, True), 3: (140, 120, u, False), 4: (0, 180, p, True)}, [(1, 2), (1, 3), (2, 4)])
    _rb_row(f, 395,"情形 2：叔叔 u 是黑色（或空），z 是 p 的右孩子", "对 p 左旋，两个红结点排成一条左斜线（z 和 p 互换名字），变成情形 3。", b2, a2)
    # 情形 3：叔叔黑，z 是左孩子
    b3 = ({1: (90, 60, g, False), 2: (40, 120, p, True), 3: (140, 120, u, False), 4: (0, 180, z, True)}, [(1, 2), (1, 3), (2, 4)])
    a3 = ({1: (90, 60, p, False), 2: (40, 120, z, True), 3: (140, 120, g, True), 4: (190, 180, u, False)}, [(1, 2), (1, 3), (3, 4)])
    _rb_row(f, 655,"情形 3：叔叔 u 是黑色（或空），z 是 p 的左孩子", "p 染黑，g 染红，对 g 右旋。子树根变黑，黑高不变，修复结束。", b3, a3)
    return f.save()


def _kp(f, x, y, key, pri, kind="blue", r=26):
    """Treap 结点：上面写键值，下面写优先级。"""
    bg, ink = PALETTE[kind]
    f.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{bg}" stroke="{ink}" stroke-width="2"/>')
    f.text(x, y - 2, str(key), 18, INK, "700", "middle")
    f.text(x, y + 15, f"p={pri}", 12, SUB, anchor="middle")


def fig_treap_split():
    f = Fig("c4-10-treap-split", "Treap 的 split：沿一条路径把树劈成两棵", "每个结点写着键值和优先级 p（大根堆）。split(root, 3)：键值 <= 3 的归左树，其余归右树。", 480,
            "路径上 4 > 3 归右，2 <= 3 归左，3 <= 3 归左；不在路径上的子树整棵保留。两棵结果仍满足堆序。")
    T = {4: (250, 150, 9), 2: (130, 250, 7), 6: (370, 250, 8), 1: (70, 350, 3), 3: (190, 350, 5), 5: (310, 350, 2), 7: (430, 350, 4)}
    for a, b in [(4, 2), (4, 6), (2, 1), (2, 3), (6, 5), (6, 7)]:
        line(f, T[a][0], T[a][1], T[b][0], T[b][1])
    for k, (x, y, p) in T.items():
        _kp(f, x, y, k, p, "orange" if k in (4, 2, 3) else "blue")
    f.arrow(500, 250, 545, 250, GREY)
    f.text(522, 232, "split", 15, SUB, anchor="middle")
    A = {2: (620, 200, 7), 1: (570, 300, 3), 3: (670, 300, 5)}
    for a, b in [(2, 1), (2, 3)]:
        line(f, A[a][0], A[a][1], A[b][0], A[b][1])
    for k, (x, y, p) in A.items():
        _kp(f, x, y, k, p, "green")
    f.text(620, 365, "左树：键值 <= 3", 16, PALETTE["green"][1], "700", "middle")
    B = {4: (800, 200, 9), 6: (870, 290, 8), 5: (830, 380, 2), 7: (930, 380, 4)}
    for a, b in [(4, 6), (6, 5), (6, 7)]:
        line(f, B[a][0], B[a][1], B[b][0], B[b][1])
    for k, (x, y, p) in B.items():
        _kp(f, x, y, k, p, "purple")
    f.text(850, 440, "右树：键值 > 3", 16, PALETTE["purple"][1], "700", "middle")
    return f.save()


def fig_splay():
    f = Fig("c4-10-splay-rotate", "Splay 的双旋：同向转父亲，异向转两次自己", "x 是要伸展的结点，y 是父亲，z 是祖父。", 620,
            "zig-zig 会把路径压扁，这是均摊 O(log n) 的关键；只把 x 连转两次（每次都转 x）会让链保持很长。")
    f.text(24, 112, "同向（左左）：zig-zig，先旋转 y，再旋转 x", 18, PALETTE["blue"][1], "700")
    for ox, nodes, edges in ((90, {"z": (120, 160), "y": (70, 220), "x": (20, 280)}, [("z", "y"), ("y", "x")]),
                             (560, {"x": (20, 160), "y": (70, 220), "z": (120, 280)}, [("x", "y"), ("y", "z")])):
        for a, b in edges:
            line(f, ox + nodes[a][0], nodes[a][1], ox + nodes[b][0], nodes[b][1])
        for k, (x, y) in nodes.items():
            circ(f, ox + x, y, k, "orange" if k == "x" else "blue")
    f.arrow(330, 220, 520, 220, GREY)
    f.text(24, 352, "异向（左右）：zig-zag，把 x 连转两次", 18, PALETTE["blue"][1], "700")
    for ox, nodes, edges in ((90, {"z": (120, 400), "y": (60, 460), "x": (100, 520)}, [("z", "y"), ("y", "x")]),
                             (560, {"x": (80, 400), "y": (30, 480), "z": (130, 480)}, [("x", "y"), ("x", "z")])):
        for a, b in edges:
            line(f, ox + nodes[a][0], nodes[a][1], ox + nodes[b][0], nodes[b][1])
        for k, (x, y) in nodes.items():
            circ(f, ox + x, y, k, "orange" if k == "x" else "blue")
    f.arrow(330, 460, 520, 460, GREY)
    return f.save()


def fig_dyn_nodes():
    f = Fig("c4-11-dynamic-nodes", "动态开点：只创建用到的结点", "值域 [1, 8]，依次在位置 3 和 6 各加一个数。", 570,
            "完整的线段树有 15 个结点；这里只创建了 7 个。每次修改最多新建 log(值域) 个结点。")
    lv_y = [130, 230, 330, 430]
    nodes = {}

    def build(l, r, d):
        if l == r:
            x = 90 + (l - 1) * 110
        else:
            m = (l + r) // 2
            xl, xr = build(l, m, d + 1), build(m + 1, r, d + 1)
            x = (xl + xr) / 2
            nodes[(l, r)] = (x, lv_y[d], xl, xr, m)
            return x
        nodes[(l, r)] = (x, lv_y[d], None, None, None)
        return x

    build(1, 8, 0)
    made = set()
    for p in (3, 6):
        l, r = 1, 8
        while True:
            made.add((l, r))
            if l == r:
                break
            m = (l + r) // 2
            l, r = (l, m) if p <= m else (m + 1, r)
    for (l, r), (x, y, xl, xr, m) in nodes.items():
        if xl is None:
            continue
        for cx, cl, cr in ((xl, l, m), (xr, m + 1, r)):
            cy = nodes[(cl, cr)][1]
            ok = (l, r) in made and (cl, cr) in made
            line(f, x, y, cx, cy, PALETTE["blue"][1] if ok else GREY, 2 if ok else 1.5, not ok, 1 if ok else .45)
    for (l, r), (x, y, *_rest) in nodes.items():
        s = str(l) if l == r else f"{l}~{r}"
        if (l, r) in made:
            f.chip(x, y, 62, 34, "blue", s, 16, bold=True)
        else:
            f.rect(x - 31, y - 17, 62, 34, "grey", r=8, dash=True)
            f.text(x, y + 6, s, 15, GREY, anchor="middle")
    f.rect(32, 480, 24, 18, "blue", r=5)
    f.text(66, 495, "已创建（共 7 个）", 16)
    f.rect(300, 480, 24, 18, "grey", r=5, dash=True)
    f.text(334, 495, "尚未创建：访问到它时，空指针 0 就表示这一段全是 0", 16)
    return f.save()


def fig_merge():
    f = Fig("c4-11-merge", "线段树合并：两棵树按位置相加", "值域 [1, 4]，结点里写的是该区间内的个数。", 480,
            "绿色：只有一边有这个结点，整棵子树直接复用。橙色：两边都有，递归相加。")

    def tree(ox, title, cells, kinds):
        f.text(ox + 140, 112, title, 18, PALETTE["blue"][1], "700", "middle")
        pos = {"r": (140, 170), "L": (70, 260), "R": (210, 260), 1: (35, 350), 2: (105, 350), 3: (175, 350), 4: (245, 350)}
        par = {"L": "r", "R": "r", 1: "L", 2: "L", 3: "R", 4: "R"}
        for k, v in cells.items():
            if k in par and par[k] in cells:
                line(f, ox + pos[par[k]][0], pos[par[k]][1], ox + pos[k][0], pos[k][1])
        for k, v in cells.items():
            f.chip(ox + pos[k][0], pos[k][1], 56, 34, kinds.get(k, "blue"), str(v), 17, bold=True)
        for i in range(1, 5):
            f.text(ox + pos[i][0], 392, f"位置 {i}", 14, SUB, anchor="middle")

    tree(30, "树 A", {"r": 3, "L": 1, "R": 2, 1: 1, 3: 2}, {})
    tree(360, "树 B", {"r": 2, "R": 2, 3: 1, 4: 1}, {})
    tree(690, "合并结果（原地修改 A）", {"r": 5, "L": 1, "R": 4, 1: 1, 3: 3, 4: 1},
         {"r": "orange", "R": "orange", 3: "orange", "L": "green", 1: "green", 4: "green"})
    f.text(332, 262, "+", 34, SUB, "700", "middle")
    f.text(662, 262, "=", 34, SUB, "700", "middle")
    f.text(32, 440, "合并只会遍历两棵树重叠的部分，每走一步都会少掉一个结点，所以总代价不超过创建过的结点总数。", 16, INK)
    return f.save()


def fig_persistent():
    f = Fig("c4-12-persistent", "可持久化：每次修改只新建一条链", "在版本 i-1 的基础上把值 3 的个数加 1，得到版本 i。", 520,
            "新版本只新建根到叶的一条链（橙色，约 log n 个结点）；没动过的子树用指针指向旧版本，旧版本完全不受影响。")
    f.text(190, 112, "版本 i-1", 18, PALETTE["blue"][1], "700", "middle")
    f.text(710, 112, "版本 i（插入值 3）", 18, PALETTE["orange"][1], "700", "middle")
    old = {"r": (150, 170, "1~4"), "L": (80, 260, "1~2"), "R": (220, 260, "3~4"),
           1: (45, 350, "1"), 2: (115, 350, "2"), 3: (185, 350, "3"), 4: (255, 350, "4")}
    par = {"L": "r", "R": "r", 1: "L", 2: "L", 3: "R", 4: "R"}
    ox = 40
    for k, p in par.items():
        line(f, ox + old[p][0], old[p][1], ox + old[k][0], old[k][1])
    for k, (x, y, s) in old.items():
        f.chip(ox + x, y, 62, 34, "blue", s, 16, bold=True)
    new = {"r": (150, 170, "1~4", "orange"), "L": (80, 260, "1~2", "dash"), "R": (220, 260, "3~4", "orange"),
           3: (185, 350, "3", "orange"), 4: (255, 350, "4", "dash")}
    nox = 560
    for k, p in {"L": "r", "R": "r", 3: "R", 4: "R"}.items():
        shared = new[k][3] == "dash"
        line(f, nox + new[p][0], new[p][1], nox + new[k][0], new[k][1], GREY if shared else PALETTE["orange"][1], 2, shared)
    for k, (x, y, s, kd) in new.items():
        if kd == "dash":
            f.rect(nox + x - 31, y - 17, 62, 34, "blue", r=8, dash=True)
            f.text(nox + x, y + 6, s, 16, PALETTE["blue"][1], anchor="middle")
        else:
            f.chip(nox + x, y, 62, 34, "orange", s, 16, bold=True)
    f.text(nox + 80, 322, "共用旧结点，", 13, SUB, anchor="middle")
    f.text(nox + 80, 338, "下面整棵子树也共用", 13, SUB, anchor="middle")
    f.arrow(470, 260, 540, 260, GREY)
    f.text(505, 242, "update", 14, SUB, anchor="middle")
    f.rect(40, 410, 24, 18, "orange", r=5)
    f.text(74, 425, "新建的结点", 16)
    f.rect(240, 410, 24, 18, "blue", r=5, dash=True)
    f.text(274, 425, "指向旧版本的同一个结点（没有复制）", 16)
    return f.save()


def fig_pst_kth():
    f = Fig("c4-12-kth-diff", "区间第 k 小：两个版本相减", "数组 a = [3, 1, 4, 1, 5]，表里是每个版本中各个值出现的次数。", 650,
            "root[r] 的计数减去 root[l-1] 的计数，就是 a[l..r] 的值分布；在线段树上同时下降，不需要真的建出差。")
    vals = [1, 3, 4, 5]
    rows = [("root[0]  空", [0, 0, 0, 0], "grey"), ("root[1]  加入 3", [0, 1, 0, 0], "blue"),
            ("root[2]  加入 1", [1, 1, 0, 0], "grey"), ("root[3]  加入 4", [1, 1, 1, 0], "grey"),
            ("root[4]  加入 1", [2, 1, 1, 0], "orange"), ("root[5]  加入 5", [2, 1, 1, 1], "grey"),
            ("root[4] - root[1]", [2, 0, 1, 0], "green")]
    f.text(32, 128, "版本", 16, SUB, "700")
    for j, v in enumerate(vals):
        f.text(330 + j * 100, 128, f"值 {v}", 16, SUB, "700", "middle")
    for i, (name, cnt, kd) in enumerate(rows):
        y = 140 + i * 46 + (12 if i == 6 else 0)
        f.rect(24, y, 250, 38, kd, r=8)
        f.text(38, y + 25, name, 16, INK, "700" if kd != "grey" else None)
        for j, c in enumerate(cnt):
            f.chip(330 + j * 100, y + 19, 80, 38, kd, str(c), 17, bold=(kd != "grey"))
    f.text(32, 505, "查询区间 [2, 4] 的第 2 小：把 root[4] 和 root[1] 同时放到线段树根上。", 16, INK)
    f.text(32, 535, "左半边值 {1,3} 的个数 = 3 - 1 = 2，k = 2 <= 2，进左半边；再看值 {1} 的个数 = 2 >= 2，进左边。", 16, INK)
    f.text(32, 565, "到达叶子：值 1。a[2..4] = [1, 4, 1]，排序后的第 2 个数确实是 1。", 16, PALETTE["green"][1], "700")
    return f.save()


# 4.13 用的示例树：1 的孩子 2、3、4；2 的孩子 5、6；3 的孩子 7；5 的孩子 8、9；7 的孩子 10；10 的孩子 11
T13_CH = {1: [2, 3, 4], 2: [5, 6], 3: [7], 5: [8, 9], 7: [10], 10: [11]}
T13_POS = {1: (500, 140), 2: (280, 240), 3: (620, 240), 4: (840, 240), 5: (180, 340), 6: (380, 340),
           7: (620, 340), 8: (110, 440), 9: (250, 440), 10: (620, 440), 11: (620, 540)}
T13_SZ = {1: 11, 2: 5, 3: 4, 4: 1, 5: 3, 6: 1, 7: 3, 8: 1, 9: 1, 10: 2, 11: 1}
T13_DFN = {1: 1, 2: 2, 5: 3, 8: 4, 9: 5, 6: 6, 3: 7, 7: 8, 10: 9, 11: 10, 4: 11}
T13_HEAVY = {(1, 2), (2, 5), (5, 8), (3, 7), (7, 10), (10, 11)}
CHAIN_A, CHAIN_B = {1, 2, 5, 8}, {3, 7, 10, 11}


def _draw_t13(f, kinds, heavy_color=None):
    for p, cs in T13_CH.items():
        for c in cs:
            if (p, c) in T13_HEAVY:
                line(f, *T13_POS[p], *T13_POS[c], (heavy_color or {}).get(c, PALETTE["blue"][1]), 5)
            else:
                line(f, *T13_POS[p], *T13_POS[c], GREY, 1.5, True)
    for v, (x, y) in T13_POS.items():
        circ(f, x, y, v, kinds.get(v, "grey"))
        f.text(x + 30, y + 5, f"sz{T13_SZ[v]} dfn{T13_DFN[v]}", 13, SUB)


def fig_hld_tree():
    f = Fig("c4-13-hld-tree", "重链剖分：重边连成链，链上 dfn 连续", "每个结点下面写着子树大小 sz 和 dfs 序 dfn。", 650,
            "dfs 时先走重儿子，所以每条重链的 dfn 连续；任意子树也是连续的一段 [dfn, dfn + sz - 1]。")
    kinds = {v: "blue" for v in CHAIN_A}
    kinds.update({v: "green" for v in CHAIN_B})
    kinds.update({9: "orange", 6: "orange", 4: "orange"})
    _draw_t13(f, kinds, {c: PALETTE["green"][1] for c in CHAIN_B})
    f.rect(720, 400, 262, 200, "grey")
    f.text(736, 432, "图例", 17, INK, "700")
    f.text(736, 462, "粗线：重边（连向最大的孩子）", 14, INK)
    f.text(736, 488, "虚线：轻边", 14, INK)
    f.text(736, 520, "蓝色：重链 1-2-5-8", 14, PALETTE["blue"][1], "700")
    f.text(736, 546, "绿色：重链 3-7-10-11", 14, PALETTE["green"][1], "700")
    f.text(736, 572, "橙色：只有一个点的链", 14, PALETTE["orange"][1], "700")
    return f.save()


def fig_hld_path():
    f = Fig("c4-13-path-jump", "路径操作：沿链顶一段一段往上跳", "路径 9 到 11：每次让链顶更深的一端跳到链顶的父亲，每一段对应一个连续的 dfn 区间。", 810,
            "一条路径最多经过 O(log n) 条链，每段区间交给线段树，所以路径操作是 O(log² n)。")
    kinds = {9: "orange", 11: "red", 10: "red", 7: "red", 3: "red", 5: "purple", 2: "purple", 1: "purple"}
    _draw_t13(f, kinds, {10: PALETTE["red"][1], 7: PALETTE["red"][1], 11: PALETTE["red"][1]})
    f.rect(32, 600, 936, 140, "grey")
    f.text(48, 632, "① u = 9，链顶 9 比链顶 3 深：处理 dfn 区间 [5, 5]，跳到 fa[9] = 5", 16, PALETTE["orange"][1], "700")
    f.text(48, 664, "② 现在 5 的链顶是 1，11 的链顶 3 更深：处理 [7, 10]，11 跳到 fa[3] = 1", 16, PALETTE["red"][1], "700")
    f.text(48, 696, "③ 5 和 1 在同一条链上：处理 [dfn[1], dfn[5]] = [1, 3]，结束", 16, PALETTE["purple"][1], "700")
    f.text(48, 726, "三段区间 [5,5]、[7,10]、[1,3] 合起来正好是路径上的 8 个点", 16, INK)
    return f.save()


def fig_sack():
    f = Fig("c4-14-sack-steps", "树上启发式合并：一次 dfs 的四步", "dfs(u, keep)：keep = true 表示处理完后保留 u 子树的统计。", 620,
            "每个点被重新加入的次数等于它到根路径上的轻边数，而轻边不超过 log2 n 条，所以总复杂度 O(n log n)。")
    steps = ["① 递归轻儿子\n算完就清空", "② 递归重儿子\n保留它的统计", "③ 加入 u 自己\n和所有轻子树的点", "④ 记录 ans[u]\nkeep 为假就清空"]
    kinds = ["orange", "green", "blue", "purple"]
    for i, (s, k) in enumerate(zip(steps, kinds)):
        x = 130 + i * 250
        f.chip(x, 170, 210, 96, k, s, 17, bold=True)
        if i < 3:
            f.arrow(x + 108, 170, x + 140, 170, GREY)
    f.text(32, 272, "为什么重儿子的统计可以保留：重儿子的子树最大，留着它省掉最多的重复加入。", 16, INK)
    f.text(32, 330, "每跨过一条轻边，子树大小至少减半：", 17, PALETTE["blue"][1], "700")
    bars = [("整棵树 n 个点", 900), ("跨 1 条轻边：子树 <= n/2", 450), ("跨 2 条：<= n/4", 225), ("跨 k 条：<= n / 2^k", 112)]
    for i, (s, w) in enumerate(bars):
        y = 360 + i * 46
        f.rect(32, y, w, 34, ["blue", "green", "orange", "purple"][i], r=8)
        if i == 0:
            f.text(46, y + 24, s, 16, INK)
        else:
            f.text(32 + w + 12, y + 24, s, 16, INK)
    return f.save()


def tidy(ch, root, dx, dy, ox, oy):
    """简单的树布局：叶子从左到右均匀排开，内部结点居中。返回 {点: (x, y)}。"""
    pos, cnt = {}, [0]

    def go(v, d):
        kids = ch.get(v, [])
        if not kids:
            x = ox + cnt[0] * dx
            cnt[0] += 1
        else:
            xs = [go(c, d + 1) for c in kids]
            x = (xs[0] + xs[-1]) / 2
        pos[v] = (x, oy + d * dy)
        return x

    go(root, 0)
    return pos


def centroid_tree(adj):
    """返回 (重心树的孩子表, 根, 每个点成为重心的层数)。"""
    n = len(adj)
    removed, level, ch = set(), {}, {}

    def size(u, f):
        s = 1
        for v in adj[u]:
            if v != f and v not in removed:
                s += size(v, u)
        return s

    def find(u, f, total):
        for v in adj[u]:
            if v != f and v not in removed and size(v, u) * 2 > total:
                return find(v, u, total)
        return u

    def solve(u, d):
        c = find(u, 0, size(u, 0))
        level[c] = d
        removed.add(c)
        ch[c] = []
        for v in adj[c]:
            if v not in removed:
                ch[c].append(solve(v, d + 1))
        return c

    r = solve(1, 0)
    return ch, r, level


def fig_centroid():
    edges = [(1, 2), (2, 3), (3, 4), (4, 5), (3, 6), (6, 7), (6, 8), (8, 9)]
    adj = {i: [] for i in range(1, 10)}
    adj[0] = []
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    ch, root, level = centroid_tree(adj)
    f = Fig("c4-14-centroid", "点分治：每次删掉重心，递归处理剩下的子块", "左边是原树，右边是递归过程形成的重心树；颜色代表被选为重心的层数。", 700,
            "每个子块的大小至少减半，所以重心树的深度不超过 log2 n；每一层的总工作量是 O(n)。")
    # 原树
    oc, seen = {}, set()

    def dfs(u):
        seen.add(u)
        oc[u] = [v for v in adj[u] if v not in seen]
        for v in oc[u]:
            dfs(v)

    dfs(1)
    kinds = ["red", "orange", "green", "blue", "purple"]
    pos = tidy(oc, 1, 150, 85, 70, 150)
    f.text(250, 112, "原树", 18, PALETTE["blue"][1], "700", "middle")
    for a, b in edges:
        line(f, *pos[a], *pos[b])
    for v, (x, y) in pos.items():
        circ(f, x, y, v, kinds[level[v]])
    # 重心树
    leaves = sum(1 for v in ch if not ch[v])
    cpos = tidy(ch, root, 440 / max(leaves, 1) if leaves > 1 else 100, 85, 540, 150)
    f.text(750, 112, "重心树", 18, PALETTE["blue"][1], "700", "middle")
    for p, cs in ch.items():
        for c in cs:
            line(f, *cpos[p], *cpos[c])
    for v, (x, y) in cpos.items():
        circ(f, x, y, v, kinds[level[v]])
    for i in range(max(level.values()) + 1):
        f.rect(32 + i * 150, 632, 20, 16, kinds[i], r=4)
        f.text(58 + i * 150, 646, f"第 {i + 1} 层重心", 14, SUB)
    return f.save()


def fig_vtree():
    f = Fig("c4-14-vtree", "虚树：只保留关键点和它们的 LCA", "关键点 {6, 8, 9, 11}（橙色）；补上相邻关键点的 LCA（绿色）；其余点被压缩掉（灰色）。", 640,
            "虚树点数不超过 2k - 1；虚树边上标的是它在原树里对应的路径长度（边数）。")
    pos = {1: (250, 150), 2: (140, 240), 3: (330, 240), 4: (450, 240), 5: (80, 330), 6: (200, 330),
           7: (330, 330), 8: (40, 420), 9: (120, 420), 10: (330, 420), 11: (330, 510)}
    ch = {1: [2, 3, 4], 2: [5, 6], 3: [7], 5: [8, 9], 7: [10], 10: [11]}
    key, add = {6, 8, 9, 11}, {1, 2, 5}
    f.text(250, 112, "原树", 18, PALETTE["blue"][1], "700", "middle")
    for p, cs in ch.items():
        for c in cs:
            line(f, *pos[p], *pos[c])
    for v, (x, y) in pos.items():
        circ(f, x, y, v, "orange" if v in key else "green" if v in add else "grey", r=20)
    vch = {1: [2, 11], 2: [5, 6], 5: [8, 9]}
    wlen = {(1, 2): 1, (1, 11): 4, (2, 5): 1, (2, 6): 1, (5, 8): 1, (5, 9): 1}
    vp = tidy(vch, 1, 95, 90, 610, 150)
    f.text(760, 112, "虚树", 18, PALETTE["blue"][1], "700", "middle")
    for p, cs in vch.items():
        for c in cs:
            line(f, *vp[p], *vp[c])
            mx, my = (vp[p][0] + vp[c][0]) / 2, (vp[p][1] + vp[c][1]) / 2
            f.chip(mx + (14 if vp[c][0] >= vp[p][0] else -14), my, 30, 24, "white", str(wlen[(p, c)]), 14)
    for v, (x, y) in vp.items():
        circ(f, x, y, v, "orange" if v in key else "green", r=20)
    f.text(540, 540, "虚树边 1-11 对应原树里", 16, INK)
    f.text(540, 566, "1-3-7-10-11 这条长度为 4 的路径。", 16, INK)
    return f.save()


def build_all():
    out = []
    for fn in (fig_rotate, fig_avl_cases, fig_rb_example, fig_rb_insert, fig_treap_split, fig_splay,
               fig_dyn_nodes, fig_merge, fig_persistent, fig_pst_kth, fig_hld_tree, fig_hld_path,
               fig_sack, fig_centroid, fig_vtree):
        out += fn()
    return out
