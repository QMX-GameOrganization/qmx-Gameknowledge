"""第 8 章（数学）用到的配图。"""
import math
from svglib import Fig, GREY, SUB, INK, PALETTE


def circle(f, cx, cy, r, kind="blue", fill=None, stroke=None):
    bg, ink = PALETTE[kind]
    f.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill or bg}" stroke="{stroke or ink}" stroke-width="2"/>')


def table(f, x0, y0, widths, rows, header_kind="blue", row_h=46, size=15, mono=False, kinds=None):
    """rows[0] 是表头；kinds 为 {(行, 列): 配色}。每格用 chip 画，文字居中。"""
    kinds = kinds or {}
    y = y0
    for r, row in enumerate(rows):
        x = x0
        for c, cell in enumerate(row):
            w = widths[c]
            kind = header_kind if r == 0 else kinds.get((r, c), "white")
            f.chip(x + w / 2, y + row_h / 2, w - 6, row_h - 6, kind, cell, size, mono, bold=(r == 0 or (r, c) in kinds))
            x += w
        y += row_h
    return y


# ---------------------------------------------------------------- 8.1
def exgcd_trace():
    f = Fig("c8-exgcd-trace", "扩展欧几里得：先下潜求 gcd，再回溯还原 x、y",
            "以 exgcd(240, 46) 为例，目标是找到 240x + 46y = gcd。", 560,
            "回溯公式：x = y'，y = x' - (a/b)·y'（x'、y' 是下一层返回的值）。")
    rows = [["层", "(a, b)", "商 a/b", "回溯得到 (x, y)", "验证 a·x + b·y"],
            ["5", "(2, 0)", "-", "(1, 0)", "2·1 + 0·0 = 2"],
            ["4", "(4, 2)", "2", "(0, 1)", "4·0 + 2·1 = 2"],
            ["3", "(6, 4)", "1", "(1, -1)", "6·1 + 4·(-1) = 2"],
            ["2", "(10, 6)", "1", "(-1, 2)", "10·(-1) + 6·2 = 2"],
            ["1", "(46, 10)", "4", "(2, -9)", "46·2 + 10·(-9) = 2"],
            ["0", "(240, 46)", "5", "(-9, 47)", "240·(-9) + 46·47 = 2"]]
    kinds = {(6, 3): "green", (6, 4): "green", (1, 3): "orange"}
    table(f, 40, 105, [70, 170, 120, 250, 310], rows, row_h=48, kinds=kinds)
    f.text(40, 480, "上面从第 5 层（b = 0，gcd = a）开始往上读；递归时是从第 0 层往下走到第 5 层。", 16, SUB)
    return f.save()


def inverse_compare():
    f = Fig("c8-inverse-compare", "三种求逆元的方法", "逆元：满足 a·x ≡ 1 (mod m) 的 x。选哪种取决于模数和个数。", 470,
            "只求一两个数用前两种；要一次求出 1..n 的全部逆元用第三种。")
    f.h = 380
    f.box(32, 105, 300, 210, "blue", "扩展欧几里得",
          ["解 a·x + m·y = 1", "取 x mod m 即逆元", "条件：gcd(a, m) = 1", "m 可以不是质数", "复杂度 O(log m)", "不存在时能判断出来"], 16)
    f.box(350, 105, 300, 210, "green", "费马小定理",
          ["a^(p-1) ≡ 1 (mod p)", "所以 a 的逆元 = a^(p-2)", "条件：p 是质数", "且 a 不是 p 的倍数", "复杂度 O(log p)", "写法最短"], 16)
    f.box(668, 105, 300, 210, "orange", "线性递推",
          ["inv[1] = 1", "inv[i] = (p - p/i)", "         × inv[p mod i]", "条件：p 是质数", "一次求 1..n 全部", "复杂度 O(n)"], 16)
    return f.save()


def linear_congruence():
    f = Fig("c8-linear-congruence", "解同余方程 6x ≡ 4 (mod 10)：把 x 从 0 试到 9",
            "g = gcd(6, 10) = 2，4 能被 2 整除，所以有解；解之间相隔 m/g = 5。", 400,
            "两个解 x = 4 和 x = 9，写成 x ≡ 4 (mod 5)。如果右边是 5（不被 2 整除），整行都不会出现 5。")
    f.text(40, 142, "x", 18, SUB, "700")
    f.text(40, 214, "6x mod 10", 18, SUB, "700")
    vals = [(6 * x) % 10 for x in range(10)]
    for x in range(10):
        cx = 220 + x * 74
        hit = vals[x] == 4
        f.chip(cx, 135, 62, 50, "green" if hit else "white", str(x), 20, bold=hit)
        f.chip(cx, 207, 62, 50, "green" if hit else "white", str(vals[x]), 20, bold=hit)
    f.arrow(220 + 4 * 74, 164, 220 + 4 * 74, 180, PALETTE["green"][1])
    f.arrow(220 + 9 * 74, 164, 220 + 9 * 74, 180, PALETTE["green"][1])
    f.rect(220 + 4 * 74 - 31, 262, 5 * 74 + 62, 58, "orange", dash=True)
    f.text(220 + 4 * 74 + 5 * 74 / 2 + 0, 298, "相隔 5 = m / g，之后重复", 17, PALETTE["orange"][1], "700", "middle")
    return f.save()


