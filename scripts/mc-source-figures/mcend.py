"""EndIslandDensityFunction 的移植：LegacyRandomSource + SimplexNoise(2D) + getHeightValue。
与游戏一致：给定世界种子，输出的就是游戏里这个种子的末地外岛分布（不是示意）。"""
import numpy as np, math

MASK = (1 << 48) - 1
MUL = 25214903917
DM = float(np.float32(1.110223e-16))      # BitRandomSource.DOUBLE_MULTIPLIER 是 float 常量，再提升为 double


class LegacyRandom:
    def __init__(self, seed):
        self.s = (seed ^ MUL) & MASK

    def next(self, bits):
        self.s = (self.s * MUL + 11) & MASK
        v = self.s >> (48 - bits)
        if bits == 32 and v >= 1 << 31:        # (int) 强转
            v -= 1 << 32
        return v

    def next_int(self):
        return self.next(32)

    def next_int_b(self, n):
        if n & (n - 1) == 0:
            return (n * self.next(31)) >> 31
        while True:
            j = self.next(31)
            k = j % n
            if j - k + (n - 1) < (1 << 31):
                return k

    def next_double(self):
        i = self.next(26); j = self.next(27)
        return ((i << 27) + j) * DM


GRAD = [(1, 1), (-1, 1), (1, -1), (-1, -1), (1, 0), (-1, 0), (1, 0), (-1, 0),
        (0, 1), (0, -1), (0, 1), (0, -1), (1, 1), (0, -1), (-1, 1), (0, -1)]
SQ3 = math.sqrt(3.0); F2 = 0.5 * (SQ3 - 1.0); G2 = (3.0 - SQ3) / 6.0


class Simplex:
    def __init__(self, rng):
        rng.next_double(); rng.next_double(); rng.next_double()      # xo, yo, zo
        p = list(range(256))
        for i in range(256):
            j = rng.next_int_b(256 - i)
            p[i], p[j + i] = p[j + i], p[i]
        self.p = p + p

    def _p(self, i):
        return self.p[i & 255]

    @staticmethod
    def _corner(i, x, y):
        h = 0.5 - x * x - y * y
        if h < 0:
            return 0.0
        h *= h
        g = GRAD[i]
        return h * h * (g[0] * x + g[1] * y)

    def value(self, d, e):
        f = (d + e) * F2
        i = math.floor(d + f); j = math.floor(e + f)
        g = (i + j) * G2
        l = d - (i - g); m = e - (j - g)
        n, o = (1, 0) if l > m else (0, 1)
        p = l - n + G2; q = m - o + G2
        r = l - 1 + 2 * G2; s = m - 1 + 2 * G2
        t = i & 255; u = j & 255
        v = self._p(t + self._p(u)) % 12
        w = self._p(t + n + self._p(u + o)) % 12
        x = self._p(t + 1 + self._p(u + 1)) % 12
        return 70.0 * (self._corner(v, l, m) + self._corner(w, p, q) + self._corner(x, r, s))


def make_islands(seed):
    rng = LegacyRandom(seed)
    for _ in range(17292):
        rng.next_int()
    return Simplex(rng)


def height_grid(simplex, I, J, qmax):
    """I,J: 同形整数数组（单位 = 8 方块）。返回 getHeightValue。qmax：simplex 表半宽。"""
    N = 2 * qmax + 1
    tab = np.empty((N, N))
    for a in range(N):
        for b in range(N):
            tab[a, b] = simplex.value(a - qmax, b - qmax)
    ok = (tab < float(np.float32(-0.9)))
    K = np.trunc(I / 2).astype(int); L = np.trunc(J / 2).astype(int)
    M = I - 2 * K; Nn = J - 2 * L
    f = np.clip(100.0 - np.sqrt((I * I + J * J).astype(float)) * 8.0, -100.0, 80.0)
    for o in range(-12, 13):
        for p in range(-12, 13):
            q = K + o; r = L + p
            msk = (q * q + r * r > 4096) & ok[q + qmax, r + qmax]
            if not msk.any():
                continue
            g = (np.abs(q) * 3439.0 + np.abs(r) * 147.0) % 13.0 + 9.0
            h = (M - o * 2).astype(float); s = (Nn - p * 2).astype(float)
            t = np.clip(100.0 - np.sqrt(h * h + s * s) * g, -100.0, 80.0)
            f = np.where(msk, np.maximum(f, t), f)
    return f
