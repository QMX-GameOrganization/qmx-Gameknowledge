import numpy as np, sys
sys.path.insert(0, '.')
from style import *
import mcnoise as m, mcend
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

def clg(y, y0, y1, v0, v1):
    t = np.clip((np.asarray(y, float) - y0) / (y1 - y0), 0, 1)
    return v0 + t * (v1 - v0)

def slide(df, y, minY, h, k, l, dt, mm, n, et):
    top = clg(y, minY + h - k, minY + h - l, 1.0, 0.0)
    d2 = dt + top * (df - dt)
    bot = clg(y, minY + mm, minY + n, 0.0, 1.0)
    return et + bot * (d2 - et)

def squeeze(d):
    c = np.clip(d, -1, 1)
    return c / 2 - c ** 3 / 24

# ====================== 图34：下界密度 ======================
def nether_slide(df, y):
    return slide(df, y, 0, 128, 24, 0, 0.9375, -8, 24, 2.5)

rng = np.random.default_rng(11)
bn = m.BlendedNoise(rng, 0.25, 0.375, 80.0, 60.0, 8.0)
xs = np.arange(0, 256, 1.0); ys = np.arange(0, 128, 1.0)
X, Y = np.meshgrid(xs, ys)
noise = bn.compute(X, Y, np.zeros_like(X) + 37.0)
dens = nether_slide(noise, Y)
fin = squeeze(0.64 * dens)
solid = fin > 0

fig, ax = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw=dict(width_ratios=[1, 1.45]))
a = ax[0]
yy = np.linspace(-10, 135, 400)
for nv, c in [(-0.4, C['blue']), (0.0, C['gray']), (0.4, C['red'])]:
    a.plot(nether_slide(nv, yy), yy, color=c, lw=2, label=f'base_3d_noise = {nv:+.1f}')
a.axvline(0, color='#0f172a', lw=1)
a.axhline(32, color=C['orange'], ls='--', lw=1); a.text(2.55, 33, '海平面 32（岩浆）', color=C['orange'], fontsize=8, ha='right')
a.axhspan(104, 128, color='#fde68a', alpha=.4); a.text(2.55, 116, '顶部 24 格\n向 0.9375 淡入', fontsize=8, ha='right', va='center')
a.axhspan(-8, 24, color='#bfdbfe', alpha=.4); a.text(2.55, 8, '底部 32 格\n向 2.5 淡入', fontsize=8, ha='right', va='center')
a.set_xlim(-1.2, 2.6); a.set_ylim(-10, 135)
a.set_xlabel('slide 之后的密度（>0 为实心）'); a.set_ylabel('y'); a.set_title('下界密度的垂直剖面：两端被 slide 压成实心')
a.legend(loc='center right', fontsize=8, frameon=True, framealpha=.9)
b = ax[1]
img = np.zeros(solid.shape)
img[solid] = 1
lava = (~solid) & (Y <= 32)
img[lava] = 2
cm = ListedColormap(['#fef3c7', '#7f1d1d', '#f97316'])
b.imshow(img, origin='lower', cmap=cm, extent=[0, 256, 0, 128], aspect='equal', interpolation='nearest')
b.set_xlabel('x'); b.set_ylabel('y'); b.grid(False)
b.set_title('下界 x–y 切片（numpy 移植，种子示意）')
b.legend(handles=[Patch(color='#7f1d1d', label='下界岩'), Patch(color='#f97316', label='岩浆海 y≤32'), Patch(color='#fef3c7', label='空气')],
         loc='upper right', fontsize=8, ncol=3, framealpha=.9, frameon=True)
fig.tight_layout(); save(fig, '34-nether-density.png')
print('nether solid frac', solid.mean(), 'noise range', noise.min(), noise.max())