# ---------------------------------------------------------------- 8.2
def sieve_eratosthenes():
    f = Fig("c8-sieve-eratosthenes", "埃氏筛：按最小质因子给 1 到 30 上色",
            "从 2 开始，把每个质数的倍数划掉；每个合数在它的最小质因子那一轮第一次被划掉。", 460,
            "同一个合数会被多个质数划到（如 30 被 2、3、5 都划到），线性筛的目标就是消除这种重复。")
    f.h = 500
    def lp(n):
        for p in range(2, n + 1):
            if n % p == 0:
                return p
    kind = {2: "blue", 3: "green", 5: "orange"}
    for n in range(2, 31):
        r, c = divmod(n - 1, 10)
        cx, cy = 90 + c * 90, 140 + r * 80
        p = lp(n)
        if p == n and n > 5:
            k = "purple"
        elif p == n:
            k = kind[n]
        else:
            k = kind.get(p, "white")
        f.chip(cx, cy, 70, 58, k, str(n), 22, bold=(p == n))
    f.chip(90, 140, 70, 58, "grey", "1", 22)
    lx = 90
    for k, s in [("blue", "最小质因子 2"), ("green", "最小质因子 3"), ("orange", "最小质因子 5"), ("purple", "7 及以上的质数")]:
        f.rect(lx - 16, 372, 30, 24, k, r=6)
        f.text(lx + 22, 391, s, 15, INK)
        lx += 215
    f.text(40, 428, "加粗的是质数本身。合数最小质因子不超过 √30 ≈ 5.5，所以只需处理 2、3、5。", 16, SUB)
    return f.save()


def linear_sieve_trace():
    f = Fig("c8-linear-sieve-trace", "线性筛：每个合数只被它的最小质因子标记一次",
            "筛到 30。对每个 i，依次用已找到的质数 p 标记 i·p，遇到 p = lp[i] 就停。", 620,
            "对比埃氏筛：30 只在 i = 15、p = 2 时被标记一次，其余质数轮到它之前已经 break。")
    f.h = 660
    rows = [["i", "lp[i]", "依次标记 i·p（括号里是 p）", "停止原因"],
            ["2", "2", "4（2）", "p = lp[i]"],
            ["3", "3", "6（2）  9（3）", "p = lp[i]"],
            ["4", "2", "8（2）", "p = lp[i]"],
            ["5", "5", "10（2）  15（3）  25（5）", "p = lp[i]"],
            ["6", "2", "12（2）", "p = lp[i]"],
            ["7", "7", "14（2）  21（3）", "35 > 30"],
            ["9", "3", "18（2）  27（3）", "p = lp[i]"],
            ["15", "3", "30（2）", "45 > 30"]]
    kinds = {(8, 2): "green", (5, 2): "orange"}
    table(f, 40, 105, [90, 110, 500, 210], rows, row_h=50, kinds=kinds)
    f.text(40, 590, "i = 9 时不会再用 p = 5 标记 45：9 的最小质因子是 3，再往后用更大的 p 会让 lp 记错。", 16, SUB)
    return f.save()


def lp_factorize():
    f = Fig("c8-lp-factorize", "用 lp 数组在 O(log n) 内分解质因数", "反复取最小质因子 lp[x]，除掉后继续。", 340,
            "每一步 x 至少减半，所以最多 log2 n 步；对多次查询比试除快得多。")
    xs = [84, 42, 21, 7, 1]
    ps = [2, 2, 3, 7]
    for i, x in enumerate(xs):
        cx = 120 + i * 190
        f.chip(cx, 170, 100, 60, "blue" if x > 1 else "green", f"x = {x}", 20, bold=True)
        if i < 4:
            f.arrow(cx + 52, 170, cx + 138, 170, PALETTE["blue"][1])
            f.text(cx + 95, 150, f"÷ {ps[i]}", 18, PALETTE["blue"][1], "700", "middle")
            f.text(cx + 95, 202, f"lp = {ps[i]}", 14, SUB, anchor="middle")
    f.text(500, 270, "84 = 2² × 3 × 7", 24, INK, "700", "middle")
    return f.save()


