---
title: "01.1 Entity、Component 与建筑组合"
description: shapez.io 如何用实体和组件组合建筑能力，而不是为每种建筑建立深继承树。
sidebar:
  order: 1
---

## Entity 只是身份和组件集合

`Entity` 本身不代表“矿机”或“熔炉”的全部行为。建筑由一组组件组合出来，例如同一个实体可以同时拥有：

```text
StaticMapEntity   地图位置、旋转、占地
ItemEjector       输出槽
ItemAcceptor      输入槽
ItemProcessor     加工状态
Storage           库存
Belt              传送带拓扑信息
```

系统通过“拥有某组件”筛选实体，而不是调用建筑基类中的虚方法。

## 能力组件与状态组件

建议把组件分成两类：

- **能力/接口组件**：说明实体能接收、发出、存储或加工。
- **运行时状态组件**：记录当前物品、进度、输入数量、输出队列。

例如 `ItemAcceptor` 的槽位主要是位置、方向和过滤器；真正的加工库存位于 `ItemProcessor`，这样“能接收”与“如何消费”没有耦合。

## 对 Unity ECS 的直接启发

```csharp
public struct Producer : IComponentData { public int RecipeId; }
public struct ItemAcceptor : IComponentData { public int SlotCount; }
public struct ItemEjector : IComponentData { public int SlotCount; }
public struct ProcessingState : IComponentData
{
    public float Progress;
    public int InputCount;
}
```

不要先做 `BaseMachine -> Furnace -> AdvancedFurnace` 的继承树。优先让实体通过组件组合表达能力，再让系统按组件查询。

## 一个容易忽略的点

shapez.io 的组件是可序列化对象，因此组件里既有静态配置，也有运行时状态。迁移到 ECS 时应拆开：

```text
Authoring / Baker 数据：位置、方向、配方、端口配置
Runtime Component：当前进度、库存、路径引用、阻塞状态
```

这样运行时组件才能保持小而稳定，Baking 也不会把编辑器对象引用带进 Burst 数据。
