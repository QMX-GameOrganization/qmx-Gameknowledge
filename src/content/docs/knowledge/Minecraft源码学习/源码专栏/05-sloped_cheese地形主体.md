---
title: "5. sloped_cheese：一步一步搭出山地"
description: 把地形主体公式拆成六步，逐项说明每一项解决什么问题、去掉会怎样，配对照图；并给出“你的笔记 vs 源码”的逐项核对。
sidebar:
  order: 5
---

> 对应源码：`NoiseRouterData.registerTerrainNoises`、数据包 `density_function/overworld/sloped_cheese.json`、`depth.json`、`offset.json`……

## 要点

- 地形主体只有一个公式：`sloped_cheese = 4 · quarter_negative( (depth + jaggedness · half_negative(jagged)) · factor ) + base_3d_noise`。
- 前半部分是 **2D 低频场驱动的“竖直密度剖面”**：每根 (x,z) 柱子有自己的地表高度（`offset`）、陡峭度（`factor`）、山顶锯齿（`jaggedness`）。
- 后半部分 `base_3d_noise` 是整个地形里**唯一的 3D 噪声**，只负责在地表附近“撕开”悬崖、拱门、悬挑。
- 关键在于乘法：**`factor` 乘在 `depth` 上**，它决定 3D 噪声能影响多大的高度范围。
- `quarter_negative` 让空气一侧的坡度比实心一侧缓 4 倍，噪声因此更容易在地表之上“撑出”实心。

## 完整公式

![sloped_cheese 的节点树](/qmx-Gameknowledge/assets/mc-source/12-sloped-cheese-tree.png)

把树写成公式：

```text
offset     = -0.50375 + spline_offset(continents, erosion, ridges_folded)
factor     = spline_factor(continents, erosion, ridges, ridges_folded)
jaggedness = spline_jaggedness(continents, erosion, ridges, ridges_folded)

depth      = yClampedGradient(y: -64 → 320, 值: 1.5 → -1.5) + offset
X          = (depth + jaggedness · half_negative(jagged_noise)) · factor
sloped_cheese = 4 · quarter_negative(X) + base_3d_noise
```

其中橙色节点（`offset / factor / jaggedness / continents / …`）都被包在 `flat_cache` 里：**它们只依赖 (x,z)，每 4×4 格算一次**。只有 `yClampedGradient` 和 `base_3d_noise` 随 y 变化。

## 第 1 步：只有 yClampedGradient —— 一个无限平坦的世界

最基础的竖直密度就是一条随 y 递减的直线：

```text
g(y) = clampedMap(y, -64, 320, 1.5, -1.5)      // y=-64 时 1.5，y=320 时 -1.5，中间线性
```

`g(y) > 0` 的地方是实心。它在 `y = 128` 处过零，所以世界是“y<128 全是石头”的平面。这是所有后面步骤的底板。

## 第 2 步：加 offset —— 每根柱子的地表高度不同

![depth = 渐变 + offset，depth=0 就是地表](/qmx-Gameknowledge/assets/mc-source/03-depth-offset-surface.png)

把一个只依赖 (x,z) 的偏移量加到渐变上：`depth(x,y,z) = g(y) + offset(x,z)`。`depth` 在哪个 y 过零，那里就是这根柱子的地表。

左图每条线是一个 offset 值，圆点是过零点。推导：

```text
g(y) + offset_total = 0
→ y = -64 + (1.5 + offset_total) · 128        // 渐变斜率是 3/384 每格，即 128 格 = 1.0
offset_total = spline − 0.50375
→ y = 63.5 + 128 · spline                      // 右图
```

这就解释了为什么 `GLOBAL_OFFSET = -0.50375`：它把“样条输出 0”对齐到海平面附近（y ≈ 63.5，海平面是 63）。样条于是可以用“以海平面为 0 的相对量”来设计，每增加 1.0 就升高 128 格。

这一步已经能得到起伏的地形，但**每根柱子只有一个地表高度，不会有悬崖、拱门，也没有洞穴**。这就是你最早手搓的“深度图扩展成高度”的做法。

## 第 3 步：乘 factor —— 决定 3D 噪声有多大话语权

要让地形不只是“一个高度图”，就要往密度里加 3D 噪声。问题是：噪声加多大？加在哪？