# ---------------------------------------------------------------- 8.3
def pascal():
    f = Fig("c8-pascal", "杨辉三角：每个数等于肩上两个数之和", "第 n 行第 m 个数就是 C(n, m)，从 0 开始编号。", 520,
            "递推式 C(n,m) = C(n-1,m-1) + C(n-1,m)：选或不选第 n 个元素。")
    f.h = 570
    rows = 7
    pos = {}
    for n in range(rows):
        for m in range(n + 1):
            cx = 500 + (m - n / 2) * 96
            cy = 130 + n * 56
            pos[(n, m)] = (cx, cy)
            val = math.comb(n, m)
            hl = (n, m) in [(4, 2)]
            par = (n, m) in [(3, 1), (3, 2)]
            f.chip(cx, cy, 70, 42, "green" if hl else ("orange" if par else "white"), str(val), 19, bold=hl or par)
    f.arrow(pos[(3, 1)][0] + 14, pos[(3, 1)][1] + 21, pos[(4, 2)][0] - 14, pos[(4, 2)][1] - 21, PALETTE["orange"][1])
    f.arrow(pos[(3, 2)][0] - 14, pos[(3, 2)][1] + 21, pos[(4, 2)][0] + 14, pos[(4, 2)][1] - 21, PALETTE["orange"][1])
    for n in range(rows):
        f.text(40, 136 + n * 56, f"n = {n}", 15, SUB)
    f.text(690, 200, "C(4,2) = C(3,1) + C(3,2)", 18, PALETTE["green"][1], "700")
    f.text(690, 230, "6 = 3 + 3", 18, INK)
    f.text(690, 300, "每行之和 = 2^n", 18, SUB)
    return f.save()


def stars_bars():
    f = Fig("c8-stars-bars", "隔板法：10 个相同的球放进 4 个盒子，每盒至少 1 个",
            "10 个球之间有 9 个空隙，在其中选 3 个空隙放隔板，就把球分成 4 段。", 440,
            "每盒可以为空时，先每盒借 1 个球变成 14 个球，答案是 C(13, 3)；至少 1 个时是 C(9, 3) = 84。")
    xs = [70 + i * 88 for i in range(10)]
    for i, x in enumerate(xs):
        circle(f, x, 190, 22, "blue")
        f.text(x, 196, str(i + 1), 16, INK, anchor="middle")
    for g in range(9):
        gx = (xs[g] + xs[g + 1]) / 2
        use = g in (2, 4, 8)
        if use:
            f.parts.append(f'<line x1="{gx}" y1="145" x2="{gx}" y2="235" stroke="#a33a3a" stroke-width="5" stroke-linecap="round"/>')
        else:
            f.parts.append(f'<line x1="{gx}" y1="165" x2="{gx}" y2="215" stroke="#c4ccda" stroke-width="2" stroke-dasharray="4 4"/>')
        f.text(gx, 262, f"空隙{g + 1}", 12, SUB, anchor="middle")
    segs = [("盒 A：3 个", 70, 246), ("盒 B：2 个", 334, 422), ("盒 C：4 个", 510, 774), ("盒 D：1 个", 862, 862)]
    kinds = ["blue", "green", "orange", "purple"]
    for (s, a, b), k in zip(segs, kinds):
        w = max(b - a + 56, 110)
        f.rect((a + b) / 2 - w / 2, 300, w, 54, k, r=10)
        f.text((a + b) / 2, 334, s, 17, PALETTE[k][1], "700", "middle")
    f.text(40, 395, "选出的隔板位置 {空隙3, 空隙5, 空隙9} 与一种放法一一对应，所以方案数就是 C(9, 3)。", 16, INK)
    return f.save()


def fact_inverse():
    f = Fig("c8-fact-inverse", "阶乘逆元的反推：只做一次快速幂", "先求最大的 ifact[N]，再往小的方向乘回来。", 470,
            "之后 C(n, m) = fact[n] · ifact[m] · ifact[n-m]，每次查询 O(1)。")
    labels = ["ifact[N]", "ifact[N-1]", "ifact[N-2]", "…", "ifact[1]", "ifact[0]"]
    xs = [100 + i * 160 for i in range(6)]
    for i, (x, s) in enumerate(zip(xs, labels)):
        f.chip(x, 200, 134, 56, "green" if i == 0 else "white", s, 17, bold=(i == 0))
        if i < 5:
            f.arrow(x + 72, 200, x + 160 - 72, 200, PALETTE["green"][1])
            f.text(x + 80, 168, ["× N", "× (N-1)", "× …", "× 2", "× 1"][i], 14, SUB, anchor="middle")
    f.text(100, 262, "快速幂：fact[N]^(p-2)", 15, PALETTE["green"][1], "700", "middle")
    f.rect(32, 310, 936, 110, "blue")
    f.text(52, 346, "为什么能这样推：ifact[i-1] = 1/(i-1)! = i/i! = i · ifact[i]", 18, INK)
    f.text(52, 380, "n! 的逆元乘上 n，恰好去掉分母里的一个因子 n，得到 (n-1)! 的逆元。", 17, SUB)
    return f.save()


def build_all():
    w = []
    for fn in [exgcd_trace, inverse_compare, linear_congruence, sieve_eratosthenes, linear_sieve_trace,
               lp_factorize, pascal, stars_bars, fact_inverse]:
        w += fn()
    w += build_more()
    return w


