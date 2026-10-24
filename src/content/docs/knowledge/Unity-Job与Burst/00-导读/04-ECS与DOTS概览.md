---
title: "0.4 ECS 与 DOTS 概览"
description: 按 Entities 1.4 官方手册梳理 DOTS 的五个主要部分与 ECS 核心概念，说明它与 Job、Burst 的关系，并判断本项目是否需要 ECS
sidebar:
  order: 4
---

> 适用版本：以 Entities 1.x 与 Unity 6000.x 手册为主线。本项目 Unity 7000.0.0a8 的 `Packages/manifest.json` 已声明 `com.unity.entities` 与 `com.unity.entities.graphics` 为 1.5.0；本地 PackageCache 显示 Entities 6.7.0 的 Unity 7 内置实现。深入章节见 `05-Entities`，版本差异处会写明，核实不了的标“待核实”。

## 要点

- 官方 Entities 手册的 "ECS packages" 页写道：DOTS 需要使用的 Unity 主要部分有五个，即 Entities（ECS 模式的实现）、作业系统（Job system）、Burst 编译器、Collections、Mathematics。本资料详细覆盖后四个，Entities 见第 05 部分。
- 在这五者之上构建的 ECS 包有 Unity Physics、Havok Physics for Unity、Netcode for Entities、Entities Graphics、Character Controller。Entities 手册首页说，通常不会单独使用 Entities 包，一般会配合 Entities Graphics、Unity Physics 和/或 Netcode for Entities。
- ECS 的三个角色：实体（Entity）是唯一标识，不含代码；组件（Component）存数据；系统（System）写逻辑，每帧在主线程执行 `OnUpdate`，需要多线程时再调度 Job。
- 拥有相同组件类型组合的实体属于同一个原型（Archetype）。手册说同原型的实体与组件存放在 16 KiB 的内存块（chunk）里。
- 创建或销毁实体、增删组件、设置共享组件的值，都是结构性变更（Structural change）。它们只能在主线程做，不能在 Job 里做；Job 里要用 `EntityCommandBuffer` 记录命令，之后回放。
- 对本项目的判断：体素区块生成是"每区块一大块数组"的批处理流水线，不是大量带不同组件的小实体，项目已接入 Entities；是否把体素区块迁移到 ECS 仍需按实体数量和数据布局评估。以后做大量生物、掉落物、方块实体时再深入学。

## 原理

### DOTS 的五个主要部分与 ECS 包

下图把手册的两层关系画在一起，上层建立在下层之上。

```
  ECS 包（建立在下面五个部分之上）
  +----------------+------------------+----------------------+
  | Unity Physics  | Havok Physics    | Netcode for Entities |
  +----------------+------------------+----------------------+
  | Entities Graphics                 | Character Controller |
  +-----------------------------------+----------------------+
                         ^
                         | 构建于
  DOTS 需要使用的 Unity 主要部分
  +----------+------------+--------+-------------+-------------+
  | Entities | Job system | Burst  | Collections | Mathematics |
  | (ECS)    |            |        |             |             |
  +----------+------------+--------+-------------+-------------+
    本资料：   详细覆盖 --------------------------->
              仅概览（本页）
```

| 部分 | 手册里的定位 | 在本资料中 | 本项目 |
| --- | --- | --- | --- |
| Entities | ECS（Entity、Component、System）模式的实现 | 第 05 部分；本页做总览 | 已声明 1.5.0（本地内置 6.7.0） |
| Job system | 快速、安全的多线程代码方案 | 第 1 部分 | 使用 |
| Burst compiler | 生成高度优化代码的 C# 编译器 | 第 2 部分 | 使用 |
| Collections | 非托管集合类型（列表、哈希表等），Job 与 Burst 代码只能访问非托管数据，所以需要它 | 1.4、1.5 等 | 使用 |
| Mathematics | 为 Burst 编译代码专门优化的数学库 | 2.3 | 使用 |
| Unity Physics | 无状态、确定性的实体物理 | 不涉及 | 未使用 |
| Havok Physics for Unity | 有状态、确定性的实体物理 | 不涉及 | 未使用 |
| Netcode for Entities | 面向实体的客户端-服务器网络方案 | 不涉及 | 未使用 |
| Entities Graphics | 用可编程渲染管线（SRP）渲染实体 | 不涉及 | 未使用 |
| Character Controller | 搭建基于 ECS 的角色控制器的机制 | 不涉及 | 未使用 |

