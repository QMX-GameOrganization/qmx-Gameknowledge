import numpy as np, sys
sys.path.insert(0, '.')
from style import *
import mcnoise as m, terrain as T
from matplotlib.patches import Rectangle, FancyBboxPatch, FancyArrowPatch
from matplotlib.colors import ListedColormap

# ======================= 图15：chunk 内的 cell 格点与循环顺序 =======================
fig, axs = plt.subplots(1, 3, figsize=(15.5, 5.2), gridspec_kw={'width_ratios': [1, 1, 1.15]})
ax = axs[0]
ax.set_aspect('equal'); ax.set_xlim(-1.5, 17.5); ax.set_ylim(-3.2, 17.5)
for i in range(0, 17, 4):
    ax.axhline(i, color='#cbd5e1', lw=1); ax.axvline(i, color='#cbd5e1', lw=1)
xs, zs = np.meshgrid(np.arange(0, 17, 4), np.arange(0, 17, 4))
ax.plot(xs, zs, 'o', color=C['red'], ms=8)
ax.add_patch(Rectangle((0, 0), 16, 16, fill=False, ec=C['dark'], lw=2))
ax.add_patch(Rectangle((0, 0), 4, 16, fc=C['blue'], alpha=.12)); ax.add_patch(Rectangle((4, 0), 4, 16, fc=C['green'], alpha=.12))
ax.text(2, 16.7, 'slice0', ha='center', color=C['blue'], fontsize=9); ax.text(6, 16.7, 'slice1', ha='center', color=C['green'], fontsize=9)
ax.annotate('', xy=(16.8, -1.0), xytext=(-0.5, -1.0), arrowprops=dict(arrowstyle='->', color=C['dark']))
ax.text(8, -2.6, 'cellX 方向推进 →（x 是最外层循环，每推进一格只算一层新 slice）', ha='center', fontsize=9)
ax.set_title('俯视（x–z）：一个区块 16×16\n红点 = 5×5 个角点（间距 4 格）', fontsize=11); ax.grid(False)
ax.set_xlabel('x'); ax.set_ylabel('z')

ax = axs[1]
ax.set_xlim(-1, 22); ax.set_ylim(-3, 52)
for i in range(0, 17, 4):
    ax.axvline(i, color='#cbd5e1', lw=1)
for k in range(49):
    ax.axhline(k, color='#e2e8f0', lw=.6) if False else None
ys_ = np.arange(0, 49)
for xx in range(0, 17, 4):
    ax.plot([xx] * len(ys_), ys_, '.', color=C['red'], ms=3.2)
ax.add_patch(Rectangle((0, 0), 16, 48, fill=False, ec=C['dark'], lw=2))
ax.add_patch(Rectangle((0, 40), 4, 8, fc=C['orange'], alpha=.35)); ax.text(4.6, 44, '← 一个 cell\n4(x)×8(y)×4(z)', fontsize=9, va='center', bbox=dict(fc='white', ec='none', alpha=.9))
ax.text(18.0, 24, '49 层角点\n(384/8+1)', fontsize=10, color=C['red'], va='center', rotation=90)
ax.set_title('侧视（x–y）：高度 384 = 48 个 cell\n每根“角点柱”有 49 个密度值', fontsize=11); ax.grid(False)
ax.set_xlabel('x'); ax.set_ylabel('y（cell 层）'); ax.set_yticks([0, 12, 24, 36, 48]); ax.set_yticklabels(['-64', '32', '128', '224', '320'])

ax = axs[2]; ax.axis('off'); ax.set_xlim(0, 10); ax.set_ylim(0, 10)
lines = [(0, 'initializeForFirstCellX()', '填 slice0（5×49 个角点）'),
         (0, 'for cellX in 0..3:', ''),
         (1, 'advanceCellX(cellX)', '填 slice1'),
         (1, 'for cellZ in 0..3:', ''),
         (2, 'for cellY in 47..0:', '自顶向下'),
         (3, 'selectCellYZ(cellY, cellZ)', '取 8 个角点；预填该 cell 内全部 finalDensity'),
         (3, 'for yIn in 7..0:', ''),
         (4, 'updateForY(...)', '4 次 lerp'),
         (4, 'for xIn in 0..3:', ''),
         (5, 'updateForX(...)', '2 次 lerp'),
         (5, 'for zIn in 0..3:', ''),
         (6, 'updateForZ(...)', '1 次 lerp'),
         (6, '写入方块 / 更新 heightmap', ''),
         (1, 'swapSlices()', 'slice1 变成下一轮的 slice0')]
ax.add_patch(FancyBboxPatch((0.0, 2.9), 9.9, 7.0, boxstyle='round,pad=0.05,rounding_size=0.2', fc='#f8fafc', ec='#cbd5e1'))
for k, (ind, t, cm_) in enumerate(lines):
    yy = 9.5 - k * 0.48
    ax.text(0.25 + ind * 0.32, yy, t, fontsize=9, va='center', color='#0f172a')
    if cm_:
        ax.text(9.7, yy, '# ' + cm_, fontsize=8.2, va='center', ha='right', color=C['gray'])
ax.text(0.0, 2.5, '增量插值的顺序是 Y → X → Z（矿脉噪声等走这条路）：\n最内层 z 每格 1 次 lerp，y 变化最慢，4 次 lerp 被摊薄。\nfinalDensity 则在 selectCellYZ 里按 cell 一次性预填\n（CacheAllInCell）。相邻 cell 共用角点，只重算新的 slice。', fontsize=9.3, color='#334155', va='top')
ax.set_title('NoiseBasedChunkGenerator.doFill 的循环骨架', fontsize=11)
fig.tight_layout(); save(fig, '15-chunk-cell-lattice.png')