def line(f, x1, y1, x2, y2, color="#66758d", width=2, dash=False):
    d = ' stroke-dasharray="6 5"' if dash else ""
    f.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}" stroke-linecap="round"{d}/>')


# ---------------------------------------------------------------- 8.4
def crt_grid():
    f = Fig("c8-crt-grid", "中国剩余定理：(x mod 3, x mod 5) 与 0..14 一一对应",
            "表中每个格子写的是满足该组余数的 x。例：x ≡ 2 (mod 3) 且 x ≡ 3 (mod 5)，答案落在 x = 8。", 520,
            "继续合并 x ≡ 2 (mod 7)：8 + 15k ≡ 2 (mod 7)，得 k = 1，x ≡ 23 (mod 105)。")
    f.text(180, 128, "x mod 5 =", 16, SUB, "700")
    for c in range(5):
        f.chip(330 + c * 120, 120, 100, 40, "grey", str(c), 18, bold=True)
    for r in range(3):
        f.chip(110, 200 + r * 80, 150, 60, "grey", f"x mod 3 = {r}", 16, bold=True)
        for c in range(5):
            x = next(v for v in range(15) if v % 3 == r and v % 5 == c)
            kind = "green" if (r, c) == (2, 3) else ("orange" if r == 2 or c == 3 else "white")
            f.chip(330 + c * 120, 200 + r * 80, 100, 60, kind, str(x), 22, bold=(r, c) == (2, 3))
    f.text(40, 450, "橙色是满足单个条件的数（x ≡ 2 mod 3 的一整行，x ≡ 3 mod 5 的一整列），绿色是两者的交点。", 16, INK)
    return f.save()


