---
title: "00.2 从场景到运行时 ECS 的完整链路"
description: "用可编译的最小示例串起 GameObject、Authoring、Baker、SubScene、World、系统组、查询、ECB 与表现层。"
sidebar:
  order: 2
---

## 先回答：为什么场景里没有挂系统组件

`SystemBase` 不是 `MonoBehaviour`，`ISystem` 也不是 GameObject 组件。系统由 ECS World 创建并持有，再由系统组调度；不需要把一个 `ReceiverSystem` 拖到 GameObject 上。

`IComponentData` 也不是 Inspector 上的 MonoBehaviour 组件。定义一个组件 struct 只是定义数据类型，并没有自动创建 Entity，也没有让任何 Entity 拥有该组件。

| 对象 | 谁创建或提供 | 存放位置 | 从哪里观察 |
| --- | --- | --- | --- |
| Authoring MonoBehaviour | 场景编辑或 Prefab 配置 | GameObject | 普通 Hierarchy / Inspector |
| Baker | Baking 管线调用 | 编辑器烘焙过程 | 烘焙诊断、生成的数据 |
| Entity 与 ECS 组件 | 加载烘焙结果，或运行时创建 | 某一个 World | Entities Hierarchy / 实体 Inspector |
| SystemBase / ISystem | 默认启动流程或自定义 Bootstrap | 某一个 World 的系统集合 | Systems 窗口 |
| 系统组 | 启动流程或自定义创建 | 同一 World 的系统树 | Systems 的组层级 |
| GameObject 模型 | 普通场景或表现桥接代码 | GameObject 场景 | 普通 Hierarchy / Game 视图 |

窗口位置和名字随 Entities/Editor 版本变化；先确认观察的是哪个 World。编辑器烘焙 World、默认运行 World、自建测试 World 不是同一个容器。

## 两条入口，汇合到同一套运行逻辑

```text
编辑器入口                              运行时入口
GameObject + Authoring                  输入 / 加载 / 初始化代码
    ↓ Baking 管线调用 Baker                 ↓ EntityManager 或 ECB
烘焙后的 Entity Scene / Entity Prefab     创建或实例化 Entity、写组件
    ↓ 加载实体场景 / 实例化                   │
    └───────────────────┬───────────────────┘
                        ↓
            运行 World 中的 Entity + 组件
                        ↓
       系统组调度 System → Query 找到匹配组件
                        ↓
        主线程修改数据，或显式 Schedule Job
                        ↓
     完成必要依赖；有 ECB 时在规定位置 Playback
                        ↓
             后续系统查询并使用新状态
                        ↓
    Entities Graphics 或自定义表现桥接显示结果
```

Baker 的职责在入口处结束，运行时 System 不需要每帧回头调用 Baker。Entity Prefab 的数据先经烘焙，运行时实例化则走右侧入口；运行时完全可以直接创建数据 Entity，不依赖 Authoring。

“有实体”“有系统”“画面有模型”是三件事。没有渲染组件或表现桥接时，ECS 逻辑可以正常运行而画面没有变化。

## World 和系统从哪里来

正常安装并启用 Entities、使用默认启动流程时，Unity 会建立默认运行 World，发现符合条件的系统，将它们创建并安排进根系统组，并把更新接入 PlayerLoop。

```text
PlayerLoop
  → 默认 World
      → InitializationSystemGroup
      → SimulationSystemGroup
          → FixedStepSimulationSystemGroup
      → PresentationSystemGroup
```

这是一张简化的包含关系图，并非所有包内系统的完整清单。固定步组在一次渲染帧中可能执行零次、一次或多次。

默认机制有前提：`[DisableAutoCreation]`、`[WorldSystemFilter]`、自定义 `ICustomBootstrap`、关闭自动启动、测试 World 等都会改变发现和创建行为。不要把“继承 SystemBase”理解为任何环境都一定运行。

**手动 `new World(...)` 不会自动复制默认 World 的系统树，也不会自动加入 PlayerLoop。** `GetOrCreateSystemManaged<T>()` 可以创建/取得托管系统，但仅创建系统不代表它已经加入某个组并持续更新。测试可显式调用 `Update()`；生产环境需要配置系统组和 PlayerLoop。通常先使用默认启动流程，理解后再自定义。

## 一次系统更新究竟发生了什么

```text
系统创建 → OnCreate：缓存查询、声明更新条件
    ↓ 系统已加入组，组被调度，Enabled 为 true，更新条件满足
OnStartRunning → OnUpdate → 后续 OnUpdate ...
    ↓ 禁用或更新条件不再满足
OnStopRunning
    ↓ 再次满足条件可恢复；系统被销毁则进入 OnDestroy
```

