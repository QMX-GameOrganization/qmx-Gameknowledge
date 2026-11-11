---
title: "1. 对象、组件与最终移动权"
description: "先明确 Actor、Pawn、Character、碰撞体、Mesh、移动组件与动画的职责。"
sidebar:
  order: 1
---

## 谁在移动角色

`Actor` 提供世界对象的基础；`Pawn` 增加可被 Controller 控制的语义；`Character` 是带角色胶囊体、骨骼网格和 CharacterMovement 等约定的 Pawn。Controller 表达控制关系，输入系统生成操作信息，移动组件把意图转成受约束的运动。

| 对象 | 核心职责 | 不应默认承担的职责 |
| --- | --- | --- |
| Controller / 输入逻辑 | 按键、视角、控制权、意图转换 | 绕过碰撞每帧直接写角色位置 |
| Capsule 等碰撞组件 | 定义实际移动与碰撞的空间形状 | 自动选择匹配动作 |
| CMC / Mover | 根据输入、状态和环境推进运动 | 替代全部动画与技能架构 |
| SkeletalMesh / AnimInstance | 计算、播放和呈现骨骼姿态 | 私自维护第二套权威移动状态 |
| SpringArm / Camera | 组织镜头与跟随表现 | 与角色碰撞体争夺移动权 |

骨骼脚底的位置、Mesh 的世界位置、胶囊体中心不是同一个量。动画可以让身体前倾而胶囊体不变；网络平滑也可以修饰视觉呈现。排查“角色在滑”时，先确认滑的是骨骼、Mesh 还是实际碰撞体。

## 组件组合不等于多个系统一起写 Transform

典型 CMC 角色以 `ACharacter + UCharacterMovementComponent` 为基础；Mover 的 `UMoverComponent` 自身继承 `UActorComponent`，并非 CMC 的子类。面向常规角色的 `UCharacterMoverComponent` 则继承 `UMoverComponent`。

```text
UActorComponent
└─ UMoverComponent
   └─ UCharacterMoverComponent
```

因此通常使用一个 CharacterMover 实例即可，而不是再额外挂一个核心 Mover 实例。Mode 是 `UObject`，也不是每个模式都要作为 ActorComponent 挂到角色上。

移动系统需要知道它驱动哪个 UpdatedComponent，并通过合适的后端推进。动画、摄像机、导航和玩法组件可以读写各自接口，但不应让 CMC、Mover、物理模拟、每帧 SetActorLocation 无约束地同时驱动同一对象。

## 三个量分别记录

- **输入意图**：玩家想向哪里走、以什么方式朝向。
- **模拟状态**：实际位置、速度、移动模式、基座等。
- **表现状态**：选择的动画、混合权重、IK 调整、镜头偏移。

向墙输入时，意图可以非零，实际位移却接近零。用输入长度直接冒充移动速度，会导致顶墙时跑步动画仍然高速播放。反过来，只用实际速度也不够表达启动意图；动画系统可能同时需要两者。

## 自测

**问：换成 Mover 后是否就不需要 AnimBP？** 仍然需要姿态计算系统。Mover 负责运动，AnimBP 负责骨骼姿态，两者通过状态和根运动等接口协作。

**问：组件多是否天然更慢？** 不能根据结构数量判断。需要测量 Tick、碰撞查询、动画更新、网络开销及等待时间。

下一章：[CMC 的一次地面移动](/qmx-Gameknowledge/knowledge/ue专栏/运动系统/02-cmc/)。
