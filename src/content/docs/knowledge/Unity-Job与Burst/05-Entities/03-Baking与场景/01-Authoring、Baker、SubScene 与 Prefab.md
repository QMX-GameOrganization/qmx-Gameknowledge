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

完整链路是“编辑数据 → 烘焙产物 → 运行时加载 → World 中的实体”，中间不能省略加载这一层。构建也会生成所需的烘焙产物，Player 使用产物而不执行 Baker。

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

| 场景状态 | 意味着什么 |
| --- | --- |
| Authoring 只挂在普通主场景 GameObject | 不会仅凭 Baker 类存在就自动产生运行时 ECS 组件 |
| Authoring 放在 SubScene 并完成烘焙 | 生成可供实体场景加载的 ECS 数据 |
| SubScene 关闭编辑状态 | 使用烘焙后的实体场景数据，不等于卸载运行时实体 |
| 运行时实体场景已加载 | 对应数据进入目标 World，系统可查询 |
| 实体场景被卸载 | 对应运行时内容退出加载状态，业务缓存也需要处理失效 |

检查 SubScene 的 Auto Load 或代码加载流程；数据是否加载完成不能仅根据编辑器里能否展开源 GameObject 判断。运行时查询也可能早于异步加载完成，系统可通过更新条件等待所需组件。

## 为什么 Inspector 能配置，Entity 却找不到

Baker 把 Authoring 字段复制为 ECS 数据，两者不是同一个对象。运行时改 ECS 字段不会自动写回 MonoBehaviour；普通 Player 运行中改 Authoring 也不会自动重跑 Baker。编辑器 Live Baking 的增量更新是特定编辑流程，不要当成 Player 的运行逻辑。

当前 FactoryGridView 直接读 FactoryGridConfig，因此普通场景里也能显示网格；这只能证明 MonoBehaviour 路径在工作，不证明 FactoryGridSettings 已进入 ECS World。要观察 ECS 配置，应将 Authoring 放入 SubScene 并确认加载，或由运行时初始化代码显式创建组件。

## Prefab 实例化

Baker 可以把一个 GameObject Prefab 转成 Entity Prefab；运行时通过 `EntityCommandBuffer.Instantiate` 批量生成实例。不要在 Job 中直接调用 `GameObject.Instantiate`。

Prefab 必须经烘焙流程引用或注册，不是 Project 窗口里的每个 GameObject Prefab 都会自动产生 Entity Prefab。Baker 中通过 GetEntity(prefab, flags) 获取所需实体引用，再放入运行时组件。运行时可以用 EntityManager.Instantiate 或在 ECB 中记录 Instantiate；ECB 实例要等回放后才真正存在。Prefab 模板通常有 Prefab 标记，普通实体查询默认排除模板。

TransformUsageFlags.None 适合不需要运行时 Transform 的纯数据；Dynamic 等标志用于需要对应 Transform 数据的实体。拥有 LocalTransform 仍不等于有可见模型，渲染数据或表现桥接还要另外配置。

## 不走 SubScene 的另一条入口

运行时初始化、输入或加载代码也可以用 EntityManager.CreateEntity/AddComponentData，或记录 ECB，建立同样的数据组合。系统只关心查询匹配和 World，不关心数据最初来自 Baker 还是代码。

因此“系统存在”和“场景中挂了什么组件”不是一一对应关系。系统由启动流程创建，实体由数据入口创建，查询把两者联系起来。完整可运行的两条入口见 [00.2 完整链路与最小示例](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/00-导读/02-从场景到运行时ecs的完整链路/)。

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
- 把关闭 SubScene 编辑状态误认为运行时卸载；应检查实体场景实际加载状态。
