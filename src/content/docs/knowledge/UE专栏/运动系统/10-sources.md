---
title: "10. 源码索引与证据范围"
description: "记录本系列使用的引擎版本、源码入口、蓝图读取方法及尚未执行的运行验证。"
sidebar:
  order: 10
---

## 研究对象与版本

- 引擎：`5.8.4-58902052+++UE5+Release-5.8`，从本机 `Engine/Build/Build.version` 读取。
- 工程：本地“游戏动画示例”的 GASP 内容；不是从最新线上版本反推。
- 日期：2026 年 11 月 11 日。
- 范围：源码静态阅读、蓝图结构与引脚连接读取、知识库构建。未进行 PIE、联机正确性或性能实测。

工程自定义 C++ 模块目前是模板 Actor，不包含本专题讨论的移动实现。重点对象是引擎模块和 `/Game/Blueprints` 中的蓝图。

## CMC 索引

以下路径相对引擎安装根目录。行号用于本机本版快速定位；换版本时以符号名为准。

| 文件 | 符号 | 本版行号 |
| --- | --- | --- |
| `Engine/Source/Runtime/Engine/Private/Components/CharacterMovementComponent.cpp` | TickComponent | 1650 |
| 同上 | PerformMovement | 2772 |
| 同上 | StartNewPhysics | 3531 |
| 同上 | PhysFalling | 4887 |
| 同上 | PhysWalking | 5653 |
| 同上 | ClientUpdatePositionAfterServerUpdate | 8606 |
| 同上 | ReplicateMoveToServer | 8907 |

对应头文件：`Engine/Source/Runtime/Engine/Classes/GameFramework/CharacterMovementComponent.h`。继续搜索 `FSavedMove_Character`、`FCharacterNetworkMoveData`、`ServerMove_PerformMovement` 和根运动处理，而不是只阅读 Tick。

## Mover 索引

以下路径相对 `Engine/Plugins/Experimental/Mover/Source/Mover/`。

| 文件 | 重点 |
| --- | --- |
| `Public/MoverComponent.h`、`Private/MoverComponent.cpp` | 输入生产、模式表、后端、Finalize 与回滚通知 |
| `Public/MoverDataModelTypes.h` | FCharacterDefaultInputs / FMoverDefaultSyncState |
| `Public/MoverSimulationTypes.h` | 模拟时间步、输入与状态上下文 |
| `Private/KinematicActorSimulation.cpp` | DoSimulationTick / RollbackToPriorState |
| `Private/MovementModeStateMachine.cpp` | 子步、行为混合、转换与模式执行 |
| `Public/MovementMode.h` | GenerateMove / SimulationTick / 异步能力约束 |
| `Private/DefaultMovementSet/CharacterMoverComponent.cpp` | 默认模式与 Jump 的 Instant Effect 路径 |
| `Private/DefaultMovementSet/Modes/WalkingMode.cpp` | 通用 Walking 的提案与实际模拟 |
| `Private/DefaultMovementSet/Modes/SmoothWalkingMode.cpp` | GASP Walking/Slide 蓝图父类的具体扩展机制 |
| `Private/Backends/MoverNetworkPredictionLiaison.cpp` | ProduceInput / RestoreFrame / FinalizeFrame |
| `Private/MoveLibrary/MovementMixer.cpp` | 多种移动贡献如何混合 |
| `Public/MoverPoseSearchTrajectoryPredictor.h` | Mover 与 Pose Search 轨迹预测接口 |

MoverExamples 的原生示例位于独立插件 `Engine/Plugins/Experimental/MoverExamples/`；不要把它的 `AMoverExamplesCharacter` 自动当作 GASP Mover 蓝图的父类。已导出的 GASP 角色直接父类是 Pawn。

## 蓝图怎样读取

本轮使用临时查看工程：保留样例插件配置，去掉不兼容的模板 C++ 模块，并让 Content 映射到原资源目录。脚本只加载和查询，没有保存、重编译或修改原蓝图资源。

```text
UnrealEditor-Cmd.exe GaspInspection.uproject
  -run=pythonscript -script=inspect_gasp.py
  -unattended -nullrhi -nosound
```

实际使用的读取接口：

1. `BlueprintEditorLibrary.get_blueprint_parent_class` 和 `list_graphs` 读取父类与图。
2. 直接读取 EdGraph 的 nodes 属性受到 protected 限制，首次尝试未获得节点；修正为 `ObjectIterator(EdGraphNode)` 按 Outer 筛选。
3. 对支持的 K2 节点使用公开节点标题与引脚接口，读取引脚名称、方向、连接和常量。
4. 使用 `SubobjectDataSubsystem` 读取蓝图组件模板及后端、模式和动画类默认配置。

共读取 **12 个蓝图、5,490 个节点对象**，其中 **5,033 个节点**成功取得公开引脚列表。部分注释、动画专用节点不适用 K2 接口；本系列没有宣称完整反编译全部 AnimGraph 内部数据。

:::note[不要误读导出结果]
连接中的引脚即使有默认值，运行时也通常由连线供值，不能把其默认值当作真实输出。例如一个连接着 CalculateMaxSpeed 的引脚写着 0，并不表示角色最大速度恒为 0。节点枚举顺序也不是执行顺序，应追踪执行引脚和数据依赖。
:::

## 已核实与尚未覆盖

| 内容 | 证据级别 |
| --- | --- |
| 角色父类、组件类型、Mover 后端与模式表 | 蓝图资产默认配置 |
| 输入集合、属性接口、轨迹节点与翻越双路径 | 指定图内节点及连接 |
| 滑行 380/200 条件、蹲伏判断和 NextMode | Evaluate 图的实际引脚连接与常量 |
| ToSlide/FromSlide 注册位置、五种模式的异步支持标志 | 角色蓝图内模式实例的默认配置 |
| 模拟前、Finalize 后和基座移动回调的绑定 | Create Delegate 指定函数与绑定节点连接 |
| CMC 模式分派、Walking 处理、Mover 后端恢复 | 本机源码静态阅读 |
| 帧率、耗时、实际调用次数、网络误差和中断恢复 | 本轮未测，需要实验验证 |

图示是为解释职责重新绘制的 SVG，不是编辑器截图。蓝图摘录与阅读定位可下载：[GASP 蓝图证据摘要](/qmx-Gameknowledge/assets/ue-movement/blueprint-evidence.json)。本地还保留完整导出、原资源哈希和构建记录，便于继续研究。

## 官方资料入口

- [Epic：Character Movement Component](https://dev.epicgames.com/documentation/en-us/unreal-engine/character-movement-component-in-unreal-engine)
- [Epic：Mover](https://dev.epicgames.com/documentation/en-us/unreal-engine/mover-in-unreal-engine)
- [Epic：Game Animation Sample](https://dev.epicgames.com/documentation/en-us/unreal-engine/game-animation-sample-project-in-unreal-engine)
- [EpicGames/UnrealEngine 源码仓库](https://github.com/EpicGames/UnrealEngine)：需要对应访问权限。

官方文档用于继续查阅；本文的版本特定结论以本机源码和样本读取为依据。回到 [专题目录](/qmx-Gameknowledge/knowledge/ue专栏/运动系统/目录/)。
