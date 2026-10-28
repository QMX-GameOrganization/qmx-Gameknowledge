---
title: "2.4 骨骼合成与 Blender 坐标补偿"
description: 局部 TRS 如何合成全局姿态、蒙皮矩阵的两个乘法顺序，以及导入 Blender 时为什么必须做 rest 补偿和坐标轴转换。
sidebar:
  order: 4
---

> 适用版本：Dying Light 1.55.0.0。依据 `DL1/Notes/DL1动画格式逆向.md` 第四到七节。矩阵约定均为列向量。

## 要点

- 骨架数据来自网格节点：本地矩阵、逆绑定矩阵 `Reference`、父索引三样东西。
- 蒙皮矩阵 = 动画后的全局矩阵 × `Reference`。`Reference` 直接用原始数据，不要重新求逆。
- Blender 会重建 edit bone 的 rest 轴，不能把 ANM2 的局部 TRS 直接写进 pose bone，必须做补偿。
- 未被任何动画轨道驱动的辅助骨也必须保留，否则父子层级会断。

## 骨架数据

网格节点 +0 是 3×4 本地矩阵（平移在第四列），+48 是全局逆绑定矩阵 `Reference`，+198 是父索引（65535 为根）。

合成规则：

```text
Global[i] = Global[parent(i)] × Local[i]          // 列向量约定
Skin[i]   = AnimatedGlobal[i] × Reference[i]
v'        = Σ weightₖ · Skin[boneₖ] · v           // 线性混合蒙皮
```

动画用在哪里：匹配到轨道的骨骼，用轨道里的 TRS 替换绑定姿态的局部矩阵；没匹配的骨骼保留绑定局部矩阵。然后自父到子递推全局矩阵。

校验：Jade 的 206 个节点，`BindGlobal × Reference` 对单位矩阵的最大元素误差为 1.46e-6，静止姿态高度 1.82 m 与包围盒一致。这个检查成立，才说明 `Reference` 确实是全局逆绑定矩阵，可以直接使用。

## 为什么 Blender 需要补偿

Blender 在创建 edit bone 时会重建每根骨骼自身的 rest 轴，导致它的 rest 全局矩阵与原始绑定全局矩阵不同。记：

- `R` 原始绑定全局
- `G` 动画后的全局
- `B` Blender 的 rest 全局

目标是让 Blender 里每根骨骼的最终全局姿态 `D = G × inverse(R) × B`。写入 `matrix_basis` 时：

```text
子骨：matrix_basis = inverse(B_child) × B_parent × inverse(D_parent) × D_child
根骨：matrix_basis = inverse(B_root) × D_root
```

这里的含义很直观：`G × inverse(R)` 是“相对绑定姿态的变化”，乘上 `B` 把这个变化叠到 Blender 自己的 rest 上，再按父子关系求出相对父骨的局部变换。

## 坐标系转换

DL1 的 (x, y, z) 转成 Blender 的 (x, −z, y)。顶点用 `C × v`，矩阵用 `C × M × inverse(C)`。矩阵必须做相似变换，只对平移分量换轴是不够的。

## 保留全部节点

工具保留全部 206 个 entity，包括没有动画轨道的辅助骨。理由笔记写得很清楚：不能只保留有动画轨的骨骼，否则未匹配辅助骨会失去父层级。另一个细节是：对只检查“实际变形骨引用”的原 `Reference`，未变形的辅助节点使用层级逆矩阵（hierarchy inverse）构造 Blender rest。

## 双角色场景的 MotionAccumulator

处决动画由两个角色配对，场景里的位置由特殊轨 MotionAccumulator 给出。规则是：

```text
G_scene = MotionAccumulator × G_bone    // 完整保留旋转、平移、缩放，且只应用一次
```

样本中背后快速处决攻击者的 Motion 恒为单位矩阵，受害者平移为 (0, 0, 0.79999995)；肘击攻击者旋转 Cayley 约为 (0.00157, 0.99843, −0.00157)、平移 (−0.02875, 0, 1.3015)，受害者平移 (0, 0, 0.5)。这些数值在 3.3 节还会用到。

## 验证数据

| 项 | 结果 |
| --- | --- |
| Blender 与独立 CPU LBS 全帧最大坐标分量差 | 2.90e-6 m |
| 独立读取 GLB 实际缓冲，最大欧氏位置差 | 8.03e-5 m，沿用既定 1e-4 m 阈值 |
| 验证器检查 | 真实 mesh node.skin 指向活跃场景、骨名、UV、权重、原始 ANM Cayley 逐帧结果 |

## 值得学的点

- **相似变换换轴**。跨引擎导入时，位置换轴简单，矩阵必须 `C·M·C⁻¹`。这是常见 bug 的源头。
- **用 rest 补偿代替改写 rest**。不改 Blender 内部的 rest，而是在 pose 端补偿，保持了工具的可预测性。
- **对 `Reference` 的信任来自测试**，而不是来自命名。

## 常见坑

- 把 `Reference` 当局部逆矩阵或自己重算。应直接用节点 +48 的原始数据。
- 双角色处决时，对 MotionAccumulator 重复应用，或对它用普通骨名哈希。
- 把采样帧通过当作所有时刻插值一致：笔记明确说，非采样时刻与原引擎是否一致没有证明。

## 参考资料

- `DL1/Notes/DL1动画格式逆向.md`（第四到八节）
- `DL1/Tools/DL1Blender/`（build、pair、validation 脚本）
