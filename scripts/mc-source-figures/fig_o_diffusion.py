import numpy as np, sys
sys.path.insert(0, '.')
from style import *
from gv import render

# ====================== 图37：爆炸 ======================
def dirs():
    out = []
    for j in range(16):
        for k in range(16):
            for l in range(16):
                if j in (0, 15) or k in (0, 15) or l in (0, 15):
                    v = np.array([j, k, l], float) / 15.0 * 2 - 1
                    out.append(v / np.linalg.norm(v))
    return np.array(out)
D = dirs()
assert len(D) == 1352

def explode(res, c, radius, rng):
    """res: 3D 数组，nan = 空气（无阻力）；c: 爆心（浮点坐标）。返回被炸掉的方块布尔数组。"""
    n = len(D)
    h = radius * (0.7 + rng.random(n) * 0.6)
    pos = np.tile(np.asarray(c, float), (n, 1))
    boom = np.zeros(res.shape, bool)
    for _ in range(60):
        alive = h > 0
        if not alive.any():
            break
        idx = np.floor(pos).astype(int)
        inb = np.all((idx >= 0) & (idx < np.array(res.shape)), axis=1)
        alive &= inb
        ii = idx[alive]
        r = res[ii[:, 0], ii[:, 1], ii[:, 2]]
        sub = np.where(np.isnan(r), 0.0, (r + 0.3) * 0.3)
        h[alive] -= sub
        ok = h[alive] > 0
        sel = ii[ok]
        boom[sel[:, 0], sel[:, 1], sel[:, 2]] = True
        pos += D * 0.3
        h -= 0.22500001
        h[~inb] = -1
    return boom

rng = np.random.default_rng(3)
S = 41; cc = 20.5
fig, ax = plt.subplots(1, 4, figsize=(15.5, 4.2))
cases = [('泥土 (0.5)，TNT 半径 4', 0.5, 4.0, False), ('石头 (6)，TNT 半径 4', 6.0, 4.0, False),
         ('黑曜石 (1200)，TNT 半径 4', 1200.0, 4.0, False)]
for a, (ttl, rs, R, _) in zip(ax[:3], cases):
    grid = np.full((S, S, S), rs)
    grid[int(cc), int(cc), int(cc)] = np.nan
    acc = np.zeros((S, S, S))
    N = 150
    for _ in range(N):
        acc += explode(grid, (cc, cc, cc), R, rng)
    a.imshow((acc / N)[:, :, int(cc)].T, origin='lower', cmap='magma_r', vmin=0, vmax=1, extent=[-cc, cc, -cc, cc])
    th = np.linspace(0, 2 * np.pi, 200)
    a.plot(1.73 * R * np.cos(th), 1.73 * R * np.sin(th), color=C['teal'], lw=.8, ls='--')
    a.set_xlim(-8, 8); a.set_ylim(-8, 8); a.set_title(ttl, fontsize=10); a.grid(False); a.set_aspect('equal')
    a.set_xlabel('x（方块）')
ax[0].set_ylabel('y（方块）')
ax[0].text(0, 6.7, '虚线：1.73×半径（空气中的最大射程）', fontsize=7, ha='center', color=C['teal'])
b = ax[3]
radii = {'苦力怕 3': 3, 'TNT 4': 4, '床 5': 5, '末影水晶 6': 6, '凋灵 7': 7}
for rs, c, nm in [(0.5, C['amber'], '泥土'), (6.0, C['gray'], '石头'), (1200.0, C['red'], '黑曜石')]:
    ys = []
    for R in radii.values():
        grid = np.full((41, 41, 41), rs); grid[20, 20, 20] = np.nan
        ys.append(np.mean([explode(grid, (20.5, 20.5, 20.5), R, rng).sum() for _ in range(25)]))
    b.plot(list(radii.values()), ys, 'o-', color=c, label=nm)
b.set_yscale('log'); b.set_xlabel('爆炸半径'); b.set_ylabel('进入爆炸集合的格子数（含爆心空气格，均值）')
b.set_xticks(list(radii.values())); b.set_title('半径 vs 破坏量'); b.legend(fontsize=8)
fig.suptitle('爆炸：1352 条射线逐步衰减（numpy 移植，统计一致；颜色 = 150 次模拟中被炸掉的概率）', fontsize=11, y=1.02)
fig.tight_layout(); save(fig, '37-explosion-rays.png')

