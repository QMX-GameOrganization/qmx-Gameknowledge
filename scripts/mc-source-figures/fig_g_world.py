import numpy as np, sys
sys.path.insert(0, '.')
from style import *
import mcnoise as m, terrain as T
from matplotlib.colors import ListedColormap, BoundaryNorm

# ======================= 图17：shift_x / shift_z 域扭曲 =======================
w = T.World(74)
x = np.arange(1050, 1450.0, 1.0); z = np.arange(-200, 200.0, 1.0)
X, Z = np.meshgrid(x, z)
c0, _, _ = w.climate(X, Z, warp=False)
c1, _, _ = w.climate(X, Z, warp=True)
sx, sz = w.shifts(X, Z)
fig, axs = plt.subplots(1, 3, figsize=(15, 4.9))
th = -0.12
for ax, c, ttl in [(axs[0], c0, '没有 shift：直接采样 continents（黑线=海岸线）'), (axs[1], c1, '有 shift（游戏真实做法）：红线=新海岸线\n黑虚线=没有 shift 时的海岸线')]:
    ax.imshow(c, origin='lower', extent=[x[0], x[-1], z[0], z[-1]], cmap='coolwarm', vmin=-0.7, vmax=0.7, aspect='equal')
    if c is c0:
        ax.contour(X, Z, c, levels=[th], colors='k', linewidths=1.6)
    else:
        ax.contour(X, Z, c0, levels=[th], colors='k', linewidths=1.2, linestyles='--')
        ax.contour(X, Z, c, levels=[th], colors=[C['red']], linewidths=1.8)
    ax.set_title(ttl, fontsize=11); ax.grid(False); ax.set_xlabel('x'); ax.set_ylabel('z')
im = axs[2].imshow(np.hypot(sx, sz) / 0.25 * 0.25 * 1.0, origin='lower', extent=[x[0], x[-1], z[0], z[-1]], cmap='viridis', aspect='equal')
axs[2].set_title('shift 位移量（噪声坐标单位）\n×4 = 实际偏移的方块数上限', fontsize=11); axs[2].grid(False); fig.colorbar(im, ax=axs[2], fraction=.046)
fig.suptitle('域扭曲（domain warping）：先用小尺度噪声把采样点推一下（最多十几格），再去采样大尺度噪声 → 海岸线多出自然的细小曲折', fontsize=12.5, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '17-shift-domain-warp.png')

# ======================= 图18：BiomeManager 的“模糊放大” =======================
M64 = (1 << 64) - 1
def lcg_next(seed, salt):
    seed &= M64
    seed = (seed * ((seed * 6364136223846793005 + 1442695040888963407) & M64)) & M64
    return (seed + salt) & M64
def to_signed(v):
    return v - (1 << 64) if v >= (1 << 63) else v
def fiddle(l):
    d = ((to_signed(l) >> 24) % 1024) / 1024.0
    return (d - 0.5) * 0.9
def fiddled_distance(seed, i, j, k, d, e, f):
    mm = lcg_next(seed, i); mm = lcg_next(mm, j); mm = lcg_next(mm, k)
    mm = lcg_next(mm, i); mm = lcg_next(mm, j); mm = lcg_next(mm, k)
    g = fiddle(mm); mm = lcg_next(mm, seed); h = fiddle(mm); mm = lcg_next(mm, seed); n = fiddle(mm)
    return (f + n) ** 2 + (e + h) ** 2 + (d + g) ** 2
def get_biome_quart(seed, bx, by, bz, grid):
    """BiomeManager.getBiome：把方块坐标 -2 后落到 4×4×4 的“四分位”网格，在 8 个角里挑被抖动后最近的那个"""
    i, j, k = bx - 2, by - 2, bz - 2
    l, m_, n = i >> 2, j >> 2, k >> 2
    d, e, f = (i & 3) / 4.0, (j & 3) / 4.0, (k & 3) / 4.0
    best, bd = 0, 1e18
    for p in range(8):
        bl, bl2, bl3 = (p & 4) == 0, (p & 2) == 0, (p & 1) == 0
        q, r, s = (l if bl else l + 1), (m_ if bl2 else m_ + 1), (n if bl3 else n + 1)
        h = d if bl else d - 1.0; t = e if bl2 else e - 1.0; u = f if bl3 else f - 1.0
        v = fiddled_distance(seed, q, r, s, h, t, u)
        if bd > v: best, bd = p, v
    px = l if (best & 4) == 0 else l + 1; pz = n if (best & 1) == 0 else n + 1
    return grid[pz % grid.shape[0], px % grid.shape[1]]
