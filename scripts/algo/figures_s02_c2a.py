"""第 2 章配图（上）：单调栈、单调队列、离散化。"""
from svglib import Fig, GREY, SUB, INK, PALETTE
from figures_s02_c0a import ln


def monostack():
    f = Fig("c2-monostack", "单调栈求「下一个更大的数」", "a = [2, 7, 3, 4, 8, 5]。栈内从栈底到栈顶递减，新元素更大就弹出并回答。", 600,
            "每个元素最多入栈一次、出栈一次，整体 O(n)。栈里剩下的 8 和 5 没有更大的数。")
    a = [2, 7, 3, 4, 8, 5]
    stacks = [[2], [7], [7, 3], [7, 4], [8], [8, 5]]
    pops = [("", ""), ("弹出 2", "2 的答案是 7"), ("", ""), ("弹出 3", "3 的答案是 4"),
            ("弹出 4 和 7", "答案都是 8"), ("", "")]
    for i in range(6):
        x, w = 32 + i * 156, 146
        f.chip(x + w / 2, 140, w, 42, "grey", f"i={i}  a={a[i]}", 16)
        f.rect(x, 180, w, 270, "white", opacity=".6")
        for j, v in enumerate(stacks[i]):
            f.chip(x + w / 2, 398 - j * 48, 90, 38, "blue", str(v), 18, bold=True)
        f.text(x + w / 2, 439, "栈底", 13, SUB, anchor="middle")
        f.text(x + w / 2, 480, pops[i][0], 15, PALETTE["red"][1], "700", "middle", maxw=w - 6)
        f.text(x + w / 2, 504, pops[i][1], 14, INK, anchor="middle", maxw=w - 6)
    return f.save()


def monoqueue():
    f = Fig("c2-monoqueue", "单调队列求滑动窗口最大值", "a = [1, 3, -1, -3, 5, 3, 6, 7]，窗口长度 k = 3。队内保持从队首到队尾递减。", 640,
            "队首永远是当前窗口的最大值；过期的从队首出，更小的从队尾出，整体 O(n)。")
    a = [1, 3, -1, -3, 5, 3, 6, 7]
    dq = [[(0, 1)], [(1, 3)], [(1, 3), (2, -1)], [(1, 3), (2, -1), (3, -3)],
          [(4, 5)], [(4, 5), (5, 3)], [(6, 6)], [(7, 7)]]
    ans = ["", "", 3, 3, 5, 5, 6, 7]
    f.text(48, 118, "加入元素", 16, SUB, "700")
    f.text(210, 118, "队列内容（下标:值），绿色是队首", 16, SUB, "700")
    f.text(760, 118, "窗口最大值", 16, SUB, "700")
    for i in range(8):
        y = 140 + i * 54
        f.rect(32, y, 936, 46, "white", opacity=".6")
        f.text(48, y + 30, f"i={i}  a={a[i]}", 17)
        for j, (idx, v) in enumerate(dq[i]):
            f.chip(245 + j * 90, y + 23, 78, 34, "green" if j == 0 else "blue", f"{idx}:{v}", 16)
        if ans[i] != "":
            f.text(800, y + 31, str(ans[i]), 20, PALETTE["orange"][1], "700", "middle")
        else:
            f.text(800, y + 31, "窗口未满", 15, SUB, anchor="middle")
    return f.save()


def discretize_map():
    f = Fig("c2-discretize-map", "离散化：把数值换成排名", "a = [1000, 5, 99999, 5, 70]。先排序去重得到 v，再用 lower_bound 找每个数在 v 里的位置。", 560,
            "重复的数得到相同的编号，大小关系不变。")
    xs = [150 + i * 170 for i in range(5)]
    a = [1000, 5, 99999, 5, 70]
    v = [5, 70, 1000, 99999]
    vx = [235 + j * 170 for j in range(4)]
    f.text(32, 128, "原数组 a", 17, SUB, "700")
    f.text(32, 288, "排序去重后的 v（下标 0 到 3）", 17, SUB, "700")
    f.text(32, 448, "离散化后的结果（v 中的下标）", 17, SUB, "700")
    for i in range(5):
        f.chip(xs[i], 175, 110, 42, "blue", str(a[i]), 18)
        j = v.index(a[i])
        f.arrow(xs[i], 197, vx[j], 313, PALETTE["blue"][1])
        f.chip(xs[i], 480, 110, 42, "green", str(j), 18, bold=True)
    for j in range(4):
        f.chip(vx[j], 336, 110, 42, "orange", str(v[j]), 18)
        f.text(vx[j], 374, f"下标 {j}", 14, SUB, anchor="middle")
    return f.save()


def discretize_axis():
    f = Fig("c2-discretize-axis", "离散化压缩的是间距", "值域很大但只有几个不同的数时，只保留它们的相对顺序。", 420,
            "差值、比例都不保留，所以只适用于只关心大小关系的题目。")
    ln(f, 60, 170, 940, 170, GREY)
    ln(f, 60, 330, 940, 330, GREY)
    f.text(60, 118, "原数值轴（点之间可能隔很远）", 17, SUB, "700")
    f.text(60, 295, "压缩后的下标轴（编号连续）", 17, SUB, "700")
    old = [(100, "5"), (160, "70"), (470, "1000"), (880, "99999")]
    new = [(180, "0"), (400, "1"), (620, "2"), (840, "3")]
    for (ox, ol), (nx, nl) in zip(old, new):
        ln(f, ox, 178, nx, 322, PALETTE["blue"][1], dash=True, w=1)
        f.parts.append(f'<circle cx="{ox}" cy="170" r="8" fill="{PALETTE["blue"][1]}"/>')
        f.parts.append(f'<circle cx="{nx}" cy="330" r="8" fill="{PALETTE["green"][1]}"/>')
        f.text(ox, 152, ol, 16, PALETTE["blue"][1], "700", "middle")
        f.text(nx, 362, nl, 17, PALETTE["green"][1], "700", "middle")
    return f.save()


def build_all():
    w = []
    for fn in (monostack, monoqueue, discretize_map, discretize_axis):
        w += fn()
    return w
