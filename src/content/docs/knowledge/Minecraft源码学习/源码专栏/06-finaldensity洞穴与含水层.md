---
title: "6. finalDensity：封顶封底、洞穴与含水层"
description: 解读 final_density 的顶层结构（slide、range_choice 闸门、squeeze、noodle），cheese 洞穴的组成，以及含水层与巨型矿脉如何在 doFill 里决定“空的地方是什么”。
sidebar:
  order: 6
---

> 对应源码：`NoiseRouterData.overworld / underground / slideOverworld / postProcess`、`Aquifer`、`OreVeinifier`、`NoiseChunk`（`blockStateRule`）。数据：`noise_settings/overworld.json` 里的 `final_density`。

## 要点

- `final_density` 的真实顶层是 `min( squeeze(0.64 × interpolated(blend_density(slide(range_choice(…))))), noodle )`。
- `sloped_cheese`（上一页）是 `range_choice` 的输入，也是其中一个分支；**洞穴只在 `sloped_cheese ≥ 1.5625`（够深的实心区）才会被求值**，这既是美观需要，也是性能开关。
- `slide` 在上下两端把密度拉向固定值，把世界“封顶封底”。
- 洞穴的基本手法都一样：**让某些位置的密度小于 0**，也就是在已有的实心里“挖”出空。
- 含水层（`Aquifer`）和巨型矿脉（`OreVeinifier`）不在密度函数里，而是 `doFill` 对每个方块依次询问的“材质规则”。

## 顶层结构

![final_density 的顶层结构](/qmx-Gameknowledge/assets/mc-source/11-final-density-tree.png)

从外到内读：

| 层 | 作用 |
| --- | --- |
| `min(…, noodle)` | `noodle` 是细长的“面条洞”。取 `min` 就是“任何一边 ≤ 0 就是空” |
| `squeeze(0.64 × …)` | 后处理：把幅度限制到约 ±0.458，不改变正负 |
| `interpolated(…)` | **缓存标记**：里面整棵子树只在 cell 角点求值，其余线性插值（第 10 页） |
| `blend_density` | 与旧版本区块融合；新世界里等于恒等 |
| `slide` | 上缘封顶、下缘封底 |
| `range_choice` | 根据 `sloped_cheese` 的值决定走哪一支 |

注意 `interpolated` **包住了从 `slide` 到所有洞穴的整棵子树**。也就是说，洞穴噪声、`sloped_cheese`、所有样条，全部只在每个 cell 的角点算；`squeeze`、`× 0.64` 和 `min noodle` 这些便宜的运算才逐方块执行。

## slide：封顶与封底

```java
// NoiseRouterData.slideOverworld(false, d) 即 slide(d, -64, 384, 80, 64, -0.078125, 0, 24, 0.1171875)
top = yClampedGradient(240 → 256, 1.0 → 0.0)
d2  = lerp(top, -0.078125, d)         // 在 240~256 之间从 d 渐变到 -0.078
bot = yClampedGradient(-64 → -40, 0.0 → 1.0)
out = lerp(bot, 0.1171875, d2)         // 在 -64~-40 之间从 0.117 渐变到 d2
```

![slide、闸门、squeeze](/qmx-Gameknowledge/assets/mc-source/13-slide-gate-squeeze.png)

左图：不管输入密度多大，**在 y ≥ 256 时输出都是 -0.078（空）**，在 y = -64 时输出是 +0.117（实）。中间 240~256 与 -64~-40 是渐变过渡。

结果是：

- 地形不会越过 y = 256（虽然世界高度到 320）；山顶在 240 以上会被逐渐“削平”。
- 世界最底部一层一定是实心，下面不会挖穿（基岩由后面的地表规则放置）。
- 洞穴噪声再强，也挖不到最底部或最顶部，两端的边界总是干净的。

## range_choice：把洞穴关在“闸门”后面

```text
range_choice(
  input         = sloped_cheese,
  [min, max)    = [-1000000, 1.5625),
  when_in_range = min( sloped_cheese, 5 × entrances ),          // 浅层/空中：只有“洞穴入口”
  when_out_of_range = max( min( min(cheese, entrances), spaghetti_2d + roughness ),
                           pillars_or_-1e6 )                      // 深层实心：全套洞穴
)
```