rng = np.random.default_rng(5)
G = 10
f0 = rng.random((G, G))
for _ in range(2):   # 简单的 3×3 平均，让色块更连贯
    f0 = sum(np.roll(np.roll(f0, a, 0), b, 1) for a in (-1, 0, 1) for b in (-1, 0, 1)) / 9.0
cell = np.minimum(((f0 - f0.min()) / (f0.max() - f0.min() + 1e-9) * 5).astype(int), 4)
seed = 0x1234ABCD
size = G * 4
img_f = np.zeros((size, size), int); img_n = np.zeros((size, size), int)
for bz in range(size):
    for bx in range(size):
        img_f[bz, bx] = get_biome_quart(seed, bx, 0, bz, cell)
        img_n[bz, bx] = cell[bz // 4, bx // 4]
cmap = ListedColormap(['#86efac', '#fde68a', '#93c5fd', '#fca5a5', '#c4b5fd'])
fig, axs = plt.subplots(1, 3, figsize=(15, 5.2))
axs[0].imshow(cell, cmap=cmap, vmin=0, vmax=4, extent=[0, size, size, 0], interpolation='nearest'); axs[0].set_title(f'① 生成阶段只存/只算：每 4×4×4 格 1 个群系\n（{G}×{G} = {G*G} 个值）', fontsize=11)
axs[1].imshow(img_n, cmap=cmap, vmin=0, vmax=4, interpolation='nearest'); axs[1].set_title('② 如果直接“放大 4 倍”：格子边界是笔直的，\n方块感太强', fontsize=11)
axs[2].imshow(img_f, cmap=cmap, vmin=0, vmax=4, interpolation='nearest'); axs[2].set_title('③ BiomeManager.getBiome：每格看 8 个角，\n加伪随机抖动取最近 → 边界参差自然', fontsize=11)
for a in axs: a.grid(False); a.set_xticks([]); a.set_yticks([])
fig.suptitle('群系的“存储分辨率”与“查询分辨率”分离：存得粗（省内存、省算力），查得细（视觉自然）', fontsize=12.5, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '18-biome-zoom.png')

# ======================= 图19：含水层 Aquifer 的抖动网格 =======================
def floordiv(a, b): return int(np.floor(a / b))
rng2 = np.random.default_rng(9)
centers = {}
def center(gx, gy, gz):
    key = (gx, gy, gz)
    if key not in centers:
        centers[key] = (gx * 16 + rng2.integers(0, 10), gy * 12 + rng2.integers(0, 9), gz * 16 + rng2.integers(0, 10))
    return centers[key]
def probe(xq, yq, zq):
    l, mm, n = floordiv(xq - 5, 16), floordiv(yq + 1, 12), floordiv(zq - 5, 16)
    best = []
    for u in (0, 1):
        for v in (-1, 0, 1):
            for ww in (0, 1):
                c = center(l + u, mm + v, n + ww)
                d2 = (c[0] - xq) ** 2 + (c[1] - yq) ** 2 + (c[2] - zq) ** 2
                best.append((d2, (l + u, mm + v, n + ww)))
    best.sort()
    return best
xs = np.arange(0, 96); ys = np.arange(-30, 66)
ID = np.zeros((len(ys), len(xs)), int); SIM = np.zeros_like(ID, float)
ids = {}
zq = 20
for iy, yq in enumerate(ys):
    for ix, xq in enumerate(xs):
        b = probe(xq, yq, zq)
        key = b[0][1]
        ids.setdefault(key, len(ids))
        ID[iy, ix] = ids[key]
        SIM[iy, ix] = 1 - abs(b[1][0] - b[0][0]) / 25.0
fig, axs = plt.subplots(1, 2, figsize=(13.5, 5.6))
cm_ = plt.get_cmap('tab20')
axs[0].imshow(ID % 20, origin='lower', extent=[0, 96, -30, 66], cmap='tab20', alpha=.55, aspect='equal', interpolation='nearest')
cx = [c for c in centers.values() if 0 <= c[0] < 96 and -30 <= c[1] < 66]
axs[0].plot([c[0] for c in cx], [c[1] for c in cx], 'k^', ms=7, label='含水层中心（每个 16×12×16 网格 1 个）')
axs[0].set_title('每个方块归属“最近的含水层中心”（z=20 的 x–y 剖面）', fontsize=11); axs[0].legend(fontsize=9, loc='upper center', bbox_to_anchor=(0.5, -0.12)); axs[0].set_xlabel('x'); axs[0].set_ylabel('y'); axs[0].grid(False)
im = axs[1].imshow(np.clip(SIM, 0, 1), origin='lower', extent=[0, 96, -30, 66], cmap='magma_r', aspect='equal', interpolation='nearest')
fig.colorbar(im, ax=axs[1], fraction=.046, label='similarity = 1 − |d₂ − d₁| / 25')
axs[1].set_title('similarity 越大 → 越靠近两个含水层的交界\n→ 越可能被“屏障”（barrier 噪声 + 水位差压力）隔开', fontsize=11); axs[1].set_xlabel('x'); axs[1].grid(False)
fig.suptitle('Aquifer：用“抖动网格 + 最近两/三个中心”，把地下水位分成互相独立的水体，并在交界处留出岩壁', fontsize=12.5, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '19-aquifer-jittered-grid.png')

# ======================= 图20：噪声 octave 叠加 =======================
rng3 = np.random.default_rng(3)
amps = [1.0, 1.0, 2.0, 2.0, 2.0, 1.0, 1.0, 1.0, 1.0]
pn = m.PerlinNoise(rng3, -9, amps)
xs = np.arange(0, 4096, 2.0)
fig, axs = plt.subplots(1, 2, figsize=(14.5, 6.2), gridspec_kw={'width_ratios': [1.5, 1]})
j = pn.lowest_in; k = pn.lowest_val
total = 0; offs = 0
cols = plt.cm.viridis(np.linspace(0, .9, len(amps)))
for idx, (lv, a) in enumerate(zip(pn.levels, amps)):
    contrib = a * lv.noise(m.wrap(xs * j), 0 * xs, m.wrap(0 * xs)) * k
    total = total + contrib
    axs[0].plot(xs, contrib + (len(amps) - idx) * 0.6, color=cols[idx], lw=1.4)
    axs[0].text(4110, (len(amps) - idx) * 0.6, f'octave {-9+idx}\n波长≈{int(1/(j))} 格, 振幅×{a:g}', fontsize=7.8, va='center', color=cols[idx])
    j *= 2; k /= 2
axs[0].plot(xs, total * 2.0 - 0.6, color=C['red'], lw=2.4); axs[0].text(4110, -0.6, 'Σ 叠加 (×2 放大显示)', color=C['red'], fontsize=9, va='center')
axs[0].set_xlim(0, 4096 + 700); axs[0].set_yticks([]); axs[0].set_xlabel('x（噪声坐标）')
axs[0].set_title('PerlinNoise = 多个 ImprovedNoise 的叠加\n每个 octave 频率×2、权重（lowestFreqValueFactor 起）÷2，再乘 amplitudes[i]', fontsize=11)
nn = m.NormalNoise(rng3, -9, amps)
v1 = nn.a.value(xs, 0 * xs, 0 * xs); v2 = nn.b.value(xs * 1.0181268882175227, 0 * xs, 0 * xs); vv = nn.value(xs, 0 * xs, 0 * xs)
axs[1].plot(xs, v1, color=C['blue'], lw=1.2, label='first'); axs[1].plot(xs, v2, color=C['green'], lw=1.2, label='second（频率×1.018）'); axs[1].plot(xs, vv / nn.factor * 0.5, color=C['red'], lw=2.2, label='(first+second)/2')
axs[1].set_title('NormalNoise = 两份 PerlinNoise 平均\n第二份频率略高 → 打破单份噪声的规整感，并让分布更接近正态', fontsize=11)
axs[1].legend(fontsize=8.5); axs[1].set_xlabel('x（噪声坐标）')
fig.tight_layout(); save(fig, '20-noise-octaves.png')
