import numpy as np, random, sys, os, subprocess
sys.path.insert(0, '.')
from style import *
from matplotlib.patches import Rectangle

# ======================= 图21：Jigsaw 拼图的 2D 玩具模拟 =======================
# 规则与 JigsawPlacement 一致：广度优先；每个连接点从池里挑候选；方向相反才能接上；包围盒不能与已放置的重叠；深度受 size 限制；
# 候选全部失败则退到 fallback 池。
DIRS = {'N': (0, -1), 'E': (1, 0), 'S': (0, 1), 'W': (-1, 0)}
OPP = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}
ROT = {'N': 'E', 'E': 'S', 'S': 'W', 'W': 'N'}      # 顺时针 90°

def make(name, w, h, conns, color):
    # conns: [(x, y, dir, pool)]，(x,y) 是紧贴边界的格子
    return dict(name=name, w=w, h=h, conns=conns, color=color)

PLAZA = make('广场', 11, 11, [(5, 0, 'N', 'streets'), (10, 5, 'E', 'streets'), (5, 10, 'S', 'streets'), (0, 5, 'W', 'streets')], '#f59e0b')
STREET = make('街道', 16, 3, [(0, 1, 'W', 'streets'), (15, 1, 'E', 'streets'), (4, 0, 'N', 'houses'), (11, 0, 'N', 'houses'), (4, 2, 'S', 'houses'), (11, 2, 'S', 'houses')], '#94a3b8')
HOUSE_A = make('小屋', 6, 6, [(2, 5, 'S', 'none')], '#38bdf8')
HOUSE_B = make('大屋', 8, 6, [(3, 5, 'S', 'none')], '#2563eb')
FARM = make('农田', 7, 7, [(3, 6, 'S', 'none')], '#4ade80')
END = make('街尽头', 3, 3, [(1, 2, 'S', 'none')], '#cbd5e1')
POOLS = {'streets': ([STREET, STREET, STREET], END), 'houses': ([HOUSE_A, HOUSE_A, HOUSE_B, FARM], None)}

def rotate(p, k):
    w, h, conns = p['w'], p['h'], p['conns']
    for _ in range(k):
        conns = [(h - 1 - y, x, ROT[d], pool) for (x, y, d, pool) in conns]
        w, h = h, w
    return dict(p, w=w, h=h, conns=conns)

def overlaps(a, b):
    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])

def grow(max_depth, max_dist, seed):
    rnd = random.Random(seed)
    placed = []   # (x, y, w, h, piece, depth)
    start = rotate(PLAZA, 0)
    sx, sy = -start['w'] // 2, -start['h'] // 2
    placed.append((sx, sy, start['w'], start['h'], start, 0))
    queue = [(0, c) for c in start['conns']]
    queue = [(0, (sx + x, sy + y, d, pool)) for (x, y, d, pool) in start['conns']]
    while queue:
        depth, (cx, cy, d, pool) = queue.pop(0)             # 广度优先
        if depth >= max_depth: continue
        cands, fb = POOLS[pool] if pool in POOLS else ([], None)
        order = rnd.sample(cands, len(cands)) + ([fb] if fb else [])
        done = False
        for base in order:
            rots = rnd.sample(range(4), 4)
            for k in rots:
                p = rotate(base, k)
                for (x, y, dd, pl) in p['conns']:
                    if dd != OPP[d]: continue
                    ox, oy = cx + DIRS[d][0] - x, cy + DIRS[d][1] - y
                    box = (ox, oy, p['w'], p['h'])
                    if any(overlaps(box, q[:4]) for q in placed): continue
                    if abs(ox) > max_dist or abs(oy) > max_dist or abs(ox + p['w']) > max_dist or abs(oy + p['h']) > max_dist: continue
                    placed.append((ox, oy, p['w'], p['h'], p, depth + 1))
                    for (x2, y2, d2, pl2) in p['conns']:
                        if (x2, y2, d2) != (x, y, dd):
                            queue.append((depth + 1, (ox + x2, oy + y2, d2, pl2)))
                    done = True; break
                if done: break
            if done: break
    return placed

fig, axs = plt.subplots(1, 3, figsize=(15.5, 5.4))
for ax, md in zip(axs, [1, 3, 6]):
    placed = grow(md, 45, 8)
    for (x, y, w, h, p, dep) in placed:
        ax.add_patch(Rectangle((x, y), w, h, fc=p['color'], ec='#334155', lw=1.0))
    ax.add_patch(Rectangle((-45, -45), 90, 90, fill=False, ec=C['red'], ls='--', lw=1.2))
    ax.set_xlim(-50, 50); ax.set_ylim(50, -50); ax.set_aspect('equal'); ax.grid(False)
    ax.set_title(f'size（最大深度）= {md}：共 {len(placed)} 块', fontsize=11)
    ax.set_xticks([]); ax.set_yticks([])
import matplotlib.patches as mp
fig.legend(handles=[mp.Patch(fc=c['color'], ec='#334155', label=c['name']) for c in [PLAZA, STREET, HOUSE_A, HOUSE_B, FARM, END]] + [mp.Patch(fill=False, ec=C['red'], ls='--', label='max_distance_from_center')],
           loc='lower center', ncol=7, fontsize=9, bbox_to_anchor=(0.5, -0.02))
fig.suptitle('Jigsaw 的 2D 玩具模拟：从广场出发，沿连接点广度优先生长（规则与 JigsawPlacement 一致，素材是示意）', fontsize=12.5, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '21-jigsaw-toy.png')

# ======================= 图22：流体扩散范围 =======================
def spread(drop, slope_max=99):
    n = 9; g = np.zeros((2 * n + 1, 2 * n + 1)); c = n
    g[c, c] = 8
    from collections import deque
    q = deque([(c, c, 8)])
    seen = {(c, c): 8}
    while q:
        x, y, a = q.popleft()
        na = a - drop
        if na <= 0: continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < 2 * n + 1 and 0 <= ny < 2 * n + 1 and seen.get((nx, ny), 0) < na:
                seen[(nx, ny)] = na; g[ny, nx] = na; q.append((nx, ny, na))
    return g
fig, axs = plt.subplots(1, 3, figsize=(14.5, 4.9))
for ax, (ttl, drop) in zip(axs, [('水（dropOff = 1，tickDelay = 5）', 1), ('岩浆·下界（dropOff = 1，tickDelay = 10）', 1), ('岩浆·主世界（dropOff = 2，tickDelay = 30）', 2)]):
    g = spread(drop)
    ax.imshow(np.where(g > 0, g, np.nan), cmap='Blues' if 'water' in ttl or ttl.startswith('水') else 'Oranges', vmin=0, vmax=9, interpolation='nearest')
    for (yy, xx), v in np.ndenumerate(g):
        if v > 0: ax.text(xx, yy, int(v), ha='center', va='center', fontsize=8, color='#0f172a')
    reach = int(max(abs(np.argwhere(g > 0) - 9).max(), 0))
    ax.set_title(f'{ttl}\n平地上最远流 {reach} 格', fontsize=10.5); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
fig.suptitle('流体在平地上的扩散：每走一格 amount 减去 dropOff，减到 0 为止（数字 = amount，源方块为 8；上下左右四个方向扩散）', fontsize=11.5, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '22-fluid-spread.png')