# ---------------------------------------------------------------- 8.5
def block_division():
    f = Fig("c8-block-division", "整除分块：floor(12/d) 相同的 d 连成一段", "n = 12 时，d 从 1 到 12 只有 6 种不同的商。", 460,
            "对每段 [l, r]：商 q = n / l，右端点 r = n / q。总段数不超过 2√n，所以一次查询 O(√n)。")
    qs = [12 // d for d in range(1, 13)]
    blocks = [(1, 1), (2, 2), (3, 3), (4, 4), (5, 6), (7, 12)]
    kinds = ["blue", "green", "orange", "purple", "blue", "green"]
    f.text(40, 140, "d", 18, SUB, "700")
    f.text(40, 214, "12 / d", 18, SUB, "700")
    for bi, (l, r) in enumerate(blocks):
        for d in range(l, r + 1):
            cx = 120 + (d - 1) * 70
            f.chip(cx, 132, 62, 44, kinds[bi], str(d), 19)
            f.chip(cx, 206, 62, 44, kinds[bi], str(qs[d - 1]), 19, bold=True)
        x1, x2 = 120 + (l - 1) * 70 - 31, 120 + (r - 1) * 70 + 31
        f.rect(x1, 262, x2 - x1, 40, kinds[bi], r=8)
        f.text((x1 + x2) / 2, 289, f"[{l},{r}]" if r > l else f"[{l}]", 15, PALETTE[kinds[bi]][1], "700", "middle")
    f.text(40, 352, "l = 5：q = 12 / 5 = 2，r = 12 / 2 = 6，这一段是 [5, 6]。", 17, INK)
    f.text(40, 384, "l = 7：q = 12 / 7 = 1，r = 12 / 1 = 12，这一段是 [7, 12]，直到 n 结束。", 17, INK)
    return f.save()


def mobius_coprime():
    f = Fig("c8-mobius-coprime", "莫比乌斯函数与互质对计数", "μ(d) 只取 0、1、-1。n = m = 4 时，互质的 (i, j) 对数等于 Σ μ(d)·(4 除以 d 取整)²。", 480,
            "验证：16 对里 gcd > 1 的有 (2,2) (2,4) (4,2) (4,4) (3,3) 共 5 对，16 - 5 = 11。")
    f.h = 560
    mu = [1, -1, -1, 0, -1, 1, -1, 0, 0, 1, -1, 0]
    f.text(40, 142, "d", 17, SUB, "700")
    f.text(40, 202, "μ(d)", 17, SUB, "700")
    for d in range(1, 13):
        cx = 120 + (d - 1) * 70
        v = mu[d - 1]
        k = "grey" if v == 0 else ("green" if v == 1 else "orange")
        f.chip(cx, 135, 58, 44, "white", str(d), 18)
        f.chip(cx, 195, 58, 44, k, str(v), 19, bold=True)
    f.text(40, 262, "μ(d) = 0：d 含平方因子（4、8、9、12）；否则 μ = (-1)^(质因子个数)，如 μ(6) = 1、μ(7) = -1。", 15, SUB)
    rows = [["d", "μ(d)", "取整(4/d)的平方", "μ(d) 乘以左列"], ["1", "1", "16", "+16"], ["2", "-1", "4", "-4"],
            ["3", "-1", "1", "-1"], ["4", "0", "1", "0"], ["合计", "", "", "11"]]
    table(f, 160, 285, [120, 150, 250, 230], rows, row_h=36, size=15, kinds={(5, 3): "green", (5, 0): "green"})
    return f.save()


# ---------------------------------------------------------------- 8.6
def miller_rabin():
    f = Fig("c8-miller-rabin", "Miller-Rabin：把 n - 1 写成 d·2^s，看 a^d 反复平方的轨迹",
            "质数的轨迹要么一开始就是 1，要么在回到 1 之前经过 -1（即 n - 1）。", 470,
            "合数可能蒙混过关（强伪素数），所以换多个底数 a；前 12 个质数做底数可保证 64 位内无误判。")
    f.box(32, 105, 936, 150, "green", "n = 13（质数），a = 2：n - 1 = 12 = 3 · 2²，d = 3",
          ["a^d = 2^3 = 8", "8² = 64 ≡ 12 ≡ -1 (mod 13)  → 出现 -1，通过"], 17)
    chips = [("8", "white"), ("12 = -1", "green")]
    for i, (t, k) in enumerate(chips):
        f.chip(620 + i * 160, 190, 120, 44, k, t, 18, bold=(k == "green"))
    f.arrow(682, 190, 698, 190, PALETTE["green"][1])
    f.box(32, 275, 936, 150, "red", "n = 21（合数），a = 2：n - 1 = 20 = 5 · 2²，d = 5",
          ["a^d = 2^5 = 32 ≡ 11   不是 1 也不是 -1", "11² = 121 ≡ 16   不是 -1，轨迹结束  → 判为合数"], 17)
    chips = [("11", "white"), ("16", "red")]
    for i, (t, k) in enumerate(chips):
        f.chip(620 + i * 160, 360, 120, 44, k, t, 18, bold=(k == "red"))
    f.arrow(682, 360, 698, 360, PALETTE["red"][1])
    return f.save()


def pollard_rho():
    f = Fig("c8-pollard-rho", "Pollard's Rho：伪随机序列在模 p 下会先成环", "序列 x → x² + c 对 n 取模；对因子 p 取模后的序列更早出现重复。", 520,
            "两个下标 i、j 满足 x_i ≡ x_j (mod p) 但 x_i ≠ x_j (mod n)，则 gcd(|x_i - x_j|, n) 是 n 的非平凡因子。")
    tail = [(100, 400), (190, 360), (280, 320), (360, 275)]
    cx, cy, R = 600, 235, 105
    cyc = [(cx + R * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a))) for a in range(150, 150 + 360, 60)]
    pts = tail + cyc
    for i in range(len(tail) + 5):
        a, b = pts[i], pts[i + 1]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        f.arrow(round(a[0] + dx / L * 24), round(a[1] + dy / L * 24), round(b[0] - dx / L * 27), round(b[1] - dy / L * 27), GREY)
    line(f, round(cyc[-1][0]), round(cyc[-1][1]), round(cyc[0][0]), round(cyc[0][1]), PALETTE["red"][1], 3)
    for i, (x, y) in enumerate(pts):
        circle(f, round(x), round(y), 21, "blue" if i < len(tail) else "orange")
        f.text(round(x), round(y) + 6, f"x{i}", 15, INK, anchor="middle")
    f.text(60, 450, "尾巴（rho 的柄）", 17, PALETTE["blue"][1], "700")
    f.text(520, 410, "环：模 p 下 x9 与 x4 相同", 17, PALETTE["red"][1], "700")
    f.text(60, 150, "快指针一步走两格，慢指针一步走一格，", 16, INK)
    f.text(60, 178, "进环后两者迟早在环里相遇，", 16, INK)
    f.text(60, 206, "此时差值是 p 的倍数。", 16, INK)
    return f.save()


# ---------------------------------------------------------------- 8.7
def gauss_steps():
    f = Fig("c8-gauss-steps", "高斯消元：先消成上三角，再回代", "方程组 x+y+z=6，y+2z=8，2x+5y−z=9，解为 (1, 2, 3)。", 520,
            "消元每一步用主元所在行去消掉下面各行同一列的数；复杂度 O(n³)。")
    mats = [
        ("原始增广矩阵", [[1, 1, 1, 6], [0, 1, 2, 8], [2, 5, -1, 9]]),
        ("R3 ← R3 − 2·R1", [[1, 1, 1, 6], [0, 1, 2, 8], [0, 3, -3, -3]]),
        ("R3 ← R3 − 3·R2", [[1, 1, 1, 6], [0, 1, 2, 8], [0, 0, -9, -27]]),
    ]
    for k, (title, m) in enumerate(mats):
        x0 = 40 + k * 320
        f.text(x0 + 100, 140, title, 16, PALETTE["blue"][1], "700", "middle")
        for r in range(3):
            for c in range(4):
                kind = "green" if (k == 2 and r == 2 and c < 3 and c != 2) else "white"
                if c == 3:
                    kind = "orange"
                f.chip(x0 + 20 + c * 52, 190 + r * 50, 46, 40, kind, str(m[r][c]), 17)
        if k < 2:
            f.arrow(x0 + 242, 240, x0 + 296, 240, GREY)
    f.box(40, 340, 920, 120, "green", "回代（从最后一行往上）",
          ["−9·z = −27  →  z = 3", "y + 2z = 8  →  y = 8 − 6 = 2", "x + y + z = 6  →  x = 6 − 2 − 3 = 1"], 17)
    return f.save()


