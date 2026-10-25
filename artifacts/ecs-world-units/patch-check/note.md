---
title: "00.2 世界单位、网格坐标与方向约定"
description: "从 shapez.io 源码确认像素、格子、建筑锚点、旋转和运输距离，并制定 Unity ECS 实践的阶段 0。"
sidebar:
  order: 2
---

## 先明确：原项目没有米制世界

shapez.io 是二维游戏。它把建筑布局的格坐标、绘制用的像素世界坐标、相机转换后的屏幕坐标分开；传送带内部距离又以格为单位。

因此，“1 Unity Unit = 1 米、1 格 = 1 米”是我们迁移到 Unity 时可选的项目规范，不是 shapez.io 的原始设定。此前建议的“世界原点对应格中心”也不同于原项目，不能直接与原项目的坐标转换公式混用。

本文核对版本：`tobspr-games/shapez.io`，提交 `8a79de5255fb6756f3a1d26579b1e9bc36e0c811`（2026-10-25 核对）。下面的链接固定到该提交。

## 1. 三种空间与两种长度单位

| 空间或数值 | 原项目的表示 | 用途 |
| --- | --- | --- |
| 格空间 Tile Space | 建筑占用位置使用整数 `(x, y)` | 建筑布局、占地、端口和地图查询 |
| 像素世界空间 World Space | 每格 32 像素；可使用小数 | 精灵绘制、相机位置、世界范围 |
| 屏幕空间 Screen Space | 相对游戏视口的屏幕位置 | 鼠标输入和最终显示 |
| 传送带内部距离 | 以格长为单位的连续数值 | 路径长度、物品间距、沿路径运动 |

注意：Tile Space 不代表任何向量都只能取整数。传送带绘制也会使用格空间中的小数坐标；整数限制主要用于建筑占地和地图索引。