`sloped_cheese` 在这里扮演了**“深度计”**：它越大，说明离地表越深、越“实”。

- `s < 1.5625`：空气、地表附近的实心。只允许 `entrances`（地表洞穴入口），其它洞穴噪声一律不算。
- `s ≥ 1.5625`：足够深，才计算 cheese、spaghetti、pillars。

中图是 cheese 洞穴的偏置项 `clamp(1.5 − 0.64·s, 0, 0.5)`：刚越过闸门时偏置是 +0.5（让密度更偏向实心），随着 `s` 增大线性降到 0（`s ≥ 2.34`）。**越靠近地表，洞穴越难形成；越深越容易。**这避免了洞穴一下子把地表掏空，也不需要单独写一套“离地表多远”的距离计算，直接复用了地形密度本身。

这个设计同时是性能优化：地表之上的空气、地表附近的柱子占了绝大多数方块，它们**不会触发 cheese、spaghetti、pillars 的求值**（`range_choice.compute` 只算其中一支；只有 `entrances` 仍可能被求值，而且 `min` 的短路常常能把它也跳过）。

## 洞穴家族

| 类型 | 形状 | 主要手法 |
| --- | --- | --- |
| cheese | 大空洞，像瑞士奶酪 | 一个 3D 噪声小于阈值的区域（-0.27 以下）为空，再叠一个沿 y 分层的项 |
| spaghetti_2d | 细长水平“走廊” | 用 `weird_scaled_sampler` 按稀有度缩放噪声，与一个随高度变化的“海拔”噪声比较 |
| entrances | 通向地表的入口（基于 3D spaghetti） | 两个 3D 噪声取 `max` 再加厚度，与一个入口噪声取 `min`；入口噪声的偏置在 y = -10 → 30 之间从 +0.3 渐变到 0，所以越高越容易出现 |
| noodle | 极细的管状洞 | 两个“脊线噪声”的零值面相交成一条线，再给厚度 |
| pillars | 洞里的巨型石柱 | 一个稀有的噪声，大于阈值时取 `max` 变成实心 |
| carvers（传统洞穴/峡谷） | 蠕虫洞、深沟 | 不是密度函数，而是 `CARVERS` 阶段的随机游走（第 9 页） |

几乎所有“管状”洞穴都用同一个技巧：**两张曲面的交线是一条线**。一个 3D 噪声的零等值面是一张曲面，两个噪声零面的交集就是一条曲线。把判定写成 `max(|A|, |B|) < 阈值`，就得到一条以这条线为轴的管道，阈值越大管子越粗。`noodle` 和矿脉（见下文）都是这个思路。

## cheese 洞穴的公式

```text
cheese = 4 · square( cave_layer )                       // ① 沿 y 的“层”
       + clamp( 0.27 + cave_cheese, -1, 1 )              // ② 3D 空洞
       + clamp( 1.5 − 0.64 · sloped_cheese, 0, 0.5 )     // ③ 离地表越近越难开
```

- **①** `cave_layer` 的 `y_scale = 8`，沿 y 变化很快；平方后非负，所以这一项只会抬高密度。它只有在噪声接近 0 的那些薄薄的水平层里才接近 0，所以洞穴在 y 方向上倾向于成**薄层**，有“楼层”感。
- **②** `cave_cheese` 是一个 octave 比较多的 3D 噪声，噪声 < -0.27 的位置，这一项为负。
- **③** 就是前面说的闸门偏置。

三项相加，结果 ≤ 0 的地方就是洞。

## 一张真实的洞穴剖面

![cheese 洞穴的剖面](/qmx-Gameknowledge/assets/mc-source/14-cheese-caves-slice.png)

这张图只实现了 cheese 洞穴（没有 spaghetti、noodle、pillars），其余部分与源码一致。黄色是“地形本来是实心、被洞穴挖空”的部分。

