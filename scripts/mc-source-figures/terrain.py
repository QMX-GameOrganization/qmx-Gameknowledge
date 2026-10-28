"""把 NoiseRouterData 里 overworld 的 sloped_cheese 搭起来（numpy 版，随机种子是示意性的）。"""
import numpy as np
import mcnoise as m


class World:
    def __init__(self, seed=7):
        r = np.random.default_rng(seed)
        self.shift = m.NormalNoise(r, -3, [1.0, 1.0, 1.0, 0.0])                    # noise/offset.json
        self.cont = m.NormalNoise(r, -9, [1.0, 1.0, 2.0, 2.0, 2.0, 1.0, 1.0, 1.0, 1.0])  # continentalness
        self.eros = m.NormalNoise(r, -9, [1.0, 1.0, 0.0, 1.0, 1.0])                  # erosion
        self.ridge = m.NormalNoise(r, -7, [1.0, 2.0, 1.0, 0.0, 0.0, 0.0])            # ridge (= weirdness)
        self.jag = m.NormalNoise(r, -16, [1.0] * 16)                                 # jagged
        self.base = m.BlendedNoise(r)                                                # overworld/base_3d_noise

    # shift_x / shift_z：对采样坐标做“域扭曲”，让海岸线更不规则
    def shifts(self, x, z):
        sx = self.shift.value(x * 0.25, 0.0 * x, z * 0.25) * 4.0
        sz = self.shift.value(z * 0.25, x * 0.25, 0.0 * x) * 4.0
        return sx, sz

    def climate(self, x, z, warp=True):
        x = np.asarray(x, float); z = np.asarray(z, float)
        if warp:
            sx, sz = self.shifts(x, z)
        else:
            sx = sz = 0.0
        px, pz = x * 0.25 + sx, z * 0.25 + sz        # shifted_noise: xz_scale=0.25
        zero = 0.0 * px
        return (self.cont.value(px, zero, pz), self.eros.value(px, zero, pz), self.ridge.value(px, zero, pz))

    def jag_noise(self, x, z):
        return self.jag.value(np.asarray(x, float) * 1500.0, 0.0 * np.asarray(x, float), np.asarray(z, float) * 1500.0)


def sloped_cheese(depth, factor, jag, jnoise, base3d, qn=True):
    """sloped_cheese = 4·quarterNegative((depth + jaggedness·halfNegative(jnoise)) · factor) + base_3d_noise"""
    x = (depth + jag * m.half_negative(jnoise)) * factor
    return (4.0 * m.quarter_negative(x) if qn else 4.0 * x) + base3d


def depth_of(y, offset):
    return m.y_clamped_gradient(y, -64, 320, 1.5, -1.5) + offset


def slide_overworld(d, y):
    """NoiseRouterData.slideOverworld(false, …)：底部 24 格淡入、顶部 16 格淡出"""
    top = m.y_clamped_gradient(y, 240, 256, 1.0, 0.0)
    d2 = (d - (-0.078125)) * top + (-0.078125)           # lerp(top, -0.078125, d)
    bot = m.y_clamped_gradient(y, -64, -40, 0.0, 1.0)
    return (d2 - 0.1171875) * bot + 0.1171875            # lerp(bot, 0.1171875, d2)
