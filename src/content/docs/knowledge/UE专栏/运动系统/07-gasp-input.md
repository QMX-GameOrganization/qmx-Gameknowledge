---
title: "7. GASP：追踪输入与移动配置"
description: "从 CMC 参数更新到 Mover 输入集合、Walking 扩展与滑行转换，追踪真实节点连接。"
sidebar:
  order: 7
---

## CMC：在运动前准备参数

`SandboxCharacter_CMC.UpdateMovement_PreCMC` 中可以读到 `GetDesiredGait` 和一系列 Calculate 函数，并连接到 `MaxWalkSpeed`、`MaxWalkSpeedCrouched`、`MaxAcceleration`、`BrakingDecelerationWalking`、`GroundFriction` 的设置节点。

其设计是先将步态与玩法状态转成 CMC 参数，再由 CMC 完成运动计算。`UpdateRotation_PreCMC` 则存在对 `bUseControllerDesiredRotation`、`bOrientRotationToMovement`、`RotationRate` 的不同设置分支。

这里的参数更新职责已经从最终位移中分离，但“PreCMC”这个名字本身不构成 Tick 顺序的证明。精确顺序还需要检查注册的 Tick 依赖和运行时执行情况；本轮未单独导出 `AC_PreCMCTick` 的图。

## Mover：ProduceInput 构建两类输入

在 `SandboxCharacter_Mover.ProduceInput` 中，实际节点包括：

- `Get_MoveInput → SetDirectionalInput`，构建默认方向输入。
- `Get_OrientationIntent`、`Get_AimingRotation`，参与默认输入字段设置。
- `Get_RotationMode`、`Get_Gait`、`Get_MovementDirectionAndOffset`，参与 `S_MoverCustomInputs` 字段设置。
- 默认输入和自定义输入分别通过 `Add Data To Collection` 加入集合。

自定义字段还包括蹲伏意图、转向速率等。字段出现在输入结构中，不等于它们都影响所有模式；继续查模式实际读取哪些字段，才能确认作用范围。

![输入意图、模拟状态与动画表现需要分别观察](/qmx-Gameknowledge/assets/ue-movement/intent-state.svg)

## 模拟前与提交后的数据不能混用

`CacheInputsFromMover` 从 `GetLastInputCmd` 的集合读取默认与自定义输入，缓存为 `MoverDefaultInputs_PostSim`、`MoverCustomInputs_PostSim`。`On_PreSimulateTick` 图中则有从输入集合读取数据并调用 Crouch/UnCrouch 的分支。

`On_MovementPostFinalize` 查询模式名，与缓存模式比较后调用 `On_MovementModeChanged_PostFinalize` 并更新缓存。这解释了为什么观察移动结果的玩法逻辑，应有明确的提交后入口。

EventGraph 中的 Create Delegate 和绑定节点已核实：`On_PreSimulateTick` 绑定到 `On Pre Simulation Tick`，`On_MovementPostFinalize` 绑定到 `On Post Finalize`，`On_BasedMovementApplied` 绑定到 `On Based Movement Applied`。这比只根据函数名判断时序更可靠，但实际调用次数仍取决于后端和运行场景，不能假设逐渲染帧恰好一次。

## Walking：复用父类，再定制手感

`BP_MovementMode_Walking` 继承 `SmoothWalkingMode`。其 `GenerateWalkMove` 图读取默认/自定义输入，计算或设置 `MaxSpeedOverride`、Acceleration、Deceleration、TurningStrength、FacingSmoothingTime、期望朝向和速度等，并有父类 `Generate Simple Walk Move` 调用。

这是“在既有模式扩展点配置运动提案”的例子。它不意味着该蓝图自行重写了整个 Floor Sweep 或台阶处理。研究具体公式时，应沿每个输入引脚追值，而不是只看参数设置节点。

`BP_MovementMode_Falling.GenerateMove` 同样存在父类调用，并计算角速度、设置 Proposed Move 的字段。这说明可以保留父类的基础下落行为，同时扩展空中转向。

## Sliding：从真实引脚读出条件

![GASP 滑行转换：大于 380 且蹲伏进入，小于等于 200 或不再蹲伏退出](/qmx-Gameknowledge/assets/ue-movement/slide-transitions.svg)

`BP_MovementTransition_ToSlide.Evaluate` 的连线为：

```text
Params.ProposedMove.LinearVelocity
  → Vector Length XY
  → > 380
       AND HasGameplayTag("Mover.Stance.IsCrouching")
  → 条件成立时返回 NextMode = Sliding
```

`BP_MovementTransition_FromSlide.Evaluate` 的连线为：

```text
Vector Length XY(Params.ProposedMove.LinearVelocity) <= 200
  OR NOT CharacterMover.IsCrouching()
  → 条件成立时返回 NextMode = Walking
```

进入阈值高、退出阈值低形成迟滞区，避免在同一个阈值附近反复切换。数值单位跟随 UE 项目的长度/时间约定，常规厘米制下速度为 cm/s。

尤其注意这里比较的是 **ProposedMove 的水平速度**，不是未经核实的胶囊体最终实测速率。角色默认配置也已核实：Walking 的 Transitions 包含 ToSlide，Sliding 包含 FromSlide。默认注册证明这些转换有实际接入位置；运行时是否被覆盖、何时触发仍需要实验确认。

## 最小练习

在复制工程里，只调整进入阈值，保持退出阈值不动，观察同样的助跑和蹲伏输入下何时进入滑行。然后同时记录模式名、提案速度、实际速度、蹲伏状态。该实验尚未在本文执行，不把静态条件当作已测运行表现。

下一章：[翻越和动画实现](/qmx-Gameknowledge/knowledge/ue专栏/运动系统/08-gasp-animation/)。
