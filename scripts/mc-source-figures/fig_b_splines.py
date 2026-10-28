import numpy as np, sys
sys.path.insert(0, '.')
from style import *
import mcnoise as m

# ---------- 图4：样条基础 ----------
fig, axs = plt.subplots(1, 3, figsize=(14, 4.3))
ax = axs[0]
P = [(0, 0), (10, 100), (20, 30)]
xs = np.linspace(-2, 22, 300)
ax.plot([p[0] for p in P], [p[1] for p in P], color=C['gray'], lw=2, marker='o', label='分段线性（折线）')
sp = m.Spline('x')
for (a, b), d in zip(P, [0, 0, 0]):
    sp.add(a, b, d)
ax.plot(xs, [sp({'x': v}) for v in xs], color=C['blue'], lw=2.4, label='三次样条，每点斜率=0')
# 斜率取割线斜率
sp2 = m.Spline('x'); sl = [10.0, (30 - 0) / 20, -7.0]
for (a, b), d in zip(P, sl):
    sp2.add(a, b, d)
ax.plot(xs, [sp2({'x': v}) for v in xs], color=C['red'], lw=2.4, label='三次样条，斜率=(10, 1.5, -7)')
ax.set_title('1) 样条 = 规定“必须经过的点”\n+（可选）每点的斜率'); ax.legend(fontsize=8, loc='lower center', bbox_to_anchor=(0.5, -0.38), ncol=1); ax.set_xlabel('x'); ax.set_ylabel('f(x)')

ax = axs[1]
xs = np.linspace(-0.4, 1.4, 400)
for d0, d1, col in [(0, 0, C['blue']), (2, 2, C['green']), (4, 0, C['orange']), (0, 4, C['purple']), (-2, -2, C['red'])]:
    s = m.Spline('x').add(0, 0, d0).add(1, 1, d1)
    ax.plot(xs, [s({'x': v}) for v in xs], color=col, lw=2.2, label=f"d0={d0}, d1={d1}")
ax.plot([0, 1], [0, 1], 'ko', ms=6); ax.axvspan(-0.4, 0, color='#f1f5f9'); ax.axvspan(1, 1.4, color='#f1f5f9')
ax.text(-0.38, 1.35, '区间外：沿端点斜率\n直线外推', fontsize=8.5, color='#475569')
ax.set_title('2) 同样两个点 (0,0) (1,1)\n斜率不同，曲线形状完全不同'); ax.legend(fontsize=8, loc='lower center', bbox_to_anchor=(0.5, -0.5), ncol=2); ax.set_xlabel('x'); ax.set_ylim(-1, 1.6)

ax = axs[2]
ero = np.linspace(-1, 1, 200)
def inner(vals):
    s = m.Spline('e')
    for (loc, v) in vals: s.add(loc, v)
    return s
i0 = inner([(-1, 0.0), (0, 0.0), (1, 0.0)])
i1 = inner([(-1, 1.0), (-0.3, 0.2), (0.4, 0.9), (1, 0.1)])
i2 = inner([(-1, 0.4), (0, 1.2), (1, 0.6)])
outer = m.Spline('c').add(0.0, i0).add(0.5, i1).add(1.0, i2)
for cv, col, ls in [(0.0, C['gray'], '-'), (0.5, C['blue'], '-'), (1.0, C['red'], '-'), (0.12, C['gray'], ':'), (0.25, C['teal'], '--'), (0.38, C['teal'], ':'), (0.75, C['purple'], '--')]:
    ax.plot(ero, [outer({'c': cv, 'e': e}) for e in ero], color=col, ls=ls, lw=2.2 if ls == '-' else 1.8, label=f'continents={cv}')
ax.set_title('3) 嵌套样条：外层的“值”本身是内层样条\n外层 c 在两个控制点之间时，内层曲线逐点混合'); ax.legend(fontsize=8, loc='lower center', bbox_to_anchor=(0.5, -0.5), ncol=2); ax.set_xlabel('erosion（内层坐标）'); ax.set_ylabel('样条输出')
fig.tight_layout(); save(fig, '04-spline-basics.png')

