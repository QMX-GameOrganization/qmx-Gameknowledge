---
title: "2. CMC：从输入到地面移动"
description: "追踪 TickComponent、PerformMovement、StartNewPhysics 与 PhysWalking 的职责和边界。"
sidebar:
  order: 2
---

## 先看调用骨架

源码：`Engine/Source/Runtime/Engine/Private/Components/CharacterMovementComponent.cpp`。注意本版本实现位于 `Private/Components`，不要照旧文章在 `Private` 根目录找。

```text
TickComponent
  ├─ 消费输入、检查组件和网络角色
  ├─ 本地预测路径 → ReplicateMoveToServer → PerformMovement
  ├─ 权威控制路径 → ControlledCharacterMove → PerformMovement
  └─ 模拟代理等路径 → SimulatedTick / SimulateMovement 等

PerformMovement
  → 处理移动前状态、外力与根运动等
  → StartNewPhysics
      → PhysWalking / PhysFalling / PhysFlying / PhysSwimming / PhysCustom
  → 收尾与移动后状态更新
```

这是职责骨架，省略了条件分支。`TickComponent` 不是每次都走同一条链；暂停、无效数据、网络角色、根运动和异步配置都会影响路径。本机 CMC 还包含 `CharacterMovementComponentAsync.cpp`，不能将它描述为“完全没有异步支持”。

## PerformMovement 是一次运动的协调入口

它不只是计算 `Location += Velocity * DeltaTime`。角色还可能站在移动平台上、处于蹲伏姿态、受外力影响、播放根运动 Montage，或者在本次更新中途离开地面。外部修改位置也可能影响地面缓存是否仍有效。

读这个函数时，可用四个问题做笔记：起始状态从哪里来？哪些输入会改变速度？哪个函数实际移动碰撞体？结束时哪些状态必须更新？不要一开始就逐行记所有参数。

## StartNewPhysics 是模式分派

本版函数按 `MovementMode` 调用 `PhysWalking`、`PhysFalling`、`PhysNavWalking` 等。它先检查最小时间步、迭代上限和组件有效性；如果 UpdatedComponent 正在模拟物理，还会提前退出。

自定义模式常用 `MOVE_Custom + CustomMovementMode`，由 `PhysCustom` 承接扩展。增加一个枚举或切换模式，不会自动获得攀爬碰撞、联网状态与动画衔接。

## PhysWalking 的关键不是“水平移动”

本机源码可以观察到以下步骤：

1. 用 `GetSimulationTimeStep` 从剩余时间中取出子步，并限制模拟迭代次数。
2. 保存旧位置、旧地面和基座信息，恢复叠加根运动前的速度。
3. 在重力方向定义的平面上处理水平速度和加速度。
4. 在没有动画根运动或覆盖速度的根运动源等条件下调用 `CalcVelocity`。
5. 调用 `ApplyRootMotionToVelocity`，处理可能由根运动触发的模式变化。
6. 通过地面移动、台阶和碰撞处理得到实际结果，继续检查地面和下落条件。

**坡面上的期望速度、碰撞前的位移、实际完成的位移可能不同。** `MaxWalkSpeed` 是运动规则中的速度限制，不是每帧实际位移的保证；根运动等路径还需要单独检查。

## 从 Walking 进入 Falling

本步中途失去地面时，需要将未消耗时间交给新的物理模式继续计算。否则“前半帧走到边缘，后半帧下落”会被错误地推迟或重复计算。

`PhysFalling` 则处理重力、空中控制、碰撞和落地等。跳跃上升通常也属于 Falling 模式：Falling 表示没有依托地面的运动状态，不等于竖直速度一定向下。

## 如何扩展

简单调整优先使用现有参数和公开接口；持续改变运动规则时，再考虑 CMC 子类与自定义模式。若技能状态会影响预测，还必须研究 SavedMove 和网络移动数据，不能只让本地 `PhysCustom` 表现正确。

**自测：** 为什么设置 `MaxWalkSpeed=600` 后，顶墙也不可能每秒前进 600 单位？因为速度规则仍要经过碰撞和实际移动约束。

下一章：[CMC 网络预测](/qmx-Gameknowledge/knowledge/ue专栏/运动系统/03-cmc-network/)。