# ======================= 图16：ChunkStatus 流水线 + 依赖金字塔 =======================
fig = plt.figure(figsize=(15.5, 7.3))
gs = fig.add_gridspec(2, 2, height_ratios=[0.9, 1.4], width_ratios=[1.35, 1], hspace=0.28)
ax = fig.add_subplot(gs[0, :]); ax.axis('off'); ax.set_xlim(0, 24); ax.set_ylim(0, 4)
stg = [('EMPTY', '', '#f1f5f9'), ('STRUCTURE\n_STARTS', 'range 0', '#fde68a'), ('STRUCTURE\n_REFERENCES', 'range 8', '#fde68a'), ('BIOMES', 'range 8', '#bbf7d0'),
       ('NOISE', 'range 8', '#bfdbfe'), ('SURFACE', 'range 8', '#bfdbfe'), ('CARVERS', 'range 8', '#ddd6fe'), ('FEATURES', 'range 8', '#fbcfe8'),
       ('INITIALIZE\n_LIGHT', 'range 0', '#e2e8f0'), ('LIGHT', 'range 1', '#e2e8f0'), ('SPAWN', 'range 0', '#e2e8f0'), ('FULL', 'range 0', '#bbf7d0')]
w_ = 1.82
for i, (nm, rg, col) in enumerate(stg):
    x0 = 0.1 + i * 1.98
    ax.add_patch(FancyBboxPatch((x0, 1.3), w_, 1.5, boxstyle='round,pad=0.02,rounding_size=0.15', fc=col, ec='#475569', lw=1.2))
    ax.text(x0 + w_ / 2, 2.05, nm, ha='center', va='center', fontsize=8.6, fontweight='bold')
    ax.text(x0 + w_ / 2, 0.9, rg, ha='center', va='center', fontsize=8.5, color='#475569')
    if i < len(stg) - 1:
        ax.annotate('', xy=(x0 + 1.98, 2.05), xytext=(x0 + w_, 2.05), arrowprops=dict(arrowstyle='->', color='#475569'))
ax.text(0.1, 3.5, 'ChunkStatus：一个区块从“空”走到“可玩”的 12 个台阶（range = 该步骤需要的邻居半径，单位：区块）', fontsize=11.5, fontweight='bold')
ax.text(0.1, 0.2, '蓝 = 地形主体（本项目主线）   绿 = 生物群系   紫 = 洞穴   粉 = 特征/植被   黄 = 结构   灰 = 光照等运行时', fontsize=9, color='#475569')

ax = fig.add_subplot(gs[1, 0]); ax.set_aspect('equal'); ax.axis('off')
R = 7
stat_col = {0: '#86efac', 1: '#fbcfe8', 2: '#ddd6fe', 3: '#bbf7d0'}
for dx in range(-R, R + 1):
    for dz in range(-R, R + 1):
        d = max(abs(dx), abs(dz))
        col = stat_col.get(d, '#fde68a')
        ax.add_patch(Rectangle((dx - .5, dz - .5), 1, 1, fc=col, ec='white', lw=1.2))
ax.add_patch(Rectangle((-.5, -.5), 1, 1, fc='#16a34a', ec='k', lw=2))
ax.text(0, 0, 'F', ha='center', va='center', fontsize=8, color='white', fontweight='bold')
ax.set_xlim(-R - .6, R + .6); ax.set_ylim(-R - .6, R + .6)
import matplotlib.patches as mp
ax.legend(handles=[mp.Patch(fc='#16a34a', label='中心：要变成 FULL'), mp.Patch(fc='#fbcfe8', label='第 1 圈：至少到 INITIALIZE_LIGHT（features 已跑完）'),
                   mp.Patch(fc='#ddd6fe', label='第 2 圈：至少到 CARVERS'), mp.Patch(fc='#bbf7d0', label='第 3 圈：至少到 BIOMES'),
                   mp.Patch(fc='#fde68a', label='第 4~11 圈：至少到 STRUCTURE_STARTS')], loc='upper center', bbox_to_anchor=(0.5, 0.02), fontsize=9)
ax.set_title('要让中心区块 FULL，周围各圈区块必须先到达的状态\n（ChunkStatus.STATUS_BY_RANGE）', fontsize=11)

ax = fig.add_subplot(gs[1, 1]); ax.axis('off'); ax.set_xlim(0, 10); ax.set_ylim(0, 10)
txt = ('为什么是“金字塔”？（每一圈的状态，大致对应\n“下一步会用到它的什么信息”）\n\n'
       '• 第 1 圈已跑完 features：树、矿会越界写进\n  中心区块，所以邻居的 features 必须先结束；\n\n'
       '• 第 2 圈到 CARVERS：第 1 圈的 features 要读\n  周围方块，所以再外一圈要先有地形+洞穴；\n\n'
       '• 第 3 圈到 BIOMES：carvers 按“源区块”的\n  群系挑洞穴，源区块最远在 8 格外；\n\n'
       '• 第 4 圈起只要 STRUCTURE_STARTS：NOISE 只\n  需要邻居的“结构起点”（Beardifier 让地形\n  贴合结构），不需要邻居的方块 —— 噪声是\n  确定性函数，所以区块的地形互不依赖，可并行。')
ax.text(0, 10, txt, fontsize=10, va='top', color='#0f172a', bbox=dict(boxstyle='round,pad=0.6', fc='#f8fafc', ec='#cbd5e1'))
fig.tight_layout(); save(fig, '16-chunk-status-pyramid.png')
