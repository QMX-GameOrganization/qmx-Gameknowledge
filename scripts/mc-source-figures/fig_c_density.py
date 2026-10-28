import numpy as np, sys, time
sys.path.insert(0, '.')
from style import *
import mcnoise as m, terrain as T
from matplotlib.colors import ListedColormap

w = T.World(7)
t0 = time.time()

# ======================= 图7：factor 决定“3D 噪声有多大话语权” =======================
x1 = np.arange(0, 256.0); y1 = np.arange(10, 210.0)
X, Y = np.meshgrid(x1, y1)
base = w.base.compute(X, Y, 0 * X)
off_total = 0.18 - 0.50375          # 样条输出取 0.18 → 基础地表约 y = 63.5+128·0.18 ≈ 86
dep = T.depth_of(Y, off_total)
surf_y = 63.5 + 128 * 0.18
cm = ListedColormap(['#e0f2fe', '#475569'])
facs = [6.25, 3.0, 1.5, 0.7]

fig, axs = plt.subplots(2, 4, figsize=(15, 7.4), sharex=True, sharey=True)
for j, f in enumerate(facs):
    for i, qn in enumerate([True, False]):
        ax = axs[i, j]
        d = T.sloped_cheese(dep, f, 0.0, 0.0, base, qn=qn)
        ax.imshow(d > 0, origin='lower', extent=[x1[0], x1[-1], y1[0], y1[-1]], cmap=cm, aspect='auto', interpolation='nearest')
        ax.axhline(surf_y, color=C['red'], lw=1.2, ls='--')
        ax.grid(False)
        if i == 0:
            ax.set_title(f'factor = {f}', fontsize=11)
        if j == 0:
            ax.set_ylabel(('用 quarter_negative（真实）' if qn else '去掉 quarter_negative（对照）') + '\ny')
        ax.set_xlabel('x（z=0 的竖直剖面）') if i == 1 else None
fig.suptitle('同一份 3D 噪声、同一条基准地表（红虚线 y≈86）：factor 越小，噪声越能“撕开”地形（灰=实心）', fontsize=13, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '07-factor-and-quarter-negative.png')

# 1D 视角：一根柱子上，density 随 y 的变化 + 噪声“带宽”
fig, axs = plt.subplots(1, 2, figsize=(12.5, 4.8))
yy = np.linspace(10, 210, 600)
dd = T.depth_of(yy, off_total)
ns = base.std()
for f, col in zip([6.25, 3.0, 1.5, 0.7], [C['teal'], C['blue'], C['orange'], C['red']]):
    axs[0].plot(4 * m.quarter_negative(dd * f), yy, color=col, lw=2.3, label=f'factor={f}')
axs[0].axvspan(-0.3, 0.3, color='#fde68a', alpha=.45, label='3D 噪声典型幅度 ≈ ±0.3')
axs[0].axvline(0, color='#334155', lw=1.2); axs[0].set_xlim(-2.2, 6); axs[0].set_ylim(10, 210)
axs[0].set_xlabel('4·quarter_negative(depth·factor)  （噪声加上去之前）'); axs[0].set_ylabel('y')
axs[0].set_title('黄带 = 噪声能改变的范围\n曲线穿过黄带的这段 y 就是“被噪声支配的高度区间”', fontsize=11); axs[0].legend(fontsize=8.5, loc='upper right')
# 右：被噪声支配的高度区间宽度
fs = np.linspace(0.5, 6.5, 80)
def band(f, qn):
    d = dd * f
    v = 4 * (m.quarter_negative(d) if qn else d)
    ok = (v > -0.3) & (v < 0.3)
    return yy[ok].max() - yy[ok].min() if ok.any() else 0
