"""4.7 线段树 的配图。"""
from s4a_common import *

A = [5, 3, 8, 6, 2, 7, 4, 1]


def seg_nodes():
    """返回 {编号: (l, r, 和, x, y)}，编号沿用堆式下标：孩子是 2i 与 2i+1。"""
    res = {}

    def go(i, l, r, lv):
        if l == r:
            res[i] = [l, r, A[l - 1], 80 + 120 * (l - 1), 130 + 100 * lv]
            return
        m = (l + r) // 2
        go(2 * i, l, m, lv + 1)
        go(2 * i + 1, m + 1, r, lv + 1)
        res[i] = [l, r, res[2 * i][2] + res[2 * i + 1][2], (res[2 * i][3] + res[2 * i + 1][3]) / 2, 130 + 100 * lv]
    go(1, 1, 8, 0)
    return res


def draw_seg(f, kind_of, dashed=lambda i: False):
    nd = seg_nodes()
    for i in nd:
        if i > 1:
            p = nd[i // 2]
            edge(f, p[3], p[4], nd[i][3], nd[i][4], GREY, 2, dashed(i))
    for i, (l, r, s, x, y) in nd.items():
        f.chip(x, y, 104, 54, kind_of(i, l, r), f"[{l},{r}]\n{s}", 15)
        if i % 2 == 0 or i == 1:
            f.text(x - 46, y - 31, f"#{i}", 12, SUB)
        else:
            f.text(x + 46, y - 31, f"#{i}", 12, SUB, anchor="end")
    return nd


def c407_structure():
    f = Fig("c4-07-seg-structure", "线段树：每个节点管一段区间", "数组 [5,3,8,6,2,7,4,1] 的区间和线段树，节点 i 的孩子是 2i 和 2i+1。", 560,
            "每个节点存“区间 [l, r] 及其和”；叶子是单个元素，根是整个数组。树高约 log n。")
    draw_seg(f, lambda i, l, r: "green" if l == r else "blue")
    return f.save()


def c407_query():
    f = Fig("c4-07-query-decompose", "区间查询 [2, 6]：拆成 O(log n) 个完整节点", "只在与查询区间部分重叠的节点上继续往下走。", 580,
            "橙色：完全落在 [2,6] 内，直接取值；蓝色：部分重叠，继续向下；灰色：无交集，返回。")
    qa, qb = 2, 6
    seen = set()

    def visit(i, l, r):
        seen.add(i)
        if qa <= l and r <= qb or r < qa or l > qb:
            return
        m = (l + r) // 2
        visit(2 * i, l, m)
        visit(2 * i + 1, m + 1, r)
    visit(1, 1, 8)

    def kind(i, l, r):
        if i not in seen:
            return "white"
        return "orange" if qa <= l and r <= qb else "grey" if r < qa or l > qb else "blue"
    draw_seg(f, kind, lambda i: i not in seen)
    f.text(32, 130, "答案 = a2 + (a3+a4) + (a5+a6)", 16, INK, "700")
    f.text(32, 156, "     = 3 + 14 + 9 = 26", 16, INK, "700")
    return f.save()


def c407_lazy():
    f = Fig("c4-07-lazy", "懒标记：先欠着，需要时再还", "区间 [1,4] 都加 3：只改最上面的节点，把修改记在 lz 里。", 520,
            "lz 表示“这个节点的整段区间欠着子树一次加 lz 的修改”。")
    stages = [("① 初始", [("[1,4]", 22, 0), ("[1,2]", 8, 0), ("[3,4]", 14, 0)], [], "所有 lz 都是 0。"),
              ("② add [1,4] +3", [("[1,4]", 34, 3), ("[1,2]", 8, 0), ("[3,4]", 14, 0)], [0],
               "[1,4] 完全被覆盖：sum 加 3×4，记 lz=3，不再往下。"),
              ("③ 查询 [1,2] 时下推", [("[1,4]", 34, 0), ("[1,2]", 14, 3), ("[3,4]", 20, 3)], [1, 2],
               "走进孩子前先下推：孩子 sum 加 3×长度，lz 加 3。")]
    xs = [180, 500, 820]
    for k, (title, nds, hot, note) in enumerate(stages):
        x = xs[k]
        f.rect(x - 150, 100, 300, 340, "grey")
        f.text(x, 132, title, 18, PALETTE["grey"][1], "700", "middle")
        pts = [(x, 195), (x - 75, 320), (x + 75, 320)]
        edge(f, *pts[0], *pts[1])
        edge(f, *pts[0], *pts[2])
        for j, ((lab, s, lz), (px, py)) in enumerate(zip(nds, pts)):
            f.chip(px, py, 150 if j == 0 else 130, 66, "orange" if j in hot else "white", f"{lab}\nsum={s}  lz={lz}", 15)
        for r, line in enumerate(wrap(note, 17)):
            f.text(x, 385 + r * 24, line, 15, INK, anchor="middle", maxw=280)
    f.arrow(334, 270, 366, 270, GREY)
    f.arrow(654, 270, 686, 270, GREY)
    return f.save()


def wrap(s, n):
    return [s[i:i + n] for i in range(0, len(s), n)]


def build_all():
    w = []
    for fn in (c407_structure, c407_query, c407_lazy):
        w += fn()
    return w
