---
title: "02.1 System、SystemAPI.Query 与 EntityQuery"
description: 讲清 System 生命周期、查询方式和系统组更新顺序。
sidebar:
  order: 1
---

## 先看系统如何运行

系统不是挂在 GameObject 上的 MonoBehaviour。正常默认启动流程会创建运行 World、发现符合条件的系统、创建系统实例并把它们安排进系统组，最后由 PlayerLoop 更新组。

```text
World → SystemGroup → System.OnUpdate → Query → 匹配 Entity 的组件
```

创建系统、调度系统、匹配数据是三个不同条件。存在 `ReceiverSystem` 类型，不代表已经创建实例；创建实例不代表已加入被调度的组；OnUpdate 执行也不代表查询非空。

`[DisableAutoCreation]`、WorldSystemFilter、自定义 Bootstrap 和测试 World 会改变默认创建流程。手动 new World 后还需配置系统、系统组与更新入口；测试里显式调用系统 Update 也属于手动调度。

## 生命周期与更新条件

| 阶段 | SystemBase | ISystem | 职责 |
| --- | --- | --- | --- |
| 创建 | OnCreate() | OnCreate(ref SystemState) | 缓存查询、初始化系统资源、设置更新条件 |
| 开始/恢复更新 | OnStartRunning() | 额外实现 ISystemStartStop | 可选启用处理 |
| 每次实际更新 | OnUpdate() | OnUpdate(ref SystemState) | 查询、主线程处理或调度 Job |
| 停止更新 | OnStopRunning() | 额外实现 ISystemStartStop | 可选暂停处理 |
| 销毁 | OnDestroy() | OnDestroy(ref SystemState) | 释放系统持有的资源 |

OnCreate 不意味着实体场景已加载完成，不能假设初始化时所有单例都已存在。可在 OnCreate 中声明 `RequireForUpdate<FactoryGridSettings>()`，等数据出现后才更新。

系统 Enabled、所在组是否更新，以及 RequireForUpdate 等条件共同决定是否调用 OnUpdate。普通空 Query 可以只是一个零次循环，不应把它与更新条件失败混为一谈。Enableable、Disabled、Prefab 和查询过滤选项也会影响实际匹配范围。

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

`FixedStepSimulationSystemGroup` 位于模拟组内部，一帧可能更新零次或多次。因此系统的 OnUpdate 不等于 MonoBehaviour 的“每渲染帧一次 Update”。输入收集和低频占格可以在帧模拟层，高频运输在固定步层；应明确两者交接点。

UpdateBefore / UpdateAfter 主要在同一父组的兄弟系统间排序。不同层级的业务要在共同父组安排组与组的关系，不能靠跨组标注推导全局顺序。OrderFirst / OrderLast 还会影响同组内的排序区段；不要忽略它们再只看 Before/After。

系统排序决定 OnUpdate 的先后和 Job 的提交顺序，不表示工作线程已经完成。JobHandle/Dependency 管完成关系，ECB Playback 管结构改变何时可见。

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

SystemAPI.Query 每次遍历当前匹配数据；缓存的 EntityQuery 也不是创建时拍下的一份永久实体列表。`ToEntityArray` 等得到的是该时刻的句柄快照，后续实体仍可能被销毁。结构变更后的 RefRW/Buffer 等访问器要重新获取。

本章 MoveSystem/MoveJob 片段省略 Velocity 等业务定义，用来说明查询。可直接照步骤运行的一套统一类型，见 [00.2 完整链路与最小示例](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/00-导读/02-从场景到运行时ecs的完整链路/)。
