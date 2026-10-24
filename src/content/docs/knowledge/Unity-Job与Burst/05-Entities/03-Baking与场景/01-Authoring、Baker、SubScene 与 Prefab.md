---
title: "03.1 Authoring、Baker、SubScene 与 Prefab"
description: 解释编辑器数据如何通过 Baking 转成运行时 Entity 数据。
sidebar:
  order: 1
---

## 两套数据

```text
Authoring 数据：GameObject、MonoBehaviour、Prefab、编辑器引用
Runtime 数据：Entity、IComponentData、DynamicBuffer、BlobAsset
```

Baking 发生在编辑器，不是运行时把 MonoBehaviour 临时转换成 ECS。它把适合编辑的数据转换为适合查询和运行的数据。

## Baker 的职责

```csharp
public sealed class ProducerAuthoring : MonoBehaviour
{
    public int itemType;
    public float interval = 1f;
}

public sealed class ProducerBaker : Baker<ProducerAuthoring>
{
    public override void Bake(ProducerAuthoring authoring)
    {
        Entity entity = GetEntity(TransformUsageFlags.None);
        AddComponent(entity, new Producer
        {
            ItemType = authoring.itemType,
            Interval = authoring.interval
        });
    }
}
```

Baker 读取 Inspector 配置，写入运行时组件。不要把 Authoring MonoBehaviour 引用直接存进 Burst 组件。

## SubScene 的作用

SubScene 是 ECS 场景数据的编辑入口和加载边界。打开时可以增量烘焙，运行时加载已生成的实体场景。大量静态机器、地图和装饰适合放进 SubScene。

## Prefab 实例化

Baker 可以把一个 GameObject Prefab 转成 Entity Prefab；运行时通过 `EntityCommandBuffer.Instantiate` 批量生成实例。不要在 Job 中直接调用 `GameObject.Instantiate`。

## 工厂项目的 Authoring 分层

```text
ProducerAuthoring     配方、生产间隔、输出容量
ConveyorAuthoring     长度、速度、连接 GameObject
ReceiverAuthoring     物品过滤、容量、消费速度
        ↓ Baker
Producer / BeltPath / Receiver + Buffers
```

静态连接可在 Baker 阶段解析；如果玩家运行时建造，则由拓扑系统在运行时重建。

## 常见坑

- 修改 Baker 后没有触发 SubScene 重新烘焙。
- 把 `MonoBehaviour`、`GameObject`、接口放进非托管组件。
- 把编辑器配置和运行时状态共用一个可变对象。
- 以为关闭 SubScene 后 Entity 仍会留在默认 World。
