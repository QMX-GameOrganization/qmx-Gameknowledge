import numpy as np, sys, math
sys.path.insert(0, '.')
from style import *
import mcnoise as m
from matplotlib.patches import Rectangle
from matplotlib.colors import ListedColormap

# ====================== 图30：OreFeature.doPlace 的 numpy 移植 ======================
def vein(size, rng):
    f = rng.random() * math.pi
    g = size / 8.0
    d, e = math.sin(f) * g, -math.sin(f) * g          # x 端点（以 0 为原点）
    h, p = math.cos(f) * g, -math.cos(f) * g          # z 端点
    l, mm = rng.integers(0, 3) - 2, rng.integers(0, 3) - 2     # 两端 y 各自独立
    cs = np.zeros((size, 4))
    for q in range(size):
        t = q / size
        cx = d + (e - d) * t; cy = l + (mm - l) * t; cz = h + (p - h) * t
        v = rng.random() * size / 16.0
        r = ((math.sin(math.pi * t) + 1.0) * v + 1.0) / 2.0          # 中间粗、两端细
        cs[q] = (cx, cy, cz, r)
    for q in range(size):                                            # 一球包含另一球 → 去掉较小的
        if cs[q, 3] < 0: continue
        for x in range(q + 1, size):
            if cs[x, 3] < 0: continue
            dd = cs[q, :3] - cs[x, :3]
            if (cs[q, 3] - cs[x, 3]) ** 2 > dd @ dd:
                if cs[q, 3] > cs[x, 3]: cs[x, 3] = -1
                else: cs[q, 3] = -1
    blocks = set()
    for cx, cy, cz, r in cs:
        if r < 0: continue
        for x in range(int(math.floor(cx - r)), int(math.floor(cx + r)) + 1):
            for y in range(int(math.floor(cy - r)), int(math.floor(cy + r)) + 1):
                for z in range(int(math.floor(cz - r)), int(math.floor(cz + r)) + 1):
                    dx, dy, dz = (x + .5 - cx) / r, (y + .5 - cy) / r, (z + .5 - cz) / r
                    if dx * dx + dy * dy + dz * dz < 1.0: blocks.add((x, y, z))
    return blocks

rng = np.random.default_rng(4)
fig, axs = plt.subplots(2, 4, figsize=(15, 7.4), gridspec_kw={'height_ratios': [1.2, 1]})
for j, (size, name) in enumerate([(4, '钻石·小 size 4'), (9, '铁 size 9'), (17, '煤 size 17'), (64, 'size 64（配置上限）')]):
    b = vein(size, rng)
    arr = np.array(sorted(b))
    ax = axs[0, j]
    ax.scatter(arr[:, 0], arr[:, 2], c=arr[:, 1], cmap='viridis', s=60 if size < 30 else 14, marker='s')
    ax.set_aspect('equal'); ax.set_title(f'{name}\n本次放置 {len(b)} 格（俯视，颜色=y）', fontsize=10.5); ax.grid(True)
    counts = [len(vein(size, rng)) for _ in range(120)]
    ax = axs[1, j]; ax.hist(counts, bins=14, color=C['blue'], alpha=.8)
    ax.set_title(f'120 次的方块数分布：{min(counts)}~{max(counts)}，均值 {np.mean(counts):.1f}', fontsize=10); ax.set_xlabel('一条矿脉的方块数')
fig.suptitle('OreFeature：在水平线段上放置一串大小渐变的球（中间粗两端细），再按球逐格判定并用 BitSet 去重', fontsize=12.5, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '30-ore-vein-shape.png')

# ====================== 图31：叶片放置器每层半径（侧视，经过树干的切面） ======================
def rows_blob(h, r, off):         # BlobFoliagePlacer：m 从 off 降到 off-h
    return [(m, max(r + 0 - 1 - int(m / 2), 0)) for m in range(off, off - h - 1, -1)]
def rows_spruce(h, r, off, seed):
    mm = seed; n = 1; o = 0; out = []
    for p in range(off, -h - 1, -1):
        out.append((p, mm))
        if mm >= n: mm = o; o = 1; n = min(n + 1, r + 0)
        else: mm += 1
    return out
def rows_pine(h, r, off):
    mm = 0; out = []
    for n in range(off, off - h - 1, -1):
        out.append((n, mm))
        if mm >= 1 and n == off - h + 1: mm -= 1
        elif mm < r: mm += 1
    return out
def rows_fancy(h, r, off):
    return [(m, r + (1 if m != off and m != off - h else 0)) for m in range(off, off - h - 1, -1)]
trees = [
    ('橡树 oak（blob：高 3，半径 2，偏移 0，树干 5 格）', 5, rows_blob(3, 2, 0)),
    ('云杉 spruce（树高 7，叶高 max(4, 7−1)=6，半径 3，偏移 1）', 7, rows_spruce(6, 3, 1, 0)),
    ('松树 pine（树高 9，叶高 4，半径 1，偏移 1）', 9, rows_pine(4, 1, 1)),
    ('大橡树 fancy 的一团叶（高 4，半径 2，偏移 4）', 0, rows_fancy(4, 2, 4)),
]
fig, axs = plt.subplots(1, 4, figsize=(15, 5.6))
for ax, (ttl, H, rows) in zip(axs, trees):
    for (yy, rad) in rows:
        for x in range(-rad, rad + 1):
            ax.add_patch(Rectangle((x - .5, H + yy - .5), 1, 1, fc='#4ade80', ec='#166534', lw=.6))
    for y in range(H):
        ax.add_patch(Rectangle((-.5, y - .5), 1, 1, fc='#92400e', ec='#451a03', lw=.6))
    top = max(y for y, _ in rows) + H
    ax.set_xlim(-6, 6); ax.set_ylim(-1, 13); ax.set_aspect('equal'); ax.grid(False)
    ax.set_title(ttl, fontsize=9.6)
    ax.text(0, -0.9 + 0, '各层半径（自上而下）：' + ' '.join(str(r) for _, r in rows), ha='center', fontsize=8.5, color='#334155')
