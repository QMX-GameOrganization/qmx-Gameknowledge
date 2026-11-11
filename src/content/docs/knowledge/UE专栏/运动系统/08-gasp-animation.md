---
title: "8. GASP：翻越、根运动与动画"
description: "沿实际 GASP 蓝图区分翻越检测、Chooser、Motion Matching、Warp Targets 和两种 Montage 执行路径。"
sidebar:
  order: 8
---

## 翻越是一条跨系统链

`AC_TraversalLogic` 不只是播放动画。其 `TryTraversalAction` 图包含环境查询、翻越结果构造、角色属性获取、动作选择与执行入口。

```text
角色提供 Traversal 属性
  → 环境检测与障碍信息
  → Chooser 选择动作及相关结果
  → 配置 Warp Targets
  → 按 CMC / Mover 执行动作
  → 回调中恢复运动与碰撞相关状态
```

这是对图中阶段的归纳，不表示每个分支都完整执行所有阶段。检测失败、没有选到 Montage 和正常执行是不同结果，图中也有不同的返回节点。

## 检测：动作能否成立

`TryTraversalAction` 可见 Capsule Trace、对 `LevelBlock_Traversable` 的 Cast、`GetLedgeTransforms` 以及后续空间检测。结果字段包括前缘、后缘、后方地面是否存在，以及障碍高度、深度等。

样例依赖它支持的可翻越场景对象和几何约定。不能因为它有胶囊体扫描，就认为任意网格、任意可动物体都能直接获得稳定翻越。

调试时先检查环境结果，再查动画选择。角色根本没有检测到有效前缘时，反复调整 Montage 混合时间不会解决问题。

## 选择：Chooser 不等于 Motion Matching

该图中存在 `CHT_TraversalMontages_CMC` 与 `CHT_TraversalMontages_Mover` 的 Evaluate Chooser 节点，表明样例为不同运动路径配置了动作选择。

Chooser 根据配置的条件和上下文选择结果；Pose Search / Motion Matching 使用姿态和轨迹等特征进行匹配。它们可以配合，但不能将“运行 Chooser”直接称为“执行一次运动匹配”。具体表格条件和数据库 Schema 本轮未逐行导出。

## 对齐：Warp Target 是空间约束

`SetWarpTargets` 中可读到三个命名目标：`FrontLedge`、`BackLedge`、`BackFloor`。图中调用 `AddOrUpdateWarpTargetFromLocationAndRotation`，也会按分支移除不适用的目标。

还可见按 Warp Target 查询动画窗口，以及读取 `Distance_From_Ledge` 曲线的逻辑。这说明对齐不仅需要“有一个目标点”，还依赖动作窗口、动画数据和障碍几何。

Motion Warping 修正受支持窗口内的根运动以对齐目标，不会自动保证碰撞可行，也不是脚部 IK 的替代品。手穿墙、胶囊体穿障碍、落脚偏差分别需要从约束、运动与姿态层排查。

## 执行：两条实际连线

`AC_TraversalLogic.EventGraph` 中已核对以下直接执行引脚：

| 事件 | then 连接到 |
| --- | --- |
| `PerformTraversalAction_CMC` | `K2Node_PlayMontage_0`：普通播放 Montage 节点 |
| `PerformTraversalAction_Mover` | `K2Node_PlayMontageOnMoverActor_0`：Mover Actor 播放 Montage 节点 |

Mover 分支还有请求 `Traversing` 模式以及条件恢复 `Walking` 的节点；角色模式表里 `Traversing` 映射原生 FlyingMode。这是用现有运动规则承接翻越阶段的具体配置。

CMC 分支则有设置 CMC 移动模式、调整碰撞响应和复制行为的节点。复制相关函数还包括服务器/客户端事件入口，但单凭静态图不能证明各网络角色、打断路径和异常路径都正确恢复。

因此迁移时不能把普通 Montage 播放节点原封不动替换后就结束。必须检查根运动如何进入模拟、模式何时改变、打断时恢复哪些状态，以及网络重复执行时副作用如何处理。

## 动画：共同接口，不同轨迹入口

| 图 | CMC AnimBP | Mover AnimBP |
| --- | --- | --- |
| `Update_PropertiesFromCharacter` | GetOwningActor → Get_PropertiesForAnimation | 同样通过接口读取，并另取 Ragdoll 属性 |
| `Update_Trajectory` | `Pose Search Generate Trajectory (for Character)`，并有 `HandleTrajectoryWorldCollisions` | `Pose Search Generate Trajectory (using Predictor)` |
| `Update_MotionMatching` | Chooser `CHT_PoseSearchDatabases` → ValidDatabases / SetDatabasesToSearch | Chooser `CHT_PoseSearchDatabases_Relaxed` → 对应数据库设置 |

Mover 的轨迹调用使用 Predictor 接口；具体 Predictor 对象的创建与参数需要沿配置和调用继续确认，不能仅由节点名认定全部设置。数据库选择之后如何采样和混合姿态，还要继续看 AnimGraph 与动画节点本身。

**自测：** 翻越播放了正确动画却落在错误位置，应先检查什么？先比对检测出的边缘变换、Warp Target 名称、Montage 窗口和根运动执行路径；不要先换一套 Pose Search 数据库。

下一章：[调试实验与迁移](/qmx-Gameknowledge/knowledge/ue专栏/运动系统/09-labs/)。
