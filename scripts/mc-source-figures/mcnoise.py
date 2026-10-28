"""
Minecraft 1.20.1 世界生成核心算法的 numpy 移植（仅用于画图讲解）。

移植对象（均对照 out/src/mojmaps 下的反编译源码）：
  - ImprovedNoise / PerlinNoise / NormalNoise      (levelgen/synth)
  - BlendedNoise (old_blended_noise)                (levelgen/synth/BlendedNoise)
  - CubicSpline                                     (util/CubicSpline)
  - TerrainProvider.overworldOffset/Factor/Jaggedness (data/worldgen/TerrainProvider)
  - Mapped: abs/square/cube/halfNegative/quarterNegative/squeeze (DensityFunctions.Mapped)
  - NoiseChunk 的三线性 cell 插值                     (levelgen/NoiseChunk.NoiseInterpolator)

注意：随机数用 numpy 的 RNG，不是 Minecraft 的 Xoroshiro + 名字哈希。
所以“算法、频率、振幅、数值范围”与游戏一致，但“具体某个坐标的值”不会和游戏逐点一致。
"""
import numpy as np

GRAD = np.array([
    (1, 1, 0), (-1, 1, 0), (1, -1, 0), (-1, -1, 0),
    (1, 0, 1), (-1, 0, 1), (1, 0, -1), (-1, 0, -1),
    (0, 1, 1), (0, -1, 1), (0, 1, -1), (0, -1, -1),
    (1, 1, 0), (0, -1, 1), (-1, 1, 0), (0, -1, -1)], dtype=np.float64)


