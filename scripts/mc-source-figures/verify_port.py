"""用 data/…/density_function/overworld/{offset,factor,jaggedness}.json 里烘焙好的样条，验证 mcnoise.py 里对 TerrainProvider 的移植。"""
import json, sys, random, os
sys.path.insert(0, os.path.dirname(__file__))
import mcnoise as m

R = os.environ.get('MC_DF', '/sessions/upbeat-epic-knuth/mnt/Minecraft源码学习/out/resources/data/minecraft/worldgen/density_function/overworld/')


def find_spline(d):
    if isinstance(d, dict):
        if d.get('type') == 'minecraft:spline':
            return d['spline']
        for v in d.values():
            r = find_spline(v)
            if r is not None:
                return r
    return None


def ev(sp, ctx):
    if isinstance(sp, (int, float)):
        return float(sp)
    x = ctx[sp['coordinate'].split('/')[-1]]
    pts = sp['points']
    loc = [p['location'] for p in pts]; der = [p['derivative'] for p in pts]
    n = len(pts); i = -1
    for t in range(n):
        if x < loc[t]:
            break
        i = t
    if i < 0:
        v = ev(pts[0]['value'], ctx); return v if der[0] == 0 else v + der[0] * (x - loc[0])
    if i == n - 1:
        v = ev(pts[-1]['value'], ctx); return v if der[-1] == 0 else v + der[-1] * (x - loc[-1])
    g, h = loc[i], loc[i + 1]; t = (x - g) / (h - g)
    a = ev(pts[i]['value'], ctx); b = ev(pts[i + 1]['value'], ctx)
    p = der[i] * (h - g) - (b - a); q = -der[i + 1] * (h - g) + (b - a)
    return a + t * (b - a) + t * (1 - t) * (p + t * (q - p))


if __name__ == '__main__':
    random.seed(3)
    for nm, idx in {'offset': 0, 'factor': 1, 'jaggedness': 2}.items():
        sp = find_spline(json.load(open(R + nm + '.json')))
        worst = 0.0
        for _ in range(3000):
            c, e, w = random.uniform(-1.1, 1.1), random.uniform(-1.1, 1.1), random.uniform(-1, 1)
            # JSON 里：overworld/ridges 是原始 weirdness，overworld/ridges_folded 是折叠后的
            ctx = {'continents': c, 'erosion': e, 'ridges': w, 'ridges_folded': float(m.folded(w))}
            o, f, j = m.terrain_params(c, e, w)
            mine = [float(o) - m.GLOBAL_OFFSET, float(f), float(j)][idx]
            worst = max(worst, abs(ev(sp, ctx) - mine))
        print(f'{nm:11s} max abs diff = {worst:.2e}')
