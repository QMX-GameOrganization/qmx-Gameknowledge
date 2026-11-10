"""5.8 二分图匹配（匈牙利算法）的配图。"""
from svglib import Fig, PALETTE, INK, SUB
from s5b_helpers import node, link, lines

GREEN, RED, GREY = PALETTE["green"][1], PALETTE["red"][1], PALETTE["grey"][1]


def _bip(f, ox, lx, rx, ys, edges, matched, path=(), cover=(), prefix=("a", "b")):
    """画一张二分图。edges 为 (左下标, 右下标)，matched/path 是其中的子集。"""
    pos_l = {i: (ox + lx, ys[i - 1]) for i in range(1, len(ys) + 1)}
    pos_r = {i: (ox + rx, ys[i - 1]) for i in range(1, len(ys) + 1)}
    for (i, j) in edges:
        if (i, j) in matched:
            link(f, pos_l[i], pos_r[j], r=24, arrow=False, color=GREEN, width=6)
        elif (i, j) in path:
            link(f, pos_l[i], pos_r[j], r=24, arrow=False, color=RED, dash=True, width=3)
        else:
            link(f, pos_l[i], pos_r[j], r=24, arrow=False)
    for i, (x, y) in pos_l.items():
        node(f, x, y, f"{prefix[0]}{i}", "orange" if ("L", i) in cover else "white", r=24, size=16)
    for j, (x, y) in pos_r.items():
        node(f, x, y, f"{prefix[1]}{j}", "orange" if ("R", j) in cover else "white", r=24, size=16)


def augment():
    f = Fig("c5-08-augment", "增广路：沿着“非匹配边、匹配边、非匹配边”换一遍，匹配数加 1", "a2 想要配对，但 b1 已经被 a1 占了。", 540,
            "增广路两端都是未匹配点，路上匹配边和非匹配边交替出现。")
    ys = [200, 300, 400]
    edges = [(1, 1), (1, 2), (2, 1), (3, 3)]
    f.rect(32, 105, 470, 370, "blue")
    f.text(48, 137, "增广前：已配 a1-b1、a3-b3", 18, PALETTE["blue"][1], "700")
    _bip(f, 0, 150, 390, ys, edges, {(1, 1), (3, 3)}, path={(2, 1), (1, 2)})
    f.text(48, 452, "红色虚线：a2→b1→a1→b2 这条增广路", 15, SUB)
    f.rect(530, 105, 438, 370, "green")
    f.text(546, 137, "增广后：已配 a2-b1、a1-b2、a3-b3", 18, GREEN, "700")
    _bip(f, 0, 620, 880, ys, edges, {(2, 1), (1, 2), (3, 3)})
    f.arrow(502, 300, 530, 300, GREY)
    f.text(546, 452, "路上的边换了身份，匹配数从 2 变成 3", 15, SUB)
    return f.save()


def konig():
    f = Fig("c5-08-konig", "König 定理：最大匹配数等于最小点覆盖数", "从未匹配的左点出发走交错路，访问到的点决定覆盖集。", 560,
            "覆盖集 = 左部没访问到的 + 右部访问到的；最大独立集 = 总点数 - 最大匹配。")
    f.h = 590
    ys = [175, 275, 375, 475]
    edges = [(1, 1), (1, 2), (2, 2), (3, 2), (3, 3), (4, 3)]
    f.rect(32, 105, 590, 420, "blue")
    _bip(f, 0, 190, 470, ys, edges, {(1, 1), (2, 2), (4, 3)}, path={(3, 2), (3, 3)},
         cover={("L", 1), ("R", 2), ("R", 3)})
    f.rect(640, 105, 328, 420, "grey")
    f.text(656, 137, "步骤", 19, GREY, "700")
    lines(f, 656, 172, [
        "① 最大匹配 3 条（粗绿线），",
        "    a3 没有配上。",
        "② 从 a3 出发走非匹配边",
        "    到 b2、b3（红色虚线）。",
        "③ 再沿匹配边回到 a2、a4。",
        "④ 访问到：a3 a2 a4 b2 b3。",
        "⑤ 覆盖集 = 左部没访问到的 a1",
        "    + 右部访问到的 b2、b3。",
        "⑥ 大小 3 = 最大匹配数，",
        "    橙色点即覆盖集。",
        "最大独立集：",
        "    8 - 3 = 5，如 a2 a3 a4 b1 b4。",
    ], 14, gap=29, maxw=300)
    return f.save()


def build_all():
    return augment() + konig()
