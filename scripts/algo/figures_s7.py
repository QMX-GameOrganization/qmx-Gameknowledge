"""第 7 章（字符串）用到的配图。"""
from svglib import Fig, GREY, SUB, INK, PALETTE

BLUE, GREEN, ORANGE, RED, PURPLE = (PALETTE[k][1] for k in ("blue", "green", "orange", "red", "purple"))


def cells(f, x, y, items, w=56, h=46, kinds=None, size=20, idx=True, mono=True, start=0):
    """一排方格，返回各格中心 x。kinds 可以是与 items 等长的颜色名列表。"""
    xs = []
    for i, s in enumerate(items):
        cx = x + i * w + w / 2
        f.chip(cx, y, w - 6, h, kinds[i] if kinds else "white", s, size, mono)
        if idx:
            f.text(cx, y + h / 2 + 19, str(i + start), 13, SUB, anchor="middle")
        xs.append(cx)
    return xs


def roadmap():
    f = Fig("c7-roadmap", "第 7 章路线：先学三个基础工具，再按需补进阶", "哈希、KMP、Z 函数是主线；带 ★ 的进阶算法互相独立。", 500,
            "实线是必需的前置；虚线表示用到相近的思想，先学 KMP / Z 函数会更轻松。")
    for i, (k, t, a, b) in enumerate([
        ("blue", "7.1 字符串哈希", "把子串变成一个整数", "O(1) 比较任意两个子串"),
        ("green", "7.2 KMP", "前缀函数 / border", "线性时间做单模式匹配"),
        ("orange", "7.3 Z 函数", "每个位置与整串的公共前缀", "另一种线性匹配思路"),
    ]):
        x = 32 + i * 326
        f.box(x, 108, 284, 124, k, t, [a, b], 16)
    labels = [
        ("purple", "7.4 ★Manacher", "线性求所有", "回文半径"),
        ("purple", "7.5 ★AC 自动机", "多模式匹配", "（前置：KMP、Trie）"),
        ("purple", "7.6 ★后缀数组", "后缀排序 + LCP", "子串问题通用工具"),
        ("purple", "7.7 ★后缀自动机", "与回文自动机", "最强的子串结构"),
        ("purple", "7.8 ★最小表示法", "循环同构的", "最小旋转"),
    ]
    for i, (k, t, a, b) in enumerate(labels):
        x = 32 + i * 190
        f.rect(x, 292, 176, 140, k)
        num, name = t.split(" ", 1)
        f.text(x + 12, 322, num, 15, PURPLE, "700")
        f.text(x + 12, 346, name, 16, PURPLE, "700", maxw=150)
        f.text(x + 12, 378, a, 14, INK, maxw=150)
        f.text(x + 12, 402, b, 13, SUB, maxw=156)
    f.arrow(440, 232, 330, 290, GREY)                 # 7.2 -> 7.5
    f.arrow(520, 232, 500, 290, GREY, dash=True)      # 7.2 ⇢ 7.6（虚线：思想相近）
    f.arrow(826, 232, 700, 290, GREY, dash=True)      # 7.3 ⇢ 7.7（虚线）
    return f.save()