说明：把 Job System、Burst、Collections、Mathematics 称作"四个组件"、把 ECS 另算一层，与手册的"五个主要部分"说法不一致，本资料以手册为准。

### ECS 核心概念

手册的 "Entity component system concepts" 把概念分成：ECS 简介、Entity、Component、System、World、Archetypes、Structural changes、Safety in Entities。下面按这个顺序概括，再补上 EntityQuery 与 EntityCommandBuffer。

#### Entity

实体代表程序里某个独立的东西，比如角色、特效、UI 元素，甚至网络事务这类抽象对象。手册把它比作轻量的、非托管的 GameObject，但它只是一个 ID，用来把各自的组件关联在一起，既不含代码，也不是组件的容器。

实体存放在世界（`World`）里，由该世界的 `EntityManager` 管理。常用方法有 `CreateEntity`、`Instantiate`、`DestroyEntity`、`AddComponent`、`RemoveComponent`、`GetComponent`、`SetComponent`。实体没有类型，只能按它带有的组件类型组合来分类。

#### Component

组件装实体的数据，供系统读写。用 `IComponentData` 接口把 struct 标成组件，它只能含非托管数据，可以带方法，但手册建议保持纯数据。手册列出的组件种类如下：

| 种类 | 手册的描述 |
| --- | --- |
| 非托管组件（Unmanaged） | 最常见，只能存某些类型的字段 |
| 托管组件（Managed） | 定义为 class，可存任意字段类型 |
| 共享组件（Shared） | 按值把实体分组到同一个 chunk |
| 清理组件（Cleanup） | 销毁带它的实体时，Unity 移除其余非清理组件，用来标记需要清理的实体 |
| 标签组件（Tag） | 不存数据、不占空间，可用在查询里过滤实体 |
| 缓冲组件（Buffer） | 充当可变长数组的组件 |
| Chunk 组件 | 存的是整个 chunk 的值，而不是单个实体的值 |
| 可启用组件（Enableable） | 运行时可启用或禁用，不需要昂贵的结构性变更 |
| 单例组件（Singleton） | 在一个世界里只有一个实例 |

#### System

系统提供把组件数据从当前状态变到下一状态的逻辑。系统在主线程上每帧运行一次，并组织成系统组（system group）的层级来决定更新顺序。手册给出两种系统写法：

- `ISystem`：struct，非托管系统。
- `SystemBase`：class，托管系统。

两者都有 `OnCreate`、`OnUpdate`、`OnDestroy` 三个可重写方法。手册的 "Systems comparison" 页对比如下：

| 特性 | `ISystem` | `SystemBase` |
| --- | --- | --- |
| 对 `OnCreate`/`OnUpdate`/`OnDestroy` 做 Burst 编译 | 支持 | 不支持 |
| 分配非托管内存 | 是 | 否 |
| GC 分配 | 否 | 是 |
| 在系统类型里直接存托管数据 | 不能 | 能 |
| `IJobEntity`、`IJobChunk` | 支持 | 支持 |
| `Job.WithCode` | 不支持 | 支持 |
| 支持继承 | 不支持 | 支持 |

手册的结论是：`ISystem` 与 Burst 兼容、比 `SystemBase` 快，一般应优先用 `ISystem`；`SystemBase` 方便，代价是 GC 分配或更长的 `SourceGen` 编译时间。Entities 1.4 把 `Entities.ForEach` 与 `Job.WithCode` 标为过时，分别改用 `IJobEntity` / `SystemAPI.Query` 与 `IJob`。

系统只能处理一个世界里的实体。默认的自动引导（bootstrapping）会创建默认世界，带 `InitializationSystemGroup`、`SimulationSystemGroup`、`PresentationSystemGroup` 三个系统组，系统默认放进 `SimulationSystemGroup`，可用 `[UpdateInGroup]` 改。

#### World

世界是实体的集合，实体 ID 只在自己的世界里唯一。世界拥有一个 `EntityManager` 和一组系统；同一世界里组件类型组合相同的实体存放在一起（即原型），原型决定组件在内存中的组织方式。进入 Play 模式时，Unity 默认创建一个世界并把所有系统加进去；需要手动控制时可用 `ICustomBootstrap` 或 `#UNITY_DISABLE_AUTOMATIC_SYSTEM_BOOTSTRAP` 等脚本宏。