如果直接 `density = depth + noise`，噪声的影响范围是固定的，平原和山地没法区别对待。Minecraft 的做法是把 `depth` **乘以 `factor`** 再加噪声：

```text
density ≈ factor · depth + noise
```

`depth` 每走一格变化 3/384 ≈ 0.0078，乘上 `factor` 之后，密度随高度的变化速度就是 `factor × 0.0078` 每格。3D 噪声幅度大约 ±0.3，所以噪声能把地表挪动的距离是：

```text
挪动距离 ≈ 噪声幅度 ÷ (每格密度变化) = 0.3 ÷ (factor · 0.0078)
```

![噪声带宽度 vs factor](/qmx-Gameknowledge/assets/mc-source/08-factor-noise-band.png)

左图：纵轴是 y，横轴是噪声叠加前的密度。黄带是噪声能改变的范围，曲线穿过黄带的 y 区间就是“被噪声支配的高度带”。`factor` 越大（青线），曲线越陡，穿过黄带的高度越短，噪声几乎改不动地表。`factor` 越小（红线），曲线越平缓，同样的噪声可以把地表搬动几十格。右图把这个宽度画成了 `factor` 的函数。

下面是对应的真实剖面（上排）：

![同一份噪声，不同 factor](/qmx-Gameknowledge/assets/mc-source/07-factor-and-quarter-negative.png)

`factor = 6.25`（海岸平原那一档）地表平整，噪声只是让它微微起伏；`factor = 3` 略有起伏；`factor = 1.5` 开始出现明显的高低差；`factor = 0.7` 出现悬崖，甚至一块孤立的浮空小岛。

**这就是 `factor` 的真实含义：“这片地区允许 3D 噪声破坏多少”。** 海岸、平原用大 `factor`（4~6），保证平整；山地用小 `factor`，让噪声塑造悬崖。

## 第 4 步：用 quarter_negative 让空气一侧更“松”

上面那张图的下排是**去掉 `quarter_negative`** 的对照：地表在 `factor` 较小时也明显更平，没有悬挑和浮岛。

`4 · quarter_negative(X)` 是一个不对称的放大：

| X 的符号 | 含义 | 变换 | 每格密度变化（相对） |
| --- | --- | --- | --- |
| X > 0 | 地表之下（实心一侧） | `4·X` | `4 · factor · 0.0078` |
| X < 0 | 地表之上（空气一侧） | `4·0.25·X = X` | `1 · factor · 0.0078` |

实心一侧陡 4 倍，空气一侧缓。结果是：

| factor | 噪声改变实心侧地表的距离 | 噪声在空气侧撑出实心的最大高度 |
| --- | --- | --- |
| 6.25 | 约 1.5 格 | 约 6 格 |
| 4 | 约 2.4 格 | 约 10 格 |
| 2 | 约 5 格 | 约 19 格 |
| 1 | 约 10 格 | 约 38 格 |
| 0.7 | 约 14 格 | 约 55 格 |

（按噪声幅度 ±0.3 估算。）也就是说：**噪声可以让实心体向上伸出很高，但很难在地表以下挖出空洞。** 地表之下 4 倍陡的斜率把噪声“压住”，所以山体内部是实的；地表之上的斜率缓，才有悬崖、拱门、浮岛。想要内部的洞穴，由后面专门的洞穴函数负责（第 6 页）。

## 第 5 步：jaggedness —— 只给山顶加锯齿

```text
depth' = depth + jaggedness · half_negative(jagged_noise)
```

`jagged` 是一个**只依赖 (x,z)** 的噪声（`xz_scale = 1500, y_scale = 0`，16 个 octave，最低频率也只有约 43 格一个周期），值域约 ±1.1。它被 `half_negative` 处理：负值只剩一半，正值保持原样。再乘 `jaggedness`（山谷里是 0，只有内陆低侵蚀山峰才有，最大约 0.3~0.63）加到 `depth` 上。

换算成方块：`depth` 每 1.0 是 128 格，所以 `0.3 × 1.1 ≈ 0.33` 约等于**把山顶地表抬高 40 多格的尖刺**。平原、河谷因为 `jaggedness = 0`，这一项完全消失。

> 这里还有一个设计细节：锯齿是加在 `depth` 里的（乘 `factor` 之前），不是直接加在最终密度上。因此它同样会被 `factor` 放大或压制，在海岸附近 `factor` 大，锯齿就算存在也不会造成破碎。

