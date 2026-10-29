import numpy as np, sys, random
from collections import deque
sys.path.insert(0, '.')
from style import *
from gv import render
from matplotlib.patches import Rectangle
from matplotlib.colors import ListedColormap

# ====================== 图25：VisGraph + 广度优先遍历（2D 玩具） ======================
N = 12           # 每个“区块段”12×12 个格子（真实是 16³）
S = 9            # 9×9 个段
DIRS = {'N': (0, -1), 'E': (1, 0), 'S': (0, 1), 'W': (-1, 0)}
OPP = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}

rng = np.random.default_rng(12)
def smooth(a, k=3):
    for _ in range(k):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
    return a
f = smooth(rng.random((S * N, S * N)), 4)
world = f < np.quantile(f, 0.50)          # True = 实心
# 凿出几条“洞穴”隧道，让可见性有结构
for (x0, y0, x1, y1) in [(0, 40, 107, 40), (54, 0, 54, 107), (20, 70, 80, 70)]:
    for t in np.linspace(0, 1, 400):
        x, y = int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t)
        world[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = False
# 加几道实心“墙”，用来挡住视线
world[:, 78:82] = True; world[44:48, :] = True; world[40:41, 78:82] = False; world[44:48, 14:17] = False

def section_visibility(sec):
    """段内泛洪：返回 {(a,b)} 表示面 a 与面 b 在同一连通块里"""
    sx, sy = sec
    blk = world[sy * N:(sy + 1) * N, sx * N:(sx + 1) * N]
    seen = np.zeros_like(blk, bool); pairs = set()
    edge = lambda x, y: [d for d, c in (('N', y == 0), ('S', y == N - 1), ('W', x == 0), ('E', x == N - 1)) if c]
    for y0 in range(N):
        for x0 in range(N):
            if blk[y0, x0] or seen[y0, x0]: continue
            q = deque([(x0, y0)]); seen[y0, x0] = True; faces = set()
            while q:
                x, y = q.popleft(); faces.update(edge(x, y))
                for dx, dy in DIRS.values():
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < N and 0 <= ny < N and not blk[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; q.append((nx, ny))
            for a in faces:
                for b in faces:
                    if a != b: pairs.add((a, b))
    return pairs
VIS = {(x, y): section_visibility((x, y)) for x in range(S) for y in range(S)}

def bfs(cam):
    """LevelRenderer.updateRenderChunks 的 2D 版：沿面传播，不回头，必须存在“入口面→出口面”的连通"""
    visited = {cam: (set(), set())}      # sec -> (已走过的方向集合, 到达方向集合)
    q = deque([cam])
    while q:
        sec = q.popleft(); dirs, src = visited[sec]
        for d, (dx, dy) in DIRS.items():
            nb = (sec[0] + dx, sec[1] + dy)
            if not (0 <= nb[0] < S and 0 <= nb[1] < S): continue
            if OPP[d] in dirs: continue                          # !hasDirection(opposite)
            if src and not any((OPP[j], d) in VIS[sec] for j in src): continue   # facesCanSeeEachother
            if nb in visited:
                visited[nb][0].update(dirs | {d}); visited[nb][1].add(d); continue
            visited[nb] = (set(dirs) | {d}, {d}); q.append(nb)
    return set(visited)

fig, axs = plt.subplots(1, 3, figsize=(16, 5.4))
cams = [(1, 4), (4, 1), (7, 7)]
for ax, cam in zip(axs, cams):
    vis = bfs(cam)
    ax.imshow(~world, cmap=ListedColormap(['#334155', '#f8fafc']), interpolation='nearest', extent=[0, S * N, S * N, 0])
    for sx in range(S):
        for sy in range(S):
            if (sx, sy) in vis:
                ax.add_patch(Rectangle((sx * N, sy * N), N, N, fc=C['green'], alpha=.16, ec=C['green'], lw=1))
            else:
                ax.add_patch(Rectangle((sx * N, sy * N), N, N, fc='#94a3b8', alpha=.45, ec='#64748b', lw=.6, hatch='///'))
    ax.add_patch(Rectangle((cam[0] * N, cam[1] * N), N, N, fill=False, ec=C['red'], lw=2.4))
    ax.set_title(f'相机在红框所在段：送去绘制 {len(vis)} / {S*S} 个段（灰斜线 = 被遮挡剔除）', fontsize=10.5)
    ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
fig.suptitle('VisGraph + 广度优先遍历（2D 玩具）：白=空气，深色=实心；每个段先算“哪些面互相连通”，再沿连通的面一层层传播', fontsize=12, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '25-visgraph-culling.png')

# ====================== 图26：平滑光照 / AO ======================
W, H = 15, 9
solid = np.zeros((H, W), bool)         # 地面之上这一层里的实心方块（站在地面上的方块）
for (x, y) in [(3, 2), (4, 2), (3, 3), (4, 3), (8, 5), (11, 2), (12, 2), (12, 3), (12, 4), (6, 7), (7, 7)]:
    solid[y, x] = True
shade = np.where(solid, 0.2, 1.0)

def sh(x, y):
    return shade[y, x] if 0 <= x < W and 0 <= y < H else 1.0

def vertex_values(x, y):
    """地面砖 (x,y) 的上表面，4 个顶点的 AO：取 中心 + 两条边邻 + 角邻 的平均；两条边都被挡时，角邻按边值算"""
    c = sh(x, y); vs = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        e1, e2, cn = sh(x + sx, y), sh(x, y + sy), sh(x + sx, y + sy)
        if e1 < 1 and e2 < 1: cn = e1
        vs.append((c + e1 + e2 + cn) * 0.25)
    return vs      # 顺序：左上、右上、右下、左下

R = 8
def render_tiles(use_ao):
    img = np.ones((H * R, W * R))
    for y in range(H):
        for x in range(W):
            if solid[y, x]: img[y * R:(y + 1) * R, x * R:(x + 1) * R] = np.nan; continue
            tl, tr, br, bl = vertex_values(x, y) if use_ao else (1, 1, 1, 1)
            u = (np.arange(R) + .5) / R
            U, V = np.meshgrid(u, u)
            img[y * R:(y + 1) * R, x * R:(x + 1) * R] = tl * (1 - U) * (1 - V) + tr * U * (1 - V) + br * U * V + bl * (1 - U) * V
    return img
fig, axs = plt.subplots(1, 3, figsize=(16, 4.6))
for ax, (ttl, ao) in zip(axs[:2], [('不做 AO：整面一个亮度（flat）', False), ('平滑光照 + AO：4 个顶点各算一个亮度，面内插值', True)]):
    ax.imshow(render_tiles(ao), cmap='gray', vmin=0.15, vmax=1.0, interpolation='nearest', extent=[0, W, H, 0])
    for (yy, xx), v in np.ndenumerate(solid):
        if v: ax.add_patch(Rectangle((xx, yy), 1, 1, fc='#92400e', ec='#451a03', lw=1))
    ax.set_title(ttl, fontsize=10.5); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
ax = axs[2]; ax.axis('off'); ax.set_xlim(0, 10); ax.set_ylim(0, 10)
txt = ('一个顶点的亮度（ModelBlockRenderer.AmbientOcclusionFace.calculate）：\n\n'
       '  v = ( 中心 + 边邻1 + 边邻2 + 角邻 ) × 0.25\n\n'
       '• 每一项是该格的 shade brightness：\n  完整碰撞方块 0.2，否则 1.0\n'
       '• 两条边邻都被挡住时，角邻直接用边邻的值\n  （角邻那格即使是空气也不算亮）\n'
       '• 光照（lightmap）同理，4 项取平均，0 值用中心替代\n'
       '• 最后整个面再乘以方向系数 getShade(direction)\n\n'
       '结果：墙角、凹处自然变暗，不需要光线追踪。')
ax.text(0, 9.8, txt, fontsize=10, va='top', bbox=dict(boxstyle='round,pad=0.6', fc='#f8fafc', ec='#cbd5e1'))
fig.suptitle('地面砖的上表面（俯视）：棕色=站在地面上的方块；AO 只用邻居的 shade 值，在 CPU 上建网格时一次性算好', fontsize=12, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '26-smooth-lighting-ao.png')

# ====================== 图27：区块网格编译的流水线 ======================
nodes = [
    ('d', '方块 / 光照变化 → LevelRenderer.setSectionDirty\\n（周围 3×3×3 个段都标脏；光变化只标一个段）', 'switch'),
    ('c', 'compileChunks：每帧在视锥内遍历脏段\\n距离 < 28 格或“玩家改的” → 同步编译；否则 → 异步', 'math'),
    ('s', '快照 RenderRegionCache.createRegion\\n复制区块向外 1 格（PalettedContainer 副本）→ 后台线程无需加锁', 'cache'),
    ('t', 'RebuildTask（后台线程，ProcessorMailbox 串行派发）\\n高优先级队列（按距离）与低优先级队列 2:1 交替', 'math'),
    ('v', '逐方块：shouldRenderFace 面剔除（OCCLUSION_CACHE）\\n→ 平滑光照 / AO → 写入各渲染层的 BufferBuilder\\n不透明格子同时喂给 VisGraph', 'noise'),
    ('r', '结果：每层网格数据 + VisibilitySet + SortState（半透明排序）', 'ref'),
    ('u', '上传队列 toUpload → 渲染线程批量 uploadAllPendingUploads\\n（OpenGL 调用只在渲染线程）', 'cache'),
    ('f', '每帧：updateRenderChunks（VisibilitySet 剪枝的 BFS）\\n→ 视锥剔除 → 按层绘制（solid → cutout → translucent）', 'switch'),
]
edges = [('d', 'c'), ('c', 's'), ('s', 't'), ('t', 'v'), ('v', 'r'), ('r', 'u'), ('u', 'f')]
render('27-chunk-compile-pipeline', nodes, edges)