#### Archetype 与内存布局

原型是同一世界里"组件类型组合完全相同"的所有实体的标识。手册对内存布局的说法是：

- 同一原型的实体与组件存放在统一的内存块 chunk 里，每个 chunk 为 16 KiB，能放多少实体取决于该原型里组件的数量与大小。
- chunk 内每种组件类型一个数组，另有一个数组存实体 ID。数组紧密排列，实体按顺序占用下标；移除实体时，把 chunk 里最后一个实体移过来填补空位。
- chunk 满了就新建，最后一个实体离开就销毁。原型只在世界被销毁时才销毁。

按原型组织使"按组件类型查询实体"很高效：只需找到含这些组件类型的原型，不必逐个扫描实体。手册还说，世界中的原型集合通常很早就趋于稳定，所以可以缓存查询来提速。

注意名词冲突：这里的 chunk 是 ECS 的内存块，与本项目里 `VoxelChunk` 那种"区块"不是一回事。

#### Structural change 与同步点

重组 chunk 或 chunk 内容的操作叫结构性变更。手册列出的有：创建或销毁实体、增删组件、设置共享组件的值。设置普通组件的值不是结构性变更。它们可能很耗资源，而且只能在主线程做，不能在 Job 里做。

原因是 Job 里做结构性变更可能使已调度的其它 Job 失效，并制造同步点（sync point）。同步点是主线程等待此前所有已调度 Job 完成的位置，会让工作线程在一段时间内闲置，所以要尽量避免。手册说结构性变更是同步点的主要来源。

#### EntityQuery

`EntityQuery` 找出含指定组件类型集合的原型，再把这些原型的 chunk 收集成数组交给系统处理。迭代时可用 `SystemAPI.Query`（主线程，可 Burst 编译）、`IJobEntity` 或 `IJobChunk`。

#### EntityCommandBuffer

`EntityCommandBuffer`（ECB）存放一个线程安全的命令队列，之后回放。方法与 `EntityManager` 对应，如 `CreateEntity`、`DestroyEntity`、`SetComponent<T>`、`AddComponent<T>`。用法有两种：在 Job 里记录结构性变更、Job 完成后在主线程回放；或在主线程延后变更。ECB 有类似 NativeContainer 的 Job 安全句柄，只在 Editor 里提供。手册建议每个 Job 用各自的 ECB。`EntityCommandBufferSystem` 为其它系统提供 ECB，用来把结构性变更合并到一处。

#### Safety

手册说明 Entities 为追求性能大量使用 unsafe 代码与原始指针，有些 API 返回的引用可能比被引用的数据活得更久。多数情况下 Editor 与开启安全检查时会报错，但运行时构建不保证不崩溃或内存损坏。常见问题是结构性变更使数据失效，因为实体被移到了另一个 chunk。`RefRW<T>` / `RefRO<T>` 在开启安全检查时会检查所含数据是否仍有效。还有没有保护的情形：`IJobEntity` 的 `Execute` 参数与查询的组件不匹配时，ECS 不检查，可能崩溃或内存损坏。

### ECS 与 Job、Burst、Collections、Mathematics 的关系

- 调度 Job：手册的 "Job system in Entities" 页列出两种方式。`IJobEntity` 方便调度；`IJobChunk` 配合 `Schedule()` 与 `ScheduleParallel()` 在主线程之外手动处理数据。主线程访问可用 `SystemAPI.Query` 的 `foreach`。
- 依赖自动管理：调度 Job 时，ECS 会跟踪哪些系统读写了哪些组件。后面系统的 `Dependency` 属性会包含前面系统已调度 Job 的句柄（条件是读写的组件有重叠）。这对应本资料 1.3 里手写的 `JobHandle` 依赖链，只是改成按组件读写自动推导。
- 自动管理有边界：手册指出这是系统级别的依赖，可能让 Job 等待它并不需要的组件上的 Job，是已知问题。`Dependency` 也不跟踪经由 `NativeArray` 等容器传递的依赖，这类依赖仍要手动用 `JobHandle.CombineDependencies` 合并。显式调用 `Schedule` 覆盖默认依赖时，ECS 不再自动合并句柄。
- Burst：`ISystem` 的三个生命周期方法可以 Burst 编译，`IJobEntity` 默认不做 Burst 编译，需要加 `[BurstCompile]`（升级指南的说明）。手册的 Safety 页也说 Entities 依赖 Burst 与原生互操作来直接访问数据。
- Collections 与 Mathematics：手册 "ECS packages" 页把它们列为同级的主要部分。Collections 提供 Job 与 Burst 代码可用的非托管容器，Mathematics 为 Burst 编译代码优化，用法同本资料其它章节。