上述启停回调适用于 `SystemBase`；`ISystem` 若要接收对应回调，需要额外实现 `ISystemStartStop`。`OnDestroy` 属于系统销毁，不是每次暂停时执行。

默认情况下，`SystemBase` 不会仅仅因为一个查询为空就必然跳过 `OnUpdate`；循环也可能只是执行零次。`RequireForUpdate<T>()` 可明确要求存在匹配数据；`[RequireMatchingQueriesForUpdate]` 是另一种更新限制。诊断时区分：系统未创建、系统未调度、更新被条件阻止、查询循环为空。

## 最小完整示例：一个库存每模拟秒增加一件

下面四个文件使用同一命名空间和同一组件。示例不负责渲染；运行后从实体 Inspector 观察 `Stored`。这是教学示例，不是当前工厂项目已经接好的业务链。

### 文件 1：ReceiverDemoData.cs

```csharp
using Unity.Entities;

namespace EntitiesLearning
{
    public struct ReceiverDemoData : IComponentData
    {
        public int Capacity;
        public int Stored;
        public float AccumulatedSeconds;
    }
}
```

### 文件 2：ReceiverDemoAuthoring.cs

```csharp
using Unity.Entities;
using UnityEngine;

namespace EntitiesLearning
{
    public sealed class ReceiverDemoAuthoring : MonoBehaviour
    {
        [Min(1)] public int capacity = 10;
    }

    public sealed class ReceiverDemoBaker : Baker<ReceiverDemoAuthoring>
    {
        public override void Bake(ReceiverDemoAuthoring authoring)
        {
            var entity = GetEntity(TransformUsageFlags.None);
            AddComponent(entity, new ReceiverDemoData
            {
                Capacity = Mathf.Max(1, authoring.capacity)
            });
        }
    }
}
```

### 文件 3：ReceiverDemoSystem.cs

```csharp
using Unity.Entities;

namespace EntitiesLearning
{
    [UpdateInGroup(typeof(FixedStepSimulationSystemGroup))]
    public partial class ReceiverDemoSystem : SystemBase
    {
        protected override void OnCreate()
        {
            RequireForUpdate<ReceiverDemoData>();
        }

        protected override void OnUpdate()
        {
            float dt = SystemAPI.Time.DeltaTime;
            foreach (var receiver in SystemAPI.Query<RefRW<ReceiverDemoData>>())
            {
                if (receiver.ValueRO.Stored >= receiver.ValueRO.Capacity) continue;
                receiver.ValueRW.AccumulatedSeconds += dt;
                while (receiver.ValueRO.AccumulatedSeconds >= 1f &&
                       receiver.ValueRO.Stored < receiver.ValueRO.Capacity)
                {
                    receiver.ValueRW.AccumulatedSeconds -= 1f;
                    receiver.ValueRW.Stored++;
                }
            }
        }
    }
}
```

这段 `foreach` 在主线程执行；`partial` 让源码生成器补充 SystemAPI 相关代码，不代表自动并行。填满容量后停止增长。

### 文件 4：ReceiverDemoRuntimeBootstrap.cs（可选入口）

```csharp
using Unity.Entities;
using UnityEngine;

namespace EntitiesLearning
{
    public sealed class ReceiverDemoRuntimeBootstrap : MonoBehaviour
    {
        private World world;
        private Entity receiver;

        private void Start()
        {
            world = World.DefaultGameObjectInjectionWorld;
            if (world == null || !world.IsCreated)
            {
                Debug.LogError("Default ECS World is not available.");
                return;
            }
            receiver = world.EntityManager.CreateEntity(typeof(ReceiverDemoData));
            world.EntityManager.SetComponentData(receiver,
                new ReceiverDemoData { Capacity = 10 });
        }

        private void OnDestroy()
        {
            if (world != null && world.IsCreated &&
                world.EntityManager.Exists(receiver))
                world.EntityManager.DestroyEntity(receiver);
        }
    }
}
```

两种运行方式任选一种，先不要混用，避免产生两份接收器：

1. **烘焙入口**：创建 SubScene，把挂有 `ReceiverDemoAuthoring` 的 GameObject 放入其中；确认运行时实体场景加载。普通主场景不挂 Bootstrap。
2. **运行时入口**：在普通场景挂 `ReceiverDemoRuntimeBootstrap`；不放 Authoring 接收器，也不需要 SubScene。系统仍由默认 World 启动流程创建。