fig.suptitle('FoliagePlacer.createFoliage：每一层只是“半径 + 是否跳过角落”；不同树种靠不同的半径序列做出锥形、球形、塔形', fontsize=12, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '31-foliage-layers.png')

# ====================== 图32：晶洞 GeodeFeature 的“距离和”判定 ======================
rng = np.random.default_rng(21)
k = 4
dist_max = 6
pts = [(rng.integers(4, 7), rng.integers(4, 7), rng.integers(4, 7), rng.integers(1, 3)) for _ in range(k)]
d_ = k / dist_max
thr = dict(fill=1 / math.sqrt(1.7), inner=1 / math.sqrt(2.2 + d_), mid=1 / math.sqrt(3.2 + d_), outer=1 / math.sqrt(4.2 + d_))
noise = m.NormalNoise(np.random.default_rng(5), -4, [1.0])
crack = [(0, 7, 0), (0, 5, 0), (0, 1, 0)]
l_ = 1 / math.sqrt(2.0 + rng.random() / 2 + (d_ if k > 3 else 0))
R_ = 16
X, Z = np.meshgrid(np.arange(-R_, R_ + 1), np.arange(-R_, R_ + 1))
def slab(y):
    Y = np.full_like(X, y)
    n = noise.value(X.astype(float), Y.astype(float), Z.astype(float)) * 0.05
    s = sum(1 / np.sqrt((X - px) ** 2 + (Y - py) ** 2 + (Z - pz) ** 2 + off) + n for (px, py, pz, off) in pts)
    t = sum(1 / np.sqrt((X - cx) ** 2 + (Y - cy) ** 2 + (Z - cz) ** 2 + 2) + n for (cx, cy, cz) in crack)
    cls = np.full(X.shape, -1)
    cls[s >= thr['outer']] = 0; cls[s >= thr['mid']] = 1; cls[s >= thr['inner']] = 2; cls[s >= thr['fill']] = 3
    cls[(t >= l_) & (s < thr['fill']) & (s >= thr['outer'])] = 4        # 裂缝（空气）
    return cls
cmap = ListedColormap(['#f8fafc', '#475569', '#fcd34d', '#c4b5fd', '#7c3aed', '#ffffff'])
fig, axs = plt.subplots(1, 3, figsize=(15, 5.2))
for ax, y in zip(axs, [2, 5, 8]):
    cls = slab(y)
    show = np.where(cls == -1, 0, np.where(cls == 4, 5, cls + 1))
    ax.imshow(show, cmap=ListedColormap(['#f8fafc', '#475569', '#fcd34d', '#c4b5fd', '#7c3aed', '#fef2f2']), vmin=0, vmax=5, extent=[-R_ - .5, R_ + .5, R_ + .5, -R_ - .5], interpolation='nearest')
    ax.set_title(f'水平切片 y = {y}', fontsize=11); ax.grid(False); ax.set_xticks([]); ax.set_yticks([])
import matplotlib.patches as mp
fig.legend(handles=[mp.Patch(fc=c, ec='#94a3b8', label=l) for c, l in [('#475569', '外层 outer（玄武岩）'), ('#fcd34d', '中层 middle（方解石）'), ('#c4b5fd', '内层 inner（紫水晶块）'), ('#7c3aed', '填充 filling（空腔）'), ('#fef2f2', '裂缝（空气）')]], loc='lower center', ncol=5, fontsize=9, bbox_to_anchor=(0.5, -0.03))
fig.suptitle('GeodeFeature：对每个格子算 s = Σ 1/√(到各中心点的距离² + 偏移) + 噪声，再与四个递减的阈值比较，决定属于哪一层（算法移植，种子示意）', fontsize=11.5, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '32-geode-layers.png')

# ====================== 图33：滴水石的高度曲线 ======================
def drip_height(dist, radius, scale, blunt):
    if dist < blunt: dist = blunt
    i = dist / radius * 0.384
    mm = scale * (0.75 * i ** (4 / 3) - i ** (2 / 3) - (1 / 3) * math.log(i))
    return max(mm, 0.0) / 0.384 * radius
fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
ax = axs[0]
dd = np.linspace(0, 8, 400)
for blunt, col in [(0.3, C['teal']), (0.6, C['blue']), (0.9, C['red'])]:
    hs = np.array([drip_height(d, 8, 1.0, blunt) for d in dd])
    ax.plot(np.concatenate([-dd[::-1], dd]), np.concatenate([hs[::-1], hs]), color=col, lw=2.2, label=f'bluntness = {blunt}')
ax.set_title('getDripstoneHeight：柱子的轮廓（半径 8，高度缩放 1.0）', fontsize=11); ax.legend(); ax.set_xlabel('到中心的水平距离'); ax.set_ylabel('该处的柱高')
ax = axs[1]
for scale, col in [(0.5, C['teal']), (1.0, C['blue']), (2.0, C['red'])]:
    hs = np.array([drip_height(d, 8, scale, 0.5) for d in dd])
    ax.plot(np.concatenate([-dd[::-1], dd]), np.concatenate([hs[::-1], hs]), color=col, lw=2.2, label=f'height_scale = {scale}')
ax.set_title('同一半径，不同 height_scale', fontsize=11); ax.legend(); ax.set_xlabel('到中心的水平距离')
fig.tight_layout(); save(fig, '33-dripstone-profile.png')
