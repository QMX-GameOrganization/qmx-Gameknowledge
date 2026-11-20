"""树专题补充配图：堆的局部调整与 DFS 序的子树区间。"""
from s4a_common import *


def c4_heap_structure():
    f = Fig("c4-heap-structure", "完全二叉树堆与数组下标", "堆用数组保存，父子关系由下标直接计算。", 610,
            "小根堆只保证父节点不大于孩子，左右子树之间没有整体有序关系。")
    pos = {1: (500, 150), 2: (330, 280), 3: (670, 280), 4: (220, 420), 5: (440, 420), 6: (590, 420), 7: (800, 420)}
    tree(f, pos, [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (3, 7)],
         {1: "orange", 2: "blue", 3: "blue", 4: "green", 5: "green", 6: "green", 7: "green"}, size=16)
    f.text(500, 108, "小根堆示例：1 ≤ 2、3，2 ≤ 4、5，3 ≤ 6、7", 18, INK, "700", "middle")
    f.text(70, 535, "数组下标", 17, SUB, "700")
    cells(f, 190, 505, ["1", "2", "3", "4", "5", "6", "7"], 86, 44, ["orange", "blue", "blue", "green", "green", "green", "green"], 18)
    f.text(70, 585, "parent(i)=i/2    left(i)=2i    right(i)=2i+1", 16, SUB, mono=True)
    return f.save()


def c4_heap_sift_up():
    f = Fig("c4-heap-sift-up", "插入 2 后向上调整", "新元素先放在末尾，再沿父链交换直到恢复小根堆。", 570,
            "每次交换上移一层，复杂度是 O(log n)。")
    rows = [
        ("① 放到末尾", ["1", "3", "4", "7", "6", "2"], ["white", "white", "white", "white", "white", "orange"]),
        ("② 2 < 4，交换", ["1", "3", "2", "7", "6", "4"], ["white", "white", "orange", "white", "white", "blue"]),
        ("③ 2 < 3，交换", ["1", "2", "3", "7", "6", "4"], ["white", "orange", "blue", "white", "white", "blue"]),
        ("④ 2 ≥ 1，停止", ["1", "2", "3", "7", "6", "4"], ["green", "orange", "blue", "white", "white", "blue"]),
    ]
    for i, (head, vals, kinds) in enumerate(rows):
        y = 115 + i * 105
        f.text(32, y + 28, head, 17, INK, "700")
        cells(f, 220, y, vals, 92, 44, kinds, 18)
        if i < len(rows) - 1:
            f.arrow(805, y + 55, 805, y + 82, PALETTE["orange"][1])
    return f.save()


def c4_tree_dfs_order():
    f = Fig("c4-tree-dfs-order", "DFS 序把子树变成连续区间", "进入节点时编号，某个节点的整棵子树会连续出现在 order 中。", 660,
            "节点 2 的子树对应区间 [2, 5]，可以交给前缀和、树状数组或线段树。")
    pos = {1: (500, 145), 2: (310, 285), 3: (690, 285), 4: (190, 445), 5: (375, 445), 6: (650, 445), 7: (375, 570)}
    tree(f, pos, [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (5, 7)],
         {2: "orange", 4: "orange", 5: "orange", 7: "orange", 1: "green"}, size=16)
    f.text(500, 100, "以 1 为根，先访问左子树", 18, INK, "700", "middle")
    f.text(70, 625, "进入顺序", 17, SUB, "700")
    cells(f, 175, 592, ["1", "2", "4", "5", "7", "3", "6"], 92, 42,
          ["green", "orange", "orange", "orange", "orange", "blue", "blue"], 18)
    f.text(175, 565, "位置", 14, SUB)
    for i in range(7):
        f.text(175 + i * 92 + 46, 582, str(i + 1), 13, SUB, anchor="middle", mono=True)
    f.text(710, 565, "subtree(2) = order[2..5]", 16, PALETTE["orange"][1], "700", maxw=250)
    return f.save()


def build_all():
    return c4_heap_structure() + c4_heap_sift_up() + c4_tree_dfs_order()