## 第 6 步：base_3d_noise —— 唯一的 3D 噪声

最后加上 `old_blended_noise`（数据里叫 `overworld/base_3d_noise`）：

```json
{ "type": "minecraft:old_blended_noise",
  "xz_scale": 0.25, "y_scale": 0.125, "xz_factor": 80.0, "y_factor": 160.0,
  "smear_scale_multiplier": 8.0 }
```

它是三组 Perlin 噪声的“选择器式混合”（第 7 页详讲）：`main` 噪声先算出一个混合系数 `q`（实际作用时被夹到 0~1），再在 `min` 与 `max` 两组噪声之间插值。移植版统计的结果是 95% 的取值落在 ±0.28 以内，标准差约 0.15，这就是前面一直用“±0.3”的来源。

它名字里的 *old* 说明这是沿用旧版地形的混合噪声算法（源码没有注释具体原因）。读源码时可以把它当黑盒：**输入三维坐标，输出一个均值接近 0、幅度约 0.3 的噪声**，具体算法放到第 7 页再看。

## 把六步拼在一起

![完整剖面：低频场 → 样条 → 地形](/qmx-Gameknowledge/assets/mc-source/09-transect-pipeline.png)

这是用移植算法对 6000 格长的 x 方向剖面（z=0）的计算，图自上而下：

1. **三个低频场**：`continents`（蓝）、`erosion`（绿）、`ridges`（红）。它们变化缓慢，最短的特征也有数百格。
2. **offset 样条**：平台段（-0.2222、-0.12）对应海底；爬升段对应陆地与山脉。右轴是对应的基础地表高度。
3. **factor 与 jaggedness**：`factor` 在海区是常数 3.95，海岸处升到 6 以上，x≈3500 附近的内陆山区降到 1 以下（那里地形最“松”）；`jaggedness` 只在最左边的山脉（x<600）非零。
4. **剖面**：灰色是实心，蓝色是海平面（y=63）以下的水，绿线是地表。左侧 x<1000 的山脉最高接近 y=220，中间的海洋与低地平整，x≈3500 附近有一座起伏更碎的小山。

注意这张图**没有洞穴**，只是 `sloped_cheese` 加了 `slide`（顶部封顶）。洞穴在下一页叠上去。

## 你的笔记 vs 源码：逐项核对

下面是你笔记（`y 轴渐变`、`小记`）里的内容与源码的核对。大部分是对的，少数地方需要修正。

| 笔记里的说法 | 源码实际 | 结论 |
| --- | --- | --- |
| `YBase = YGradient(Y)`，`yClampedGradient(-64, 320, 1.5, -1.5)` | 完全一致 | ✔ |
| `Offset = Spline(Continents, Erosion, Ridges)` | 第三个坐标是 **`ridges_folded`**（折叠后的山谷/山峰），不是原始 `ridges` | 需修正 |
| `TerrainBase = YBase + Offset + Jaggedness × HalfNegative(JaggedNoise)` | 一致（即 `depth + jaggedness·half_negative(jagged)`），另外 `offset` 里还含有 `-0.50375` | ✔（补一个常数） |
| `ScaledTerrain = Factor × TerrainBase` | 一致 | ✔ |
| `SlopedCheese = 4 × QuarterNegative(ScaledTerrain)` | 一致，**还要再加上 `base_3d_noise`** | ✔ |
| `FinalDensity = SlopedCheese + Base3DNoise` | 这个和是 **`sloped_cheese` 本身**；真正的 `final_density` 还包含 `slide`、洞穴、`squeeze` 等（第 6 页） | 命名需修正 |

阶段小记里画的树：

```text
finalDensity
├── min
│   ├── terrainDensity (yClampedGradient, offsetSpline, factorSpline, jaggednessSpline, baseNoise)
│   └── caveDensity (spaghettiNoise, pillarNoise, caveModifiers)
└── blendDensity
```

和源码的差别：

