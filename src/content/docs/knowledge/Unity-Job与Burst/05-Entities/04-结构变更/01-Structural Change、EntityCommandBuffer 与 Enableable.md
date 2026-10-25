---
title: "04.1 Structural Change、EntityCommandBuffer 与 Enableable"
description: 解释结构性变更的同步点、ECB 回放时机和无需迁移的启停方式。
sidebar:
  order: 1
---

## 什么是结构性变更

以下操作会改变实体所在 Archetype 或实体集合：

```text
CreateEntity / Instantiate
DestroyEntity
AddComponent / RemoveComponent
修改 SharedComponent
```

它们可能使 chunk 重排，并要求此前访问这些数据的 Job 结束。普通组件字段写入不是结构性变更。

## 为什么 Job 里不能直接改结构

Job 正在遍历 chunk 时，如果另一个线程把实体移动到别的 Archetype，查询得到的数组就可能失效。Entities 因此要求 Job 记录命令，稍后统一回放。

```csharp
public partial struct SpawnJob : IJobEntity
{
    public EntityCommandBuffer.ParallelWriter Ecb;

    private void Execute([EntityIndexInQuery] int sortKey, in SpawnRequest request)
    {
        Entity spawned = Ecb.CreateEntity(sortKey);
        Ecb.AddComponent(sortKey, spawned, new Item { Type = request.Type });
    }
}
```

## ECB 的使用原则

- 每个并行 Job 使用自己的 `ParallelWriter` 或由系统组提供的 ECB。
- 回放时机要明确，通常放在 Simulation 组的末端或专用 ECB System。
- `EntityCommandBuffer` 延迟执行已记录的命令，也可记录普通组件写入；它不能代替 Job 依赖和业务数据同步。
- 回放前必须保证写入命令的 Job 已完成或依赖已正确连接。

## Enableable Component

可启用组件可以在不迁移 Archetype 的情况下改变查询可见性，适合频繁暂停/恢复：

```csharp
public struct Paused : IComponentData, IEnableableComponent {}
```

如果状态本身是长期分类的一部分，Tag + ECB 可能更容易理解；不要把所有结构变化都换成 Enableable。

## 工厂场景

```text
生产出新物品 Entity       ECB.Instantiate
物品被销毁/回收            ECB.DestroyEntity
生产器进入阻塞             Enableable 或普通状态字段
传送带拓扑改变             标记 Dirty，稍后重建连接
```

创建/销毁物品属于结构改变；改变路径中 `BeltItem` 的数量是 Buffer 数据更新，不是 Archetype 迁移。

## 把 ECB 放回系统时序里看

```text
SpawnSystem.OnUpdate 记录 CreateEntity + AddComponent
  → 此时真实 Entity 和组件还没有出现
EndSimulationEntityCommandBufferSystem 回放
  → 真实 Entity 和组件现在存在
下一个有机会执行的 ConsumerSystem 查询到它们
```

若消费者本帧已经在回放前执行过，它通常要到下一帧或下一模拟 tick 才处理新数据；若消费者配置在回放之后，则可能同一轮处理。ECB 不会自动让先前执行的系统重新运行。

CreateEntity 返回的临时实体只用于关联该 ECB 内后续命令，不是回放前可供 EntityManager 任意访问的真实实体。

ECB 也能记录 SetComponent 等普通写入；它不只是结构变更命令容器。但“记录命令”始终不等于“立即提交”。主线程初始化和低频拓扑操作，在安全位置可直接使用 EntityManager，不必为了 ECS 形式一律套 ECB。

并行写入需要兼容的 ParallelWriter、排序键和生产 Job 的完成依赖；它不替多个生产者解决业务容量竞争。现代 ECB 单例流程与旧式 AddJobHandleForProducer 用法不要混抄，按当前包 API 配置。

关联阅读：[00.2 完整链路与最小示例](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/00-导读/02-从场景到运行时ecs的完整链路/) 说明数据从哪里来；系统章节说明回放前后谁执行；Job 章节说明写命令的工作什么时候完成。
