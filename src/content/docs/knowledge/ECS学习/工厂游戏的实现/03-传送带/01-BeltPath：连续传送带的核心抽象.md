---
title: "03.1 BeltPath：连续传送带的核心抽象"
description: 解读 shapez.io 把多段传送带合并成 BeltPath 的运行时优化。
sidebar:
  order: 1
---

## 单段 Belt 与 BeltPath 的区别

`BeltComponent` 只描述单段带子的方向和几何长度，并保存一个 `assignedPath` 引用。真正的物品数组在 `BeltPath` 中：

```text
entityPath          连续带段列表
items               按运输顺序排列的物品
spacingToFirstItem  路径起点到第一个物品的距离
totalLength         整条路径长度
boundAcceptor       路径末端的接收函数
```

一条直线上的十个 Belt 实体，在运行时可以由一个 `BeltPath` 统一更新。

## 路径的合并和拆分

放置新 Belt 时，`BeltSystem` 会寻找前驱和后继：

```text
无前驱、无后继 → 创建新路径
只有前驱       → 追加到前驱路径
只有后继       → 插入到后继路径头部
前驱和后继都有 → 合并两条路径
```

删除中间带段时，一条路径会拆成两条。删除路径首尾则只需缩短路径。

## 为什么这是重要优化

如果每段传送带单独保存物品，物品每跨一格都要做一次实体间转移；`BeltPath` 把这变成一条有序数组上的位移。拓扑只在建造变化时处理，模拟 tick 只遍历路径中的物品。

## Unity ECS 映射

初版可以保留两种实体：

```text
ConveyorSegment Entity  位置、方向、渲染和拓扑
BeltPath Entity          总长度、速度、物品 DynamicBuffer
```

```csharp
public struct BeltPath : IComponentData
{
    public float TotalLength;
    public float MovementSpeed;
    public float ItemSpacing;
    public Entity EndTarget;
}

public struct BeltPathItem : IBufferElementData
{
    public int ItemType;
    public float Distance;
}
```

之后再把连续路径的物品改成更紧凑的 Native 容器或批量结构。不要在第一版就把拓扑、渲染和运输全部压成一个复杂组件。
