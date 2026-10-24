---
title: "08.1 Entities API 速查、自测与资料"
description: 汇总学习 Entities 时最常用的 API、术语和验证问题。
sidebar:
  order: 1
---

## API 速查

| 目标 | 常用 API |
| --- | --- |
| 创建实体 | `EntityManager.CreateEntity`、`ECB.CreateEntity` |
| 添加/删除组件 | `AddComponent`、`RemoveComponent` |
| 读写组件 | `SystemAPI.Query`、`ComponentLookup<T>` |
| 可变数组 | `DynamicBuffer<T>`、`GetBuffer<T>` |
| 并行实体处理 | `IJobEntity`、`IJobChunk` |
| 延迟结构改变 | `EntityCommandBuffer` |
| Authoring 转换 | `Baker<TAuthoring>`、`GetEntity` |
| 系统排序 | `[UpdateInGroup]`、`[UpdateBefore]`、`[UpdateAfter]` |
| 固定模拟步 | `FixedStepSimulationSystemGroup` |
| 只读声明 | `RefRO<T>`、`in T`、`[ReadOnly]` |

## 术语

- **World**：Entity、EntityManager 和系统的运行容器。
- **Archetype**：组件类型组合。
- **Chunk**：一个 Archetype 的连续内存块。
- **Structural change**：改变实体/组件结构的操作。
- **Baking**：把 Authoring 数据转换成运行时 Entity 数据。
- **ECB**：延迟并安全回放结构性变更的命令缓冲。
- **Enableable**：不迁移 Archetype 的可启用组件。

## 自测题

1. 为什么 Entity 句柄不能直接当作存档 ID？
2. `RefRO` 和 `RefRW` 如何影响依赖推导？
3. 为什么 Job 中要用 ECB 创建物品实体？
4. 传送带路径和单段传送带分别应该保存什么？
5. 多个生产器写同一个接收器时，为什么需要仲裁阶段？
6. 什么情况下 `DynamicBuffer` 比独立 Item Entity 更合适？

## 参考

- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/index.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/concepts.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/systems.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/baking.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/systems-entity-command-buffers.html
- https://github.com/Unity-Technologies/EntityComponentSystemSamples
- https://github.com/tobspr-games/shapez.io
- `D:\UnityHub\Project\程序化生成\Packages\manifest.json`
