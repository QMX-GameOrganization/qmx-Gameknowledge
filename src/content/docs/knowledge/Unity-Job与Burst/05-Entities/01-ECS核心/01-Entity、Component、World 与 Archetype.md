---
title: "01.1 Entity、Component、World 与 Archetype"
description: 从内存布局角度理解 Entities 的实体、组件、世界、原型和 chunk。
sidebar:
  order: 1
---

## 结论

```text
Entity     身份句柄
Component  纯数据
System     数据转换逻辑
World      Entity 的容器和系统运行环境
Archetype  相同组件组合的实体集合
Chunk      Archetype 的连续内存块
```

Entity 不持有行为代码。系统根据组件组合找到实体，再批量读写数组。

## Entity 不是业务对象引用

`Entity` 是当前 World 内的索引与版本句柄，可以作为组件字段表达连接关系：

```csharp
public struct OutputPort : IComponentData
{
    public Entity Target;
    public ushort TargetSlot;
}
```

句柄只在当前 World 生命周期内有效。存档或网络协议需要另设稳定业务 ID，不能把 `Entity.Index` 当永久 ID。

## Archetype 与 Chunk

拥有完全相同组件类型组合的实体属于同一个 Archetype。Archetype 按组件列组织 chunk：

```text
Entity[]
Position[]
Velocity[]
Health[]
```

系统查询 `Position` 和 `Velocity` 时，可以直接遍历连续数组。组件越大，一个 16 KiB chunk 能容纳的实体越少；把冷数据塞进常驻组件会降低密度。

## 结构改变为什么昂贵

增删组件、创建/销毁实体、修改共享组件值都可能让实体迁移到另一个 Archetype。普通组件字段赋值不是结构改变。

```text
SetComponentData      普通写入
AddComponent           结构改变
RemoveComponent        结构改变
DestroyEntity          结构改变
```

Job 里不能直接做结构改变，应记录到 `EntityCommandBuffer`，在安全的系统组阶段回放。

## 与工厂游戏的对应

```text
Producer + OutputBuffer
Receiver + InputBuffer
BeltPath + DynamicBuffer<BeltItem>
```

不要把配方、库存、动画、渲染引用全部塞进一个大组件。按查询频率拆分组件，才能让生产、运输和表现系统各自遍历紧凑数据。

## 常见误解

- Entity 不是 GameObject 的轻量版实例，它不包含方法。
- ECS chunk 不是体素世界的 `VoxelChunk`。
- ECS 不会自动让每个系统并行；并行来自 Job 调度。
