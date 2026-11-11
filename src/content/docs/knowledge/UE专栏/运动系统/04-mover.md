---
title: "4. Mover：输入、状态与可组合行为"
description: "从数据边界理解 Mode、Layered Move、Movement Modifier 与 Instant Movement Effect。"
sidebar:
  order: 4
---

## 核心组件与后端分开

`UMoverComponent` 连接游戏对象、输入生产者、可用模式和模拟结果。`UCharacterMoverComponent` 在它之上提供常规角色的跳跃、姿态处理与 Montage 状态相关支持。

本机 `UMoverComponent` 构造函数默认设置 `UMoverNetworkPredictionLiaisonComponent` 为后端；这只是默认值，蓝图可以覆盖。启用 ChaosMover 插件，并不能证明某个角色实例真的使用 ChaosMover 后端。

## 输入是命令，状态是模拟事实

| 类型 | 用途 |
| --- | --- |
| `FMoverInputCmdContext` | 一个模拟步要使用的输入集合 |
| `FCharacterDefaultInputs` | 常规角色的移动输入、朝向意图与跳跃等字段 |
| `FMoverSyncState` | 移动模式及可扩展的同步状态集合等 |
| `FMoverDefaultSyncState` | 常用的变换、速度、移动基座等状态 |
| `FMoverAuxStateContext` | 后端契约中的辅助状态上下文，具体内容由实现决定 |

数据集合允许扩展，不代表向集合放入任意变量就自动获得正确的序列化、比较、插值和回滚语义。自定义数据必须符合所使用接口的复制、网络序列化和协调契约。

不要把 Input / Sync / Aux 误解成“输入 / 必须联网 / 不用联网”。它们是模拟接口中的职责划分，是否传输、如何保存与使用依赖后端和类型实现。

## 四种行为的边界

| 机制 | 适合表达 | 设计时要检查 |
| --- | --- | --- |
| Movement Mode | 一套持续的运动规则，如行走、下落、攀爬 | 激活/退出、环境检测、状态转换、剩余时间 |
| Layered Move | 一段有生命周期的运动贡献，如冲刺或根运动 | 持续时间、混合模式、优先级、结束后的速度 |
| Movement Modifier | 在移动生命周期中施加修饰，如姿态处理 | 开始/结束、设置恢复、同步状态 |
| Instant Movement Effect | 在模拟中应用一次性运动效果 | 应用时机、位置/速度/模式变化与恢复 |

“跳跃一定是 Layered Move”是错误概括。本机 `UCharacterMoverComponent::Jump()` 创建 `FJumpImpulseEffect` 并调用 `QueueInstantMovementEffect`。插件也有其他跳跃相关 Layered Move，说明同一玩法可以按不同需求实现。

## Mode 不直接等于技能

持续沿墙移动，可能需要独立 WallRun Mode；短暂向前冲刺，可能用 Layered Move；如果冲刺需要独特碰撞、转向和地面规则，也可能需要独立 Mode。

判断标准是：它改了基础运动规则，还是只贡献一段速度？什么状态必须参与恢复？它与其他行为发生冲突时谁优先？先回答这些问题，再选机制。

## 混合不是简单相加

`MovementModeStateMachine.cpp` 将 Layered Move 的贡献交给 `MovementMixer`，并结合模式生成的提案。不同混合方式可以叠加、覆盖，或保留部分速度分量；源码甚至包含被完全覆盖时跳过模式 GenerateMove 的条件优化。

因此“基础跑速 + 冲刺速度 + 根运动速度”不是固定公式。应沿 Mixer 的具体策略确认结果，尤其注意竖直分量和行为结束后的残余速度。

**自测：** 为什么不能将“输入事件触发一次”直接等同于“模拟效果只执行一次”？网络重放可能重新执行模拟；效果的排队、消费与状态必须符合模拟契约。

下一章：[模拟与后端](/qmx-Gameknowledge/knowledge/ue专栏/运动系统/05-mover-simulation/)。