def xor_basis():
    f = Fig("c8-xor-basis", "异或线性基：依次插入 5、3、6、1", "每个基向量占据一个二进制最高位；插入时用已有基向量把最高位消掉。", 520,
            "能凑出的异或值恰好有 2^3 = 8 个。6 = 5 ⊕ 3 已在张成空间中，所以插入失败。")
    rows = [["插入", "二进制", "过程", "结果"],
            ["5", "101", "最高位 2 为空", "b2 = 101"],
            ["3", "011", "最高位 1 为空", "b1 = 011"],
            ["6", "110", "⊕b2=011，⊕b1=000", "失败，不加入"],
            ["1", "001", "最高位 0 为空", "b0 = 001"]]
    table(f, 40, 105, [110, 140, 330, 250], rows, row_h=50, kinds={(3, 3): "red"})
    f.text(40, 395, "求最大异或和：从高位到低位，若 r ⊕ b[i] 比 r 大就异或进去。", 17, INK)
    for i, (t, k) in enumerate([("r = 000", "white"), ("⊕b2 → 101", "blue"), ("⊕b1 → 110", "blue"), ("⊕b0 → 111 = 7", "green")]):
        f.chip(130 + i * 230, 440, 200, 44, k, t, 17, bold=(k == "green"))
        if i < 3:
            f.arrow(232 + i * 230, 440, 258 + i * 230, 440, GREY)
    return f.save()


# ---------------------------------------------------------------- 8.8
def ntt_butterfly():
    f = Fig("c8-ntt-butterfly", "n = 8 的迭代 NTT：位反转后做 3 层蝶形运算", "每层把相距 len/2 的两个数做一次 (u + w·v, u − w·v)。", 560,
            "每层 n/2 次蝶形，共 log2(n) 层，总计 O(n log n)。")
    order = [0, 4, 2, 6, 1, 5, 3, 7]
    xs = [140, 340, 540, 740]
    ys = [120 + i * 52 for i in range(8)]
    f.text(60, 108, "位反转后", 15, SUB, "700")
    for i in range(8):
        f.chip(80, ys[i] + 10, 56, 36, "white", f"a{order[i]}", 16)
    for st, length in enumerate([2, 4, 8]):
        x = xs[st] + 40
        f.text(x + 100, 108, f"第 {st + 1} 层：len = {length}", 15, PALETTE["blue"][1], "700", "middle")
        for blk in range(0, 8, length):
            for j in range(length // 2):
                a, b = blk + j, blk + j + length // 2
                kind = ["blue", "green", "orange"][st]
                color = PALETTE[kind][1]
                line(f, x, ys[a] + 10, x + 160, ys[a] + 10, "#c4ccda", 1.5)
                line(f, x, ys[b] + 10, x + 160, ys[b] + 10, "#c4ccda", 1.5)
                line(f, x + 30, ys[a] + 10, x + 130, ys[b] + 10, color, 2)
                line(f, x + 30, ys[b] + 10, x + 130, ys[a] + 10, color, 2)
                circle(f, x + 30, ys[a] + 10, 5, kind)
                circle(f, x + 30, ys[b] + 10, 5, kind)
                circle(f, x + 130, ys[a] + 10, 5, kind)
                circle(f, x + 130, ys[b] + 10, 5, kind)
    for i in range(8):
        f.chip(840, ys[i] + 10, 56, 36, "green", f"A{i}", 16, bold=True)
    return f.save()


def poly_pipeline():
    f = Fig("c8-poly-pipeline", "用 NTT 做多项式乘法的流程", "把系数表示变成点值表示，逐点相乘，再变换回来。", 420,
            "朴素卷积 O(n²)；NTT 方案 O(n log n)。n 要补到不小于 deg(A) + deg(B) + 1 的 2 的幂。")
    steps = [("A(x)、B(x)\n系数", "blue"), ("NTT\nO(n log n)", "green"), ("点值逐点相乘\nO(n)", "orange"), ("逆 NTT\nO(n log n)", "green"), ("C(x) = A(x)B(x)\n系数", "blue")]
    for i, (t, k) in enumerate(steps):
        cx = 100 + i * 200
        f.chip(cx, 200, 170, 90, k, t, 17, bold=True)
        if i < 4:
            f.arrow(cx + 88, 200, cx + 112, 200, GREY)
    f.text(40, 320, "n 个点的取值就足以确定一个次数小于 n 的多项式，逐点相乘不再需要卷积。", 17, INK)
    f.text(40, 352, "NTT 在模 998244353 下用单位根 3^((p−1)/len) 代替复数 FFT 的 e^(2πi/len)，结果是精确整数。", 17, INK)
    return f.save()


# ---------------------------------------------------------------- 8.9
def sg_graph():
    f = Fig("c8-sg-graph", "有向无环图上的游戏：SG(u) = mex{ SG(v) | u→v }", "棋子在点上，沿边走，无路可走的一方输。SG = 0 是必败点。", 480,
            "mex：集合里没出现过的最小非负整数。终点没有后继，mex{} = 0。")
    pos = {0: (180, 220), 1: (420, 150), 2: (420, 300), 3: (660, 150), 4: (660, 300)}
    sg = {0: 0, 1: 1, 2: 1, 3: 0, 4: 0}
    edges = [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4)]
    for a, b in edges:
        (x1, y1), (x2, y2) = pos[a], pos[b]
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        f.arrow(round(x1 + dx / L * 32), round(y1 + dy / L * 32), round(x2 - dx / L * 36), round(y2 - dy / L * 36), GREY)
    for u, (x, y) in pos.items():
        circle(f, x, y, 30, "green" if sg[u] == 0 else "orange")
        f.text(x, y + 6, f"v{u}", 18, INK, "700", "middle")
        f.text(x, y + 58, f"SG={sg[u]}", 16, PALETTE["green"][1] if sg[u] == 0 else PALETTE["orange"][1], "700", "middle")
    f.text(40, 400, "v3、v4 无后继：SG = 0。 v1 → v3，mex{0} = 1。 v2 → v3、v4，mex{0, 0} = 1。", 16, INK)
    f.text(40, 430, "v0 → v1、v2，后继 SG 是 {1, 1}，mex = 0，所以起点 v0 是必败点。", 16, INK)
    return f.save()


