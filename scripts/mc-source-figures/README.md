# 源码专栏配图脚本

这些脚本生成 `public/assets/mc-source/` 下的配图，对应 `src/content/docs/knowledge/Minecraft源码学习/源码专栏/` 各页。

## 依赖

Python 3、`numpy`、`matplotlib`、`Pillow`；`fig_d_tree.py` / `fig_i_spawn.py` 还需要系统里装有 Graphviz（`dot`）。
图里的中文用 `Noto Sans CJK`（在 `style.py` 里配置，没有就换成你机器上有的中文字体）。

## 运行

```bash
export MC_FIG_OUT=./out           # 图片输出目录（默认见 style.py）
export MC_DF="D:/Minecraft源码学习/out/resources/data/minecraft/worldgen/density_function/overworld/"
python verify_port.py             # 先验证移植：样条与数据包 JSON 的最大差应在 1e-6 量级
python fig_a_functions.py         # 图 01-03
python fig_b_splines.py           # 图 04-06
python fig_c_density.py           # 图 07-10
python fig_d_tree.py              # 图 11-12
python fig_e_caves.py             # 图 13-14
python fig_f_systems.py           # 图 15-16
python fig_g_world.py             # 图 17-20
python fig_h_runtime.py           # 图 21-22
python fig_i_spawn.py             # 图 23
python fig_j_light.py             # 图 24
```

## 说明

- `mcnoise.py`：对 `ImprovedNoise / PerlinNoise / NormalNoise / BlendedNoise / CubicSpline / TerrainProvider` 的 numpy 移植。随机数用 numpy 的 RNG，**不是** Minecraft 的 Xoroshiro + 名字哈希，所以具体坐标的值与游戏不逐点一致，但算法、频率、振幅与统计特性一致。
- `terrain.py`：用 `mcnoise` 搭出 `sloped_cheese`、`slide` 等。
- `fig_h_runtime.py`、`fig_j_light.py` 里是 2D 玩具模拟（Jigsaw、流体扩散、方块光），规则与源码一致，素材与尺寸是示意。