[`core/config.js`](https://github.com/tobspr-games/shapez.io/blob/8a79de5255fb6756f3a1d26579b1e9bc36e0c811/src/js/core/config.js#L49) 中的配置是：

```js
tileSize: 32,
halfTileSize: 16,
mapChunkSize: 16,
beltSpeedItemsPerSecond: 2,
itemSpacingOnBelts: 0.63,
```

`mapChunkWorldSize = mapChunkSize * tileSize`，所以一个地图块为 16×16 格，对应 512×512 个世界像素单位。`assetsDpi` 是素材分辨率配置，不应拿来改变逻辑格子尺寸。

## 2. 格坐标原点在左上角，中心另加半格

[`core/vector.js`](https://github.com/tobspr-games/shapez.io/blob/8a79de5255fb6756f3a1d26579b1e9bc36e0c811/src/js/core/vector.js#L336) 提供统一转换：

```text
toTileSpace:                 (floor(worldX / 32), floor(worldY / 32))
toWorldSpace:                (tileX * 32, tileY * 32)
toWorldSpaceCenterOfTile:    (tileX * 32 + 16, tileY * 32 + 16)
snapWorldToTile:             (floor(worldX / 32) * 32, floor(worldY / 32) * 32)
```

例如：

| 输入 | 结果 |
| --- | --- |
| 格 `(0, 0)` 转世界左上角 | `(0, 0)` |
| 格 `(0, 0)` 转世界中心 | `(16, 16)` |
| 格 `(2, 3)` 转世界中心 | `(80, 112)` |
| 世界 `(-1, -1)` 转格 | `(-1, -1)` |
| 世界 `(32, 0)` 转格 | `(1, 0)` |

每格包含左、上边界，不包含右、下边界。负坐标必须向下取整：`floor(-1 / 32) = -1`。C# 直接转 `int` 会向零截断，不能照此代替 `floor`。

[`game/camera.js`](https://github.com/tobspr-games/shapez.io/blob/8a79de5255fb6756f3a1d26579b1e9bc36e0c811/src/js/game/camera.js#L374) 则负责：

```text
screenToWorld = (screen - viewportSize / 2) / zoomLevel + cameraCenter
worldToScreen = (world - cameraCenter) * zoomLevel + viewportSize / 2
```

鼠标选格的顺序是“屏幕 → 世界 → 格子”。缩放只影响显示与输入转换，不改变建筑占地或物流长度。

## 3. 方向与旋转：二维 Y 向下，正 90° 看起来顺时针

[`enumDirectionToVector`](https://github.com/tobspr-games/shapez.io/blob/8a79de5255fb6756f3a1d26579b1e9bc36e0c811/src/js/core/vector.js#L685) 定义：

| 方向 | 格偏移 |
| --- | --- |
| top | `(0, -1)` |
| right | `(1, 0)` |
| bottom | `(0, 1)` |
| left | `(-1, 0)` |

`Vector.rotateFastMultipleOf90` 的正 90° 变换为 `(x, y) → (-y, x)`。因此 top 经过正 90° 变成 right。在 Y 向下的二维画面中表现为顺时针。

迁移到 Unity XZ 平面时应先确定方向映射，再实现统一转换；不要直接把二维角度套进 Unity 欧拉角后凭视觉修补。

## 4. 建筑锚点、占地和端口共用局部坐标

[`StaticMapEntityComponent`](https://github.com/tobspr-games/shapez.io/blob/8a79de5255fb6756f3a1d26579b1e9bc36e0c811/src/js/game/components/static_map_entity.js) 保存 `origin`、`rotation`、`originalRotation`、`code`。尺寸由 `getTileSize()` 根据建筑代码获取。

- 未旋转时，`origin` 是建筑左上角的锚点格。
- `rotation` 必须是 90° 的整数倍，边界计算支持 0、90、180、270°。
- `localTileToWorld(localTile)` 先旋转局部格坐标，再加 `origin`。这里的方法名 World 指全局格坐标，并没有乘 32。
- `worldToLocalTile(worldTile)` 先减 `origin`，再逆旋转。
- `localDirectionToWorld` 和 `worldDirectionToLocal` 对端口方向使用同一套旋转规则。
- 绘制旋转中心为锚点格的中心，不是整栋多格建筑的几何中心。

旋转后 `origin` 不一定仍是包围盒左上角。`getTileSpaceBounds()` 对宽 `w`、高 `h` 的建筑计算如下：

| 旋转 | 包围盒左上角 | 包围盒尺寸 |
| --- | --- | --- |
| 0° | `(ox, oy)` | `(w, h)` |
| 90° | `(ox - h + 1, oy)` | `(h, w)` |
| 180° | `(ox - w + 1, oy - h + 1)` | `(w, h)` |
| 270° | `(ox, oy - w + 1)` | `(h, w)` |

例如 2×3 建筑以 `(5, 5)` 为锚点，正 90° 旋转后，包围盒左上角为 `(3, 5)`，尺寸为 3×2。不能只交换宽高而保持左上角不变。

输出端口也遵循此约定：[`ItemEjectorComponent.getSlotTargetLocalTile`](https://github.com/tobspr-games/shapez.io/blob/8a79de5255fb6756f3a1d26579b1e9bc36e0c811/src/js/game/components/item_ejector.js#L85) 返回 `slot.pos + directionVector`，再结合建筑变换定位目标格。接收口的方向表示“从哪一侧接收”，输出口表示“向哪一侧输出”；[`findMatchingSlot`](https://github.com/tobspr-games/shapez.io/blob/8a79de5255fb6756f3a1d26579b1e9bc36e0c811/src/js/game/components/item_acceptor.js#L110) 会反转输出方向进行匹配。

## 5. 传送带长度按格计算，吞吐与移动速度分开理解

[`components/belt.js`](https://github.com/tobspr-games/shapez.io/blob/8a79de5255fb6756f3a1d26579b1e9bc36e0c811/src/js/game/components/belt.js) 的 `getEffectiveLengthTiles()` 返回：

- 直线段：`1.0` 格。
- 弯道：`curvedBeltLength = 0.78` 格。源码保留了 `Math.PI / 4` 注释，但实际使用 0.78，不是精确圆弧长度。

弯道半径是半格；`transformBeltToLocalSpace` 将沿路径距离变成格中心附近的局部坐标。它的参数对弯道取值为 `0..0.78`，不能把所有带段都当作 `0..1` 的归一化进度。

[`BeltPath.computeTotalLength`](https://github.com/tobspr-games/shapez.io/blob/8a79de5255fb6756f3a1d26579b1e9bc36e0c811/src/js/game/belt_path.js#L1117) 累加每段的格长度。`update()` 中实际单步移动距离为：

```text
distancePerTick = getBeltBaseSpeed() × deltaSeconds × itemSpacingOnBelts
               = 吞吐量(件/秒) × 秒 × 间距(格/件)
               = 格/步
```

源码旁边的注释写着 Divide，但实际表达式是乘法，应以表达式为准。以基础配置的 2 件/秒和 0.63 格间距为例，移动速度为 1.26 格/秒；升级后的实际吞吐使用 `getBeltBaseSpeed()` 返回值。

在绘制阶段，格空间位置才通过 `toWorldSpaceCenterOfTile()` 转为世界像素位置。不要把 32 像素/格再乘进模拟移动距离。

## 6. Unity 实践的阶段 0：先定规范，再实现生产链

下面是迁移建议，不是 shapez.io 源码。为便于对照原项目，建议保留“格角点原点 + 半格中心偏移”，替换此前“原点位于格中心”的初始建议。

| 项目 | 本项目建议 |
| --- | --- |
| 物理尺度 | 1 Unity Unit = 1 米；初始 `CellSize = 1` 米/格 |
| 逻辑平面 | `int2(gx, gy)`，右为 `+gx`，下为 `+gy` |
| Unity 平面 | XZ；参考原点 `O` 对应逻辑 `(0,0)` 格的左上角 |
| 方向映射 | top → +Z；right → +X；bottom → -Z；left → -X |
| 建筑位置 | 保存锚点格和离散朝向；Transform 由统一转换生成 |
| 路径距离 | 第一版统一用格，速度用格/秒；显示时乘 `CellSize` |
| 配方与统计 | 生产时间用秒，吞吐用件/秒 |
| 模拟时间 | 第一版建议固定 1/30 秒；shapez.io 使用 dynamicTickrate，不是这一固定参数 |

若 `O = (Ox, Oy, Oz)`、格长 `s > 0`，地面格中心转换为：

```text
GridToWorldCenter(gx, gy) = (Ox + (gx + 0.5) * s, Oy, Oz - (gy + 0.5) * s)
WorldToGrid(x, z)        = (floor((x - Ox) / s), floor((Oz - z) / s))
```

由于逻辑第二轴映射到 -Z，边界归属按逻辑格轴定义；应直接测试公式，不要沿用另一种 Z 轴方向的边界假设。若最终选择用米存储路径距离，则必须同时转换长度、间距和速度，不能只改其中一个字段。

阶段 0 的任务顺序：

1. 固定 `CellSize`、地图原点、轴向、格边界归属、锚点和旋转规则。
2. 实现统一的 `GridToWorldCenter`、`WorldToGrid`、格偏移旋转、方向旋转及逆变换。
3. 实现多格建筑占地与局部端口转换，使用同一个锚点。
4. 制作调试场景，显示格号、锚点、占地和端口方向。
5. 验收后进入《09.1 最小生产链实践路线》的单链阶段。

验收清单：

- `(0,0)`、正坐标、负坐标的格中心往返转换保持一致。
- 格边界及边界两侧的微小偏移落到约定的格子。
- 2×3 建筑在四种朝向下的占地正确；四次 90° 旋转后回到原状。
- 端口位置和朝向随建筑一起旋转，相邻端口的匹配结果与画面一致。
- 修改 `CellSize` 后，建筑显示和路径世界长度同比缩放，逻辑占地、格/秒速度与理论吞吐保持不变。

本文仅核对源码和给出实施规范；上述 Unity 工具与场景验收仍需实际开发执行。
