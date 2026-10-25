---
title: "01.1 Entity、Component、World 与 Archetype"
description: 从内存布局角度理解 Entities 的实体、组件、世界、原型和 chunk。
sidebar:
  order: 1
---

## 结论

```text
Entity     身份句柄
Component  状态数据（本系列主要使用非托管组件）
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

增删组件可能使实体迁移到另一个 Archetype；创建/销毁实体改变实体集合，修改共享组件值可能使实体换到其它 chunk。这些操作属于结构性变更，但不一定都改变组件类型组合。普通组件字段赋值不是结构改变。

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

## World 把数据侧和执行侧接到一起

一个 World 同时包含 EntityManager 管理的数据和属于该 World 的系统实例。系统用当前 World 的查询访问当前 World 的实体；把另一个 World 的 Entity 句柄传过来，不能据此访问另一个 World 的数据。

同一系统类型可以在不同 World 中分别拥有实例，缓存和生命周期也分开。定义 `struct Receiver : IComponentData` 只是定义数据类型；必须在实体创建、烘焙加载或添加组件时才有数据实例。

Archetype/Chunk 解释“数据如何存”，不决定“系统何时运行”。系统组解释调度关系，组件查询解释匹配关系。将这两条线连起来，见 [00.2 完整链路与最小示例](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/00-导读/02-从场景到运行时ecs的完整链路/)。