- 洞穴几乎全部出现在山体深处，地表附近没有大洞（闸门 + 偏置在起作用）。
- 洞穴有明显的水平层状（`cave_layer` 的效果）。
- 下图是真实游戏的做法：只在 4×8 的角点上算密度，其余线性插值。洞穴边缘被“磨圆”，细小的洞会被抹掉，但大洞的位置和形状基本不变。

## 后处理：× 0.64 与 squeeze

右图是 `squeeze(0.64·x)`：输入落在 ±1.5625 之外会被夹到 ±0.458。它不改变正负号，所以不影响“实/空”的判定，只是把幅度限制住。

源码没有注释它的用途，一个合理的解释是：含水层会拿一个“压力项”（量级约 ±2）与密度相加来判断水体边界，密度被限制在 ±0.46 以内，压力项就总能起决定作用。这是我从 `Aquifer.computeSubstance` 的写法推测的，读到相关代码时可以自己验证。

## doFill 如何决定一个方块是什么

`NoiseChunk` 里有一个 `blockStateRule`，是一串“填充器”，按顺序询问，**第一个返回非空的获胜**：

```java
blockStateRule = [
  aquifer.computeSubstance(ctx, finalDensity + beardifier),   // ① 含水层
  oreVeinifier(veinToggle, veinRidged, veinGap)                // ② 巨型矿脉（若启用）
]
// 都返回 null → 用默认方块（石头）
```

① 含水层：先看密度。**密度 > 0 → 返回 null（交给下一条规则，最终是石头）。**密度 ≤ 0 才进入含水层逻辑，决定这个“空”的位置是空气、水还是岩浆。
② 矿脉：只对实心位置有意义，判定通过才替换石头。

所以流体的判定只对“空的方块”做，实心方块完全不触发含水层计算。

## 含水层 Aquifer

地下有大片水域和岩浆湖，它们需要满足：水面平整、互不串通、边界处有岩壁。源码用的是**抖动网格 + 最近中心**：

![含水层的抖动网格](/qmx-Gameknowledge/assets/mc-source/19-aquifer-jittered-grid.png)

1. 把空间划分成 16×12×16 的网格（x、z 方向 16，y 方向 12）。
2. 每个格子里放**一个含水层中心**，位置是格子原点加一个伪随机偏移 `(nextInt(10), nextInt(9), nextInt(10))`，随机数由 `aquiferRandom.at(格子坐标)` 派生，所以确定性。
3. 对任意一个“空”的方块，在周围 2×3×2 = 12 个候选格里找出**最近的三个中心**（距离平方 `o ≤ p ≤ q`）。
4. 最近中心决定这个方块属于哪个水体（水位高度和流体种类）。
5. `similarity(o, p) = 1 − |p − o| / 25`：如果最近两个中心几乎一样远（方块在两个水体的交界附近），`similarity` 接近 1，就要判断是否需要用岩壁隔开。
6. 隔开的方式：计算两水体的水位差产生的“压力”，加上 `barrier` 噪声，与当前密度相加；若总和 > 0 就把这个方块改成实心（返回 null）。实际代码依次比较三对中心（权重分别为 `e`、`e·g`、`e·h`，`g`、`h` 是另外两对的 `similarity`），任何一对判定成立就返回 null；全局默认流体是岩浆时，直接返回岩浆；`similarity ≤ 0` 时不做任何隔开，直接返回最近中心的流体。

上图右幅是 `similarity` 的分布：深色线是两个水体的交界，也是最容易出现岩壁的地方。

几个细节：

- 全局默认流体（`createFluidPicker`）：`y < -54` 是岩浆（水位 -54），其它地方是水（水位取海平面 63）。含水层在此基础上给局部区域不同的水位。
- 每个区块有自己的 `aquiferCache` 和 `aquiferLocationCache`（按网格索引的数组），同一个网格中心不会被重复计算。
- `barrier` 噪声只有在确实需要时才求值（`MutableDouble` 懒计算），大部分方块不会触发它。

## 巨型矿脉 OreVeinifier

