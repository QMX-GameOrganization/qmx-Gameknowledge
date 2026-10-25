---
title: "01.2 Component 类型与数据设计"
description: 对比 unmanaged、buffer、tag、enableable、singleton 等组件，并给出数据拆分方法。
sidebar:
  order: 2
---

## 常用组件种类

| 类型 | 用途 | 工厂示例 |
| --- | --- | --- |
| `IComponentData` | 固定大小数据 | `ProductionState` |
| Tag component | 只做查询筛选 | `BlockedTag` |
| `IBufferElementData` | 可变长数组 | `BeltItem`、`PendingOutput` |
| Enableable component | 临时启停而不迁移 Archetype | `Paused`、`Visible` |
| Singleton | 一个 World 一份全局状态 | `FactoryClock` |
| Shared component | 按值分组，改变会迁移 | 渲染材质或分区键 |
| Cleanup component | 销毁后保留清理标记 | 外部资源释放队列 |

## 组件应保持纯数据

```csharp
public struct ProductionState : IComponentData
{
    public float Progress;
    public int RecipeId;
    public int OutputCount;
}
```

非托管组件可以有方法，但不能包含 GameObject、string 等托管引用；辅助方法不会自动作为游戏行为调用。把规则的调度放在 System 中，组件表达状态。Entities 也支持受限的 managed component（class），但不能直接用于 Burst Job；本系列高频模拟默认使用非托管 struct。

## Buffer 的容量与生命周期

`DynamicBuffer<T>` 适合数量变化的输入、输出和路径物品。`[InternalBufferCapacity]` 以内的数据可能直接放在实体 chunk 中，超过容量后会转移到外部内存。

```csharp
[InternalBufferCapacity(8)]
public struct BeltItem : IBufferElementData
{
    public int Type;
    public float Distance;
}
```

容量不是吞吐量。吞吐量仍由速度、时间步或端口速率决定。

## Enableable 与 BlobAsset

短时间暂停可以使用 `IEnableableComponent`，避免结构迁移；长期分类状态用 Tag 更直观。配方、机器定义和物品类型表适合放 BlobAsset；当前进度和库存仍放普通组件/Buffer。

## 检查表

- 高频查询的数据是否足够小？
- 数量可变的数据是否使用 Buffer？
- 是否把 GameObject、字符串、接口错误地带进运行时组件？
- 是否把静态定义和动态状态分开？

## 声明组件、添加组件、查询组件是三步

```text
定义 GridFootprint : IComponentData       只有类型
  → Baker / EntityManager / ECB 添加到 Entity
  → System 查询带有它的实体并读取 Size
```

`Singleton` 是“查询范围内恰有一个匹配实体”的使用约定，不是一种自动创建全局对象的关键字。定义 `FactoryClock` 后，仍需明确由谁创建它，以及多 World 下每个 World 是否各有一份。

Cleanup 组件也没有自动业务行为。销毁带 cleanup 组件的实体后，实体会以清理状态保留；负责清理的系统释放索引或外部资源，再移除 cleanup 组件，清理才能结束。以当前占格模块为例，`GridFootprint` 描述范围，`GridOccupancyState` 表示成功登记，系统负责二者与索引的关系。

Enableable 的启停影响匹配查询，不等于删除组件，也不等于停止所属系统。调用专门 API 仍能判断实体是否拥有该类型。

创建、系统查询及表现层如何串起来，见 [00.2 完整链路与最小示例](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/00-导读/02-从场景到运行时ecs的完整链路/)。