def smoothstep(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def lerp(t, a, b):
    return a + t * (b - a)


def clamped_lerp(a, b, t):
    return np.where(t < 0, a, np.where(t > 1, b, lerp(t, a, b)))


def clamped_map(v, in0, in1, out0, out1):
    t = (v - in0) / (in1 - in0)
    return clamped_lerp(out0, out1, t)


def wrap(d):
    return d - np.floor(d / 3.3554432e7 + 0.5) * 3.3554432e7


class ImprovedNoise:
    """经典 Perlin（改进版）: 256 排列表 + 16 个梯度 + smoothstep(6t^5-15t^4+10t^3)。"""

    def __init__(self, rng):
        self.xo, self.yo, self.zo = rng.random(3) * 256.0
        self.p = rng.permutation(256).astype(np.int64)

    def _p(self, i):
        return self.p[i & 255]

    def noise(self, x, y, z, y_scale=0.0, y_max=0.0):
        x = np.asarray(x, dtype=np.float64) + self.xo
        y = np.asarray(y, dtype=np.float64) + self.yo
        z = np.asarray(z, dtype=np.float64) + self.zo
        xi, yi, zi = np.floor(x), np.floor(y), np.floor(z)
        xf, yf, zf = x - xi, y - yi, z - zi
        if np.ndim(y_scale) > 0 or y_scale != 0.0:
            # 源码里的 “y 轴涂抹(smear)”：把 y 的小数部分按 y_scale 量化，制造平台感
            r = np.where((y_max >= 0.0) & (y_max < yf), y_max, yf)
            sy = np.floor(r / y_scale + 1.0e-7) * y_scale
        else:
            sy = 0.0
        xi, yi, zi = xi.astype(np.int64), yi.astype(np.int64), zi.astype(np.int64)
        return self._sample(xi, yi, zi, xf, yf - sy, zf, yf)

    def _grad(self, idx, dx, dy, dz):
        g = GRAD[idx & 15]
        return g[..., 0] * dx + g[..., 1] * dy + g[..., 2] * dz

    def _sample(self, i, j, k, d, e, f, g):
        l = self._p(i); m = self._p(i + 1)
        n = self._p(l + j); o = self._p(l + j + 1)
        p = self._p(m + j); q = self._p(m + j + 1)
        h = self._grad(self._p(n + k), d, e, f)
        r = self._grad(self._p(p + k), d - 1, e, f)
        s = self._grad(self._p(o + k), d, e - 1, f)
        t = self._grad(self._p(q + k), d - 1, e - 1, f)
        u = self._grad(self._p(n + k + 1), d, e, f - 1)
        v = self._grad(self._p(p + k + 1), d - 1, e, f - 1)
        w = self._grad(self._p(o + k + 1), d, e - 1, f - 1)
        x = self._grad(self._p(q + k + 1), d - 1, e - 1, f - 1)
        sx, sy, sz = smoothstep(d), smoothstep(g), smoothstep(f)
        # Mth.lerp3(sx, sy, sz, ...)：先 x，再 y，最后 z
        def lerp2(a, b, c0, c1, c2, c3):
            return lerp(b, lerp(a, c0, c1), lerp(a, c2, c3))
        return lerp(sz, lerp2(sx, sy, h, r, s, t), lerp2(sx, sy, u, v, w, x))


class PerlinNoise:
    """多 octave 叠加。firstOctave 与 amplitudes 的含义同 noise/*.json。"""

    def __init__(self, rng, first_octave, amplitudes):
        self.first = first_octave
        self.amp = list(amplitudes)
        n = len(self.amp)
        self.levels = [ImprovedNoise(rng) if a != 0.0 else None for a in self.amp]
        self.lowest_in = 2.0 ** (first_octave)               # 2^(-j), j=-firstOctave
        self.lowest_val = 2.0 ** (n - 1) / (2.0 ** n - 1.0)

    def value(self, x, y, z):
        i = 0.0
        j = self.lowest_in
        k = self.lowest_val
        for lv, a in zip(self.levels, self.amp):
            if lv is not None:
                i = i + a * lv.noise(wrap(x * j), wrap(y * j), wrap(z * j)) * k
            j *= 2.0
            k /= 2.0
        return i


class NormalNoise:
    """两份 PerlinNoise，第二份输入频率乘 1.0181268882175227，再统一缩放到约 ±1。"""
    INPUT_FACTOR = 1.0181268882175227

    def __init__(self, rng, first_octave, amplitudes):
        self.a = PerlinNoise(rng, first_octave, amplitudes)
        self.b = PerlinNoise(rng, first_octave, amplitudes)
        nz = [i for i, v in enumerate(amplitudes) if v != 0.0]
        dev = 0.1 * (1.0 + 1.0 / ((max(nz) - min(nz)) + 1))
        self.factor = (1.0 / 6.0) / dev

    def value(self, x, y, z):
        f = self.INPUT_FACTOR
        return (self.a.value(x, y, z) + self.b.value(x * f, y * f, z * f)) * self.factor


class BlendedNoise:
    """
    old_blended_noise —— 主地形 3D 噪声。
    三组 Perlin：minLimit(16 octave)、maxLimit(16 octave)、main(8 octave)。
    main 的结果 q∈[0,1] 决定在 min / max 两个噪声之间怎么插值。
    q<=0 / q>=1 时另一组不用算（源码的 early exit）。
    """

    def __init__(self, rng, xz_scale=0.25, y_scale=0.125, xz_factor=80.0, y_factor=160.0, smear=8.0):
        self.min = [ImprovedNoise(rng) for _ in range(16)]
        self.max = [ImprovedNoise(rng) for _ in range(16)]
        self.main = [ImprovedNoise(rng) for _ in range(8)]
        self.xz_mul = 684.412 * xz_scale
        self.y_mul = 684.412 * y_scale
        self.xz_factor, self.y_factor, self.smear = xz_factor, y_factor, smear

    def compute(self, x, y, z):
        d = np.asarray(x, dtype=np.float64) * self.xz_mul
        e = np.asarray(y, dtype=np.float64) * self.y_mul
        f = np.asarray(z, dtype=np.float64) * self.xz_mul
        g, h, i = d / self.xz_factor, e / self.y_factor, f / self.xz_factor
        j = self.y_mul * self.smear
        k = j / self.y_factor
        n = 0.0
        o = 1.0
        for p in range(8):
            n = n + self.main[p].noise(wrap(g * o), wrap(h * o), wrap(i * o), k * o, h * o) / o
            o /= 2.0
        q = (n / 10.0 + 1.0) / 2.0
        use_min = q < 1.0
        use_max = q > 0.0
        l = 0.0
        m = 0.0
        o = 1.0
        for r in range(16):
            s, t, u, v = wrap(d * o), wrap(e * o), wrap(f * o), j * o
            l = l + self.min[r].noise(s, t, u, v, e * o) / o
            m = m + self.max[r].noise(s, t, u, v, e * o) / o
            o /= 2.0
        return clamped_lerp(l / 512.0, m / 512.0, q) / 128.0


# ------------------------------------------------------------------ CubicSpline
class Spline:
    """
    对应 CubicSpline.Multipoint：
      coord : 坐标名，运行时从 ctx 字典里取（continents/erosion/weirdness/ridges）
      pts   : [(location, value, derivative)]，value 可以是常数，也可以是另一条 Spline（嵌套）
    """

    def __init__(self, coord, transform=None):
        self.coord = coord
        self.loc, self.val, self.der = [], [], []
        self.tf = transform or (lambda v: v)

    def add(self, loc, value, der=0.0):
        assert not self.loc or loc > self.loc[-1], "points must be ascending"
        if not isinstance(value, Spline):
            value = ('k', self.tf(value))       # 常量要先过 valueTransformer
        self.loc.append(loc); self.val.append(value); self.der.append(der)
        return self

    @staticmethod
    def _ev(v, ctx):
        return v[1] if isinstance(v, tuple) else v(ctx)

    def __call__(self, ctx):
        x = ctx[self.coord]
        loc, der = self.loc, self.der
        n = len(loc)
        # findIntervalStart：最后一个 loc<=x 的下标，没有则 -1
        i = -1
        for t in range(n):
            if x < loc[t]:
                break
            i = t
        if i < 0:   # 左外推：沿起点斜率线性延伸
            v0 = self._ev(self.val[0], ctx)
            return v0 if der[0] == 0 else v0 + der[0] * (x - loc[0])
        if i == n - 1:
            v1 = self._ev(self.val[-1], ctx)
            return v1 if der[-1] == 0 else v1 + der[-1] * (x - loc[-1])
        g, h = loc[i], loc[i + 1]
        t = (x - g) / (h - g)
        a = self._ev(self.val[i], ctx)
        b = self._ev(self.val[i + 1], ctx)
        p = der[i] * (h - g) - (b - a)
        q = -der[i + 1] * (h - g) + (b - a)
        # lerp(t,a,b) + t(1-t)*lerp(t,p,q)
        return a + t * (b - a) + t * (1 - t) * (p + t * (q - p))


# ---------------------------------------------------------- TerrainProvider 移植
def _lerpf(t, a, b):
    return a + t * (b - a)


def _peaks_and_valleys(f):
    return -(abs(abs(f) - 0.6666667) - 0.33333334) * 3.0


def _slope(f, g, h, i):
    return (g - f) / (i - h)


def _mountain_continentalness(f, g, h):
    k = 1.0 - (1.0 - g) * 0.5
    l = 0.5 * (1.0 - g)
    m = (f + 1.17) * 0.46082947
    n = m * k - l
    return max(n, -0.2222) if f < h else max(n, 0.0)


def _mountain_zero_point(f):
    i = 1.0 - (1.0 - f) * 0.5
    j = 0.5 * (1.0 - f)
    return j / (0.46082947 * i) - 1.17


def _mountain_ridge_spline(coord, f, bl, tf):
    b = Spline(coord, tf)
    i = _mountain_continentalness(-1.0, f, -0.7)
    k = _mountain_continentalness(1.0, f, -0.7)
    l = _mountain_zero_point(f)
    if -0.65 < l < 1.0:
        n = _mountain_continentalness(-0.65, f, -0.7)
        p = _mountain_continentalness(-0.75, f, -0.7)
        q = _slope(i, p, -1.0, -0.75)
        b.add(-1.0, i, q)
        b.add(-0.75, p)
        b.add(-0.65, n)
        r = _mountain_continentalness(l, f, -0.7)
        s = _slope(r, k, l, 1.0)
        b.add(l - 0.01, r)
        b.add(l, r, s)
        b.add(1.0, k, s)
    else:
        n = _slope(i, k, -1.0, 1.0)
        if bl:
            b.add(-1.0, max(0.2, i))
            b.add(0.0, _lerpf(0.5, i, k), n)
        else:
            b.add(-1.0, i, n)
        b.add(1.0, k, n)
    return b


def _ridge_spline(coord, f, g, h, i, j, k, tf):
    l = max(0.5 * (g - f), k)
    m = 5.0 * (h - g)
    return (Spline(coord, tf).add(-1.0, f, l).add(-0.4, g, min(l, m)).add(0.0, h, m)
            .add(0.4, i, 2.0 * (i - h)).add(1.0, j, 0.7 * (j - i)))


def _erosion_offset_spline(ero, rid, f, g, h, i, j, k, bl, bl2, tf):
    c1 = _mountain_ridge_spline(rid, _lerpf(i, 0.6, 1.5), bl2, tf)
    c2 = _mountain_ridge_spline(rid, _lerpf(i, 0.6, 1.0), bl2, tf)
    c3 = _mountain_ridge_spline(rid, i, bl2, tf)
    c4 = _ridge_spline(rid, f - 0.15, 0.5 * i, _lerpf(0.5, 0.5, 0.5) * i, 0.5 * i, 0.6 * i, 0.5, tf)
    c5 = _ridge_spline(rid, f, j * i, g * i, 0.5 * i, 0.6 * i, 0.5, tf)
    c6 = _ridge_spline(rid, f, j, j, g, h, 0.5, tf)
    c7 = _ridge_spline(rid, f, j, j, g, h, 0.5, tf)
    c8 = Spline(rid, tf).add(-1.0, f).add(-0.4, c6).add(0.0, h + 0.07)
    c9 = _ridge_spline(rid, -0.02, k, k, g, h, 0.0, tf)
    b = (Spline(ero, tf).add(-0.85, c1).add(-0.7, c2).add(-0.4, c3).add(-0.35, c4)
         .add(-0.1, c5).add(0.2, c6))
    if bl:
        b.add(0.4, c7).add(0.45, c8).add(0.55, c8).add(0.58, c7)
    b.add(0.7, c9)
    return b


def overworld_offset(amplified=False):
    """offset = spline(continents, erosion, ridges_folded)；最终还要再加 GLOBAL_OFFSET=-0.50375。"""
    tf = (lambda v: v if v < 0 else v * 2.0) if amplified else None
    C, E, R = 'continents', 'erosion', 'ridges'   # 这里 R 指 ridges_folded（peaksAndValleys）
    s1 = _erosion_offset_spline(E, R, -0.15, 0.0, 0.0, 0.1, 0.0, -0.03, False, False, tf)
    s2 = _erosion_offset_spline(E, R, -0.1, 0.03, 0.1, 0.1, 0.01, -0.03, False, False, tf)
    s3 = _erosion_offset_spline(E, R, -0.1, 0.03, 0.1, 0.7, 0.01, -0.03, True, True, tf)
    s4 = _erosion_offset_spline(E, R, -0.05, 0.03, 0.1, 1.0, 0.01, 0.01, True, True, tf)
    return (Spline(C, tf).add(-1.1, 0.044).add(-1.02, -0.2222).add(-0.51, -0.2222)
            .add(-0.44, -0.12).add(-0.18, -0.12).add(-0.16, s1).add(-0.15, s1)
            .add(-0.1, s2).add(0.25, s3).add(1.0, s4))


def _erosion_factor(ero, wei, rid, f, bl, tf):
    # 注意：这里 wei=原始 ridges（weirdness），rid=ridges_folded
    c = Spline(wei, tf).add(-0.2, 6.3).add(0.2, f)
    b = (Spline(ero, tf).add(-0.6, c)
         .add(-0.5, Spline(wei, tf).add(-0.05, 6.3).add(0.05, 2.67))
         .add(-0.35, c).add(-0.25, c)
         .add(-0.1, Spline(wei, tf).add(-0.05, 2.67).add(0.05, 6.3))
         .add(0.03, c))
    if bl:
        c2 = Spline(wei, tf).add(0.0, f).add(0.1, 0.625)
        c3 = Spline(rid, tf).add(-0.9, f).add(-0.69, c2)
        b.add(0.35, f).add(0.45, c3).add(0.55, c3).add(0.62, f)
    else:
        c2 = Spline(rid, tf).add(-0.7, c).add(-0.15, 1.37)
        c3 = Spline(rid, tf).add(0.45, c).add(0.7, 1.56)
        b.add(0.05, c3).add(0.4, c3).add(0.45, c2).add(0.55, c2).add(0.58, f)
    return b


def overworld_factor(amplified=False):
    tf5 = (lambda v: 1.25 - 6.25 / (v + 5.0)) if amplified else None
    C, E, W, R = 'continents', 'erosion', 'weirdness', 'ridges'
    ident = None
    return (Spline(C).add(-0.19, 3.95)
            .add(-0.15, _erosion_factor(E, W, R, 6.25, True, ident))
            .add(-0.1, _erosion_factor(E, W, R, 5.47, True, tf5))
            .add(0.03, _erosion_factor(E, W, R, 5.08, True, tf5))
            .add(0.06, _erosion_factor(E, W, R, 4.69, False, tf5)))


def _weird_jag(wei, f, tf):
    return Spline(wei, tf).add(-0.01, 0.63 * f).add(0.01, 0.3 * f)


def _ridge_jag(wei, rid, f, g, tf):
    h = _peaks_and_valleys(0.4)
    i = _peaks_and_valleys(0.56666666)
    j = (h + i) / 2.0
    b = Spline(rid, tf)
    b.add(h, 0.0)
    b.add(j, _weird_jag(wei, g, tf) if g > 0 else 0.0)
    b.add(1.0, _weird_jag(wei, f, tf) if f > 0 else 0.0)
    return b


def _erosion_jag(ero, wei, rid, f, g, h, i, tf):
    c1 = _ridge_jag(wei, rid, f, h, tf)
    c2 = _ridge_jag(wei, rid, g, i, tf)
    return Spline(ero, tf).add(-1.0, c1).add(-0.78, c2).add(-0.5775, c2).add(-0.375, 0.0)


def overworld_jaggedness(amplified=False):
    tf = (lambda v: v * 2.0) if amplified else None
    C, E, W, R = 'continents', 'erosion', 'weirdness', 'ridges'
    return (Spline(C, tf).add(-0.11, 0.0)
            .add(0.03, _erosion_jag(E, W, R, 1.0, 0.5, 0.0, 0.0, tf))
            .add(0.65, _erosion_jag(E, W, R, 1.0, 1.0, 1.0, 0.0, tf)))


def folded(w):
    """ridges_folded.json: -3 * (|(|w| - 2/3)| - 1/3) —— 把 [-1,1] 折成“山谷-山峰”曲线"""
    return -3.0 * (np.abs(np.abs(w) - 2.0 / 3.0) - 1.0 / 3.0)


# ------------------------------------------------------------ DensityFunctions.Mapped
def half_negative(d):
    return np.where(d > 0, d, d * 0.5)


def quarter_negative(d):
    return np.where(d > 0, d, d * 0.25)


def squeeze(d):
    c = np.clip(d, -1.0, 1.0)
    return c / 2.0 - c ** 3 / 24.0


def y_clamped_gradient(y, y0, y1, v0, v1):
    return clamped_map(y, y0, y1, v0, v1)


GLOBAL_OFFSET = -0.50375


def terrain_params(c, e, w, amplified=False, _cache={}):
    """给 (continents, erosion, weirdness) 数组，返回 offset, factor, jaggedness 三个数组。"""
    key = amplified
    if key not in _cache:
        _cache[key] = (overworld_offset(amplified), overworld_factor(amplified), overworld_jaggedness(amplified))
    so, sf, sj = _cache[key]
    c, e, w = np.broadcast_arrays(np.asarray(c, float), np.asarray(e, float), np.asarray(w, float))
    out = np.empty((3,) + c.shape)
    it = np.nditer([c, e, w], flags=['multi_index'])
    for cc, ee, ww in it:
        ctx = {'continents': float(cc), 'erosion': float(ee), 'weirdness': float(ww),
               'ridges': float(folded(float(ww)))}
        idx = it.multi_index
        out[(0,) + idx] = so(ctx) + GLOBAL_OFFSET
        out[(1,) + idx] = sf(ctx)
        out[(2,) + idx] = sj(ctx)
    return out[0], out[1], out[2]
