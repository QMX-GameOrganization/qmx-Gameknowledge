"""5.11 2-SAT 的配图：蕴含图、矛盾判定。"""
from svglib import Fig, PALETTE, INK, SUB
from s5b_helpers import node, link, lines, bounding

GREEN, RED, GREY, BLUE, ORANGE = (PALETTE[k][1] for k in ("green", "red", "grey", "blue", "orange"))


def implication():
    f = Fig("c5-11-implication", "蕴含图：一个子句拆成两条边", "子句 (a ∨ b) 等价于“a 为假则 b 为真”和“b 为假则 a 为真”。", 560,
            "橙色是分量 1，绿色是分量 2；Tarjan 编号小的在拓扑序更靠后。")
    f.h = 590
    f.rect(32, 105, 640, 420, "blue")
    T = {1: (130, 220), 2: (350, 220), 3: (570, 220)}
    B = {1: (130, 430), 2: (350, 430), 3: (570, 430)}
    kind_top = {1: "green", 2: "orange", 3: "green"}
    kind_bot = {1: "orange", 2: "green", 3: "orange"}
    # 子句 (x1∨x2)：¬x1→x2，¬x2→x1；(¬x1∨x3)：x1→x3，¬x3→¬x1；(¬x2∨¬x3)：x2→¬x3，x3→¬x2
    link(f, B[1], T[2], r=28, color=BLUE)
    link(f, B[2], T[1], r=28, color=BLUE)
    link(f, T[1], T[3], r=28, color=GREEN, curve=-60)
    link(f, B[3], B[1], r=28, color=GREEN, curve=-60)
    link(f, T[2], B[3], r=28, color=ORANGE)
    link(f, T[3], B[2], r=28, color=ORANGE)
    for i in (1, 2, 3):
        node(f, *T[i], f"x{i}", kind_top[i], r=28, size=18)
        node(f, *B[i], f"¬x{i}", kind_bot[i], r=28, size=18)
    f.text(48, 140, "蓝：来自 (x1∨x2)   绿：来自 (¬x1∨x3)   橙：来自 (¬x2∨¬x3)", 15, SUB)
    f.rect(690, 105, 278, 420, "grey")
    f.text(706, 137, "规则与结果", 19, GREY, "700")
    lines(f, 706, 172, [
        "(a ∨ b)：¬a→b，¬b→a",
        "本例三个子句共 6 条边。",
        "两个强连通分量：",
        "{¬x1, x2, ¬x3} 编号 1",
        "{x1, ¬x2, x3} 编号 2",
        "没有 x 与 ¬x 同组，有解。",
        "取编号小的一侧为真：",
        "x1=0, x2=1, x3=0",
        "代回检查三个子句均成立。",
    ], 14, gap=30, maxw=258)
    return f.save()


def contradict():
    f = Fig("c5-11-contradict", "x 与 ¬x 落进同一个强连通分量，就无解", "子句 (x ∨ x) 和 (¬x ∨ ¬x) 同时出现。", 400,
            "x→¬x 和 ¬x→x 形成环：既要 x 为真又要 x 为假。")
    f.rect(32, 105, 600, 240, "red")
    a, b = (190, 230), (470, 230)
    bounding(f, 120, 160, 420, 140, "red")
    link(f, a, b, r=30, color=RED, curve=-55)
    link(f, b, a, r=30, color=RED, curve=-55)
    node(f, *a, "x", "white", r=30, size=20)
    node(f, *b, "¬x", "white", r=30, size=20)
    f.text(330, 190, "x → ¬x", 15, RED, "700", "middle")
    f.text(330, 288, "¬x → x", 15, RED, "700", "middle")
    f.rect(650, 105, 318, 240, "grey")
    lines(f, 666, 140, [
        "(x ∨ x)：¬x→x",
        "(¬x ∨ ¬x)：x→¬x",
        "comp[x] == comp[¬x]",
        "程序输出 IMPOSSIBLE",
    ], 15, gap=36, maxw=290)
    return f.save()


def build_all():
    return implication() + contradict()
