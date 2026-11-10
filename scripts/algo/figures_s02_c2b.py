"""第 2 章配图（中）：并查集。"""
from svglib import Fig, GREY, SUB, INK, PALETTE
from figures_s02_c0a import ln


def node(f, x, y, label, kind="blue"):
    f.chip(x, y, 44, 38, kind, str(label), 17, bold=True)


def up(f, c, p, color=GREY, dash=False):
    """子节点 c 指向父节点 p，c、p 为 (x, y)；箭头从子节点上沿到父节点下沿。"""
    (cx, cy), (px, py) = c, p
    f.arrow(cx, cy - 19, px, py + 20, color, dash)


def dsu_forest():
    f = Fig("c2-dsu-forest", "并查集是一片森林", "每个元素记一个父亲 parent；根的父亲是自己，同一棵树里的元素属于同一个集合。", 520,
            "合并就是让一个集合的根指向另一个集合的根。")
    f.h = 540
    titles = ["初始：每人一棵树", "合并 (1,2) 和 (3,4)", "合并 (2,4)：根 1 和根 3 相连"]
    pars = ["parent = [1, 2, 3, 4, 5, 6]", "parent = [1, 1, 3, 3, 5, 6]", "parent = [1, 1, 1, 3, 5, 6]"]
    for i in range(3):
        x = 32 + i * 322
        f.rect(x, 105, 302, 380, "grey")
        f.text(x + 14, 136, titles[i], 17, PALETTE["grey"][1], "700", maxw=274)
        f.text(x + 14, 462, pars[i], 15, INK, mono=True, maxw=274)
    for k in range(6):
        node(f, 32 + 80 + (k % 3) * 70, 250 + (k // 3) * 80, k + 1, "grey")
    b = 354
    pos2 = {1: (b + 60, 240), 2: (b + 60, 340), 3: (b + 140, 240), 4: (b + 140, 340), 5: (b + 210, 300), 6: (b + 260, 300)}
    for k, p in pos2.items():
        node(f, p[0], p[1], k, "blue" if k in (1, 3) else "grey")
    up(f, pos2[2], pos2[1]); up(f, pos2[4], pos2[3])
    c = 676
    pos3 = {1: (c + 110, 230), 2: (c + 60, 320), 3: (c + 160, 320), 4: (c + 160, 410), 5: (c + 235, 260), 6: (c + 235, 340)}
    for k, p in pos3.items():
        node(f, p[0], p[1], k, "blue" if k == 1 else "grey")
    up(f, pos3[2], pos3[1]); up(f, pos3[3], pos3[1], PALETTE["red"][1], True); up(f, pos3[4], pos3[3])
    return f.save()


def dsu_compress():
    f = Fig("c2-dsu-compress", "路径压缩：find 时顺手把路径上的点直接挂到根上", "左边是一条长链，调用 find(5) 之后变成右边的菊花形。", 640,
            "压缩只改 parent，不改变谁和谁在同一个集合；之后再查这些点只要一步。")
    f.rect(32, 105, 440, 490, "red")
    f.rect(500, 105, 468, 490, "green")
    f.text(48, 136, "压缩前：find(5) 要走 4 步", 18, PALETTE["red"][1], "700")
    f.text(516, 136, "压缩后：每个点直接指向根 1", 18, PALETTE["green"][1], "700")
    ys = [190, 285, 380, 475, 570]
    for k in range(5):
        node(f, 250, ys[k], k + 1, "blue" if k == 0 else "white")
    for k in range(1, 5):
        up(f, (250, ys[k]), (250, ys[k - 1]))
    f.text(290, 530, "5 → 4 → 3 → 2 → 1", 16, SUB)
    node(f, 734, 190, 1, "blue")
    xs = [580, 670, 760, 850]
    for k, x in enumerate(xs):
        node(f, x, 400, k + 2, "white")
        f.arrow(x, 381, 734 + (x - 734) * 0.25, 212, PALETTE["green"][1])
    return f.save()


def dsu_rank():
    f = Fig("c2-dsu-rank", "按秩（大小）合并：小树挂到大树下", "把有 3 个点的树 A 和单点 4 合并，挂法不同，树的高度不同。", 520,
            "树越矮，find 越快；按大小合并能把树高控制在 O(log n)。")
    f.rect(32, 105, 450, 370, "red")
    f.rect(518, 105, 450, 370, "green")
    f.text(48, 136, "大树挂到小树下（不好）", 18, PALETTE["red"][1], "700")
    f.text(534, 136, "小树挂到大树下（好）", 18, PALETTE["green"][1], "700")
    node(f, 257, 200, 4, "blue"); node(f, 257, 290, 1, "white")
    node(f, 197, 380, 2, "white"); node(f, 317, 380, 3, "white")
    up(f, (257, 290), (257, 200)); up(f, (197, 380), (257, 290)); up(f, (317, 380), (257, 290))
    f.text(257, 440, "高度 2", 17, PALETTE["red"][1], "700", "middle")
    node(f, 743, 200, 1, "blue")
    node(f, 683, 300, 2, "white"); node(f, 743, 300, 3, "white"); node(f, 803, 300, 4, "white")
    for x in (683, 743, 803):
        up(f, (x, 300), (743, 200))
    f.text(743, 440, "高度 1", 17, PALETTE["green"][1], "700", "middle")
    return f.save()


def build_all():
    w = []
    for fn in (dsu_forest, dsu_compress, dsu_rank):
        w += fn()
    return w
