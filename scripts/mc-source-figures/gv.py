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