三种方式的对比。"依据"列说明每行的来源，没有官方量化对比的地方只写定性描述。

| 维度 | 纯 Job + Burst（本项目） | MonoBehaviour / GameObject | ECS（Entities） |
| --- | --- | --- | --- |
| 数据组织 | 自己决定，如 `NativeArray`、托管类 | 数据与代码在组件类里；手册称其灵活但运行时开销大 | 数据按原型存进 chunk 的组件数组；实体不含代码 |
| 依赖管理 | 手写 `JobHandle`（见 1.3） | 手册未涉及；若在其中用 Job，则同左，自己维护句柄 | 按系统读写的组件自动推导 `Dependency`，容器依赖仍手动 |
| 主线程交互 | 自己设计交接，如本项目的 `Pump` | 本来就在主线程 | 系统在主线程 `OnUpdate`；结构性变更靠 ECB 回放 |
| 学习成本 | 概念较少（见 0.2、1.x） | 最低，Unity 常规工作流 | 概念最多：手册概念页有 8 个主题，另有 baking、subscene、Editor 窗口等 |
| 适用场景 | 少量大块数据的批处理 | 少量、逻辑各异的对象 | 大量同构实体，或需要 Physics、Netcode、Entities Graphics |

依据：第一列来自本资料 1.3、3.5 与本项目代码；第二列"手册称其灵活但运行时开销大"来自 Baking overview 页；第三列来自 Entities 手册各概念页。学习成本一行是定性判断，官方没有给出量化比较。

### baking 与 subscene

ECS 把"编辑时数据"和"运行时数据"分开。烘焙（Baking）把 Editor 里的 GameObject 数据（authoring data）转换成写入实体场景（entity scene）的实体与组件（runtime data）。手册说它不可逆，把灵活但耗性能的 GameObject 变成为性能优化的实体与组件。要点如下：

- 烘焙只发生在 Editor 里，不会在游戏运行时发生，和资源导入类似。
- 作者场景（authoring scene）里是 GameObject 与 MonoBehaviour；实体场景里是烘焙产出的 ECS 数据。
- 子场景（subscene）是对作者场景或实体场景的引用，手册说它只是方便加载实体场景的"挂接点"。子场景打开时触发实时烘焙（增量或完整），关闭时在后台异步完整烘焙。
- 自定义转换逻辑用 `Baker`（手册 Baking 页还列有 baking systems、baking phases 等主题）。

## 用法

### 最小示例

下面改写自手册升级指南里的 `IJobEntity` 示例（本资料未在 Unity 中编译，使用前请核对）。`RotationSpeed` 是手册示例里的自定义组件，不是引擎内置类型。

```csharp
// IJobEntity：Execute 的 ref 表示读写，in 表示只读。
// 手册说明 IJobEntity 默认不 Burst 编译，需要加 [BurstCompile]。
[BurstCompile]
public partial struct RotateJob : IJobEntity
{
    public float DeltaTime;

    void Execute(ref LocalTransform transform, in RotationSpeed rotationSpeed)
    {
        transform.Rotation = math.mul(
            math.normalize(transform.Rotation),
            quaternion.AxisAngle(math.up(), rotationSpeed.RadiansPerSecond * DeltaTime));
    }
}

public partial class RotateSystem : SystemBase
{
    protected override void OnUpdate()
    {
        var deltaTime = SystemAPI.Time.DeltaTime;
        // 没有手写 JobHandle：Dependency 由 ECS 按组件读写维护
        new RotateJob { DeltaTime = deltaTime }.ScheduleParallel();
    }
}
```

对照 1.2 的 `IJobParallelFor`：这里没有手动传 `NativeArray`，也没有手写 `Schedule(dependsOn)`，数据由查询出的组件提供，依赖由 `Dependency` 属性串起来。

### 学习路线

