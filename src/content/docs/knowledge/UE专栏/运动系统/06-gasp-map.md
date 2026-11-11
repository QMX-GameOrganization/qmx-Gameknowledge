---
title: "6. GASP：两套角色的实现地图"
description: "根据实际蓝图父类、组件默认值与图入口，对照 CMC 与 Mover 两套 GASP 角色。"
sidebar:
  order: 6
---

## 从真实资源开始

以下信息由 UE 5.8.4 无界面 Python Commandlet 读取本地 `.uasset` 得到，不是根据文件名推测。资源路径相对于 `/Game/Blueprints`。

| 项目 | `SandboxCharacter_CMC` | `SandboxCharacter_Mover` |
| --- | --- | --- |
| 直接父类 | `/Script/Engine.Character` | `/Script/Engine.Pawn` |
| 运动组件 | `CharMoveComp`：CharacterMovementComponent | `CharacterMover`：CharacterMoverComponent |
| 骨骼动画类 | `SandboxCharacter_CMC_ABP` | `SandboxCharacter_Mover_ABP` |
| Actor 默认 Replicate Movement | true | false |
| Mover 后端 | 不适用 | `MoverNetworkPredictionLiaisonComponent` |
| Mover 起始模式 | 不适用 | `Falling` |
| 共享配套组件 | MotionWarping、AC_TraversalLogic、Foley、视觉覆盖、SmartObject 等 | 同类配套，另外包含 NavMover |

这些是资产默认配置，不是 PIE 中每个实例的最终状态。CMC 组件读取到 `MaxWalkSpeed=500`，但角色图会动态计算并写入速度限制，因此 500 不能作为所有步态的固定运行速度。

Mover 角色关闭 Actor 级移动复制，与使用专门后端管理运动同步的设计一致；这不表示它“关闭了所有网络复制”。本机虽然启用了 ChaosMover 插件，此角色默认使用的却是 **NetworkPrediction Liaison**。

![GASP 中两套运动实现、公共属性接口、动画与翻越组件的关系](/qmx-Gameknowledge/assets/ue-movement/gasp-flow.svg)

## Mover 模式表不是只有默认三种

`SandboxCharacter_Mover` 中 CharacterMover 的 MovementModes 默认映射为：

| 注册名 | 实现 | 研究重点 |
| --- | --- | --- |
| `Walking` | `BP_MovementMode_Walking` | 父类是 `SmoothWalkingMode`，不是直接使用 UWalkingMode |
| `Falling` | `BP_MovementMode_Falling` | 父类 FallingMode，覆盖 GenerateMove |
| `Flying` | `B_MovementMode_Flying` | 资源存在并已注册；本轮未单独导出它的图逻辑 |
| `Sliding` | `BP_MovementMode_Slide` | 同样继承 SmoothWalkingMode，覆盖 GenerateWalkMove |
| `Traversing` | 原生 `FlyingMode` 实例 | 注册名表达玩法用途，不等于存在 TraversingMode 原生类型 |

这说明“模式名”和“实现类”是两个维度。同一个原生模式可以被配置为不同用途；自定义蓝图也可以在父类基础上扩展，而不是从零实现碰撞。

进一步读取模式实例配置可以确认：Walking 的 Transitions 中配置了 `BP_MovementTransition_ToSlide`，Sliding 中配置了 `BP_MovementTransition_FromSlide`；这五个模式实例的 `bSupportsAsync` 均为 false。因此本文样例不能直接作为“异步移动模式已就绪”的例子。

## 两套角色在哪里承接玩法

CMC 角色有 `UpdateMovement_PreCMC` 和 `UpdateRotation_PreCMC`：前者设置速度、加速度、制动和地面摩擦；后者配置朝向规则。Mover 角色则有 `ProduceInput`、`CacheInputsFromMover`、`On_PreSimulateTick`、`On_MovementPostFinalize` 等入口。

迁移时应该迁移这些入口承接的职责，而不是把所有 CMC 参数名机械复制到 Mover Tick。

## 通过接口向动画提供属性

两套角色都实现 `Get_PropertiesForAnimation`，对应的两个 AnimBP 在 `Update_PropertiesFromCharacter` 中通过 `GetOwningActor → Get_PropertiesForAnimation` 获取并缓存角色属性。这形成了一个适配边界：动画无需把所有底层查询硬编码成某一种移动组件。

接口还能提供 Camera、Traversal、Ragdoll 等不同用途的数据。不过两个 AnimBP 本身仍是不同资产，存在不同的轨迹与动画处理图；不能将其说成“同一个 AnimBP 完全无改动复用”。

## 建议打开的顺序

先看两个角色的组件配置，再看 `Get_PropertiesForAnimation`，之后对照两个 AnimBP 的 `Update_PropertiesFromCharacter` 和 `Update_Trajectory`，最后进入 `AC_TraversalLogic`。这样每一层都知道自己在消费什么，而不是在一张大 EventGraph 中迷路。

下一章：[输入与模式扩展](/qmx-Gameknowledge/knowledge/ue专栏/运动系统/07-gasp-input/)。