def hash_prefix():
    f = Fig("c7-hash-prefix", "前缀哈希：用两个前缀值 O(1) 算出任意子串的哈希", "以十进制为例：a=1, b=2, c=3，底数取 10，字符串 abcab。", 570,
            "真实代码里底数是随机大数，模数取 2^61-1；除了不会进位，公式完全一样。")
    s = "abcab"
    vals = [1, 2, 3, 1, 2]
    f.text(32, 120, "字符串与编号", 17, BLUE, "700")
    cells(f, 60, 170, list(s), 70, 50, ["white"] * 5, 24)
    cells(f, 60, 236, [str(v) for v in vals], 70, 40, ["grey"] * 5, 20, idx=False)
    f.text(32, 330, "前缀哈希 H[i] = 前 i 个字符组成的数", 17, GREEN, "700")
    hs = ["0", "1", "12", "123", "1231", "12312"]
    for i, h in enumerate(hs):
        cx = 60 + i * 88 + 40
        f.chip(cx, 382, 80, 40, "green" if i in (2, 5) else "white", h, 18, True)
        f.text(cx, 416, f"H[{i}]", 13, SUB, anchor="middle")
    f.rect(540, 108, 430, 142, "orange")
    f.text(556, 138, "取子串 s[2,5) = \"cab\"", 17, ORANGE, "700")
    f.text(556, 168, "get(l, r) = H[r] - H[l] × B^(r-l)", 16, INK, mono=True, maxw=400)
    f.text(556, 198, "= 12312 - 12 × 10^3", 16, INK, mono=True)
    f.text(556, 226, "= 312   （c=3, a=1, b=2 ✓）", 16, INK, mono=True)
    f.text(32, 470, "H[2]=12 乘上 B^3 后，刚好对齐 H[5] 的前两位，相减就剩下后三位。", 16, INK)
    f.text(32, 496, "取模之后同样成立：H[r] - H[l]×B^(r-l)，结果再模 MOD。", 16, INK)
    return f.save()


def hash_binary():
    f = Fig("c7-hash-binary", "二分答案 + 哈希：求最长重复子串", "banana：长度 L 可行（存在出现两次的子串）是单调的，L=3 有 \"ana\"。", 510,
            "每次探测 O(n)：把所有长度为 L 的子串哈希放进表，看有没有重复；二分共 O(log n) 次。")
    ok = {1: "a", 2: "an", 3: "ana", 4: "无", 5: "无"}
    f.text(32, 118, "长度 L", 16, SUB)
    for i, L in enumerate(range(1, 6)):
        cx = 150 + i * 140
        kind = "green" if L <= 3 else "red"
        f.chip(cx, 170, 120, 56, kind, f"L={L}\n{'可行 ' + ok[L] if L <= 3 else '不可行'}", 16, False)
    f.text(32, 262, "二分过程（lo=0, hi=5，mid 取上中位数）", 17, BLUE, "700")
    steps = [("mid=3", "存在重复 ana", "lo=3", "green"), ("mid=4", "没有重复", "hi=3", "red")]
    for i, (a, b, c, k) in enumerate(steps):
        y = 312 + i * 62
        f.chip(110, y, 120, 44, "white", a, 17, True)
        f.chip(380, y, 250, 44, k, b, 17)
        f.chip(640, y, 120, 44, "white", c, 17, True)
        f.arrow(172, y, 252, y)
        f.arrow(506, y, 578, y)
    f.text(32, 440, "lo == hi == 3，答案长度 3。", 17, GREEN, "700")
    return f.save()


def kmp_border():
    f = Fig("c7-kmp-border", "border：既是前缀又是后缀的真子串", "字符串 ababa 的 border 链：3 → 1 → 0。", 570,
            "pi[i] 取最长的 border；更短的 border 一定是最长 border 自己的 border，所以沿 pi 一路跳就能枚举全部。")
    s = list("ababa")
    f.text(32, 118, "s = ababa，最长 border 是 aba（长度 3）", 17, BLUE, "700")
    cells(f, 60, 170, s, 70, 50, ["white"] * 5, 24)
    pre = ["green", "green", "green", "white", "white"]
    suf = ["white", "white", "orange", "orange", "orange"]
    f.text(32, 258, "前缀 s[0,3)", 15, GREEN, "700")
    cells(f, 60, 282, list("aba"), 70, 40, ["green"] * 3, 20, idx=False)
    f.text(32, 336, "后缀 s[2,5)", 15, ORANGE, "700")
    cells(f, 60 + 2 * 70, 360, list("aba"), 70, 40, ["orange"] * 3, 20, idx=False)
    f.text(430, 300, "两段内容都是 aba，", 16, INK)
    f.text(430, 326, "所以 border 长度 3。", 16, INK)
    f.text(32, 424, "border 链：对 aba 再找 border，就是 pi[2] = 1（a）；再往下 pi[0] = 0。", 16, INK)
    f.chip(120, 468, 110, 44, "green", "长度 3 aba", 16)
    f.chip(400, 468, 110, 44, "blue", "长度 1 a", 16)
    f.chip(660, 468, 110, 44, "grey", "长度 0 空", 16)
    f.arrow(176, 468, 344, 468)
    f.arrow(456, 468, 604, 468)
    f.text(260, 456, "pi[3-1]=pi[2]=1", 13, SUB, anchor="middle")
    f.text(530, 456, "pi[1-1]=pi[0]=0", 13, SUB, anchor="middle")
    return f.save()


