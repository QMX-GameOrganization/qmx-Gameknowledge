import numpy as np, sys
sys.path.insert(0, '.')
from style import *
import mcnoise as m, terrain as T
from matplotlib.colors import ListedColormap

# ================= 图13：slide / 洞穴开关 / squeeze 三个“后处理” =================
fig, axs = plt.subplots(1, 3, figsize=(14.5, 4.6))
y = np.linspace(-64, 320, 800)
ax = axs[0]
for d0, col in [(1.2, C['gray']), (0.3, C['blue']), (-0.3, C['orange']), (-1.2, C['teal'])]:
    ax.plot(T.slide_overworld(np.full_like(y, d0), y), y, color=col, lw=2.2, label=f'输入密度 {d0:+.1f}')
ax.axvline(0, color='#334155', lw=1)
ax.axhspan(240, 256, color='#fee2e2', alpha=.6); ax.axhspan(-64, -40, color='#fee2e2', alpha=.6)
ax.text(1.5, 232, 'y∈[240,256]\n顶部渐隐', fontsize=8.5, color=C['red']); ax.text(1.5, -62, 'y∈[-64,-40]\n底部渐隐', fontsize=8.5, color=C['red'])
ax.set_xlabel('slide 之后的密度'); ax.set_ylabel('y'); ax.set_xlim(-1.4, 2.5)
ax.set_title('slide：顶部拉向 −0.078（空气），底部拉向 +0.117（实心）\n= 世界上缘封顶、下缘封底', fontsize=10.5); ax.legend(fontsize=8, loc='center right', bbox_to_anchor=(1.0, 0.55))

ax = axs[1]
s = np.linspace(-1, 4, 600)
ax.plot(s, np.clip(1.5 - 0.64 * s, 0, 0.5), color=C['purple'], lw=2.6, label='洞穴偏置 clamp(1.5 − 0.64·s, 0, 0.5)')
ax.axvline(1.5625, color=C['red'], lw=1.6, ls='--'); ax.text(1.75, 0.40, 's = 1.5625\nrange_choice 的闸门', color=C['red'], fontsize=9, bbox=dict(fc='white', ec='none', alpha=.85))
ax.axvspan(-1, 1.5625, color='#e0f2fe', alpha=.7); ax.axvspan(1.5625, 4, color='#f1f5f9', alpha=.9)
ax.text(-0.9, 0.05, '闸门内：\n只算 min(s, 5×entrances)\n不碰深层洞穴噪声', fontsize=8.5, color='#0c4a6e')
ax.text(2.45, 0.05, '闸门外：深层实心区\n才计算 cheese/spaghetti/pillars', fontsize=8.5, color='#334155')
ax.set_xlabel('s = sloped_cheese（越大越深越“实”）'); ax.set_ylabel('偏置'); ax.set_ylim(-0.03, 0.55)
ax.set_title('range_choice 闸门：浅处不挖洞、深处才挖\n（同时是性能开关：闸门内不求值洞穴噪声）', fontsize=10.5); ax.legend(fontsize=8.5, loc='upper right')

ax = axs[2]
dd = np.linspace(-2.2, 2.2, 600)
ax.plot(dd, dd, color='#cbd5e1', ls='--', label='y = x')
ax.plot(dd, m.squeeze(0.64 * dd), color=C['teal'], lw=2.6, label='squeeze(0.64·x)')
ax.axhline(0, color='#94a3b8', lw=.8); ax.axvline(0, color='#94a3b8', lw=.8)
ax.axvline(1 / 0.64, color=C['red'], lw=1, ls=':'); ax.axvline(-1 / 0.64, color=C['red'], lw=1, ls=':')
ax.text(1.62, -0.2, '|x|>1.5625\n输出饱和为 ±0.458', color=C['red'], fontsize=8.5)
ax.set_xlabel('插值后的 finalDensity'); ax.set_ylabel('最终输出'); ax.set_ylim(-0.7, 1.2)
ax.set_title('post-process：×0.64 再 squeeze\n只改变幅度，不改变正负号（=实/空判定不变）', fontsize=10.5); ax.legend(fontsize=8.5, loc='upper left')
fig.tight_layout(); save(fig, '13-slide-gate-squeeze.png')