手册首页把 ECS Samples 仓库（`https://github.com/Unity-Technologies/EntityComponentSystemSamples`）列为入门材料来源，说其中有教程、样例和视频。仓库里具体有哪些目录与样例，本页没有读过（待核实）。建议的阅读顺序：

1. 手册 "ECS packages" 页，建立全局图景（本页已概括）。
2. 手册 "ECS workflow tutorial" 页。它包含四个主题：ECS 工作流简介、起步 ECS 工作流、作者与烘焙工作流、预制体实例化工作流。
3. 手册 "Entity component system concepts" 各页，即本页前半部分对应的 Entity、Component、System、World、Archetypes、Structural changes、Safety。
4. 手册 "Programming in Entities"，包括多线程代码、组件、系统、结构性变更管理、数据迭代、变换、blob asset 等主题。
5. 跑 ECS Samples 里的样例，对照手册读代码。
6. 需要时再看 Entities Graphics、Unity Physics、Netcode for Entities 各自的包手册。

## 取舍与对本项目的判断

### 什么时候该上 ECS

- 有大量结构相同的实体，需要按组件批量处理。手册在 Scenes overview 页说 ECS 能高效处理数百万实体，这类场景是它的主场（原文是"millions of entities"）。
- 需要 Unity Physics、Havok Physics、Netcode for Entities、Entities Graphics、Character Controller 这类建在 ECS 上的包。手册首页说通常不会单独使用 Entities 包，一般会配合这些包。
- 愿意接受额外的概念与工作流：世界、系统组、原型、烘焙、子场景等。

### 什么时候不该上

- 只有少量对象，或每个对象的逻辑都不同。此时 GameObject 的灵活性更划算。
- 目标只是把一批大数组并行算快，纯 Job + Burst 已经够用，不需要引入实体层。
- 大量依赖托管对象与 Unity 对象引用的场合。手册说 `ISystem` 是非托管的，`SystemBase` 有 GC 分配；非托管组件只能存某些类型的字段（见上文的对比）。

### 本项目的现状与判断

先看现状。读过的代码是 `ChunkGenerationPipeline.cs` 与 `VoxelChunk.cs`（只读）：

- `VoxelChunk` 用一个托管 `byte[] solid` 存整个区块（`SizeX * SizeY * SizeZ`）的体素，区块 XZ 为 `ChunkSize = 16`，Y 全高。
- `ChunkGenerationPipeline` 的实体数量就是区块数（`TotalChunks = chunksX * chunksZ`），每个区块是一大块连续数组，不是成千上万个带不同组件的小对象。
- 调度逻辑是：后台 `Task.Run` 采样，主线程 `Pump` 回收结果，区块自身加 ±X/±Z 四邻居都采样完才派发建网格，用 `loaded` 字典、计数器与 `maxLoadedChunks` 等做背压和释放。

判断：这条流水线的特征是"少量对象、每个对象数据量巨大、处理逻辑一致、有邻居依赖和背压"，本质是批处理，不是"大量同构小实体"。性能瓶颈在采样与建网格的计算量和数据布局，Job + Burst + `NativeArray` 已经对准了它。引入 Entities 要多学一整套概念，而且手册也说通常不会单独使用 Entities 包。因此当前阶段不建议把体素区块整体迁移到 ECS；项目虽然已经接入 Entities，体素生成仍应继续按 3.5 的路线用 Job 链替换 `Task.Run`，ECS 先用于工厂等大量同构实体。

什么时候再回头深入学 ECS：以后要做大量生物、掉落物、方块实体（成千上万个小对象，每个只带少量不同组件）时。这类负载更接近手册描述的 ECS 主场。

### 如果将来用 ECS 做体素（思路，未验证）

以下只是推想，没有写过代码，也没有核对手册里相关页面，不能当作可行方案：

- 每个体素区块对应一个实体，体素数据放进缓冲组件（`DynamicBuffer`，手册称其为可变长数组的组件）。
- 区块状态用标签组件或可启用组件表示，如"已采样""待建网格"，由系统用 `EntityQuery` 筛选，代替现在 `Pump` 里手写的状态数组。
- 邻居依赖、背压需要重新设计，`Dependency` 只按组件读写推导，不理解"四邻居都采样完"这种业务依赖（待核实）。
- 渲染走 Entities Graphics。它能否适合运行时逐区块生成、频繁更新的自定义网格（待核实）。
- 缓冲组件能否高效承载一个区块的整块体素数组（待核实）。