def kmp_build():
    f = Fig("c7-kmp-build", "构建 pi：失配时沿 border 链往回退", "s = aabaaab，逐位算出 pi = 0 1 0 1 2 2 3，重点看 i=5 的回退。", 640,
            "每个位置只会让 j 增加 1，回退的总次数不超过增加的总次数，所以整个构建是 O(n)。")
    s_ = "aabaaab"
    pi = [0, 1, 0, 1, 2, 2, 3]
    kinds = ["white"] * 7
    kinds[5] = "orange"
    f.text(32, 118, "下标 / 字符 / pi", 16, SUB)
    cells(f, 60, 170, list(s_), 80, 48, kinds, 24)
    cells(f, 60, 250, [str(x) for x in pi], 80, 40, ["grey"] * 7, 20, idx=False)
    f.text(32, 330, "i = 5 时发生了一次回退（s[5] = a）", 18, ORANGE, "700")
    steps = [
        ("blue", "起点", "j = pi[4] = 2：s[0,2)=aa 是 s[0,5) 的 border，试着把它延长一位"),
        ("red", "失配", "s[5]=a 对 s[2]=b：不相等，j = pi[j-1] = pi[1] = 1（换成更短的 border a）"),
        ("green", "匹配", "s[5]=a 对 s[1]=a：相等，j++ 得 2，所以 pi[5] = 2"),
    ]
    for i, (k, a, b) in enumerate(steps):
        y = 388 + i * 62
        f.chip(100, y, 90, 42, k, a, 17, bold=True)
        f.text(170, y + 6, b, 16, INK, maxw=800)
    f.text(32, 575, "i = 6：j = pi[5] = 2，s[6]=b 对 s[2]=b 相等，j = 3，pi[6] = 3。", 16, GREEN, "700")
    return f.save()


def kmp_match():
    f = Fig("c7-kmp-match", "KMP 匹配：失配后模式串右移，已匹配的部分不再比较", "text = abababcab，pat = ababc（pi = 0 0 1 2 0）。", 540,
            "文本指针 i 从不后退；失配时只改 j = pi[j-1]，相当于把模式串直接滑到下一个可能的位置。")
    t = list("abababcab")
    w = 64
    x0 = 40
    f.text(32, 118, "文本", 16, SUB)
    cells(f, x0, 160, t, w, 46, None, 22)
    f.text(32, 250, "第一次对齐（偏移 0）：比到 text[4] 失配", 16, RED, "700")
    kinds = ["green"] * 4 + ["red"]
    cells(f, x0, 300, list("ababc"), w, 46, kinds, 22, idx=False)
    f.text(x0 + 5 * w + 14, 306, "a ≠ c", 16, RED, "700")
    f.text(32, 380, "j=4 失配，j = pi[3] = 2：模式串右移 4-2 = 2 位", 16, GREEN, "700")
    kinds2 = ["grey", "grey", "green", "green", "green"]
    cells(f, x0 + 2 * w, 430, list("ababc"), w, 46, kinds2, 22, idx=False)
    f.text(x0 + 2 * w, 482, "灰色两格 ab 已确认相等，从 pat[2] 接着比", 14, SUB)
    f.text(x0 + 7 * w + 14, 436, "完整匹配", 16, GREEN, "700")
    f.text(x0 + 7 * w + 14, 460, "起点 = 2", 15, INK)
    return f.save()


