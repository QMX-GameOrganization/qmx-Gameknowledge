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

组件可以有方法，但不应依赖托管对象或隐藏全局状态。把规则放在 System 中，组件只表达状态。

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
