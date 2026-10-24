---
title: "08.1 映射到 Unity Entities 1.x"
description: 将 shapez.io 的设计翻译成 Unity Entities、Burst 和 Job System 的数据与系统。
sidebar:
  order: 1
---

## 推荐的实体分层

```text
ConveyorSegment Entity
  LocalTransform / 方向 / 拓扑标记 / 渲染配置

BeltPath Entity
  BeltPath / DynamicBuffer<BeltPathItem> / 末端连接

Producer Entity
  Producer / RecipeRef / ProcessingState / OutputBuffer

Receiver Entity
  InputPort / Capacity / InputBuffer
```

`BeltPath` 是模拟核心；`ConveyorSegment` 更像编辑器和渲染层的拓扑节点。

## 不要在 Burst 中复制 shapez.io 的对象调用

shapez.io 可以写：

```js
path.tryAcceptItem(item)
```

Unity ECS 中不应在 Burst Job 里调用托管对象方法。可选择：

### 小型原型

按固定系统顺序读取目标容量，成功后直接同时修改源和目标。

### 多路竞争

```text
TransferProposal buffer
  → TransferArbitrationSystem
  → TransferCommitSystem
```

Proposal 中只放 Entity、端口、物品类型和数量，Commit 阶段统一写回。

## Component 与 Buffer 草案

```csharp
public struct BeltPath : IComponentData
{
    public float Length;
    public float Speed;
    public float Spacing;
    public Entity Target;
}

public struct BeltPathItem : IBufferElementData
{
    public int ItemType;
    public float Distance;
}

public struct TransferProposal : IBufferElementData
{
    public Entity Source;
    public Entity Target;
    public int ItemType;
    public int Count;
}
```

## Job/Burst 的切入点

先把同一种路径的大量物品移动改成 `IJobEntity` 或 `IJobFor`，再处理多路径末端交付。拓扑重建通常是低频、分支多的工作，可以留在主线程；不要为了“全 ECS”把低频地图搜索硬塞进 Burst。

## 版本注意

项目当前已接入官方 `com.unity.entities` 与 `com.unity.entities.graphics`。学习时以 Entities 1.x 的 `SystemAPI.Query`、Baker、`EntityCommandBuffer` 和固定步系统为主；不要把旧 DOTS 预览版的 API 直接混入新项目。
