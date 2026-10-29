import numpy as np, sys
sys.path.insert(0, '.')
from style import *
from gv import render
from matplotlib.patches import Rectangle
from matplotlib.colors import ListedColormap, BoundaryNorm

# ====================== 图28：ticket 等级的传播 ======================
VIEW, SIM, R = 6, 4, 22          # 视距 6、模拟距离 4（演示用，真实默认 10 / 10）
n = 2 * R + 1
yy, xx = np.mgrid[-R:R + 1, -R:R + 1]
d = np.maximum(abs(xx), abs(yy))                    # 切比雪夫距离（8 邻域，每走一圈 +1）
lvl = np.where(d <= VIEW, 31, 31 + (d - VIEW))      # PLAYER ticket = 31，之外每圈 +1
lvl = np.minimum(lvl, 46)
# 等级 → 需要到达的状态（STATUS_BY_RANGE[level-33]）
names = ['FULL', 'INITIALIZE_LIGHT', 'CARVERS', 'BIOMES'] + ['STRUCTURE_STARTS'] * 8
def status_of(l):
    if l <= 33: return 0
    k = l - 33
    return k if k <= 3 else (4 if k <= 11 else 5)
sid = np.vectorize(status_of)(lvl)
cols = ['#16a34a', '#a3e635', '#fde68a', '#fdba74', '#fca5a5', '#e2e8f0']
fig, axs = plt.subplots(1, 2, figsize=(15.5, 7.6))
ax = axs[0]
im = ax.imshow(lvl, cmap='viridis_r', vmin=30, vmax=46, extent=[-R - .5, R + .5, R + .5, -R - .5], interpolation='nearest')
for c_ in range(-R, R + 1):          # 沿过玩家的一行，标出每个区块的等级
    ax.text(c_, 0, int(lvl[R, c_ + R]), ha='center', va='center', fontsize=6, color='white' if lvl[R, c_ + R] < 38 else 'black', rotation=90)
ax.add_patch(Rectangle((-VIEW - .5, -VIEW - .5), 2 * VIEW + 1, 2 * VIEW + 1, fill=False, ec='white', lw=2, ls='--'))
ax.add_patch(Rectangle((-SIM - .5, -SIM - .5), 2 * SIM + 1, 2 * SIM + 1, fill=False, ec=C['red'], lw=2.2))
ax.plot([0], [-2], 'w*', ms=14, mec='k')
fig.colorbar(im, ax=ax, fraction=.046, label='区块的 ticket 等级')
ax.set_title(f'每个区块的加载等级（中间一行标出数字）\n视距 {VIEW}（白虚线内都有 PLAYER ticket = 31），之外每圈 +1；红框 = 模拟距离 {SIM}', fontsize=10.5)
ax.set_xlim(-R - .5, R + .5); ax.set_ylim(R + .5, -R - .5); ax.grid(False); ax.set_xticks([]); ax.set_yticks([])
ax = axs[1]
ax.imshow(sid, cmap=ListedColormap(cols), vmin=0, vmax=5, extent=[-R - .5, R + .5, R + .5, -R - .5], interpolation='nearest')
ax.add_patch(Rectangle((-VIEW - .5, -VIEW - .5), 2 * VIEW + 1, 2 * VIEW + 1, fill=False, ec='black', lw=2, ls='--'))
ax.plot([0], [-2], 'k*', ms=14)
import matplotlib.patches as mp
ax.legend(handles=[mp.Patch(fc=cols[i], label=l) for i, l in enumerate(['FULL（31~33 级）', 'INITIALIZE_LIGHT（34 级）', 'CARVERS（35 级）', 'BIOMES（36 级）', 'STRUCTURE_STARTS（37~44 级）', 'EMPTY / 刚加载（45 级）'])],
          loc='lower center', bbox_to_anchor=(0.5, -0.17), ncol=3, fontsize=9)
ax.set_title('等级 → 区块必须到达的 ChunkStatus（ChunkLevel.generationStatus）\n视距之外还要再多加载约 14 圈“半成品”区块', fontsize=10.5)
ax.set_xlim(-R - .5, R + .5); ax.set_ylim(R + .5, -R - .5); ax.grid(False); ax.set_xticks([]); ax.set_yticks([])
fig.suptitle('Ticket 等级传播（演示参数；真实默认视距与模拟距离都是 10）：星 = 玩家所在区块', fontsize=12.5, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '28-ticket-levels.png')

# ====================== 图29：区块任务的线程与队列架构 ======================
nodes = [
    ('p', '玩家移动 / 加入 / 视距变化', 'switch'),
    ('dm', 'DistanceManager\\nPLAYER ticket (31) · TickingTracker · naturalSpawn 追踪器(8)\\nChunkTicketTracker：等级每圈 +1', 'math'),
    ('th', 'ticket 节流器 (ticketThrottler)\\n同时最多放入 4 个玩家 ticket（由近及远）', 'cache'),
    ('ch', 'ChunkHolder.updateFutures\\n等级变化 → 升 / 降级 → 调度各 ChunkStatus 的 future', 'math'),
    ('qs', 'ChunkTaskPriorityQueueSorter\\n3 个队列（worldgen / light / 主线程），按“区块队列等级”分 47 个桶\\n小的先执行；等级变化时 resort', 'switch'),
    ('wg', 'worldgen ProcessorMailbox → Util.backgroundExecutor()\\nForkJoinPool：线程数 = clamp(CPU−1, 1, 255)', 'noise'),
    ('lt', 'light ProcessorMailbox\\nThreadedLevelLightEngine（第 15 页）', 'noise'),
    ('mt', '主线程 mailbox\\n变成 LevelChunk、tick、发包', 'ref'),
]
edges = [('p', 'dm'), ('dm', 'th'), ('th', 'ch'), ('dm', 'ch'), ('ch', 'qs'), ('qs', 'wg'), ('qs', 'lt'), ('qs', 'mt')]
render('29-chunk-task-architecture', nodes, edges)