axs[1].plot(fs, [band(f, True) for f in fs], color=C['red'], lw=2.4, label='真实：air 侧斜率 ×¼')
axs[1].plot(fs, [band(f, False) for f in fs], color=C['gray'], lw=2.4, ls='--', label='对照：不做 quarter_negative')
axs[1].set_xlabel('factor'); axs[1].set_ylabel('噪声能决定“实/空”的高度范围（格）')
axs[1].set_title('factor ↓ → 受噪声支配的高度带 ↑\nquarter_negative 把空气一侧的带拉得更宽（更容易出现悬空/悬崖）', fontsize=11)
axs[1].legend(fontsize=9)
fig.tight_layout(); save(fig, '08-factor-noise-band.png')
print('fig7/8', time.time() - t0)

# ======================= 图9：一条完整剖面，把整条流水线摊开 =======================
w9 = T.World(74)       # 挑一个“海—岸—平原—山”都出现的种子，便于讲解
xs = np.arange(0, 6000, 3.0)
cc, ee, ww = w9.climate(xs, 0 * xs)
rf = m.folded(ww)
off, fac, jg = m.terrain_params(cc, ee, ww)
jn = w9.jag_noise(xs, 0 * xs)
ys = np.arange(-64, 300, 2.0)
XS, YS = np.meshgrid(xs, ys)
b3 = w9.base.compute(XS, YS, 0 * XS)
d_ = T.depth_of(YS, off[None, :])
sc = T.sloped_cheese(d_, fac[None, :], jg[None, :], jn[None, :], b3)
fd = T.slide_overworld(sc * 1.0, YS)
solid = fd > 0

fig = plt.figure(figsize=(14.5, 11.5))
gs = fig.add_gridspec(4, 1, height_ratios=[1.0, 0.75, 0.75, 2.2], hspace=0.38)
a = fig.add_subplot(gs[0]); a.plot(xs, cc, color=C['blue'], lw=1.8, label='continents'); a.plot(xs, ee, color=C['green'], lw=1.8, label='erosion'); a.plot(xs, ww, color=C['red'], lw=1.8, label='ridges (weirdness)')
a.set_title('① 三个只依赖 (x,z) 的低频噪声', loc='left'); a.legend(ncol=3, fontsize=9, loc='upper right'); a.set_xlim(0, 6000)
a = fig.add_subplot(gs[1]); a.plot(xs, off - m.GLOBAL_OFFSET, color=C['purple'], lw=2, label='offset 样条'); a.axhline(0, color='#94a3b8', lw=.8)
a.set_title('② 样条 1：offset（决定基础地表高度，右轴=对应 y）', loc='left'); a.set_xlim(0, 6000); a.set_ylabel('offset')
a2 = a.secondary_yaxis('right', functions=(lambda v: 63.5 + 128 * v, lambda y: (y - 63.5) / 128)); a2.set_ylabel('y')
a = fig.add_subplot(gs[2]); a.plot(xs, fac, color=C['orange'], lw=2, label='factor'); a.plot(xs, jg * 10, color=C['pink'], lw=1.8, label='jaggedness ×10')
a.set_title('③ 样条 2、3：factor（陡峭度）与 jaggedness（山顶锯齿）', loc='left'); a.legend(ncol=2, fontsize=9, loc='upper right'); a.set_xlim(0, 6000)
a = fig.add_subplot(gs[3])
img = np.zeros(solid.shape + (3,)); img[:] = [0.88, 0.95, 1.0]
water = (~solid) & (YS <= 63); img[water] = [0.25, 0.55, 0.95]
img[solid] = [0.36, 0.40, 0.46]
# 顶部 1 格用草色标出地表
top = solid & ~np.vstack([solid[1:], np.zeros((1, solid.shape[1]), bool)])
img[top] = [0.30, 0.65, 0.30]
a.imshow(img, origin='lower', extent=[0, 6000, -64, 300], aspect='auto', interpolation='nearest'); a.grid(False)
a.set_title('④ sloped_cheese + slide 之后的 x–y 竖直剖面（蓝=海平面以下的水，灰=实心，绿=地表；不含洞穴）', loc='left')
a.set_xlabel('x（方块）'); a.set_ylabel('y')
fig.suptitle('一条 6000 格长的剖面：低频噪声 → 样条 → 地形（算法忠实移植，随机种子为示意）', fontsize=13.5, fontweight='bold', y=0.93)
save(fig, '09-transect-pipeline.png')
print('fig9', time.time() - t0)

