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

## 联系自测：先回答，再看核对答案

1. 为什么 SystemBase 不挂在 GameObject 上也能运行？
2. 场景中挂了 Authoring，为什么 Query 仍找不到组件？
3. 自己 new World 后，系统会自动每帧更新吗？
4. Query 为空时，OnUpdate 一定不执行吗？
5. A 排在 B 之前，是否说明 A 的 Job 在 B 提交工作前已经完成？
6. ECB.CreateEntity 之后，EntityManager 能立即读取新实体吗？
7. 关闭 SubScene 编辑状态和卸载实体场景有什么区别？
8. 组件值变了但画面不动，应检查哪里？

核对答案：

1. 默认启动流程在 World 中创建系统，并通过系统组接入 PlayerLoop；自定义启动流程需自行配置。
2. 可能只在普通场景里，没有进入 Baking；也可能烘焙结果没加载、World 或查询条件不匹配。
3. 不会。需创建系统、加入组并安排更新，或在独立测试里手动 Update。
4. 不一定。要区分空循环和 RequireForUpdate 等更新条件。
5. 不说明。系统业务顺序与 JobHandle 完成依赖要分别表达。
6. 不能。它是该 ECB 内使用的临时身份，回放后才有实际数据。
7. 关闭编辑恢复使用烘焙数据；卸载实体场景才涉及运行时数据移除，二者不是同一个操作。
8. 检查 Entities Graphics 或自定义表现桥接是否存在、是否读取正确 World。

完整示例、两条数据入口和当前项目对照：[00.2 完整链路与最小示例](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/00-导读/02-从场景到运行时ecs的完整链路/)。
