import numpy as np, sys
sys.path.insert(0, '.')
from style import *
import mcnoise as m

# ---------- 图1：Mapped 函数族 ----------
x = np.linspace(-2, 2, 801)
fns = [
    ('abs', 'abs(x)', np.abs(x), '折叠：负变正，制造“山脊线/山谷线”', C['blue']),
    ('square', 'square(x)', x ** 2, '只保留大小，0 附近被压得很平', C['green']),
    ('cube', 'cube(x)', x ** 3, '保留符号，小值被压扁、大值被放大', C['orange']),
    ('half_negative', 'half_negative(x)', m.half_negative(x), '负半边 ×0.5', C['purple']),
    ('quarter_negative', 'quarter_negative(x)', m.quarter_negative(x), '负半边 ×0.25（地形里用它）', C['red']),
    ('squeeze', 'squeeze(x)', m.squeeze(x), 'clamp(-1,1) 后做 c/2 - c³/24：平滑限幅', C['teal']),
]
fig, axs = plt.subplots(2, 3, figsize=(11.5, 6.4))
for ax, (nm, label, y, note, col) in zip(axs.flat, fns):
    ax.plot(x, x, color='#cbd5e1', lw=1.2, ls='--', label='y = x')
    ax.plot(x, y, color=col, lw=2.4, label=label)
    ax.axhline(0, color='#94a3b8', lw=.8); ax.axvline(0, color='#94a3b8', lw=.8)
    ax.set_ylim(-2.1, 2.1); ax.set_xlim(-2, 2)
    ax.set_title(nm, fontsize=11)
    ax.text(0.5, -0.2, note, transform=ax.transAxes, ha='center', va='top', fontsize=8.5, color='#475569')
    ax.legend(loc='lower right' if nm in ('abs','square') else 'upper left', fontsize=8)
fig.suptitle('DensityFunctions.Mapped：6 种“单输入变形”函数（虚线是 y = x 作对照）', fontsize=13, fontweight='bold', y=1.0)
fig.tight_layout(h_pad=3.0)
save(fig, '01-mapped-functions.png')

# ---------- 图2：ridges → ridges_folded ----------
w = np.linspace(-1, 1, 801)
f = m.folded(w)
fig, ax = plt.subplots(figsize=(8.4, 4.2))
ax.plot(w, f, color=C['blue'], lw=2.6, label='ridges_folded = -3·(| |w|−2/3 | − 1/3)')
ax.plot(w, w, color='#cbd5e1', ls='--', label='原始 weirdness (w)')
ax.axhline(0, color='#94a3b8', lw=.8)
for xx, lab, col in [(-1, '山谷\nValleys', C['teal']), (-2/3, '', None), (0, '山峰\nPeaks', C['red']), (2/3, '', None), (1, '山谷', C['teal'])]:
    pass
ax.fill_between(w, f, -0.5, where=f < -0.5, color=C['teal'], alpha=.25)
ax.fill_between(w, 0.5, f, where=f > 0.5, color=C['red'], alpha=.25)
ax.axhline(0.5, color=C['red'], lw=.8, ls=':'); ax.axhline(-0.5, color=C['teal'], lw=.8, ls=':')
ax.annotate('w=0 → 折叠值 -1\n（山谷，平坦低地）', xy=(0, -1), xytext=(-0.45, -1.45), arrowprops=dict(arrowstyle='->', color=C['teal']), color=C['teal'], fontsize=9)
ax.annotate('|w|=2/3 → 折叠值 +1\n（山峰，最高点）', xy=(2/3, 1), xytext=(0.12, 1.15), arrowprops=dict(arrowstyle='->', color=C['red']), color=C['red'], fontsize=9)
ax.set_xlabel('weirdness / ridges（原始噪声，约 -1~1）'); ax.set_ylabel('ridges_folded')
ax.set_ylim(-1.6, 1.5)
ax.set_title('peaksAndValleys：把一个噪声折成“谷—坡—峰—坡—谷”')
ax.legend(loc='lower right', fontsize=8.5)
fig.tight_layout(); save(fig, '02-ridges-folded.png')

# ---------- 图3：depth 与表面高度 ----------
y = np.linspace(-64, 320, 800)
grad = m.y_clamped_gradient(y, -64, 320, 1.5, -1.5)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.8, 4.8), gridspec_kw={'width_ratios': [1.15, 1]})
cols = [C['teal'], C['blue'], C['green'], C['orange'], C['red']]
for s, col in zip([-0.2222, -0.12, 0.0, 0.3, 0.8], cols):
    off = s + m.GLOBAL_OFFSET
    d = grad + off
    a1.plot(d, y, color=col, lw=2.2, label=f'样条输出 {s:+.2f}')
    ys = 63.5 + 128 * s
    a1.plot([0], [ys], 'o', color=col, ms=6)
a1.axvline(0, color='#334155', lw=1.2)
a1.axhline(63, color=C['blue'], lw=1, ls=':'); a1.text(1.45, 66, '海平面 y=63', color=C['blue'], fontsize=8.5, ha='right')
a1.set_xlabel('depth = yClampedGradient(-64→320, 1.5→-1.5) + offset'); a1.set_ylabel('y')
a1.set_title('depth 过零点 = 地表\n（左边 depth<0：空气；右边 depth>0：实心）', fontsize=11)
a1.legend(fontsize=8, loc='lower left')
a1.text(1.5, -30, '实心 →', color='#334155', ha='right', fontsize=10); a1.text(-2.05, -30, '← 空气', color='#334155', fontsize=10)
a1.set_xlim(-2.1, 1.6)
# 右：样条输出 → 地表高度（线性）
ss = np.linspace(-0.3, 1.1, 50)
a2.plot(ss, 63.5 + 128 * ss, color=C['blue'], lw=2.6)
for s, col in zip([-0.2222, -0.12, 0.0, 0.3, 0.8], cols):
    a2.plot([s], [63.5 + 128 * s], 'o', color=col, ms=8)
a2.axhline(63, color=C['blue'], lw=1, ls=':')
a2.set_xlabel('offset 样条输出（还没加 GLOBAL_OFFSET）'); a2.set_ylabel('depth=0 处的 y（基础地表高度）')
a2.set_title('基础地表高度 ≈ 63.5 + 128 × offset\n（offset 每增加 1.0，地表升高 128 格）', fontsize=11)
a2.text(0.35, 45, 'GLOBAL_OFFSET = -0.50375\n正好把 offset=0 对齐到海平面附近', fontsize=9, color='#475569')
fig.tight_layout(); save(fig, '03-depth-offset-surface.png')
