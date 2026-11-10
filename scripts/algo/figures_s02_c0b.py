"""第 0 章配图（下）：均摊、主定理、浮点误差。"""
from svglib import Fig, GREY, SUB, INK, PALETTE
from figures_s02_c0a import ln


def amortized():
    f = Fig("c0-amortized", "vector 连续 push_back 16 次的实际代价", "偶尔一次扩容很贵，把代价摊到每次操作上，平均不到 2。", 550,
            "总代价 16 + (1+2+4+8) = 31，平均每次约 1.94。")
    base, unit = 430, 28
    for i in range(1, 17):
        m = i - 1
        cost = 1 + (m if m > 0 and m & (m - 1) == 0 else 0)
        x = 70 + (i - 1) * 55
        kind = "red" if cost > 1 else "blue"
        f.rect(x, base - cost * unit, 38, cost * unit, kind, r=4)
        f.text(x + 19, base - cost * unit - 8, str(cost), 15, PALETTE[kind][1], "700", "middle")
        f.text(x + 19, base + 22, str(i), 14, SUB, anchor="middle")
    ln(f, 50, base, 960, base, GREY, w=1)
    ya = base - 31 / 16 * unit
    ln(f, 50, ya, 960, ya, PALETTE["green"][1], dash=True)
    f.text(640, ya - 12, "平均 ≈ 1.94", 17, PALETTE["green"][1], "700")
    f.text(50, 492, "横轴：第几次 push_back；柱高：这一次实际做了多少次元素操作（含扩容时的搬运）。", 15, SUB)
    return f.save()


def master_cases():
    f = Fig("c0-master-cases", "主定理的三种情形", "T(n) = a·T(n/b) + f(n)，看递归树每一层的代价是递增、持平还是递减。", 540,
            "令 c = log_b a。比较 f(n) 与 n^c 的大小，就能知道哪一端的代价占主导。")
    cards = [
        ("f(n) 比 n^c 小", "叶子占主导", "递增", [60, 100, 140, 180, 220], "blue",
         "T(n) = Θ(n^c)", "例：T = 4T(n/2) + n", "结果 Θ(n²)"),
        ("f(n) 与 n^c 同阶", "每层一样", "持平", [150] * 5, "green",
         "T(n) = Θ(n^c · log n)", "例：T = 2T(n/2) + n", "结果 Θ(n log n)"),
        ("f(n) 比 n^c 大", "根占主导", "递减", [220, 180, 140, 100, 60], "orange",
         "T(n) = Θ(f(n))", "例：T = T(n/2) + n", "结果 Θ(n)"),
    ]
    for i, (a, b, c, ws, k, r1, r2, r3) in enumerate(cards):
        x = 32 + i * 322
        f.rect(x, 108, 292, 380, k)
        f.text(x + 14, 140, a, 18, PALETTE[k][1], "700", maxw=264)
        f.text(x + 14, 168, f"{b}：每层代价{c}", 16, INK, maxw=264)
        for j, w in enumerate(ws):
            f.rect(x + 14, 190 + j * 38, w, 28, k, r=5, fill="#ffffff")
            f.text(x + 14 + w + 8, 190 + j * 38 + 20, f"第 {j} 层", 13, SUB)
        f.text(x + 14, 420, r1, 17, INK, "700", maxw=264)
        f.text(x + 14, 450, r2, 16, SUB, maxw=264)
        f.text(x + 14, 476, r3, 16, SUB, maxw=264)
    return f.save()


def float_eps():
    f = Fig("c0-float-eps", "浮点数比较要留容差", "0.1 + 0.2 在二进制里存不下精确的 0.3，用 == 会判成不相等。", 460,
            "误差只有约 5.5×10^-17，图中为了看清做了放大。")
    ln(f, 80, 270, 920, 270, GREY)
    f.rect(380, 210, 150, 120, "orange", opacity=".5")
    f.text(455, 198, "容差区间 eps", 16, PALETTE["orange"][1], "700", "middle")
    for x, lab, up, col in [(425, "0.3", False, "blue"), (485, "0.1 + 0.2", True, "green"), (760, "0.31", False, "red")]:
        f.parts.append(f'<circle cx="{x}" cy="270" r="8" fill="{PALETTE[col][1]}"/>')
        f.text(x, 250 if up else 304, lab, 17, PALETTE[col][1], "700", "middle")
    f.text(485, 150, "绿点 0.1 + 0.2 实际存成 0.30000000000000004", 15, PALETTE["green"][1], anchor="middle")
    f.text(760, 334, "不在区间内：不相等", 15, PALETTE["red"][1], anchor="middle")
    f.text(455, 360, "|a - b| < eps 就当作相等（常取 1e-9）", 17, INK, anchor="middle")
    return f.save()


def build_all():
    w = []
    for fn in (amortized, master_cases, float_eps):
        w += fn()
    return w
