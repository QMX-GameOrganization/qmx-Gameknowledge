import numpy as np, sys
from collections import deque
sys.path.insert(0, '.')
from style import *
from matplotlib.patches import Rectangle

W, H = 17, 11
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]

class Light2D:
    """LightEngine 的 2D 版：两条队列（减少 / 增加），规则与 BlockLightEngine 一致。"""
    def __init__(self):
        self.solid = np.zeros((H, W), bool)
        self.solid[0, :] = self.solid[-1, :] = True; self.solid[:, 0] = self.solid[:, -1] = True
        self.em = np.zeros((H, W), int); self.lv = np.zeros((H, W), int)
        self.ops = 0
    def opac(self, x, y): return 15 if self.solid[y, x] else 1          # max(1, getLightBlock)
    def check(self, x, y, dq, iq):
        i, j = self.em[y, x], self.lv[y, x]
        if i < j:
            self.lv[y, x] = 0; dq.append((x, y, j, None))
        else:
            dq.append((x, y, 1, None))                                  # PULL_LIGHT_IN_ENTRY
        if i > 0: iq.append((x, y, i, None, True))
    def run(self, dq, iq):
        while dq:                                                       # propagateDecreases
            x, y, i, skip = dq.popleft(); self.ops += 1
            for d in DIRS:
                if d == skip: continue
                nx, ny = x + d[0], y + d[1]
                if not (0 <= nx < W and 0 <= ny < H): continue
                j = self.lv[ny, nx]
                if j == 0: continue
                if j <= i - 1:
                    k = self.em[ny, nx]; self.lv[ny, nx] = 0
                    if k < j: dq.append((nx, ny, j, (-d[0], -d[1])))
                    if k > 0: iq.append((nx, ny, k, None, True))
                else:
                    iq.append((nx, ny, j, None, False, (-d[0], -d[1])))  # 只向来的方向回灌
        while iq:                                                       # propagateIncreases
            item = iq.popleft(); self.ops += 1
            x, y, k = item[0], item[1], item[2]
            fromEm = item[4] if len(item) > 4 else False
            only = item[5] if len(item) > 5 else None
            j = self.lv[y, x]
            if fromEm and j < k: self.lv[y, x] = k; j = k
            if j != k: continue
            for d in DIRS:
                if only is not None and d != only: continue
                nx, ny = x + d[0], y + d[1]
                if not (0 <= nx < W and 0 <= ny < H): continue
                if k - 1 > self.lv[ny, nx]:
                    o = k - self.opac(nx, ny)
                    if o > self.lv[ny, nx]:
                        self.lv[ny, nx] = o
                        if o > 1: iq.append((nx, ny, o, (-d[0], -d[1]), False))
def deque_(): return deque()

L = Light2D()
def set_torch(x, y, v):
    L.em[y, x] = v
    dq, iq = deque(), deque(); L.check(x, y, dq, iq); L.run(dq, iq)
def set_solid(x, y, s):
    L.solid[y, x] = s
    dq, iq = deque(), deque(); L.check(x, y, dq, iq); L.run(dq, iq)

snaps = []
L.ops = 0
set_torch(4, 5, 14); set_torch(13, 5, 10)
snaps.append((L.lv.copy(), L.solid.copy(), L.em.copy(), L.ops, '① 放两个火把（14 与 10）'))
L.ops = 0
dq, iq = deque(), deque()
for y in range(1, 9):                                  # 中间砌一道墙，只在最下面留缺口
    L.solid[y, 8] = True; L.check(8, y, dq, iq)         # 先把 8 个位置都放进待检查集合
L.run(dq, iq)                                           # 再一次性批量处理（对应 blockNodesToCheck + runLightUpdates）
snaps.append((L.lv.copy(), L.solid.copy(), L.em.copy(), L.ops, '② 砌一道墙（8 格，批量处理）'))
L.ops = 0
L.em[5, 4] = 0; dq, iq = deque(), deque(); L.check(4, 5, dq, iq); L.run(dq, iq)
snaps.append((L.lv.copy(), L.solid.copy(), L.em.copy(), L.ops, '③ 拿走左边的火把'))

fig, axs = plt.subplots(1, 3, figsize=(16, 4.4))
prev = None
open_cells = int((~snaps[0][1]).sum())
for ax, (lv, sol, em, ops, ttl) in zip(axs, snaps):
    img = np.where(sol, np.nan, lv)
    ax.imshow(img, cmap='YlOrBr', vmin=0, vmax=15, interpolation='nearest')
    for (yy, xx), v in np.ndenumerate(lv):
        if sol[yy, xx]: ax.add_patch(Rectangle((xx - .5, yy - .5), 1, 1, fc='#334155'))
        else: ax.text(xx, yy, v, ha='center', va='center', fontsize=7.5, color='#0f172a')
        if em[yy, xx] > 0: ax.add_patch(Rectangle((xx - .5, yy - .5), 1, 1, fill=False, ec=C['red'], lw=2))
    if prev is not None:
        ch = (lv != prev[0]) & ~sol
        n = int(ch.sum())
        for (yy, xx), c in np.ndenumerate(ch):
            if c: ax.add_patch(Rectangle((xx - .5, yy - .5), 1, 1, fill=False, ec=C['blue'], lw=1.2, ls=':'))
        ttl2 = f'{ttl}\n光值变化 {n} 格，队列处理 {ops} 次（全量重算需 {open_cells} 格）'
    else:
        ttl2 = f'{ttl}\n队列处理 {ops} 次（空间共 {open_cells} 个可通行格）'
    ax.set_title(ttl2, fontsize=10.5); ax.set_xticks([]); ax.set_yticks([]); ax.grid(False)
    prev = (lv, sol)
fig.suptitle('方块光的增量更新（2D 示意，规则同 BlockLightEngine：衰减 1、不透明方块挡光；红框=光源，蓝点框=本步变化的格子）', fontsize=11.5, fontweight='bold', y=1.0)
fig.tight_layout(); save(fig, '24-block-light-incremental.png')