# ================= 图14：一个真实的洞穴剖面（只含 cheese 洞穴） =================
w = T.World(74)
rng = np.random.default_rng(11)
cave_layer = m.NormalNoise(rng, -8, [1.0])
cave_cheese = m.NormalNoise(rng, -8, [0.5, 1.0, 2.0, 1.0, 2.0, 1.0, 0.0, 2.0, 0.0])
x = np.arange(300, 812.0); yv = np.arange(-64, 256.0)
X, Y = np.meshgrid(x, yv)
Z = 0 * X
cc, ee, ww = w.climate(X[0], Z[0])
off, fac, jg = m.terrain_params(cc, ee, ww)
jn = w.jag_noise(X[0], Z[0])
b3 = w.base.compute(X, Y, Z)
s = T.sloped_cheese(T.depth_of(Y, off[None, :]), fac[None, :], jg[None, :], jn[None, :], b3)
# NoiseRouterData.underground（只实现 cheese 部分；省略 spaghetti_2d / entrances / pillars / noodle）
d4 = cave_layer.value(X, Y * 8.0, Z)
d5 = 4.0 * d4 ** 2
d6 = cave_cheese.value(X, Y * 0.6666666666666666, Z)
d7 = np.clip(0.27 + d6, -1, 1) + np.clip(1.5 + (-0.64) * s, 0.0, 0.5)
under = d5 + d7
rc = np.where(s < 1.5625, s, under)
fin = m.squeeze(0.64 * T.slide_overworld(rc, Y))
solid = fin > 0
cave = (~solid) & (s > 0) & (Y > -60)     # 地形本来是实心、被洞穴挖空的部分
img = np.zeros(solid.shape + (3,)); img[:] = [0.88, 0.95, 1.0]
img[(~solid) & (Y <= 63) & (s <= 0)] = [0.25, 0.55, 0.95]
img[solid] = [0.36, 0.40, 0.46]
img[cave] = [0.99, 0.80, 0.30]
fig, axs = plt.subplots(2, 1, figsize=(14, 8.6), gridspec_kw={'height_ratios': [1, 1]})
axs[0].imshow(img, origin='lower', extent=[300, 812, -64, 256], aspect='auto', interpolation='nearest'); axs[0].grid(False)
axs[0].set_title('逐方块求值的 finalDensity（含 cheese 洞穴）：灰=实心，黄=被洞穴挖空，蓝=海水', fontsize=11)
axs[0].set_ylabel('y')
# 下：同样的洞穴，在 4×8 cell 角点上采样再插值（真实游戏的做法）
cx = np.arange(300, 813, 4.0); cy = np.arange(-64, 257, 8.0)
CX, CY = np.meshgrid(cx, cy); CZ = 0 * CX
c2, e2, w2 = w.climate(CX[0], CZ[0]); o2, f2, j2 = m.terrain_params(c2, e2, w2); jn2 = w.jag_noise(CX[0], CZ[0])
s2 = T.sloped_cheese(T.depth_of(CY, o2[None, :]), f2[None, :], j2[None, :], jn2[None, :], w.base.compute(CX, CY, CZ))
d72 = np.clip(0.27 + cave_cheese.value(CX, CY * 0.6666666666666666, CZ), -1, 1) + np.clip(1.5 - 0.64 * s2, 0, 0.5)
rc2 = np.where(s2 < 1.5625, s2, 4 * cave_layer.value(CX, CY * 8.0, CZ) ** 2 + d72)
f_c = T.slide_overworld(rc2, CY)
fi = np.zeros_like(fin)
for iy, yy in enumerate(yv):
    j = min(int((yy + 64) // 8), f_c.shape[0] - 2); ty = (yy + 64 - j * 8) / 8
    row = m.lerp(ty, f_c[j], f_c[j + 1])
    xi = np.minimum(((x - 300) // 4).astype(int), len(cx) - 2); tx = ((x - 300) - (xi * 4)) / 4
    fi[iy] = m.lerp(tx, row[xi], row[xi + 1])
fi = m.squeeze(0.64 * fi)
sol2 = fi > 0
cave2 = (~sol2) & (s > 0) & (Y > -60)
img2 = np.zeros(solid.shape + (3,)); img2[:] = [0.88, 0.95, 1.0]
img2[(~sol2) & (Y <= 63) & (s <= 0)] = [0.25, 0.55, 0.95]
img2[sol2] = [0.36, 0.40, 0.46]; img2[cave2] = [0.99, 0.80, 0.30]
axs[1].imshow(img2, origin='lower', extent=[300, 812, -64, 256], aspect='auto', interpolation='nearest'); axs[1].grid(False)
axs[1].set_title('只在 4×8 角点求值、其余线性插值（游戏真实做法）：洞穴被“磨圆”，但整体形状一致', fontsize=11)
axs[1].set_xlabel('x'); axs[1].set_ylabel('y')
fig.suptitle('洞穴 = 在已有的 sloped_cheese 之上，让深处的某些位置密度 ≤ 0（本图只含 cheese 洞穴，种子为示意）', fontsize=12.5, fontweight='bold', y=0.995)
fig.tight_layout(); save(fig, '14-cheese-caves-slice.png')
print('cave fraction of solid terrain', cave.sum() / max(1, (s > 0).sum()))