def nim_xor():
    f = Fig("c8-nim-xor", "Nim 游戏：各堆大小异或不为 0，先手必胜", "三堆 3、4、5：二进制逐位异或，结果 010 ≠ 0。", 440,
            "必胜策略：找一堆 a，使 a ⊕ X < a，把它减到 a ⊕ X。这里 3 ⊕ 2 = 1，从 3 那堆取走 2 个，局面变成 (1, 4, 5)，异或为 0。")
    rows = [["堆", "大小", "第 2 位", "第 1 位", "第 0 位"], ["A", "3", "0", "1", "1"], ["B", "4", "1", "0", "0"],
            ["C", "5", "1", "0", "1"], ["异或", "2", "0", "1", "0"]]
    table(f, 120, 110, [140, 140, 150, 150, 150], rows, row_h=50, kinds={(4, 0): "green", (4, 1): "green", (4, 2): "green", (4, 3): "green", (4, 4): "green"})
    f.text(120, 395, "取走后：(1, 4, 5) → 001 ⊕ 100 ⊕ 101 = 000，对手面对必败局面。", 17, INK)
    return f.save()


# ---------------------------------------------------------------- 8.10
def inclusion_venn():
    f = Fig("c8-inclusion-venn", "容斥原理：1..30 中与 30 互质的数", "A、B、C 分别是 2、3、5 的倍数。各区域的个数如图。", 520,
            "|A∪B∪C| = 15+10+6 − 5−3−2 + 1 = 22，所以互质的有 30 − 22 = 8 个（1, 7, 11, 13, 17, 19, 23, 29）。")
    for cx, cy, color, name in [(360, 250, "#285caa", "A：2 的倍数  15 个"), (500, 250, "#176951", "B：3 的倍数  10 个"), (430, 360, "#8c5315", "C：5 的倍数  6 个")]:
        f.parts.append(f'<circle cx="{cx}" cy="{cy}" r="125" fill="{color}" fill-opacity=".12" stroke="{color}" stroke-width="2"/>')
    f.text(190, 128, "A：2 的倍数，15 个", 16, "#285caa", "700")
    f.text(640, 128, "B：3 的倍数，10 个", 16, "#176951", "700")
    f.text(640, 450, "C：5 的倍数，6 个", 16, "#8c5315", "700")
    for x, y, t in [(300, 220, "8"), (570, 220, "4"), (430, 430, "2"), (430, 205, "4"), (365, 330, "2"), (495, 330, "1"), (430, 285, "1")]:
        f.text(x, y, t, 24, INK, "700", "middle")
    f.rect(740, 205, 200, 80, "red", dash=True)
    f.text(840, 255, "圈外（互质）：8", 20, PALETTE["red"][1], "700", "middle")
    return f.save()