def z_def():
    f = Fig("c7-z-def", "Z 函数：每个位置与整串的最长公共前缀", "s = aabxaab，z[4] = 3 表示 s[4..] 的前 3 个字符等于 s 的前 3 个字符。", 530,
            "z[0] 按约定取 n；用 z[i] == 模式串长度判断匹配，可以替代 KMP。")
    s_ = "aabxaab"
    z = [7, 1, 0, 0, 3, 1, 0]
    f.text(32, 118, "字符串 s", 16, SUB)
    kinds = ["green"] * 3 + ["white"] * 4
    cells(f, 60, 168, list(s_), 80, 48, kinds, 24)
    f.text(32, 262, "从 i=4 开始的后缀 s[4..]，对齐到串首来比较", 16, ORANGE, "700")
    cells(f, 60, 312, list("aab"), 80, 48, ["orange"] * 3, 24, idx=False)
    f.text(60 + 3 * 80 + 14, 318, "与前缀 aab 完全相同，所以 z[4] = 3", 16, INK)
    f.text(32, 392, "z 数组", 16, SUB)
    cells(f, 60, 430, [str(x) for x in z], 80, 40, ["grey"] * 7, 20, idx=False)
    return f.save()


def z_window():
    f = Fig("c7-z-window", "Z 算法的 [l, r) 窗口：先抄答案，再往右扩", "s = aabaaab 求 z[4]：此时最靠右的窗口是 [3, 5)，即 s[3,5) = s[0,2) = aa。", 590,
            "r 只增不减，往右扩的次数总共不超过 n，所以是 O(n)。")
    s_ = "aabaaab"
    kinds = ["green", "green", "white", "orange", "orange", "white", "white"]
    f.text(32, 118, "下标 / 字符", 16, SUB)
    cells(f, 60, 168, list(s_), 80, 48, kinds, 24)
    f.text(60, 230, "前缀 aa", 14, GREEN, "700")
    f.text(60 + 3 * 80, 230, "窗口 [3,5)", 14, ORANGE, "700")
    f.text(32, 290, "求 z[4]（i=4 在窗口内，i - l = 1）", 18, BLUE, "700")
    steps = [
        ("blue", "抄", "窗口内 s[3,5) 与 s[0,2) 相同，所以 s[4] 对应 s[1]，已知 z[1] = 1"),
        ("grey", "取小", "z[4] 至少是 min(r - i, z[1]) = min(1, 1) = 1，不会超出窗口"),
        ("green", "扩", "窗口之外继续比：s[1]=a 对 s[5]=a 相等，s[2]=b 对 s[6]=b 相等，z[4] = 3"),
        ("orange", "更新", "i + z[i] = 7 > r，窗口改为 [4, 7)"),
    ]
    for i, (k, a, b) in enumerate(steps):
        y = 346 + i * 52
        f.chip(100, y, 90, 40, k, a, 17, bold=True)
        f.text(170, y + 6, b, 16, INK, maxw=800)
    return f.save()


def manacher_transform():
    f = Fig("c7-manacher-transform", "插入分隔符，把偶回文变成奇回文", "s = abaaba → t = #a#b#a#a#b#a#；p[i] 是 t 中以 i 为中心的回文半径（含中心）。", 470,
            "原串回文长度 = p[i] - 1；起点 = (i - p[i] + 1) / 2。")
    t = "#a#b#a#a#b#a#"
    p = [1, 2, 1, 4, 1, 2, 7, 2, 1, 4, 1, 2, 1]
    kinds = ["orange" if i == 6 else ("green" if i == 3 else "white") for i in range(13)]
    f.text(36, 118, "变换串 t", 16, SUB)
    cells(f, 36, 164, list(t), 70, 46, kinds, 22)
    f.text(36, 252, "p 数组", 16, SUB)
    cells(f, 36, 292, [str(x) for x in p], 70, 40, ["grey"] * 13, 20, idx=False)
    f.text(36, 372, "i=6（# 在两个 a 之间）：p=7，覆盖整个 t，原串长度 7-1 = 6，即 abaaba。", 16, ORANGE, "700")
    f.text(36, 402, "i=3（字符 b）：p=4，覆盖 t[0..6]，原串长度 3，即 aba。", 16, GREEN, "700")
    return f.save()


