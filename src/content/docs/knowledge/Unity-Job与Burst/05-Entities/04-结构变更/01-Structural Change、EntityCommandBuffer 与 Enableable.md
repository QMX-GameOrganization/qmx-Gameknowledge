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
- `EntityCommandBuffer` 只延迟结构改变，不能代替普通组件数据同步。
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