def catalan_paths():
    f = Fig("c8-catalan-paths", "卡特兰数：从 (0,0) 走到 (3,3)，不越过对角线 y = x", "每步向右（R）或向上（U）。合法路径数 = C(6,3) − C(6,2) = 20 − 15 = 5，即第 3 个卡特兰数。", 560,
            "非法路径：第一次碰到 y = x + 1 之后，把剩余部分沿这条线对称，终点从 (3,3) 变成 (2,4)；这样的路径恰有 C(6,2) 条。")
    f.h = 640
    def grid(ox, oy, title):
        s = 90
        f.text(ox + 3 * s / 2, 118, title, 17, INK, "700", "middle")
        for i in range(4):
            line(f, ox + i * s, oy, ox + i * s, oy + 3 * s + 0, "#d5dbe6", 1.5)
            line(f, ox, oy + i * s, ox + 3 * s, oy + i * s, "#d5dbe6", 1.5)
        line(f, ox, oy + 3 * s, ox + 3 * s, oy, "#66758d", 2, True)
        return s
    def pt(ox, oy, s, x, y):
        return ox + x * s, oy + 3 * s - y * s
    ox, oy = 90, 230
    s = grid(ox, oy, "合法：RRURUU（始终 y ≤ x）")
    path = [(0, 0), (1, 0), (2, 0), (2, 1), (3, 1), (3, 2), (3, 3)]
    for a, b in zip(path, path[1:]):
        (x1, y1), (x2, y2) = pt(ox, oy, s, *a), pt(ox, oy, s, *b)
        line(f, x1, y1, x2, y2, "#176951", 5)
    ox2 = 580
    grid(ox2, oy, "非法：RUURRU（碰到 y = x + 1）")
    x1, y1 = pt(ox2, oy, s, -1, 0)
    x2, y2 = pt(ox2, oy, s, 2, 3)
    line(f, max(x1, ox2 - 10), y1 - 0, x2, y2, "#a33a3a", 2, True)
    bad = [(0, 0), (1, 0), (1, 1), (1, 2)]
    for a, b in zip(bad, bad[1:]):
        (xa, ya), (xb, yb) = pt(ox2, oy, s, *a), pt(ox2, oy, s, *b)
        line(f, xa, ya, xb, yb, "#a33a3a", 5)
    rest = [(1, 2), (2, 2), (3, 2), (3, 3)]
    for a, b in zip(rest, rest[1:]):
        (xa, ya), (xb, yb) = pt(ox2, oy, s, *a), pt(ox2, oy, s, *b)
        line(f, xa, ya, xb, yb, "#8c5315", 3, True)
    refl = [(1, 2), (1, 3), (1, 4), (2, 4)]
    for a, b in zip(refl, refl[1:]):
        (xa, ya), (xb, yb) = pt(ox2, oy, s, *a), pt(ox2, oy, s, *b)
        line(f, xa, ya, xb, yb, "#5b3fa0", 3, True)
    f.text(40, 570, "右图：虚线棕色是原路径碰线后的剩余部分 RRU；紫色是它沿 y = x + 1 对称后的 UUR，终点变成 (2,4)。", 15, SUB)
    return f.save()


def burnside_necklace():
    f = Fig("c8-burnside-necklace", "Burnside 引理：4 颗珠子、2 种颜色的项链", "对每种旋转，数不动点（旋转后不变的染色）：循环数为 c 时有 2^c 个。", 520,
            "不同项链数 = 所有旋转的不动点平均 = (16 + 2 + 4 + 2) / 4 = 6。")
    pos = [(0, -1), (1, 0), (0, 1), (-1, 0)]
    cases = [("旋转 0 步", [], 4, 16), ("旋转 1 步", [(0, 1), (1, 2), (2, 3), (3, 0)], 1, 2),
             ("旋转 2 步", [(0, 2), (1, 3)], 2, 4), ("旋转 3 步", [(0, 3), (3, 2), (2, 1), (1, 0)], 1, 2)]
    for k, (title, links, cyc, fix) in enumerate(cases):
        cx, cy = 130 + k * 235, 230
        f.text(cx, 118, title, 17, PALETTE["blue"][1], "700", "middle")
        for a, b in links:
            (xa, ya), (xb, yb) = pos[a], pos[b]
            line(f, cx + xa * 55, cy + ya * 55, cx + xb * 55, cy + yb * 55, "#8c5315", 2.5, dash=(len(links) == 2))
        for i, (px, py) in enumerate(pos):
            circle(f, cx + px * 55, cy + py * 55, 18, "blue")
            f.text(cx + px * 55, cy + py * 55 + 6, str(i + 1), 16, INK, anchor="middle")
        f.text(cx, 340, f"{cyc} 个循环", 16, SUB, anchor="middle")
        f.chip(cx, 395, 150, 50, "green", f"不动点 2^{cyc} = {fix}", 16, bold=True)
    f.text(40, 470, "旋转 0 步：每颗珠子自成一个循环；旋转 1、3 步：4 颗珠子连成一圈，必须同色；旋转 2 步：对面两颗必须同色。", 15, INK)
    return f.save()


def build_more():
    w = []
    for fn in [crt_grid, block_division, mobius_coprime, miller_rabin, pollard_rho, gauss_steps, xor_basis,
               ntt_butterfly, poly_pipeline, sg_graph, nim_xor, inclusion_venn, catalan_paths, burnside_necklace]:
        w += fn()
    return w