# ---------- 图5：offset 随 continents 的变化 ----------
cs = np.linspace(-1.2, 1.0, 400)
fig, axs = plt.subplots(1, 3, figsize=(14.2, 4.5), sharey=True)
panels = [(0.0, '山谷  weirdness=0 (折叠值 -1)'), (0.33, '坡面  weirdness=0.33 (折叠值 0)'), (0.667, '山峰  weirdness=2/3 (折叠值 +1)')]
eroscale = [(-0.95, '#7f1d1d'), (-0.6, C['red']), (-0.2, C['orange']), (0.2, C['green']), (0.6, C['blue']), (0.95, C['purple'])]
for ax, (w, ttl) in zip(axs, panels):
    for e, col in eroscale:
        o, f, j = m.terrain_params(cs, np.full_like(cs, e), np.full_like(cs, w))
        ax.plot(cs, o - m.GLOBAL_OFFSET, color=col, lw=2, label=f'erosion={e:+.2f}')
    for xx, nm in [(-0.51, '深海'), (-0.4, '海'), (-0.15, '海岸'), (0.1, '平原'), (0.45, '内陆')]:
        ax.axvline(xx, color='#cbd5e1', lw=.8, ls=':')
    ax.set_title(ttl, fontsize=11); ax.set_xlabel('continents'); ax.set_ylim(-0.35, 1.6)
    ax2 = ax.secondary_yaxis('right', functions=(lambda v: 63.5 + 128 * v, lambda y: (y - 63.5) / 128))
    if ax is axs[2]: ax2.set_ylabel('对应基础地表高度 y')
    else: ax2.set_visible(False)
axs[0].set_ylabel('offset 样条输出'); axs[0].legend(fontsize=8, loc='upper left')
fig.suptitle('overworld/offset：大陆性定“海陆”，侵蚀度定“高低”，山脊度定“起伏位置”', fontsize=13, fontweight='bold', y=1.02)
fig.tight_layout(); save(fig, '05-offset-by-continents.png')

# ---------- 图6：三个地形参数的热力图 ----------
N = 120
cg = np.linspace(-1.1, 1.0, N); eg = np.linspace(-1.0, 1.0, N)
CG, EG = np.meshgrid(cg, eg)
fig, axs = plt.subplots(2, 3, figsize=(14, 8.2))
rows = [(0.0, '山谷 (w=0)'), (0.667, '山峰 (|w|=2/3)')]
cfg = [('offset（→ 地表高度）', 'terrain', lambda o, f, j: o - m.GLOBAL_OFFSET, (-0.25, 1.5)), ('factor（→ 竖向压缩/陡峭度）', 'magma_r', lambda o, f, j: f, (0.5, 6.4)), ('jaggedness（→ 山顶锯齿）', 'viridis', lambda o, f, j: j, (0, 0.32))]
for r, (w, rname) in enumerate(rows):
    o, f, j = m.terrain_params(CG, EG, np.full_like(CG, w))
    for c, (nm, cmap, sel, (vlo, vhi)) in enumerate(cfg):
        ax = axs[r, c]
        im = ax.imshow(sel(o, f, j), origin='lower', extent=[cg[0], cg[-1], eg[0], eg[-1]], aspect='auto', cmap=cmap, vmin=vlo, vmax=vhi)
        ax.set_title(f'{nm}\n{rname}', fontsize=10.5); ax.set_xlabel('continents'); ax.set_ylabel('erosion')
        ax.grid(False); fig.colorbar(im, ax=ax, fraction=.046)
fig.suptitle('同一个 (continents, erosion) 平面：山谷 vs 山峰，offset / factor / jaggedness 的分布', fontsize=13, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '06-terrain-params-heatmaps.png')