# ======================= 图10：cell 角点插值（4×8）vs 逐方块 =======================
x0 = np.arange(0, 96.0); y0 = np.arange(0, 192.0)
XX, YY = np.meshgrid(x0, y0)
# 选一块起伏比较大的区域：中等 offset + 小 factor
offv, facv = 0.30 - 0.50375, 1.3
dfull = T.sloped_cheese(T.depth_of(YY, offv), facv, 0.0, 0.0, w.base.compute(XX + 40, YY, 0 * XX))
solid_f = dfull > 0
cx = np.arange(0, 97, 4.0); cy = np.arange(0, 193, 8.0)
CX, CY = np.meshgrid(cx, cy)
dcorner = T.sloped_cheese(T.depth_of(CY, offv), facv, 0.0, 0.0, w.base.compute(CX + 40, CY, 0 * CX))
# 双线性插值（z 固定在 cell 角点平面上，所以三线性退化为二线性）；顺序同 NoiseChunk：先 Y，再 X
dint = np.zeros_like(dfull)
for iy, yv in enumerate(y0):
    cyi = int(yv // 8); ty = (yv - cyi * 8) / 8
    row0 = m.lerp(ty, dcorner[cyi], dcorner[cyi + 1])           # 沿 Y
    for ix, xv in enumerate(x0):
        cxi = int(xv // 4); tx = (xv - cxi * 4) / 4
        dint[iy, ix] = m.lerp(tx, row0[cxi], row0[cxi + 1])    # 再沿 X
solid_i = dint > 0
diff = solid_f != solid_i
fig, axs = plt.subplots(1, 4, figsize=(16, 6.3), sharey=True)
ext = [0, 96, 0, 192]
axs[0].imshow(solid_f, origin='lower', extent=ext, cmap=cm, aspect='auto', interpolation='nearest'); axs[0].set_title(f'逐方块算 finalDensity\n{solid_f.size} 次求值', fontsize=11)
axs[1].imshow(solid_i, origin='lower', extent=ext, cmap=cm, aspect='auto', interpolation='nearest')
axs[1].plot(CX.ravel(), CY.ravel(), '.', color=C['red'], ms=3)
axs[1].set_title(f'cell 角点插值（4×8）\n仅 {CX.size} 次求值，红点=角点', fontsize=11)
axs[2].imshow(solid_f, origin='lower', extent=ext, cmap=ListedColormap(['#f1f5f9', '#cbd5e1']), aspect='auto', interpolation='nearest')
dm = np.ma.masked_where(~diff, diff)
axs[2].imshow(dm, origin='lower', extent=ext, cmap=ListedColormap([C['red']]), aspect='auto', interpolation='nearest')
axs[2].set_title(f'差异（红）：{diff.sum()} 格 = {100*diff.mean():.2f}%\n只在表面附近、且贴着 0 的位置', fontsize=11)
for gx in cx: axs[3].axvline(gx, color='#e2e8f0', lw=.6)
for gy in cy: axs[3].axhline(gy, color='#e2e8f0', lw=.6)
im = axs[3].imshow(dint, origin='lower', extent=ext, cmap='RdBu_r', vmin=-1.5, vmax=1.5, aspect='auto', interpolation='nearest')
axs[3].contour(x0 + .5, y0 + .5, dint, levels=[0], colors='k', linewidths=1)
axs[3].set_title('插值后的密度场（黑线 = 0 等值线）\n角点之间是线性变化', fontsize=11)
for a in axs: a.grid(False); a.set_xlabel('x')
axs[0].set_ylabel('y')
fig.suptitle('Cell 插值：把“每格都算噪声”换成“每 4×8 格算一次，其余线性插值”', fontsize=13, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '10-cell-interpolation.png')
print('mismatch %', 100 * diff.mean(), 'full', solid_f.size, 'corners', CX.size, 'ratio', solid_f.size / CX.size)
