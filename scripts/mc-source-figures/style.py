import os, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

for f in ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']:
    if os.path.exists(f):
        fm.fontManager.addfont(f)
plt.rcParams.update({
    'font.family': ['Noto Sans CJK JP', 'DejaVu Sans'],
    'axes.unicode_minus': False,
    'figure.facecolor': '#ffffff', 'axes.facecolor': '#ffffff', 'savefig.facecolor': '#ffffff',
    'axes.edgecolor': '#475569', 'axes.labelcolor': '#1e293b', 'text.color': '#1e293b',
    'xtick.color': '#475569', 'ytick.color': '#475569',
    'axes.grid': True, 'grid.color': '#e2e8f0', 'grid.linewidth': 0.8,
    'axes.spines.top': False, 'axes.spines.right': False,
    'axes.titlesize': 12, 'axes.titleweight': 'bold', 'axes.labelsize': 10,
    'legend.frameon': False, 'figure.dpi': 110,
})
C = dict(blue='#2563eb', red='#dc2626', green='#16a34a', orange='#ea580c', purple='#7c3aed',
         gray='#64748b', teal='#0d9488', pink='#db2777', dark='#0f172a', amber='#d97706')
OUT = os.environ.get('MC_FIG_OUT', '/sessions/upbeat-epic-knuth/mnt/outputs/figs')
os.makedirs(OUT, exist_ok=True)


def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=140, bbox_inches='tight', pad_inches=0.15)
    plt.close(fig)
    print('saved', p, os.path.getsize(p) // 1024, 'KB')