## 常见误解与坑

- ECS 不等于 Job。ECS 是数据组织与程序结构的模式，Job 是并行执行机制。系统的 `OnUpdate` 本身在主线程运行，是否并行取决于里面有没有调度 Job。手册也提供了不用 Job 的主线程迭代方式（`SystemAPI.Query` 的 `foreach`）。
- 不用 ECS 也能用 Job + Burst。本项目就是例子：不引用 Entities，已经有一个 `[BurstCompile]` 的 `IJobParallelFor`。
- ECS 不只是一种设计思想。手册把 Entities 描述为一套运行时框架与工作流：有世界、系统组、`EntityManager`、烘焙与子场景、Editor 窗口等。选 ECS 就是选整套工作流。
- "自动依赖管理"不等于不会出依赖问题。系统级依赖可能多等，容器依赖仍要手动合并，见上文。
- 在 Job 里直接做结构性变更是不行的，要用 `EntityCommandBuffer`。滥用结构性变更会造成同步点，抵消并行收益。
- 混淆两个 chunk：ECS 的 16 KiB 内存块，与本项目的 `VoxelChunk` 区块。
- 照着旧教程写 `Entities.ForEach` 与 `Job.WithCode`。它们在 1.4 已标过时，改用 `IJobEntity`、`SystemAPI.Query` 与 `IJob`。`IAspect` 也已过时，没有直接替代。

## 小结

- DOTS 有五个主要部分：Entities、Job system、Burst、Collections、Mathematics；ECS 包（Physics、Netcode 等）建立在它们之上。本资料覆盖后四个。
- ECS 的核心：实体是 ID，组件是数据，系统是逻辑；原型决定 chunk 内的数据布局；结构性变更只能在主线程，Job 里用 ECB。
- 系统里调度 Job 时，依赖按组件读写自动推导，容器依赖仍要手动合并。
- 本项目的体素生成仍是"每区块一大块数组"的批处理，暂不需要把区块整体 ECS 化；工厂、掉落物等大量小实体可以使用新增的 05-Entities 路线。

## 自测题

1. 官方手册说 DOTS 需要使用的 Unity 主要部分有几个，分别是什么？
   答：五个，Entities、Job system、Burst compiler、Collections、Mathematics。
2. 为什么 Job 里不能直接创建实体，应该怎么做？
   答：创建实体是结构性变更，只能在主线程做，Job 里做会使已调度的 Job 失效并产生同步点。应使用 `EntityCommandBuffer` 记录命令，之后在主线程回放。
3. ECS 自动管理的 Job 依赖有什么局限？
   答：依赖是系统级的，可能让 Job 等待它不需要的组件上的 Job；经由 `NativeArray` 等容器传递的依赖不被跟踪，仍要手动用 `JobHandle.CombineDependencies` 合并。
4. 为什么说本项目的区块生成流水线暂时不适合 ECS？
   答：它是少量区块、每块一大数组的批处理，不是大量带不同组件的同构小实体，Job + Burst 已对准瓶颈；手册也说通常不会单独使用 Entities 包。
5. "ECS 就是 Job"为什么不对？
   答：系统的 `OnUpdate` 在主线程运行，可以不调度任何 Job；反过来，不引用 Entities 也能用 Job + Burst。

## 参考

- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/index.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/ecs-packages.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/getting-started.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/ecs-workflow-tutorial.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/concepts-ecs.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/concepts-entities.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/concepts-components.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/concepts-systems.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/concepts-worlds.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/concepts-archetypes.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/concepts-structural-changes.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/concepts-safety.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/programming-entities.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/systems-comparison.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/systems-scheduling-jobs.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/scheduling-jobs-dependencies.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/systems-entityquery.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/systems-entity-command-buffers.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/conversion-intro.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/baking.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/baking-overview.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/conversion-scene-overview.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/whats-new.html
- https://docs.unity3d.com/Packages/com.unity.entities@1.4/manual/upgrade-guide.html
- https://github.com/Unity-Technologies/EntityComponentSystemSamples （手册首页给出的链接，本页只引用链接，未读仓库内容）
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkGenerationPipeline.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelChunk.cs
- D:\UnityHub\Project\程序化生成\Packages\manifest.json
- D:\UnityHub\Project\程序化生成\Packages\packages-lock.json
