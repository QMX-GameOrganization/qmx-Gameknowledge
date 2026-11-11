---
title: "5. Mover：模拟步、模式转换与后端"
description: "追踪 KinematicActorSimulation、状态机、Movement Mode 与 NetworkPrediction 的衔接。"
sidebar:
  order: 5
---

## 不要只盯 Actor Tick

Mover 的一次模拟由后端驱动。以本机 NetworkPrediction 运动学路径为例，Liaison 的 `ProduceInput` 转发到 Mover；`SimulationTick` 衔接运动学模拟；`FinalizeFrame` 将同步状态交回组件；`RestoreFrame` 处理恢复。

```text
NetworkPrediction 后端
  → ProduceInput → UMoverComponent → 输入生产者
  → SimulationTick → UKinematicActorSimulation::DoSimulationTick
      → 准备本步状态
      → 移动前处理
      → 推进 MovementModeStateMachine
      → 移动后处理与结果保存
  → FinalizeFrame → UMoverComponent
```

这是同步运动学路径的阅读图，不是所有后端的统一实现。`UMoverSimulation` 是基础类，不能只读它就认为已经读到完整角色模拟。

## GenerateMove 与 SimulationTick

`UBaseMovementMode` 暴露两个主要蓝图原生事件：`GenerateMove` 和 `SimulationTick`。C++ 覆盖常见对应实现名为 `GenerateMove_Implementation`、`SimulationTick_Implementation`，旧版本教程可能使用不同名字。

`UWalkingMode::GenerateMove_Implementation` 从输入和起始同步状态构建 `FGroundMoveParams`，考虑地面法线、朝向、前速度、加减速、摩擦等，再调用 `ComputeControlledGroundMove` 生成 `FProposedMove`。

`SimulationTick_Implementation` 则处理实际移动所需组件、基座变化、地面查询和运动结果。**提案描述希望如何运动，实际模拟决定能实现多少。**

## 一步中可以发生模式切换

状态机协调 Mode、Transitions、Layered Moves、Modifiers 和 Instant Effects。Transition 不是 Animator 的动画过渡，它决定运动规则如何改变。

比如 Walking 走到边缘后，余下的模拟时间需要由 Falling 继续处理。状态机同时要防止无进展的反复切换和过量迭代。阅读源码时，追踪剩余时间、当前模式和输出状态，比只找一个 SetMode 调用更重要。

## 回滚恢复什么

`UKinematicActorSimulation::RollbackToPriorState` 可以看到：通知状态机、使普通黑板相关缓存失效、开始/结束回滚黑板处理、恢复上一模拟状态和时间记录，并标记接下来进入重模拟。

这说明黑板不是“随便存数据就永远有效的字典”。例如地面查询缓存依赖此前的位置和环境，恢复旧状态后可能需要重新计算；需要历史语义的数据应遵循回滚黑板或同步状态的相应契约。

## Fixed 与 Independent

本地 GASP 的 `Config/DefaultNetworkPrediction.ini` 指定 `PreferredTickingPolicy=Independent`，模拟代理 LOD 配置为 `Interpolated`。文件中同时存在 `FixedTickFrameRate=60`，但不能据此断言项目当前按固定 60 Hz 推进运动。

配置值只是已读取的默认设置，仍需运行时确认覆盖与实际角色后端。也不能把“模拟可重放”称为跨平台位级确定性保证；碰撞环境、外部依赖和浮点行为仍需验证。

## ChaosMover 与线程边界

`UBaseMovementMode` 有 `bSupportsAsync`。其源码注释明确提醒：某些模拟方法在异步移动时可能运行于工作线程，不安全地访问外部对象会出问题。把同步蓝图搬到异步后端，不会自动满足线程安全要求。

选择后端时要验证模式支持、输入快照、事件提交、动画时序和网络物理需求；不能把“使用 Mover”直接解释成“所有移动和蓝图都在异步线程”。

下一章：[GASP 实现地图](/qmx-Gameknowledge/knowledge/ue专栏/运动系统/06-gasp-map/)。
