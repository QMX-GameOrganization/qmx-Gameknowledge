---
title: "07.1 Chunk 布局、查询性能与调试"
description: 从 Archetype 设计、查询过滤、Profiler 和 Entities 调试窗口定位性能问题。
sidebar:
  order: 1
---

## 先看数据密度

一个 Archetype 的组件越多、越大，chunk 能容纳的实体越少。把很少使用的状态拆到单独组件，避免每个高频实体都携带冷数据。

```text
高频：Position、Velocity、ProductionProgress
低频：调试统计、任务描述、编辑器元数据
```

## 查询性能

查询会先找到符合组件组合的 Archetype，再遍历 chunk。建议：

- 让查询签名只包含真正需要的组件。
- 用 Tag、Enableable 或 `WithNone` 过滤状态。
- 高频查询可缓存 `EntityQuery`。
- 不要在每个实体上调用 `EntityManager.GetComponentData`。
- 统计数量时用查询计数，避免创建临时托管列表。

## 什么时候用 IJobChunk

`SystemAPI.Query` 适合清晰的实体遍历；`IJobEntity` 适合按实体并行；需要 chunk 级共享数据、实体索引或极致控制时再使用 `IJobChunk`。不要把最底层 API 当成默认写法。

## 调试顺序

```text
Entities Hierarchy      是否烘焙出目标实体
Entities Journaling     谁创建/销毁/修改了实体
Entity Debugger         实体组件组合和当前值
Profiler Timeline       Job、同步点和系统耗时
Burst Inspector         是否真的生成 Burst 代码
```

## 常见错误

| 现象 | 可能原因 |
| --- | --- |
| 查询不到实体 | Baker 没执行、SubScene 未重烘焙、组件类型不匹配 |
| `InvalidOperationException` | Job 读写冲突或容器生命周期错误 |
| `InvalidOperationException: structural changes` | 在 Job 或查询迭代期间直接改实体结构 |
| 性能没有提升 | 查询量太小、主线程 foreach、Burst 未启用或存在同步点 |
| 实体引用失效 | Entity 所属 World 不同、实体已销毁、保存了跨结构变更引用 |

## 性能结论的证据

不要只看“用了 ECS”就下结论。固定实体数量、输入、时间步和构建设置，分别比较主线程 Query、`IJobEntity`、Burst Job，并记录主线程、Worker、同步点和内存。