# ====================== 图38：火 ======================
def ignite_p(p, age, n=0, diff=2):
    o = 100 + (n - 1) * 100 if n > 1 else 100
    q = (p + 40 + diff * 7) // (age + 30)
    return 0.0 if q <= 0 else min(1.0, (q + 1) / o)

fig, ax = plt.subplots(1, 3, figsize=(14.5, 4.2))
ages = np.arange(0, 16)
a = ax[0]
for nm, p, c in [('木板 5', 5, C['amber']), ('树叶 / 羊毛 30', 30, C['green']), ('草 60', 60, C['teal'])]:
    a.plot(ages, [ignite_p(p, g) for g in ages], 'o-', ms=3, color=c, label=f'邻居 igniteOdds = {nm}')
a.set_xlabel('火的年龄 AGE'); a.set_ylabel('每次火刻点燃该空格的概率'); a.set_title('(a) 随年龄衰减（同层 / 下一层，普通难度）')
a.legend(fontsize=8, loc='upper right', bbox_to_anchor=(1, 1.0), frameon=True, framealpha=.95); a.set_ylim(0.017, 0.0475)
b = ax[1]
nn = np.arange(-1, 5)
for nm, p, c in [('igniteOdds 5', 5, C['amber']), ('igniteOdds 30', 30, C['green']), ('igniteOdds 60', 60, C['teal'])]:
    b.bar(nn + {5: -0.25, 30: 0, 60: 0.25}[p], [ignite_p(p, 0, n) for n in nn], width=0.25, color=c, label=nm)
b.set_xlabel('目标格相对火的高度 n（-1 ~ 4）'); b.set_ylabel('概率（AGE = 0）'); b.set_title('(b) 往上越远越难烧到'); b.legend(fontsize=8)
c3 = ax[2]
for nm, k, c in [('木板 burnOdds 20', 20, C['amber']), ('树叶 / 羊毛 60', 60, C['green']), ('草 / 藤 / TNT 100', 100, C['teal'])]:
    c3.plot(ages, [k / 300 for g in ages], '--', color=c, lw=1)
    c3.plot(ages, [k / 300 * 5 / (g + 10) for g in ages], 'o-', ms=3, color=c, label=nm)
c3.set_xlabel('火的年龄 AGE'); c3.set_ylabel('每次火刻（水平邻居）'); c3.set_title('(c) 相邻方块被烧掉（虚线）/ 变成新火（实线）')
c3.legend(fontsize=8, loc='center', bbox_to_anchor=(0.62, 0.72), frameon=True, framealpha=.9)
fig.tight_layout(); save(fig, '38-fire-spread.png')

# ====================== 图39：幽匿游标 ======================
nodes = [
 ('s', 'SculkCatalyst 听到 ENTITY_DIE\\n半径 8 内 → addCursors(pos, xp)', 'ref'),
 ('c', 'ChargeCursor\\npos, charge, updateDelay,\\ndecayDelay, facings', 'math'),
 ('u', 'update()：updateDelay > 0 ? 减 1 : 继续', 'switch'),
 ('v', '块脉扩展 attemptSpreadVein\\n（把周围可替换方块变成幽匿脉）', 'spline'),
 ('a', 'attemptUseCharge（幽匿块）\\n1/chargeDecayRate 的概率才结算', 'cache'),
 ('g', '在 noGrowthRadius 之外且上方可放\\n概率 charge/growthSpawnCost 长出感测体 / 尖啸体\\ncharge -= growthSpawnCost', 'noise'),
 ('d', '否则 1/additionalDecayRate 的概率衰减\\n半径内 -1；半径外 max(1, charge·f·0.5)', 'noise'),
 ('m', '移动：打乱 18 个非角邻居\\n取可通行的幽匿方块；遇到有基质的就停', 'math'),
 ('x', '同一位置的游标合并\\n（总和 ≤ 1000，非世界生成）\\n最多 32 个游标', 'const'),
]
edges = [('s', 'c'), ('c', 'u'), ('u', 'v'), ('v', 'a'), ('a', 'g'), ('a', 'd'), ('g', 'm'), ('d', 'm'), ('m', 'x'), ('x', 'u', '下一刻')]
render('39-sculk-cursor', nodes, edges, rankdir='TB')