def manacher_mirror():
    f = Fig("c7-manacher-mirror", "Manacher 的镜像：右半边的半径可以由左半边推出来", "已知以 c=6 为中心的大回文 [0, 13)，求 i=9 的半径：镜像点 j = 2c - i = 3。", 560,
            "p[i] 先取 min(r - i, p[j])，再尝试往右扩；r 只右移，所以整体 O(n)。")
    t = "#a#b#a#a#b#a#"
    kinds = ["white"] * 13
    kinds[6] = "purple"
    kinds[3] = "green"
    kinds[9] = "orange"
    cells(f, 36, 160, list(t), 70, 46, kinds, 22)
    # 大回文条
    f.rect(36 + 3, 236, 70 * 13 - 6, 34, "purple")
    f.text(500, 259, "中心 c=6，半径 7，覆盖 t[0..12]（r = 13）", 15, PURPLE, "700", "middle")
    # j 的回文
    f.rect(36 + 3, 288, 70 * 7 - 6, 34, "green")
    f.text(36 + 3 + 70 * 3.5 - 3, 311, "以 j=3 为中心，p[3]=4", 15, GREEN, "700", "middle")
    # i 的回文
    f.rect(36 + 6 * 70 + 3, 340, 70 * 7 - 6, 34, "orange")
    f.text(36 + 6 * 70 + 3 + 70 * 3.5 - 3, 363, "以 i=9 为中心，p[9]=4", 15, ORANGE, "700", "middle")
    f.text(36, 420, "r - i = 13 - 9 = 4，p[j] = 4，所以 p[9] 先取 min(4, 4) = 4。", 16, INK)
    f.text(36, 450, "再往右扩：i + 4 = 13 已经越过 t 的末尾，不用比较，p[9] = 4。", 16, INK)
    f.text(36, 480, "如果 p[j] 比 r - i 小，答案就是 p[j]，一次比较都不用做。", 16, INK)
    return f.save()


def ac_trie():
    f = Fig("c7-ac-trie", "AC 自动机 = Trie + fail 指针", "模式串 he、she、his、hers。绿色是某个模式串的结尾；橙色虚线是 fail 指针。", 650,
            "fail 指针指向“当前串的最长真后缀中，同样是 Trie 里某个节点”的那个节点；没画出的箭头都指向根。")
    nodes = {
        "root": (480, 150, "根", "grey"), "s": (250, 250, "s", "white"), "sh": (250, 350, "sh", "white"),
        "she": (250, 450, "she", "green"), "h": (710, 250, "h", "white"), "he": (590, 350, "he", "green"),
        "hi": (830, 350, "hi", "white"), "her": (590, 450, "her", "white"), "his": (830, 450, "his", "green"),
        "hers": (590, 550, "hers", "green"),
    }
    for x, y, t, k in nodes.values():
        f.chip(x, y, 96, 40, k, t, 17, True)
    def edge(a, b, label, lx, ly):
        (x1, y1, _, _), (x2, y2, _, _) = nodes[a], nodes[b]
        dx, dy = x2 - x1, y2 - y1
        n = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / n, dy / n
        f.arrow(round(x1 + ux * 26), round(y1 + uy * 26), round(x2 - ux * 30), round(y2 - uy * 30), GREY)
        f.text(lx, ly, label, 15, INK, "700", "middle")
    edge("root", "s", "s", 340, 190)
    edge("root", "h", "h", 630, 190)
    edge("s", "sh", "h", 232, 305)
    edge("sh", "she", "e", 232, 405)
    edge("h", "he", "e", 640, 300)
    edge("h", "hi", "i", 790, 300)
    edge("he", "her", "r", 574, 405)
    edge("her", "hers", "s", 574, 505)
    edge("hi", "his", "s", 814, 405)
    f.arrow(300, 340, 660, 262, ORANGE, dash=True)      # sh -> h
    f.arrow(300, 440, 540, 360, ORANGE, dash=True)      # she -> he
    f.text(470, 282, "fail(sh)=h", 14, ORANGE, "700", "middle")
    f.text(400, 440, "fail(she)=he", 14, ORANGE, "700", "middle")
    f.text(660, 560, "his、hers 的 fail 都是 s（图中省略），", 15, INK)
    f.text(660, 586, "其余节点的 fail 都是根。", 15, INK)
    return f.save()