无论选哪种，`ReceiverDemoSystem` 都不挂场景对象。检查运行 World 中是否有一个 `ReceiverDemoData`，`Capacity=10`，`Stored` 随模拟时间从 0 增加到 10。固定步累加使用浮点数，临界值可能有一 tick 误差。

这组代码需 Unity Entities 的运行环境和源码生成器。本文的编译检查不能替代你在 Editor 中加载 SubScene、进入 Play Mode 和观察状态的验收。

## ECB、Job 和表现层接在哪里

示例只改字段，所以不需要 ECB，也不需要 Job。以后功能增加时，按用途接入：

- **增删实体/组件**：主线程安全位置可用 EntityManager；Job 或不允许改结构的查询遍历中记录 ECB，再在确定阶段回放。
- **大量同类计算**：把处理改写成 `IJobEntity` 等 Job，显式 Schedule，并连接 Dependency；Burst 编译兼容的计算入口。
- **模型显示**：使用 Entities Graphics，或写桥接读取 ECS 状态更新 GameObject。Entity 不会自动得到模型。

系统排序决定“先提交谁的工作”，JobHandle 决定“工作完成前谁必须等待”，ECB 回放决定“新实体/组件从什么时候真正存在”。这三种关系必须分别表达；数据依赖不会替你选择业务顺序。

## 用当前网格占格模块对照

```text
FactoryGridConfig（GameObject 配置） → Baker → FactoryGridSettings
FactoryGridView（GameObject 调试显示） → 直接读取 Config，不等于已经烘焙

输入 / 初始化 / 测试代码
  → 创建 GridOccupancyRequest Entity
  → GridOccupancySystem 处理 Pending 请求
  → 检查全体目标格，成功后更新索引与目标组件
  → GridOccupancyState 表示实际登记成功
  → 调用方读取 Result，随后销毁请求 Entity
```

`GridPose`、`GridFootprint` 是描述；它们的存在不等于占用索引已经登记。`GridOccupancyIndex` 是系统持有的托管缓存，不是一个要挂在场景上的组件，也不是自动出现在实体 Inspector 的组件。

当前预览只显示格子与占地，尚未连接玩家建造请求；因此能看到绿色预览，不代表系统已有占格请求可处理。占格系统即使已自动创建，也可能没有业务工作。

当前占格系统在模拟组前部串行处理低频请求；生产与运输可在固定步组推进。它们不是必须全部放进同一个组。具体顺序要沿“请求产生 → 提交占用 → 消费结果”配置。

## 跨章节阅读导航

| 当前疑问 | 接着读 |
| --- | --- |
| 数据属于哪个 World、怎么存储 | [01.1 Entity、Component、World 与 Archetype](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/01-ecs核心/01-entitycomponentworld-与-archetype/) |
| 系统何时更新、Query 为什么为空 | [02.1 系统与查询](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/02-系统与查询/01-systemsystemapiquery-与-entityquery/) |
| Authoring 怎么变成 Entity | [03.1 Baking 与场景](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/03-baking与场景/01-authoringbakersubscene-与-prefab/) |
| 新创建的组件为什么稍后才可见 | [04.1 结构变更与 ECB](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/04-结构变更/01-structural-changeentitycommandbuffer-与-enableable/) |
| 顺序正确为什么仍有读写冲突 | [05.1 Job 依赖与 Burst](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/05-job与burst集成/01-ecs-job-依赖burst-与安全系统/) |
| 系统存在但没有效果怎么排查 | [07.1 性能与排错](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/07-性能与排错/01-chunk-布局查询性能与调试/) |

## 核对依据与验证范围

2026-10-25 核对当前 Unity 7000.0.0a8 本地包：manifest 声明 Entities 1.5.0，PackageCache 的 Entities package.json 为 6.7.0。默认 World 启动和系统更新条件分别对照包内 `Unity.Entities/DefaultWorldInitialization.cs`、`Unity.Entities/SystemBase.cs`。

文中的四个 C# 文件已从 Markdown 提取，使用当前项目的 Unity/Entities 引用及源码生成器编译通过。该验证只证明示例代码能编译，未执行本文的 Play Mode 与 SubScene 加载步骤。

- [Entities 官方手册](https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/index.html)
- [系统与系统组](https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/systems.html)
- [Baking](https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/baking.html)
- [ECB](https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/systems-entity-command-buffers.html)

官方链接使用公开 Entities 1.4 手册解释稳定概念；精确 API 仍应以当前包版本和编译结果为准。