| 小记里的写法 | 源码实际 |
| --- | --- |
| `min(地形, 洞穴)` 是两个并列项 | 洞穴不是和地形并列的 `min`，而是 `range_choice` 的**另一个分支**：只有当 `sloped_cheese ≥ 1.5625`（够深的实心区）才去算洞穴。顶层的 `min` 另一边是 `noodle` |
| `blendDensity` 是与 `min` 并列的 | `blend_density` 是**包在里面**的一层（与旧区块融合），新世界里等于恒等 |
| 未提 | 外面还有 `slide`（封顶封底）、`× 0.64` 和 `squeeze` |
| 最早的版本：“密度 = 山地项 + 细节噪声 + 垂直渐变 × 35” | 源码是 **乘法**：`factor × depth`，渐变不是一个固定系数 |
| “准备分型并且做多噪声的混合” | `old_blended_noise` 本身就是多噪声混合（min / max / main 三组），并且有 y 方向的“涂抹”平台效果 |

## 为什么你的图“上空非常乱”

你笔记里在加了样条之后写到：“现在有点摸样了，但是可以看到上空非常乱”。我没有看到你的实现代码，但结合上面的分析，一个很可能的原因是**“空气侧的每格密度变化”和“3D 噪声幅度”不匹配**。用这个小检查：

```text
空气侧能被噪声撑出实心的最大高度 ≈ 噪声幅度 ÷ (factor · 0.0078)
```

如果这个数大到几十上百格，天空里就会漂着碎块。对照源码，有几条解法：

1. **把噪声幅度和 depth 的单位对齐。** `depth` 的 1.0 = 128 格，噪声幅度要约 0.3 才与之协调。如果你的 3D 噪声幅度大了一个数量级，空中就会乱。
2. **提高 factor。** 平原、海岸、海洋用 4~6；只有真正想要悬崖的山地才降到 1 以下。
3. **加顶部封顶。** 源码的 `slide` 在 y=240~256 之间把密度拉向 -0.078（空气），把世界上缘封死，漂在高空的碎块无法延伸到顶（第 6 页）。
4. **别把 `quarter_negative` 的四分之一搬错方向。** 它缩小的是**负半边**（空气侧）；放反了就会变成“地表之下被噪声掏空”。

## 在 Unity 里复刻的顺序

| 步骤 | 做什么 | 验证方式 |
| --- | --- | --- |
| 1 | `depth = g(y) + offset(x,z)`，offset 先给常数 | 剖面应该是一条水平地表线 |
| 2 | `offset` 换成 `spline(continents)` | 剖面出现“海—岸—陆”的台阶（对照图 05 左图） |
| 3 | 乘 `factor`（先常数 4） | 地形不变，但密度梯度变陡；做个“显示 density”的调试视图 |
| 4 | 加 `4·quarter_negative` | 仍不变；地表上下两侧斜率不同 |
| 5 | 加 3D 噪声，幅度 ±0.3 | 地表出现小起伏，`factor` 调小时出现悬崖（对照图 07） |
| 6 | `factor` 换成 `spline(continents, erosion, …)` | 平原平整、山地粗犷；用热力图（图 06）检查接缝 |
| 7 | 加 `jaggedness` | 只有山顶出现尖刺 |

每一步都应该能单独关掉，并有一个明确的肉眼可见的验证。**不要同时调所有参数。**

## 小结

- `sloped_cheese` 的骨架是 `4·qn((depth + jag·hn(jagged))·factor) + noise3d`。
- `depth` 的零点是地表，`offset` 每 1.0 = 128 格；`GLOBAL_OFFSET` 把 0 对齐到海平面。
- `factor` 乘在 `depth` 上，决定 3D 噪声的话语权；`quarter_negative` 让空气侧更松、实心侧更紧。
- 3D 噪声只做扰动，地表的形状由 2D 低频场通过样条决定。

## 自测

1. `offset = 0.5` 时，基础地表大约在哪个 y？
2. 为什么平原地区 `factor` 取大值？
3. 如果去掉 `quarter_negative`，山地的剖面会发生什么变化？
4. 为什么海岸线附近需要比内陆更大的 `factor`？

参考答案：① `63.5 + 128 × 0.5 ≈ 127`。② 大 `factor` 让密度随高度变化陡，3D 噪声只能把地表挪 1~3 格，地面保持平整。③ 空气侧坡度变陡 4 倍，噪声很难在地表之上撑出实心，悬崖、拱门、悬挑会明显减少（图 07 下排）。④ 海岸要平整，才能形成稳定的海滩，不会被 3D 噪声搅乱海陆交界。

