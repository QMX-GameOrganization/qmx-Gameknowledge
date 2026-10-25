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

## 系统没效果：按链路逐层定位

| 顺序 | 检查位置 | 要确认的事实 |
| --- | --- | --- |
| 1 | 当前 World | 数据和系统是否在同一个运行 World，不是 Baking 或测试 World |
| 2 | Systems 窗口 | 系统是否已创建、属于哪个组、组是否实际更新 |
| 3 | 更新条件 | Enabled、RequireForUpdate、RequireMatchingQueriesForUpdate 是否允许更新 |
| 4 | Entities Hierarchy / 实体 Inspector | 目标实体存在吗，组件是否齐全且处于正确启用状态 |
| 5 | 数据入口 | 普通场景 Authoring 是否根本未进入 Baking；SubScene 是否加载完成 |
| 6 | 时序边界 | 请求是在消费前创建的吗，ECB 是否回放，Job 依赖是否完成 |
| 7 | 表现入口 | 数据变化了吗，是否有渲染组件或 GameObject 桥接读取它 |

窗口名称和菜单位置随版本变化；Entity Debugger 是旧版本常见称呼，当前优先找 Entities Hierarchy、实体 Inspector 和 Systems。

三个容易混淆的现象：

- 系统存在，但 RequireForUpdate 不满足，所以 OnUpdate 没执行。
- OnUpdate 执行了，但查询匹配数量为零，所以循环没有处理对象。
- 数据已经变化，但没有表现层，所以 Game 画面没有变化。

以占格为例，能看到绿色预览只说明 FactoryGridView 在显示；还需查询是否产生 GridOccupancyRequest、Result 是否成功、目标是否有 GridOccupancyState。不要通过预览颜色推断占格已经提交。

可先按 [00.2 完整链路与最小示例](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/00-导读/02-从场景到运行时ecs的完整链路/) 运行最小接收器示例，将“数据入口、系统运行、数据变化、显示结果”逐项观察，确认环境正常后再排查项目业务。
