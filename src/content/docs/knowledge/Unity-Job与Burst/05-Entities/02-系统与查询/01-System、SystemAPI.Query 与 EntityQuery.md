---
title: "02.1 System、SystemAPI.Query 与 EntityQuery"
description: 讲清 System 生命周期、查询方式和系统组更新顺序。
sidebar:
  order: 1
---

## 两种系统形式

| 项目 | `ISystem` | `SystemBase` |
| --- | --- | --- |
| 类型 | struct | class |
| 系统自身 Burst | 支持 | `OnUpdate` 本身不作为 Burst 入口 |
| 托管字段 | 不支持 | 支持 |
| 适合 | 纯数据、高性能系统 | 需要托管缓存或渐进迁移 |

学习时可以先用 `SystemBase` 理解查询，再把纯数据系统迁移到 `ISystem` + Job/Burst。

## `SystemAPI.Query`

```csharp
public partial class MoveSystem : SystemBase
{
    protected override void OnUpdate()
    {
        float dt = SystemAPI.Time.DeltaTime;
        foreach (var (transform, velocity) in
                 SystemAPI.Query<RefRW<LocalTransform>, RefRO<Velocity>>())
        {
            transform.ValueRW.Position += velocity.ValueRO.Value * dt;
        }
    }
}
```

`RefRO<T>` 表示只读，`RefRW<T>` 表示读写。查询签名同时声明系统的读写意图，Entities 可以据此建立依赖。

## `EntityQuery` 与 `IJobEntity`

需要缓存查询、统计 chunk 数量或使用 `IJobChunk` 时使用显式 `EntityQuery`。单实体规则可以写成 `IJobEntity`：

```csharp
[BurstCompile]
public partial struct MoveJob : IJobEntity
{
    public float DeltaTime;
    private void Execute(ref LocalTransform transform, in Velocity velocity)
        => transform.Position += velocity.Value * DeltaTime;
}
```

调度时显式调用 `ScheduleParallel()`；ECS 不会因为查询存在就自动 Burst。

## 系统组

默认世界包含 `InitializationSystemGroup`、`SimulationSystemGroup`、`PresentationSystemGroup`。用 `[UpdateInGroup]`、`[UpdateBefore]`、`[UpdateAfter]` 表达顺序。工厂项目应把生产、运输、统计放进固定步模拟组，避免渲染帧率改变产量。

## 从 Query 到完整业务链

`SystemAPI.Query` 不是孤立的遍历语法。它读取的是 Baker 或 ECB 写入的组件：

```text
Baker / ECB
  ↓ 写入组件
SystemAPI.Query
  ↓ 读取 RefRO / RefRW / DynamicBuffer
业务计算
  ↓ 必须改变实体结构时
EntityCommandBuffer
```

例如传送带系统用 `RefRO<ConveyorData>` 得到速度，用 `DynamicBuffer<ConveyorItem>` 得到物品列表；拓扑系统先写入 `Source`/`Destination`，运输系统再读取它们。查询负责找到数据，系统负责逻辑，连接关系由拓扑系统维护。
