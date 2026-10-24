---
title: "01.3 ECS 核心接口与运行时类型"
description: 集中梳理 IComponentData、Entity、World、SystemBase、ISystem、Baker、EntityManager、EntityQuery 和 EntityCommandBuffer 的职责边界。
sidebar:
  order: 3
---

## 先建立一张类型地图

Entities 中最容易混淆的是“接口”“数据类型”“管理器”和“编辑器转换类型”。它们不是同一层：

| 类型 | 所属层 | 作用 |
| --- | --- | --- |
| `Entity` | 运行时句柄 | 指向当前 World 中的实体身份 |
| `IComponentData` | 组件接口 | 标记一个固定大小的运行时数据组件 |
| `IBufferElementData` | Buffer 接口 | 标记动态数组的元素类型 |
| `IEnableableComponent` | 组件接口 | 允许运行时启停而不迁移 Archetype |
| `ISharedComponentData` | 组件接口 | 按值分组实体，改变值可能迁移实体 |
| `ICleanupComponentData` | 组件接口 | 销毁时保留清理阶段的组件标记 |
| `SystemBase` | 系统基类 | 托管系统，提供 `OnCreate/OnUpdate/OnDestroy` |
| `ISystem` | 系统接口 | 非托管系统，生命周期方法可作为 Burst 入口 |
| `EntityManager` | World 管理器 | 创建、销毁、读写实体和组件 |
| `EntityQuery` | 查询对象 | 找到匹配组件组合的 Archetype/chunk |
| `SystemAPI` | 系统 API | 在系统中生成查询和访问单例/组件 |
| `EntityCommandBuffer` | 延迟命令 | 记录结构性变更，稍后统一回放 |
| `Baker<T>` | 编辑器转换类 | 把 Authoring MonoBehaviour 转成运行时 Entity 数据 |
| `World` | 运行容器 | 持有 EntityManager、系统和实体集合 |

## `IComponentData`：固定大小组件的入口

```csharp
public struct Health : IComponentData
{
    public int Current;
    public int Max;
}
```

实现 `IComponentData` 的 struct 通常是非托管组件。它描述实体的一列数据，不描述实体的行为。系统通过组件类型查询实体，再读写字段。

```csharp
foreach (RefRW<Health> health in
         SystemAPI.Query<RefRW<Health>>())
{
    health.ValueRW.Current--;
}
```

`IComponentData` 适合进度、速度、容量、状态、Entity 连接等固定大小数据。数组、可变库存和路径物品不应硬塞进固定 struct。

## `IBufferElementData`：组件上的动态数组

```csharp
public struct InventoryItem : IBufferElementData
{
    public int ItemType;
    public int Count;
}
```

实体拥有的是 `DynamicBuffer<InventoryItem>`，而不是单个 `InventoryItem`。它适合传送带物品、生产器待输出、库存堆叠和事件队列。

```csharp
DynamicBuffer<InventoryItem> buffer =
    SystemAPI.GetBuffer<InventoryItem>(entity);
buffer.Add(new InventoryItem { ItemType = 1, Count = 4 });
```

Buffer 的元素类型仍然必须是纯数据；Buffer 本身属于实体的组件集合。

## `Entity`：句柄，不是对象

```csharp
public struct OutputPort : IComponentData
{
    public Entity Target;
    public ushort TargetSlot;
}
```

`Entity` 只在所属 World 中有效。它可以存进组件，用于连接生产器和传送带；真正读取目标数据时要用 `ComponentLookup<T>`、`BufferLookup<T>` 或 `EntityManager`。

```csharp
ComponentLookup<Receiver> receivers =
    GetComponentLookup<Receiver>(false);
Receiver receiver = receivers[port.Target];
```

实体销毁后句柄不能继续使用。存档中的永久身份应另设 `StableId`，不要保存 `Entity.Index`。

## `EntityManager`：低层管理入口

`EntityManager` 可以直接：

```csharp
CreateEntity
Instantiate
DestroyEntity
AddComponent
RemoveComponent
GetComponentData
SetComponentData
GetBuffer
```

它适合初始化、低频拓扑操作和调试。高频系统优先使用 `SystemAPI.Query`、`IJobEntity` 和缓存查询，避免在每个实体上调用管理器方法。

## `SystemBase` 与 `ISystem`

```csharp
public partial class ReceiverSystem : SystemBase
{
    protected override void OnUpdate() { }
}
```

`SystemBase` 是 class，可以保存托管缓存，适合学习和渐进迁移。

```csharp
public partial struct ReceiverSystem : ISystem
{
    public void OnUpdate(ref SystemState state) { }
}
```

`ISystem` 是 struct，不保存托管字段，生命周期更接近 Burst/Job 数据流。纯数据系统完成验证后，可以优先迁移到 `ISystem`。

## `EntityQuery`、`SystemAPI` 与 `IJobEntity`

```text
SystemAPI.Query       简洁的系统内遍历
EntityQuery            可缓存的查询对象、chunk 级控制
IJobEntity             把查询转成可调度的实体 Job
IJobChunk               对 Archetype/chunk 做更底层控制
```

选择顺序可以是：

```text
先用 SystemAPI.Query 验证逻辑
→ 用 IJobEntity + Burst 并行
→ 只有需要 chunk 级控制时才用 IJobChunk
```

## `Baker<T>`：运行时之前的转换

```csharp
public sealed class ReceiverBaker : Baker<ReceiverAuthoring>
{
    public override void Bake(ReceiverAuthoring authoring)
    {
        Entity entity = GetEntity(TransformUsageFlags.None);
        AddComponent(entity, new Receiver { Capacity = authoring.capacity });
    }
}
```

`Baker` 不是运行时系统，也不是 `EntityManager` 的替代品。它只在编辑器 Baking 阶段读取 Authoring 数据并写入运行时实体。

## `EntityCommandBuffer`：延迟结构改变

创建、销毁、添加和删除组件属于结构性变更。Job 或查询遍历期间不能直接调用 `EntityManager` 改结构，应使用：

```text
Job / System 记录 ECB 命令
→ 依赖完成
→ ECB System 回放
```

普通字段写入可以直接由查询或 Job 完成；ECB 主要解决结构改变的时机和线程安全。

## 工厂项目的接口对应

```text
FactoryProducer      IComponentData
FactoryReceiver      IComponentData
FactoryConveyor      IComponentData + Entity 字段
FactoryConveyorItem  IBufferElementData
FactoryProducerBaker Baker<Authoring>
FactoryProducerSystem SystemBase / ISystem
```

这张对应关系就是最小工厂链的 ECS 骨架：组件定义数据，Entity 保存身份，Baker 完成转换，System 批量推进状态。

## 自测题

1. `IComponentData` 和 `IBufferElementData` 的数据形态有什么区别？
2. 为什么 `Entity` 不能当作跨存档的永久 ID？
3. `EntityManager` 和 `SystemAPI.Query` 各适合什么频率的工作？
4. `Baker` 为什么不能替代运行时 System？
5. 为什么创建物品 Entity 通常要通过 ECB？
