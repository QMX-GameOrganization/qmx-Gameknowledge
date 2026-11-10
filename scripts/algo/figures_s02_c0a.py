"""第 0 章配图（上）：复杂度与递归树。"""
import math
from svglib import Fig, GREY, SUB, INK, PALETTE


def ln(f, x1, y1, x2, y2, color=GREY, dash=False, w=2):
    extra = ' stroke-dasharray="6 5"' if dash else ""
    f.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}"{extra}/>')


def range_table():
    f = Fig("c0-range-table", "数据范围反推算法", "看到 n 的大小，先想自己最多能承担多少次基本操作。", 590,
            "经验值：C++ 一秒内大约能执行 10^8 次简单运算。")
    rows = [("n ≤ 10", "O(n!)  全排列枚举", "red"), ("n ≤ 20", "O(2^n)  子集枚举、状压", "red"),
            ("n ≤ 500", "O(n³)  Floyd、区间 DP", "orange"), ("n ≤ 5000", "O(n²)  朴素 DP、双重循环", "orange"),
            ("n ≤ 10^5", "O(n log n)  排序、二分、线段树", "blue"), ("n ≤ 10^6", "O(n)，或小常数的 O(n log n)", "green"),
            ("n ≥ 10^9", "O(log n) 或 O(1)  数学公式、二分", "purple")]
    for i, (a, b, k) in enumerate(rows):
        y = 108 + i * 60
        f.rect(32, y, 936, 48, k)
        f.text(56, y + 31, a, 19, PALETTE[k][1], "700")
        f.text(250, y + 31, b, 18)
    return f.save()


def growth():
    f = Fig("c0-growth", "n = 10^5 时各复杂度的操作次数", "横轴是操作次数取以 10 为底的对数，越靠右越慢。", 520,
            "超过虚线（约 10^8）的写法，一秒内通常跑不完。")
    rows = [("O(log n)", "约 17", 17, "green"), ("O(n)", "10^5", 1e5, "green"),
            ("O(n log n)", "约 1.7×10^6", 1.7e6, "green"), ("O(n√n)", "约 3.2×10^7", 3.2e7, "blue"),
            ("O(n²)", "10^10", 1e10, "red")]
    x0, unit = 270, 62
    for i, (name, val, v, k) in enumerate(rows):
        y = 140 + i * 66
        f.text(32, y + 28, name, 20, PALETTE[k][1], "700")
        w = math.log10(v) * unit
        f.rect(x0, y, w, 40, k, r=6)
        f.text(x0 + w - 12, y + 28, val, 17, anchor="end")
    xl = x0 + 8 * unit
    ln(f, xl, 112, xl, 480, PALETTE["red"][1], dash=True)
    f.text(xl, 104, "10^8", 16, PALETTE["red"][1], "700", "middle")
    return f.save()


def fib_tree():
    f = Fig("c0-fib-tree", "fib(5) 的递归树", "同一个子问题被重复计算：fib(3) 算了 2 次，fib(2) 算了 3 次。", 560,
            "每个节点是一次函数调用，共 15 个；n 增大时节点数按指数增长。")
    cnt = [0]
    nodes = []

    def build(n, d):
        if n < 2:
            node = (n, d, 70 + cnt[0] * 118, [])
            cnt[0] += 1
        else:
            kids = [build(n - 1, d + 1), build(n - 2, d + 1)]
            node = (n, d, sum(k[2] for k in kids) / 2, kids)
        nodes.append(node)
        return node

    build(5, 0)
    kind = {5: "grey", 4: "blue", 3: "orange", 2: "red", 1: "green", 0: "green"}
    for n, d, x, kids in nodes:
        for k in kids:
            ln(f, x, 135 + d * 82 + 17, k[2], 135 + k[1] * 82 - 17)
    for n, d, x, kids in nodes:
        f.chip(x, 135 + d * 82, 84, 34, kind[n], f"fib({n})", 15)
    return f.save()


def merge_levels():
    f = Fig("c0-merge-levels", "归并排序的递归树", "每一层所有节点的规模加起来都是 n，一共 log n 层。", 540,
            "总代价 = 每层代价 n × 层数 log n = O(n log n)。")
    labels = ["n", "n/2", "n/4", "n/8"]
    kinds = ["blue", "green", "orange", "purple"]
    for k in range(4):
        y = 110 + k * 80
        cnt, gap = 2 ** k, 8
        w = (700 - gap * (cnt - 1)) / cnt
        for j in range(cnt):
            x = 48 + j * (w + gap)
            f.rect(x, y, w, 46, kinds[k])
            f.text(x + w / 2, y + 30, labels[k], 17, INK, anchor="middle")
        f.text(780, y + 20, f"{cnt} 个子问题", 16, SUB)
        f.text(780, y + 42, "本层合计 n", 16, PALETTE[kinds[k]][1], "700")
    f.text(48, 450, "……  继续对半，直到规模为 1（共 log n 层）", 17, SUB)
    return f.save()


def checker_flow():
    f = Fig("c0-checker-flow", "对拍的流程", "随机生成数据，让快解法与暴力解法各算一遍，不一致就停下。", 470,
            "暴力解法慢但简单可靠，它是判断对错的标准答案。")
    f.chip(110, 250, 170, 70, "purple", "gen\n随机数据生成器", 16)
    f.chip(280, 250, 130, 50, "white", "data.in")
    f.chip(470, 160, 170, 62, "blue", "sol\n你的解法")
    f.chip(470, 340, 170, 62, "green", "brute\n暴力解法")
    f.chip(650, 160, 120, 44, "white", "sol.out")
    f.chip(650, 340, 120, 44, "white", "brute.out")
    f.chip(860, 250, 150, 56, "orange", "比较输出")
    f.chip(590, 412, 300, 52, "green", "相同：再生成下一组数据")
    f.chip(870, 412, 230, 52, "red", "不同：保存 data.in 并停止")
    f.arrow(196, 250, 213, 250)
    f.arrow(345, 240, 383, 185)
    f.arrow(345, 262, 383, 325)
    f.arrow(556, 160, 588, 160)
    f.arrow(556, 340, 588, 340)
    f.arrow(710, 175, 795, 235)
    f.arrow(710, 340, 795, 268)
    f.path("M830 280L830 340L728 340L728 384")
    f.arrow(880, 280, 880, 386)
    return f.save()


def build_all():
    w = []
    for fn in (range_table, growth, fib_tree, merge_levels, checker_flow):
        w += fn()
    return w
