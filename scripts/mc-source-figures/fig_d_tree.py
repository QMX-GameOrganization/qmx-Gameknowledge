import subprocess, os
from style import OUT

FONT = 'Noto Sans CJK JP'
COL = {'math': ('#dbeafe', '#2563eb'), 'cache': ('#ffedd5', '#ea580c'), 'spline': ('#ede9fe', '#7c3aed'),
       'noise': ('#dcfce7', '#16a34a'), 'const': ('#f1f5f9', '#64748b'), 'switch': ('#fee2e2', '#dc2626'), 'ref': ('#fef9c3', '#ca8a04')}


def render(name, nodes, edges, rankdir='TB', extra=''):
    L = ['digraph G {', f'rankdir={rankdir}; nodesep=0.28; ranksep=0.42; bgcolor="white"; pad=0.25; {extra}',
         f'node [shape=box, style="rounded,filled", fontname="{FONT}", fontsize=11, margin="0.10,0.05", penwidth=1.6];',
         f'edge [color="#94a3b8", arrowsize=0.7, fontname="{FONT}", fontsize=9, fontcolor="#475569"];']
    for nid, label, kind in nodes:
        fill, line = COL[kind]
        L.append(f'{nid} [label="{label}", fillcolor="{fill}", color="{line}"];')
    for e in edges:
        a, b = e[0], e[1]
        lab = f' [label="{e[2]}"]' if len(e) > 2 else ''
        L.append(f'{a} -> {b}{lab};')
    L.append('}')
    dot = os.path.join(OUT, name + '.dot')
    open(dot, 'w').write('\n'.join(L))
    png = os.path.join(OUT, name + '.png')
    subprocess.run(['dot', '-Tpng', '-Gdpi=130', dot, '-o', png], check=True)
    os.remove(dot)
    print('saved', png, os.path.getsize(png) // 1024, 'KB')


# ---------------- 11：finalDensity 顶层 ----------------
nodes = [
    ('fd', 'final_density\\nmin', 'math'),
    ('sq', 'squeeze\\nc/2 − c³/24 （限幅）', 'math'),
    ('mul', 'mul × 0.64', 'math'),
    ('itp', 'interpolated\\n【Marker】4×8×4 cell 三线性插值', 'cache'),
    ('bd', 'blend_density\\n（与旧版本区块融合；新世界≈恒等）', 'math'),
    ('slide', 'slide（上下边缘渐隐）\\nlerp(yGradient, 常数, ·) ×2', 'math'),
    ('rc', 'range_choice\\n输入 = sloped_cheese，区间 [−1e6, 1.5625)', 'switch'),
    ('in', '区间内（浅层/空中）\\nmin(sloped_cheese, 5 × entrances)', 'math'),
    ('out', '区间外（深层实心区）\\nmax( min(min(cheese, entrances),\\nspaghetti_2d + roughness), pillars )', 'math'),
    ('sc', 'sloped_cheese\\n【地形主体，见下图】', 'ref'),
    ('cv', '洞穴族\\ncheese / spaghetti / pillars', 'noise'),
    ('nd', 'noodle\\n【interpolated(range_choice(y ∈ [−60,320] …))】\\n细长“面条”洞', 'cache'),
]
edges = [('fd', 'sq'), ('sq', 'mul'), ('mul', 'itp'), ('itp', 'bd'), ('bd', 'slide'), ('slide', 'rc'),
         ('rc', 'in', '范围内'), ('rc', 'out', '范围外'), ('rc', 'sc', '输入'), ('in', 'sc'), ('out', 'cv'), ('fd', 'nd')]
render('11-final-density-tree', nodes, edges)

# ---------------- 12：sloped_cheese 子树 ----------------
nodes = [
    ('sc', 'sloped_cheese\\nadd', 'math'),
    ('g', 'mul × 4', 'math'), ('qn', 'quarter_negative\\nx>0 ? x : x×0.25', 'math'),
    ('m2', 'mul', 'math'), ('add', 'add', 'math'),
    ('depth', 'depth\\nadd', 'ref'), ('yg', 'y_clamped_gradient\\ny: −64→320 ，值: 1.5→−1.5', 'math'),
    ('off', 'offset\\nflat_cache(cache_2d(\\n  −0.50375 + spline))', 'cache'),
    ('jm', 'mul', 'math'), ('jag', 'jaggedness\\nflat_cache(cache_2d(spline))', 'cache'),
    ('hn', 'half_negative\\nx>0 ? x : x×0.5', 'math'),
    ('jn', 'noise: jagged\\nxz_scale=1500, y_scale=0', 'noise'),
    ('fac', 'factor\\nflat_cache(cache_2d(spline))', 'cache'),
    ('b3', 'old_blended_noise\\n（base_3d_noise，唯一真正的 3D 噪声）', 'noise'),
    ('so', 'spline(continents, erosion, ridges_folded)', 'spline'),
    ('sf', 'spline(continents, erosion,\\nridges, ridges_folded)', 'spline'),
    ('sj', 'spline(continents, erosion,\\nridges, ridges_folded)', 'spline'),
    ('c', 'continents\\nflat_cache(shifted_noise)', 'cache'), ('e', 'erosion\\nflat_cache(shifted_noise)', 'cache'),
    ('r', 'ridges\\nflat_cache(shifted_noise)', 'cache'), ('rf', 'ridges_folded\\n−3·(|(|r|−2/3)|−1/3)', 'math'),
]
edges = [('sc', 'g'), ('sc', 'b3'), ('g', 'qn'), ('qn', 'm2'), ('m2', 'add'), ('m2', 'fac'),
         ('add', 'depth'), ('add', 'jm'), ('depth', 'yg'), ('depth', 'off'),
         ('jm', 'jag'), ('jm', 'hn'), ('hn', 'jn'),
         ('off', 'so'), ('fac', 'sf'), ('jag', 'sj'),
         ('so', 'c'), ('so', 'e'), ('so', 'rf'), ('sf', 'r'), ('sj', 'r'), ('rf', 'r')]
render('12-sloped-cheese-tree', nodes, edges)