# ====================== 图35：末地外岛 ======================
SEED = 0
simp = mcend.make_islands(SEED)
R = 2600                                 # 方块
step = 2                                 # i 以 8 方块为单位，步长 2 = 16 方块
ii = np.arange(-R // 8, R // 8 + 1, step)
I, J = np.meshgrid(ii, ii)
H = mcend.height_grid(simp, I, J, R // 16 + 14)
D = (H - 8.0) / 128.0
bx = ii * 8
# 生物群系：以区块中心 (16*c+8) 取 erosion
cs = np.arange(-R // 16, R // 16 + 1)
CX, CZ = np.meshgrid(cs, cs)
Ib = np.trunc((CX * 16 + 8) / 8).astype(int); Jb = np.trunc((CZ * 16 + 8) / 8).astype(int)
Hb = mcend.height_grid(simp, Ib, Jb, R // 16 + 14)
Db = (Hb - 8.0) / 128.0
bio = np.where(Db > 0.25, 3, np.where(Db >= -0.0625, 2, np.where(Db < -0.21875, 0, 1)))
bio = np.where(CX.astype(np.int64) ** 2 + CZ.astype(np.int64) ** 2 <= 4096, 4, bio)

fig, ax = plt.subplots(1, 2, figsize=(13, 6.2))
a = ax[0]
im = a.imshow(D, origin='lower', extent=[bx[0], bx[-1], bx[0], bx[-1]], cmap='terrain', vmin=-0.85, vmax=0.57)
a.set_title(f'end_islands 密度函数值（种子 {SEED}，真实算法）'); a.set_xlabel('x（方块）'); a.set_ylabel('z（方块）'); a.grid(False)
cb = fig.colorbar(im, ax=a, fraction=.046); cb.set_label('(heightValue − 8) / 128')
th = np.linspace(0, 2 * np.pi, 200)
a.plot(1024 * np.cos(th), 1024 * np.sin(th), 'w--', lw=1); a.text(0, 1060, '半径 1024 方块（4096 = 64² 区块）', color='k', fontsize=8, ha='center')
b = ax[1]
colors = ['#a78bfa', '#94a3b8', '#fbbf24', '#16a34a', '#0f172a']
b.imshow(bio, origin='lower', extent=[cs[0] * 16, cs[-1] * 16, cs[0] * 16, cs[-1] * 16], cmap=ListedColormap(colors), norm=BoundaryNorm([-.5, .5, 1.5, 2.5, 3.5, 4.5], 5), interpolation='nearest')
b.set_title('TheEndBiomeSource 的群系分类'); b.set_xlabel('x（方块）'); b.grid(False)
b.legend(handles=[Patch(color=colors[4], label='the_end（主岛，半径 1024 内）'), Patch(color=colors[3], label='end_highlands  d>0.25'),
                  Patch(color=colors[2], label='end_midlands  −0.0625≤d≤0.25'), Patch(color=colors[0], label='small_end_islands  d<−0.21875'),
                  Patch(color=colors[1], label='end_barrens  其余')], loc='lower left', fontsize=8, frameon=True, framealpha=.9)
fig.tight_layout(); save(fig, '35-end-islands.png')
print('biome fractions outside main', [(bio == k).sum() / (bio != 4).sum() for k in range(4)])

# ====================== 图36：主岛轮廓与垂直剖面 ======================
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.8))
a = ax[0]
xb = np.arange(0, 1400, 8)
Hx = mcend.height_grid(simp, (xb // 8).reshape(1, -1), np.zeros((1, len(xb)), int), 110)[0]
a.plot(xb, (Hx - 8) / 128, color=C['blue'], lw=2)
base = np.clip(100 - np.sqrt(((xb // 8) ** 2).astype(float)) * 8, -100, 80)
a.plot(xb, (base - 8) / 128, color=C['gray'], ls='--', label='只看主岛项  100 − 8·距离（夹在 −100~80）')
a.axhline(0.5625, color=C['green'], lw=.8, ls=':'); a.axhline(-0.84375, color=C['red'], lw=.8, ls=':')
a.text(1380, 0.58, 'maxValue 0.5625', ha='right', fontsize=8); a.text(1380, -0.81, 'minValue −0.84375', ha='right', fontsize=8)
a.axvline(1024, color=C['orange'], ls='--'); a.text(1030, -0.3, '外岛起点\n(q²+r²>4096)', fontsize=8, color=C['orange'])
a.set_xlabel('沿 +x 轴到原点的距离（方块）'); a.set_ylabel('end_islands 值'); a.set_title('主岛：平顶、陡坡')
a.legend(fontsize=8, loc='center left', bbox_to_anchor=(0.12, .55))
b = ax[1]
yy = np.linspace(0, 128, 400)
for v, c, nm in [(0.5625, C['green'], '主岛中心 0.5625'), (0.2, C['teal'], '0.2'), (-0.2, C['amber'], '−0.2（小岛边缘）'), (-0.84375, C['red'], '−0.84375（虚空）')]:
    s = slide(v, yy, 0, 128, 72, -184, -23.4375, 4, 32, -0.234375)
    b.plot(s, yy, color=c, lw=2, label=nm)
b.axvline(0, color='k', lw=1)
b.set_xlabel('slideEnd 之后的密度（忽略 base_3d_noise_end；>0 为实心）'); b.set_ylabel('y'); b.set_title('末地的垂直剖面：同一个 slide 决定岛有多厚')
b.legend(fontsize=8, loc='upper right'); b.set_xlim(-1.0, 0.8)
fig.tight_layout(); save(fig, '36-end-profile.png')