def ac_match():
    f = Fig("c7-ac-match", "在自动机上扫描文本 ushers", "每读一个字符走一步；到达节点时，它和它 fail 链上的所有模式串结尾都算出现一次。", 560,
            "代码里不是逐步沿 fail 链数，而是先给到达的节点计数，最后按 BFS 逆序把计数累加到 fail 父亲。")
    cols = [(110, "读入"), (270, "到达节点"), (560, "这一步新增的出现")]
    for x, t in cols:
        f.text(x, 122, t, 16, SUB, anchor="middle")
    rows = [
        ("u", "根（根上没有 u 边，留在根）", "无", "white"),
        ("s", "s", "无", "white"),
        ("h", "sh", "无", "white"),
        ("e", "she", "she，再沿 fail 到 he：he", "green"),
        ("r", "her（she 无 r 边，借 he 的 r 边）", "无", "white"),
        ("s", "hers", "hers", "green"),
    ]
    for i, (c, node, out, k) in enumerate(rows):
        y = 170 + i * 56
        f.chip(110, y, 70, 42, "white", c, 20, True)
        f.chip(310, y, 330, 42, "white", node, 15)
        f.chip(700, y, 300, 42, k, out, 15)
    f.text(32, 520, "合计：he 1 次，she 1 次，hers 1 次，his 0 次。", 17, GREEN, "700")
    return f.save()


def sa_banana():
    f = Fig("c7-sa-banana", "后缀数组与 height：banana 的 6 个后缀", "sa[i] 是排名第 i 的后缀的起点；height[i] 是它与前一名后缀的最长公共前缀。", 600,
            "本质不同的子串个数 = n(n+1)/2 - Σheight = 21 - 6 = 15。最长重复子串 = 最大的 height 对应的公共前缀 ana。")
    s_ = "banana"
    f.text(40, 122, "排序前（按起点）", 16, SUB)
    for i in range(6):
        f.chip(150, 170 + i * 56, 220, 42, "white", f"{i}   {s_[i:]}", 20, True)
    f.arrow(280, 300, 400, 300, GREY)
    f.text(340, 286, "按字典序排序", 14, SUB, anchor="middle")
    for x, t in [(450, "排名"), (530, "sa"), (620, "height"), (780, "后缀（绿底=公共前缀）")]:
        f.text(x, 122, t, 15, SUB, anchor="start" if x == 780 else "middle")
    sa = sorted(range(6), key=lambda i: s_[i:])
    h = [0] * 6
    for r in range(1, 6):
        a, b = s_[sa[r - 1]:], s_[sa[r]:]
        while h[r] < min(len(a), len(b)) and a[h[r]] == b[h[r]]:
            h[r] += 1
    for r in range(6):
        y = 170 + r * 56
        f.chip(450, y, 56, 42, "grey", str(r), 20, True)
        f.chip(530, y, 56, 42, "blue", str(sa[r]), 20, True)
        f.chip(620, y, 70, 42, "orange" if h[r] else "white", str(h[r]), 20, True)
        if h[r]:
            f.rect(776, y - 16, 13.2 * h[r] + 8, 32, "green", r=6)
        f.text(780, y + 8, s_[sa[r]:], 22, INK, mono=True)
    f.text(40, 540, "height[2]=3：anana 和 ana 的公共前缀是 ana；height[5]=2：nana 和 na 的公共前缀是 na。", 15, INK)
    return f.save()