整个文件只有 77 行，是理解“用噪声做概率判定”的好例子。对一个实心位置：

```java
d = veinToggle(ctx);                       // 低频噪声（ore_veininess）：>0 铜矿脉，≤0 铁矿脉
type = d > 0 ? COPPER(y 0..50) : IRON(y -60..-8);
if (y 超出该类型的范围) return null;
edge = clampedMap(min(到上下边界的距离), 0, 20, -0.2, 0);   // 靠近边界时要求更“浓”
if (|d| + edge < 0.4) return null;         // veininess 不够，不在矿脉里
if (random(x,y,z) > 0.7) return null;      // 70% 的位置参与
if (veinRidged(ctx) >= 0) return null;     // 只在“脊线”附近（两个噪声零面的交线）
richness = clampedMap(|d|, 0.4, 0.6, 0.1, 0.3);
if (random < richness && veinGap(ctx) > -0.3)
    return random < 0.02 ? RAW_ORE_BLOCK : ORE;     // 2% 是“粗矿块”
return FILLER;                              // 铜脉的填充是花岗岩，铁脉是凝灰岩
```

- `veinRidged = -0.08 + max(|vein_a|, |vein_b|)`，小于 0 的位置是两个噪声零面的交线周围，就是前面说的“两面相交成线”的技巧，于是矿脉呈**管状、弯曲**。
- 每个位置的随机数用 `oreRandom.at(x, y, z)`，由坐标直接派生，所以和计算顺序无关。
- `ore_veininess`、`ore_vein_a`、`ore_vein_b` 这三个噪声通过 `yLimitedInterpolatable` 包成了 `interpolated(range_choice(y 范围, noise, 0))`（y 范围取两种矿脉的并集 -60 ~ 50）：既只在需要的 y 范围里求值，又享受 cell 插值。`ore_gap` 是普通噪声，没有包；`veinRidged` 则是由 `vein_a / vein_b` 派生出来的 `-0.08 + max(|a|, |b|)`。

## 给 Unity 项目的取舍

| 内容 | 建议 |
| --- | --- |
| `slide` 封顶封底 | **做**，一行 `lerp` 就能解决“顶部碎块、底部被挖穿” |
| `range_choice` 闸门 | **做**，思路简单（用地形密度当深度计），性能收益大 |
| cheese 洞穴 | 做第一个洞穴，用现成的 `sloped_cheese` 做深度计 |
| spaghetti / noodle / pillars | 先跳过，等 cheese 稳定后按“两面相交成线”的套路加 |
| 含水层 | 先用一个全局海平面填水；后面再做局部水体 |
| 巨型矿脉 | 暂时跳过；和普通矿石相比，它是装饰性的 |
| `squeeze × 0.64` | 如果你没有含水层，可以不做 |

## 小结

- `final_density = min(squeeze(0.64 · interpolated(slide(range_choice(…)))), noodle)`，洞穴被关在 `range_choice` 的深层分支里。
- `slide` 用两段线性渐变把世界上下封死。
- 洞穴手法：让某些位置的密度 ≤ 0；管状洞穴用“两个噪声零面相交成线”。
- 方块类型由 `blockStateRule` 依次询问：先含水层（只对空的方块起作用），再矿脉，最后默认石头。

## 自测

1. 为什么 `range_choice` 的输入用的是 `sloped_cheese`，而不是单独写一个“离地表深度”函数？
2. 为什么 `interpolated` 要包住 `range_choice` 之外的整棵子树，而不是只包 `sloped_cheese`？
3. 含水层为什么只对密度 ≤ 0 的方块起作用？
4. 如果想让某种洞穴在 y > 100 之后完全不出现，你会在哪里改？

参考答案：① `sloped_cheese` 本身就随深度单调增加，直接复用不需要额外计算。② 因为洞穴噪声才是最贵的部分，包进去才能让它们也只在角点求值。③ 实心方块不需要判断水，省掉大量计算。④ 可以在洞穴函数外再包一层 `range_choice(y, …)`，或者像 `entrances` 那样叠一个随 y 变化的 `yClampedGradient` 偏置。

