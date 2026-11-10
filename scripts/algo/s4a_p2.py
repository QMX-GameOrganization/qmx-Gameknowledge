"""4.3 Trie、4.4 一般树与树的直径 的配图。"""
from s4a_common import *


def draw_graph(f, nodes, edges, hot=(), r=R, size=17):
    """nodes: {id: (x, y, 标签, 颜色)}；edges: [(id, id, 边标签或 None)]；用于标签可能重复的树。"""
    for a, b, lab in edges:
        (x1, y1), (x2, y2) = nodes[a][:2], nodes[b][:2]
        edge(f, x1, y1, x2, y2, HOT if (a, b) in hot else GREY, 4 if (a, b) in hot else 2)
        if lab is not None:
            f.text((x1 + x2) / 2 + (-14 if x2 <= x1 else 14), (y1 + y2) / 2 + 5, lab, 15, SUB, "700", "middle")
    for x, y, lab, kind in nodes.values():
        node(f, x, y, lab, kind, r, size)


def c403_trie():
    f = Fig("c4-03-trie", "字典树：共用前缀的多叉树", "插入 to、tea、ted、ten、i、in、inn 七个单词。", 500,
            "te 这个前缀只存一份；绿色节点表示“走到这里恰好是一个单词”。")
    N = {0: (500, 130, "根", "grey"), 1: (300, 215, "t", "blue"), 2: (760, 215, "i", "green"),
         3: (190, 300, "o", "green"), 4: (400, 300, "e", "blue"), 5: (310, 385, "a", "green"),
         6: (400, 385, "d", "green"), 7: (490, 385, "n", "green"), 8: (760, 300, "n", "green"), 9: (760, 385, "n", "green")}
    E = [(0, 1, None), (0, 2, None), (1, 3, None), (1, 4, None), (4, 5, None), (4, 6, None), (4, 7, None),
         (2, 8, None), (8, 9, None)]
    draw_graph(f, N, E)
    f.text(32, 130, "从根出发，沿着字符走：", 16, SUB)
    f.text(32, 156, "t → e → a 就是 tea", 16, INK)
    f.text(32, 182, "i → n → n 就是 inn", 16, INK)
    f.text(540, 432, "t、te 不是单词（蓝色），", 16, SUB)
    f.text(540, 458, "i 同时是单词和前缀（绿色）。", 16, SUB)
    return f.save()


def c403_xor():
    f = Fig("c4-03-xor-trie", "01 字典树求最大异或", "集合 {2, 5, 6}，查询 x = 3 与集合中某个数异或的最大值。", 600,
            "每一位尽量走与 x 相反的边：3 的二进制是 011，想要 100，最终走到 5，3 xor 5 = 6。")
    N = {0: (500, 130, "", "grey"), 1: (300, 215, "", "blue"), 2: (700, 215, "", "blue"), 3: (300, 300, "", "blue"),
         4: (580, 300, "", "blue"), 5: (820, 300, "", "blue"), 6: (300, 385, "2", "green"), 7: (580, 385, "5", "orange"),
         8: (820, 385, "6", "green")}
    E = [(0, 1, "0"), (0, 2, "1"), (1, 3, "1"), (2, 4, "0"), (2, 5, "1"), (3, 6, "0"), (4, 7, "1"), (5, 8, "0")]
    draw_graph(f, N, E, {(0, 2), (2, 4), (4, 7)})
    for y, t in ((172, "第 2 位"), (257, "第 1 位"), (342, "第 0 位")):
        f.text(32, y + 5, t, 15, SUB)
    for i, s in enumerate(["x = 011：第 2 位是 0，想走 1，存在，走。", "第 1 位是 1，想走 0，存在，走。",
                           "第 0 位是 1，想走 0，不存在，只能走 1，到达 5。", "验证：3^2=1，3^5=6，3^6=5，最大是 6。"]):
        f.text(32, 440 + i * 27, s, 16, INK, maxw=930)
    return f.save()


def c404_info():
    f = Fig("c4-04-tree-info", "有根树的基本量：父亲、深度、子树大小", "从根 1 出发做一次 DFS，回溯时累加子树大小。", 560,
            "d：深度（根为 0）；s：子树大小（含自己）。s[u] = 1 + 所有孩子的 s。")
    pos = {1: (500, 140), 2: (320, 240), 3: (700, 240), 4: (220, 340), 5: (420, 340), 6: (700, 340), 7: (420, 440)}
    tree(f, pos, [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (5, 7)])
    info = {1: "d=0 s=7", 2: "d=1 s=4", 3: "d=1 s=2", 4: "d=2 s=1", 5: "d=2 s=2", 6: "d=2 s=1", 7: "d=3 s=1"}
    for k, (x, y) in pos.items():
        f.text(x + 28, y + 5, info[k], 14, SUB)
    f.text(32, 130, "parent[2] = 1", 16, INK, mono=True)
    f.text(32, 156, "parent[5] = 2", 16, INK, mono=True)
    f.text(32, 182, "parent[7] = 5", 16, INK, mono=True)
    return f.save()


def c404_diameter():
    f = Fig("c4-04-diameter", "两次搜索求树的直径", "第一次找到的最远点，一定是某条直径的端点。", 600,
            "此方法要求边权非负；含负权边时用树形 DP。")
    N = {1: (150, 180, "1", "purple"), 2: (300, 180, "2", "blue"), 3: (450, 180, "3", "blue"),
         4: (600, 180, "4", "blue"), 5: (750, 180, "5", "orange"), 6: (300, 280, "6", "blue"),
         7: (300, 380, "7", "red"), 8: (600, 280, "8", "blue")}
    E = [(1, 2, None), (2, 3, None), (3, 4, None), (4, 5, None), (2, 6, None), (6, 7, None), (4, 8, None)]
    draw_graph(f, N, E, {(2, 3), (3, 4), (4, 5), (2, 6), (6, 7)})
    for i, (s, c) in enumerate([("第一次：从任意点 1 出发，最远的是 5（距离 4）。", INK),
                                ("第二次：从 5 出发，最远的是 7（距离 5）。", INK),
                                ("直径的长度是 5 条边，路径是 7-6-2-3-4-5（粗线）。", HOT)]):
        f.text(32, 470 + i * 34, s, 18, c, "700" if i == 2 else None, maxw=930)
    return f.save()


def build_all():
    w = []
    for fn in (c403_trie, c403_xor, c404_info, c404_diameter):
        w += fn()
    return w