def sa_doubling():
    f = Fig("c7-sa-doubling", "倍增法：排序键的长度 1 → 2 → 4，每轮用上一轮的排名拼成二元组", "banana 一共只需要两轮：按首 2 个字符、再按首 4 个字符排序，排名就全部不同了。", 600,
            "每轮是两次计数排序，共 O(log n) 轮，所以总复杂度 O(n log n)。")
    s_ = "banana"
    n = 6

    def dense(keys):
        u = sorted(set(keys))
        return [u.index(k) for k in keys]

    rk1 = dense([s_[i] for i in range(n)])
    pair1 = [(rk1[i], rk1[i + 1] if i + 1 < n else -1) for i in range(n)]
    rk2 = dense(pair1)
    pair2 = [(rk2[i], rk2[i + 2] if i + 2 < n else -1) for i in range(n)]
    rk4 = dense(pair2)
    rows = [
        ("起点 i", [str(i) for i in range(n)], "grey"),
        ("字符", list(s_), "white"),
        ("rk（首 1 个字符）", [str(x) for x in rk1], "blue"),
        ("键 (rk[i], rk[i+1])", [f"({a},{b})" for a, b in pair1], "white"),
        ("rk（首 2 个字符）", [str(x) for x in rk2], "green"),
        ("键 (rk[i], rk[i+2])", [f"({a},{b})" for a, b in pair2], "white"),
        ("rk（首 4 个字符）", [str(x) for x in rk4], "orange"),
    ]
    for r, (name, vals, k) in enumerate(rows):
        y = 150 + r * 52
        f.text(32, y + 6, name, 15, SUB, maxw=200)
        for c, v in enumerate(vals):
            f.chip(330 + c * 110, y, 96, 40, k, v, 17, True)
    f.text(32, 524, "最后一行 rk 全部不同（0..5 各出现一次），排序结束；rk 就是后缀 i 的排名。", 16, GREEN, "700")
    return f.save()


def sam_abcbc():
    f = Fig("c7-sam-abcbc", "abcbc 的后缀自动机：8 个状态", "每个状态是一组“结束位置集合相同”的子串；实线是转移，框内第三行是后缀链接 link。", 560,
            "状态 5（{b}）是克隆状态：加入第 4 个字符 b 时，从状态 2 拆出来（原来状态 2 同时装着 ab 和 b）。")
    nodes = {
        0: (100, 335, "0 · len=0\n{空串}\nlink: -"),
        1: (270, 165, "1 · len=1\n{a}\nlink→0"),
        2: (470, 165, "2 · len=2\n{ab}\nlink→5"),
        3: (670, 165, "3 · len=3\n{abc}\nlink→7"),
        4: (870, 165, "4 · len=4\n{abcb,bcb,cb}\nlink→5"),
        5: (270, 335, "5 · len=1\n{b}\nlink→0"),
        7: (570, 335, "7 · len=2\n{c,bc}\nlink→0"),
        6: (870, 335, "6 · len=5\n{abcbc,bcbc,cbc}\nlink→7"),
    }
    for k, (x, y, t) in nodes.items():
        w = 150 if k in (4, 6) else 130
        f.chip(x, y, w, 78, "green" if k in (6,) else ("grey" if k == 0 else "white"), t, 14)
    f.arrow(105, 296, 205, 206, GREY); f.text(140, 240, "a", 15, INK, "700", "middle")
    f.arrow(157, 335, 203, 335, GREY); f.text(180, 325, "b", 15, INK, "700", "middle")
    f.path("M100 374 L100 470 L570 470 L570 376", GREY); f.text(335, 462, "c", 15, INK, "700", "middle")
    f.arrow(335, 165, 405, 165, GREY); f.text(370, 155, "b", 15, INK, "700", "middle")
    f.arrow(535, 165, 605, 165, GREY); f.text(570, 155, "c", 15, INK, "700", "middle")
    f.arrow(735, 165, 795, 165, GREY); f.text(765, 155, "b", 15, INK, "700", "middle")
    f.arrow(870, 204, 870, 296, GREY); f.text(886, 255, "c", 15, INK, "700", "middle")
    f.arrow(335, 335, 505, 335, GREY); f.text(420, 325, "c", 15, INK, "700", "middle")
    f.arrow(640, 296, 815, 206, GREY); f.text(745, 262, "b", 15, INK, "700", "middle")
    f.text(32, 510, "沿 link 把各状态的 len 差相加：Σ(len[v] - len[link[v]]) = 12，就是 abcbc 本质不同的子串个数。", 15, INK)
    return f.save()


def pam_abaab():
    f = Fig("c7-pam-abaab", "abaab 的回文自动机：5 个本质不同的回文串", "两个根：奇根（len=-1）和偶根（len=0）；实线是“两侧各加一个字符”，虚线是 link（最长回文真后缀）。", 640,
            "节点数 - 2 = 本质不同的回文子串个数；每个节点的出现次数沿 link 从长到短累加。")
    pos = {"odd": (300, 160), "even": (700, 160), "a": (150, 300), "b": (410, 300), "aa": (700, 300), "aba": (410, 440), "baab": (700, 440)}
    txt = {"odd": "奇根 len=-1", "even": "偶根 len=0", "a": "a", "b": "b", "aa": "aa", "aba": "aba", "baab": "baab"}
    kind = {"odd": "grey", "even": "grey"}
    for k, (x, y) in pos.items():
        f.chip(x, y, 130 if k in ("odd", "even") else 90, 42, kind.get(k, "green"), txt[k], 16, True)
    f.arrow(270, 182, 175, 278, GREY); f.text(205, 222, "a", 15, INK, "700", "middle")
    f.arrow(325, 182, 385, 278, GREY); f.text(369, 222, "b", 15, INK, "700", "middle")
    f.arrow(700, 182, 700, 278, GREY); f.text(716, 232, "a", 15, INK, "700", "middle")
    f.arrow(410, 322, 410, 418, GREY); f.text(426, 372, "a", 15, INK, "700", "middle")
    f.arrow(700, 322, 700, 418, GREY); f.text(716, 372, "b", 15, INK, "700", "middle")
    o = ORANGE
    f.arrow(370, 424, 185, 322, o, dash=True)           # aba -> a
    f.arrow(660, 424, 440, 322, o, dash=True)           # baab -> b
    f.path("M680 322 Q440 700 160 322", o, True)        # aa -> a
    f.text(32, 590, "虚线 link：aba→a，aa→a，baab→b；a 和 b 的 link 是偶根（空串）。", 15, INK)
    return f.save()


def minrot_trace():
    f = Fig("c7-minrot-trace", "最小表示法：两个候选起点 i、j，比较失败的一方被整段淘汰", "s = cabcab，把 s 看成环，求字典序最小的旋转。", 560,
            "每次比较失败，被淘汰的候选是 i..i+k 或 j..j+k 共 k+1 个起点，i+j 总共最多增长 2n，所以 O(n)。")
    for x, t in [(60, "i"), (130, "j"), (200, "k"), (330, "比较的两个字符"), (700, "动作")]:
        f.text(x, 122, t, 16, SUB, anchor="middle")
    rows = [
        (0, 1, 0, "s[0]=c  对  s[1]=a", "c > a：i 出局，i = 1（与 j 相同，j 后移到 2）", "red"),
        (1, 2, 0, "s[1]=a  对  s[2]=b", "a < b：j 出局，j = 3", "orange"),
        (1, 3, 0, "s[1]=a  对  s[3]=c", "a < c：j 出局，j = 4", "orange"),
        (1, 4, 0, "连续 6 个字符都相等", "k 涨到 6 = n，两个候选等价，结束，答案 min(1,4) = 1", "green"),
    ]
    for r, (i, j, k, cmp_, act, kd) in enumerate(rows):
        y = 170 + r * 62
        for x, v in [(60, i), (130, j), (200, "0→6" if r == 3 else k)]:
            f.chip(x, y, 50, 44, "white", str(v), 16 if r == 3 and x == 200 else 18, True)
        f.chip(330, y, 190, 44, "white", cmp_, 14)
        f.chip(725, y, 400, 44, kd, act, 13)
    f.text(32, 440, "答案：从下标 1 开始的旋转", 17, GREEN, "700")
    cells(f, 60, 492, list("cabcab"), 60, 40, ["white", "green", "green", "green", "green", "green"], 20, idx=False)
    f.text(60 + 6 * 60 + 14, 498, "→ abcabc", 18, GREEN, "700")
    return f.save()


def build_all():
    """调用本模块里所有绘图函数（名字不以下划线开头、且不是辅助函数）。"""
    warns = []
    for name, fn in list(globals().items()):
        if callable(fn) and getattr(fn, "__module__", None) == __name__ and name not in ("cells", "build_all"):
            if fn.__code__.co_argcount == 0:
                warns += fn()
    return warns
