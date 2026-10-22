---
title: "3.5 调度管线与 Profiling"
description: 解读现有 Task.Run 流式区块管线的队列、背压与清理，设计 Job 链版本的在途上限、缓冲池、邻居生命周期与安全收尾，并给出 Profiler 埋点与对比表。
sidebar:
  order: 5
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x / Collections 2.x / Mathematics 1.3.x 为主线；本项目的 Unity 7000.0.0a8 中 Burst 2.0.0 与 Collections 6.7.0 是转发到引擎内置模块的壳包。核实不了的标"待核实"。
>
> 本章代码为教学骨架，未在 Unity 内编译，复制前核对 API 与项目现状。

## 目标与现状

目标：把 `ChunkGenerationPipeline` 里"后台任务算数据、主线程上传"的结构，演进为"每个区块一条 Job 依赖链、主线程每帧轮询完成并 Apply"，同时保留现有的背压与清理语义，并用 Profiler 给出可比较的数据。

先说结论：不要一次替换整条管线。密度函数树还是托管对象图，现在不能 Burst（见 3.2 噪声与密度函数的 Burst 化），所以采样先留在 `Task.Run`，只把可见性与网格换成 Job（见下文"过渡方案"）。

### 现有管线的数据流（以代码为准）

```
                      主线程 (Pump 的调用者; 所有调度状态只在这里改)
 +---------------------------------------------------------------------------------+
 |  nextToSample ──ScheduleSample──> Task.Run ──────────────┐                      |
 |                                                          v                      |
 |                                                  sampledQueue (ConcurrentQueue) |
 |  Pump: sampledQueue.TryDequeue                                                  |
 |     loaded[index] = chunk;  samplingInFlight--                                  |
 |     TryScheduleMesh(自己 + 四邻居)                                               |
 |         IsReady(±X, ±Z) 全满足? 否 -> 等;  meshingInFlight 满? -> pendingMesh   |
 |         ScheduleMesh: 取 center/posX/negX/posZ/negZ 引用 ──> Task.Run ─┐         |
 |                                                                        v         |
 |  Pump: meshedQueue.TryDequeue (最多 maxUploads 个非空)         meshedQueue       |
 |     uploadMesh(data)  -> VoxelWorldPreview.AddChunkObject                        |
 |     meshingInFlight--;  meshDone[index]=true;  data 回 meshDataPool              |
 |     TryRelease(自己 + 四邻居): 自己和四邻居都 Done -> loaded.Remove               |
 |  Pump: RetryPendingMeshes();  再按背压派发 ScheduleSample                         |
 +---------------------------------------------------------------------------------+
   后台: samplerPool / meshDataPool (ConcurrentBag), errors (ConcurrentQueue),
         workCompleted (AutoResetEvent), cancellation (CancellationTokenSource)
```

每个区块在管线里的生命周期：

```
未采样 -> 采样中 -> 已采样(loaded) -> 等四邻居就绪 -> 建网格中 -> 结果等待上传 -> 已上传(meshDone)
                                                                         -> 自己与四邻居都 Done 后从 loaded 移除
```

### 并发要点

| 要点 | 代码里的做法 |
| --- | --- |
| 线程模型 | `Task.Run` 跑采样与顶点计算；`Pump` 在主线程（协程每帧，或编辑器同步循环）调用 |
| 结果回传 | `ConcurrentQueue`：`sampledQueue`、`meshedQueue`；异常进 `errors` |
| 调度状态 | `loaded`、`meshScheduled`、`meshDone`、`pendingMesh`、各计数器，只在主线程访问，不加锁 |
| 采样器复用 | `samplerPool`（`ConcurrentBag<ChunkDensitySampler>`），采样器含可变状态（列缓存），不能共享，所以按任务取还 |
| 顶点缓冲复用 | `meshDataPool`（`ConcurrentBag<ChunkMeshData>`） |
| 在途上限 | `workerCount = max(1, n)`；`maxSamplingInFlight = 2 * workerCount`，`maxMeshingInFlight = 2 * workerCount` |
| 背压 | `maxLoadedChunks = chunksX * 4 + maxSamplingInFlight`；派发采样的条件是 `samplingInFlight < maxSamplingInFlight` 且 `loaded.Count + samplingInFlight < maxLoadedChunks` |
| 上传限流 | `Pump(maxUploads)`：每帧最多处理 `maxUploads` 个非空网格；`VoxelWorldPreview` 传 `chunksPerFrame`（默认 4），编辑器同步路径传 `int.MaxValue` |
| 取消 | `CancellationTokenSource`；采样任务在开始时与入队前检查 `token.IsCancellationRequested`，网格任务只在开始时检查；`Dispose` 只调用 `Cancel`，不等待任务 |
| 同步等待 | 编辑器路径用 `AutoResetEvent workCompleted` 的 `WaitForWork(50)` 避免空转 |

### 背压数值的含义

按行扫描（`index` 递增，`x` 先变），区块在被采样后要等 `±X` 与 `±Z` 邻居都采样完才能建网格，也要等四邻居的网格都完成才能释放。所以稳态下要同时保留大约三行区块；代码注释说明 `chunksX * 4` 是约 3 行驻留再加一行乱序余量，`+ maxSamplingInFlight` 给在途采样留位置。

用公式写：`maxLoadedChunks = 4 * chunksX + 2 * workerCount`。例如 `worldSize.x = 128` 时 `chunksX = 8`，上限是 `32 + 2 * workerCount`（`workerCount` 默认为 CPU 核心数减 1，随机器而变）。这是"在内存里最多同时有多少个已采样区块"的上限，每个区块的 `solid` 数组约 `16 * 16 * SizeY` 字节（`byte[]`，每体素 1 字节；`SizeY = 384` 时是 98304 字节）。

从代码里读到的几个细节，改造时要保持或有意改变：

- `meshingInFlight--` 发生在主线程从 `meshedQueue` 取出结果时，而不是后台任务完成时。所以"已算完、等上传"的结果也占用 `maxMeshingInFlight`。主线程上传慢，会自然阻止继续派发网格任务，这是一层隐式背压。
- 空网格（`data.IsEmpty`）不调用 `uploadMesh`，也不占 `maxUploads` 额度，所以一帧里可以处理任意多个空网格结果。
- `TryScheduleMesh` 遇到 `meshingInFlight >= maxMeshingInFlight` 时只入 `pendingMesh`，不设 `meshScheduled`，由 `RetryPendingMeshes` 补发；同一个索引可能被多次入队，用 `meshScheduled` 去重。
- 释放用"自己和四邻居都 `meshDone`"判定（`TryRelease` 与 `Done`），世界外按已完成处理。
- 后台任务异常进 `errors`，`Pump` 里取出后 `Cancel()` 并包装抛出。
- `Dispose` 之后已经在跑的任务不会被打断，只会在检查 token 的位置退出，且网格任务入队 `meshedQueue` 之前没有再检查 token；但此时管线对象已被丢弃，结果不会再被消费。

### 重新生成与清除（`VoxelWorldPreview`）

```
StartGeneration -> ValidateWindow -> CancelGeneration() -> StartCoroutine(GenerateOverFrames)
CancelGeneration: StopCoroutine; activePipeline?.Dispose(); IsGenerating=false
GenerateOverFrames: CreatePipeline() ; 循环 Pump(chunksPerFrame) ; yield return null; finally pipeline.Dispose()
CreatePipeline: ClearGeneratedMeshes()  <- 销毁上一轮 Mesh 和 chunkRoot
OnDisable -> CancelGeneration();  OnDestroy -> Clear() 并释放材质
```

注意 `StopCoroutine` 不会进协程里的 `finally`，所以 `CancelGeneration` 手动复位 `IsGenerating`，注释里已写明。

## 改造设计：Job 链

### 每个区块一条依赖链

```
        [采样 Job]  ->  [可见性 Job]  ->  [计数 Job]        <- 阶段 1: 全部在工作线程
         (3.2/3.3)       (3.1)            (3.4 Job1)
                                              |
                          主线程: IsCompleted 轮询 -> Complete -> 读 FaceCount
                          AllocateWritableMeshData / SetVertexBufferParams ...
                                              |
                                      [写网格 Job] (3.4 Job2)     <- 阶段 2
                                              |
                          主线程: IsCompleted 轮询 -> Complete
                          ApplyAndDisposeWritableMeshData -> 创建子 GameObject
```

图中"采样 Job 到可见性 Job"的箭头只表示数据先后：可见性 Job 要读自己和四邻居的采样结果，全 Job 版里它的 `dependsOn` 是这五个采样 handle 的 `JobHandle.CombineDependencies`（见 3.1），不是单条链；过渡方案里采样仍在 `Task.Run`，没有 handle，阶段 1 只含可见性与计数。

用依赖串联同一阶段内的 Job：`handle = visJob.Schedule(sampleHandle)`，`handle = countJob.Schedule(handle)`（见 1.3 调度与 JobHandle 依赖）。采样与网格之间隔着"四邻居就绪"这个跨区块的条件，所以不能在调度时就把整条链挂死，而是沿用现在的做法：主线程在区块"满足条件"的时刻才调度网格阶段。链的含义是"同一个区块内部的先后"，跨区块依赖仍由主线程状态机判断（`loaded`/`IsReady` 那一套逻辑可以原样保留）。

阶段 1 和阶段 2 之间有一个主线程同步点，原因见 3.4：`SetVertexBufferParams` 需要面数。也可以尝试在 Job 内调用 `MeshData.SetVertexBufferParams`，把整条链连起来，这个用法在社区示例中出现过，官方文档是否保证未核实（待核实），先不依赖。

### 每帧 Pump 的轮询逻辑

```
Pump():
  1. 遍历在途区块列表 (数组/链表, 不要每帧分配)
       if (state == Stage1 && handle.IsCompleted) { handle.Complete(); 读结果; 分配 MeshData; 调度阶段 2 }
       if (state == Stage2 && handle.IsCompleted) { handle.Complete(); 加入"待 Apply"列表 }
  2. 从"待 Apply"取最多 maxApplyPerFrame 个: 批量 ApplyAndDisposeWritableMeshData; 创建 GameObject
  3. 对已完成区块执行引用计数释放 (自己 + 四邻居)
  4. 按背压派发新的采样 (数量受 maxInFlight 与缓冲池空闲槽限制)
```

要点：

- `JobHandle.IsCompleted` 只是查询，返回 true 之后仍然必须调用 `Complete()`，这样安全系统才会释放对容器的占用（见 1.3 调度与 JobHandle 依赖、1.6 安全系统与竞争条件）。此时 Job 已经跑完，`Complete()` 不会阻塞。
- `Schedule` 后 Job 不一定立刻被提交给工作线程（有批量提交机制，`JobHandle.ScheduleBatchedJobs()` 可显式刷新）。是否需要手动刷新，按 Profiler 里 Job 的起始时间与主线程调度时刻的间隔判断（待核实）。
- 主线程会被阻塞的地方只应该有两个：同步路径的 `Complete()`（等不到才会阻塞，因为先查了 `IsCompleted`），以及 Apply 本身。

### 在途上限与 Persistent 缓冲池

现状的 `maxSamplingInFlight`、`maxMeshingInFlight`、`maxLoadedChunks` 要对应到缓冲池容量。思路：预分配固定数量的"区块槽"，没有空闲槽就不派发新的采样，槽数即背压。

```
ChunkSlot (Persistent 分配, 启动时一次分配 N 个, 退出时全部 Dispose)
  NativeArray<byte> Solid       // SizeX*SizeY*SizeZ, 与 VoxelChunk.solid 同索引 x + SizeX*(y + SizeY*z)
  NativeArray<byte> FaceMask    // 同长度
  NativeArray<int>  FaceCount   // 长度 1
  int  Refs                     // 引用计数
  JobHandle Handle; State; ChunkIndex
```

- 槽数 `N` 对应现有的 `maxLoadedChunks = 4 * chunksX + 2 * workerCount`；先用同一个公式，再按 Profiler 里的峰值调。
- 每个槽的内存是 `2 * SizeX * SizeY * SizeZ` 字节加零头（`Solid` 加 `FaceMask`），总量 `N * 2 * 16 * 16 * SizeY` 字节，是固定的 Persistent 开销，不随世界大小变化。若可见性 Job 采用 3.1 的方案 B，每个在途的可见性 Job 还要一份 padded 缓冲（约比 `Solid` 多 27%），它不在槽里，需要另算或另池化。
- 用 `Allocator.Persistent`：这些缓冲活得比 4 帧久，`TempJob` 的生命周期（要求较短时间内释放，见 1.5 内存分配器与生命周期）不适合。
- 网格用的 `MeshDataArray` 不是池化对象，每次 `AllocateWritableMeshData` 申请，Apply 时释放。

### 四邻居依赖与引用计数

现状：`ScheduleMesh` 在主线程取好 `center/posX/negX/posZ/negZ` 的引用，区块在本任务完成（`meshDone`）前不会被释放。Job 世界里完全同构，只是引用从 `VoxelChunk` 变成槽里的 `NativeArray<byte>`：

- 邻居数据以 `[ReadOnly] NativeArray<byte>` 传入 Job（世界外邻居用一个长度为 0 的 `NativeArray` 或一个"全空气"标志位，Job 里判断，见 3.1）。
- 邻居槽在使用它的 Job 运行期间必须保持存活，且不能被改写。这由"邻居都已采样完才调度网格"保证，和 `IsReady` 同一条规则。
- 引用计数代替 `Done(...)` 全检查：区块 `c` 的槽初始 `Refs = 1 + 在世界内的邻居数`（自己的网格，加每个邻居的网格都要读我）。每当区块 `d` 的网格阶段全部完成（含 Apply），对 `d` 自己和它的每个世界内邻居的槽各 `Refs--`；`Refs == 0` 时把槽还给空闲列表。这与现状 `TryRelease` 的结果相同，但是 O(1) 且不需要每次 5 个 `Done` 查询。
- 同一个槽被多个 Job 同时只读是允许的（都标 `[ReadOnly]`）；写入（采样）只发生在槽被取出之后、任何 Job 读取之前（见 1.6 安全系统与竞争条件）。

### 重新生成、清除与退出

规则：只要有 Job 还可能在读写某个 `NativeArray`，就不能 `Dispose` 它（见 1.3 与 1.5）。

```
Cancel / 重新生成 / 清除 / OnDisable / OnDestroy:
  1. 停止派发新工作 (置 cancelled 标志, 不再进入 Pump 的派发步骤)
  2. 对所有在途区块: handle.Complete()     // 必须先等完, 不能直接 Dispose
  3. 对所有未 Apply 的 MeshDataArray: Dispose() 或 Apply 到临时 Mesh 后销毁   // 防泄漏
  4. 所有槽的 Native 缓冲 Dispose()
  5. 销毁已创建的 Mesh 和 GameObject (沿用 ClearGeneratedMeshes)
```

对应现有代码的位置：

| 现有位置 | 现状 | Job 版需要补的事 |
| --- | --- | --- |
| `VoxelWorldPreview.CancelGeneration` | `StopCoroutine` 加 `activePipeline?.Dispose()`（只 `Cancel`） | 管线 `Dispose` 里同步执行上面 2 到 4 步 |
| `OnDisable` | `CancelGeneration()` | 同上，Job 版必须 `Complete` 在途 Job |
| `OnDestroy` | `Clear()` 加释放材质 | 保持，且确认管线已 `Dispose` |
| 进入/退出 Play Mode | 域重载下后台任务随域被丢弃 | 关闭域重载时（Enter Play Mode 选项）Persistent 内存不会自动回收，更要保证 `OnDisable`/`OnDestroy` 清理到位（Play Mode 选项的具体行为待核实） |
| 异常（`errors` 非空） | `Cancel()` 后抛出 | 抛出前同样执行清理，避免泄漏 |

注意：现有 `Dispose` 不等待任务，因为托管任务被丢弃后只由 GC 回收；Native 内存没有 GC，所以 Job 版的 `Dispose` 必须等待并释放，两者语义不同，这是迁移时最容易漏的一点。

## 过渡方案：Task.Run 与 Job 混合

采样要调用 `IDensityFunction.Sample`，这是托管接口调用，现在不能 Burst（见 3.2）。建议分三步：

1. 保持采样在 `Task.Run`，仍写出 `VoxelChunk`（托管 `byte[]`）。`Pump` 里在主线程把 `RawSolid` 拷到槽的 `Solid`（`NativeArray<byte>.CopyFrom(byte[])`），然后调度可见性 Job 和计数 Job。这样不会让非 Job 线程直接写 `NativeArray`（那样绕开了安全系统的约定，可行性待核实）。主线程拷贝的耗时用 Profiler 看，是 `16 * 16 * SizeY` 字节的 memcpy。
2. 网格阶段 2 换成 `MeshData` 直写（3.4），去掉 `ChunkMeshData` 与 `meshDataPool`，`uploadMesh` 回调的参数由 `ChunkMeshData` 改成已 Apply 的 `Mesh`。
3. 等 3.2/3.3 的密度与插值 Job 化之后，再把采样阶段换成 Job，并去掉主线程拷贝，`samplerPool` 也随之消失。

每一步都保持"能和上一步逐区块对比顶点数"，出问题时可以回退一步。

## 代码骨架

```csharp
using System.Collections.Generic;
using Unity.Collections;
using Unity.Jobs;
using Unity.Profiling;
using UnityEngine;

public sealed class JobChunkPipeline : System.IDisposable
{
    enum State { Free, Sampling, Stage1, Stage2, ReadyToApply, Done }

    sealed class Slot
    {
        public NativeArray<byte> Solid, FaceMask;
        public NativeArray<int> FaceCount;
        public int Refs, ChunkIndex;
        public JobHandle Handle;
        public State State;
        public Mesh.MeshDataArray MeshArray; // 阶段 2 持有
    }

    static readonly ProfilerMarker MPump = new ProfilerMarker("ChunkPipeline.Pump");
    static readonly ProfilerMarker MPoll = new ProfilerMarker("ChunkPipeline.Poll");
    static readonly ProfilerMarker MAlloc = new ProfilerMarker("ChunkPipeline.AllocMeshData");
    static readonly ProfilerMarker MApply = new ProfilerMarker("ChunkPipeline.Apply");
    static readonly ProfilerMarker MCopy = new ProfilerMarker("ChunkPipeline.CopySolid");

    readonly Slot[] slots;
    readonly Stack<Slot> free = new Stack<Slot>();
    readonly List<Slot> inFlight = new List<Slot>();
    bool disposed;

    public JobChunkPipeline(int slotCount, int chunkVoxels)
    {
        slots = new Slot[slotCount];
        for (int i = 0; i < slotCount; i++)
        {
            slots[i] = new Slot
            {
                Solid = new NativeArray<byte>(chunkVoxels, Allocator.Persistent, NativeArrayOptions.UninitializedMemory),
                FaceMask = new NativeArray<byte>(chunkVoxels, Allocator.Persistent, NativeArrayOptions.UninitializedMemory),
                FaceCount = new NativeArray<int>(1, Allocator.Persistent),
            };
            free.Push(slots[i]);
        }
    }

    public void Pump(int maxApplyPerFrame)
    {
        using var _ = MPump.Auto();
        // 1. 轮询: IsCompleted 为 true 后仍要 Complete()
        using (MPoll.Auto())
        {
            for (int i = 0; i < inFlight.Count; i++)
            {
                var s = inFlight[i];
                if ((s.State == State.Stage1 || s.State == State.Stage2) && s.Handle.IsCompleted)
                {
                    s.Handle.Complete();
                    if (s.State == State.Stage1) { /* 读 FaceCount, 分配 MeshData, 调度阶段 2 */ }
                    else s.State = State.ReadyToApply;
                }
            }
        }
        // 2. 批量 Apply 与 3. 引用计数释放 与 4. 背压派发: 逻辑见正文, 省略
    }

    public void Dispose()
    {
        if (disposed) return;
        disposed = true;
        foreach (var s in inFlight) s.Handle.Complete();        // 先等完所有 Job
        // 未 Apply 的 MeshDataArray 也要 Dispose (阶段 2 持有者), 此处省略逐个判断
        foreach (var s in slots)
        {
            if (s.Solid.IsCreated) s.Solid.Dispose();
            if (s.FaceMask.IsCreated) s.FaceMask.Dispose();
            if (s.FaceCount.IsCreated) s.FaceCount.Dispose();
        }
    }
}
```

骨架里 `ProfilerMarker` 来自 `Unity.Profiling`，`Auto()` 返回的作用域结构支持 `using`。`Mesh.MeshDataArray` 作为字段保存的写法没有逐项核实，也可以改成局部变量加批次结构（待核实）。

## Profiling 方法

项目现状：`Assets/Scripts` 下没有 `ProfilerMarker`。现有的诊断只有 `LogCompletion` 打出的一行日志：`chunks`、`solid`、`workers`、`peakLoadedChunks`、`sampleCpu`、`meshCpu`、`elapsed`。其中 `sampleCpu` 与 `meshCpu` 是所有后台任务耗时之和（CPU 时间，不是墙钟），`elapsed` 是 `wallTimer` 的墙钟。Job 版本要有可比的数据，需要埋点。

### 埋点位置建议

| 位置 | 标记名 | 看什么 |
| --- | --- | --- |
| `Pump` 整体 | `ChunkPipeline.Pump` | 每帧主线程总开销 |
| 轮询与 `Complete` | `ChunkPipeline.Poll` | `Complete` 是否在阻塞（应接近 0） |
| 主线程拷贝 `Solid` | `ChunkPipeline.CopySolid` | 过渡方案第一步的额外成本 |
| `AllocateWritableMeshData` 与 `SetVertexBufferParams` | `ChunkPipeline.AllocMeshData` | 阶段间同步点的成本 |
| `ApplyAndDisposeWritableMeshData` 与 GameObject 创建 | `ChunkPipeline.Apply` | 每帧 Apply 耗时，决定 `chunksPerFrame` 取值 |
| 各 Job 自身 | 在 Timeline 里直接看 Job 条 | Job 并行度、各 Job 时长 |

### Timeline 里看什么

在 Profiler 的 Timeline 视图下，选主线程和各 Worker 线程：

- Job 并行度：同一时间点有几个 Worker 在跑你的 Job，是否有空闲 Worker 而队列里仍有工作（若有，说明调度太保守，在途上限偏低）。
- 主线程 `Complete` 等待：`Poll` 标记里是否出现长条，或有 `JobHandle.Complete` 对应的等待条；理想情况应该看不到。
- 每帧 Apply 耗时：`Apply` 标记的总和，是否让帧时间超预算。
- 采样阶段在 Task 线程时，Timeline 里这部分显示为线程池线程的工作，Job 的 Worker 与线程池线程会争用 CPU 核（竞争程度需要实测）。
- Memory：用 Profiler 的内存模块或 Memory Profiler 看峰值，包括 Native、GfxDriver（网格显存）与 Mono 堆。

### 需要记录的数据表

每个场景（建议固定 `seed`、`worldSize`、`sampleOrigin`、`voxelSize`、`cellInterpolation`、`workerThreads`、`chunksPerFrame`）至少测三次取中位数。空白表留给读者填：

| 指标 | 现状（Task.Run） | 混合（Task 采样 + Job 网格） | 全 Job（待 3.2/3.3 完成后） |
| --- | --- | --- | --- |
| 总墙钟耗时（`elapsed`，ms） | | | |
| 采样耗时（CPU 合计，ms） | | | |
| 可见性/网格耗时（CPU 合计，ms） | | | |
| 主线程每帧 `Pump` 平均 / 最大（ms） | | | |
| 主线程每帧 `Apply` 平均 / 最大（ms） | | | |
| 主线程 `Complete` 等待合计（ms） | | | |
| 峰值在途区块数 | | | |
| 峰值已加载区块数（`PeakLoadedChunks`） | | | |
| 峰值内存：托管堆（MB） | | | |
| 峰值内存：Native（MB） | | | |
| GC 分配次数 / 字节（生成期间） | | | |
| 帧率最低值（FPS） | | | |
| 总三角形 / 顶点（对照正确性） | | | |

记录注意：在编辑器里测会受 Burst 同步编译、安全检查、泄漏检测影响，要关闭这些再测或者另做一个无安全检查的构建（见 2.5 Burst Inspector 与调试）。第一次运行包含 Burst 编译，丢弃。

## 风险清单

| 风险 | 表现 | 预防与排查 |
| --- | --- | --- |
| 安全系统报错 | 写冲突、读写同一容器的 InvalidOperationException | 邻居用 `[ReadOnly]`；同一个 `NativeArray` 同一时刻只被一个写 Job 持有（见 1.6） |
| 泄漏 | 控制台出现 NativeContainer 未释放的警告 | `Dispose` 里先 `Complete` 再释放；`MeshDataArray` 未 Apply 要 Dispose；开泄漏检测并反复生成、清除 |
| 邻居提前释放 | Job 读到被复用的槽，网格错乱 | 引用计数而不是自己的 `Done`；加断言：槽 `Refs` 不为负、释放时无在途 Job |
| 主线程阻塞 | 帧时间尖峰，`Complete` 长条 | 先 `IsCompleted` 再 `Complete`；限制每帧 Apply 数；避免在 Pump 里同步等 |
| 内存峰值 | 槽数过大或 Apply 前积压过多 | 槽数即上限；监控峰值在途区块；`MeshDataArray` 批量不宜过大 |
| 非 Job 线程写 NativeArray | 难以复现的错误或安全检查失效 | 过渡方案由主线程拷贝，不让 Task 线程直接写（待核实可行性） |
| 重新生成时的残留 | 新旧管线并存，旧结果污染 | 旧管线 `Dispose` 同步完成后再创建新管线；`ClearGeneratedMeshes` 保持在创建之前 |
| 域重载关闭时 | Persistent 内存跨 Play 会话残留 | 在 `OnDisable`/`OnDestroy` 清理；是否有额外回调需求待核实 |
| 异常 | `Pump` 抛出后留下半成品状态 | 抛出前先清理，保持 `IsGenerating` 复位 |

## 小结

- 现有管线：`ConcurrentQueue` 回传、主线程独占调度状态、`maxLoadedChunks = 4 * chunksX + 2 * workerCount` 做背压、`meshingInFlight` 在主线程出队时才减、`Dispose` 只取消不等待。
- Job 版本：每区块两个阶段（可见性与计数，写网格），阶段间由主线程做一次同步；`IsCompleted` 轮询后必须 `Complete`。
- 缓冲用固定数量的 `Persistent` 槽，槽数就是背压，邻居用只读 `NativeArray` 加引用计数保证存活。
- 清理的核心差别：Native 内存没有 GC，`Dispose` 必须先 `Complete` 再释放。
- 过渡先换网格阶段，采样留在 `Task.Run`，等 3.2 和 3.3 完成后再迁。
- 没有数据就没有结论：先加 `ProfilerMarker`，用同一个表比较三个阶段。

## 自测题

1. `JobHandle.IsCompleted` 返回 true 后，为什么还要调用 `Complete()`？
   答：为了让安全系统释放该 Job 对容器的占用，并让后续主线程访问合法；此时 `Complete()` 不会阻塞。
2. 现有管线里 `meshingInFlight--` 为什么在主线程出队时才发生，这有什么效果？
   答：它统计"已派发但还没被主线程取走"的网格任务，所以上传慢会阻止派发更多网格任务，形成一层隐式背压。
3. 为什么 Job 版的 `Dispose` 不能照抄现有的 `Dispose`？
   答：现有 `Dispose` 只取消托管任务，内存交给 GC；Native 缓冲没有 GC，且可能仍被 Job 使用，必须先 `Complete` 再 `Dispose`。
4. 邻居槽的引用计数初始值是多少，何时递减？
   答：`1 + 世界内邻居数`；每当自己或任一世界内邻居的网格阶段完成，就对相关槽各减 1，到 0 时归还。
5. 为什么采样先留在 `Task.Run` 而不直接 Job 化？
   答：密度函数树是托管对象图、接口虚调用，现在不能 Burst，需要先按 3.2 和 3.3 改写。

## 参考

- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkGenerationPipeline.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelWorldPreview.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelChunk.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkDensitySampler.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelMeshBuilder.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelFaceVisibilityJob.cs
- https://docs.unity3d.com/ScriptReference/Mesh.ApplyAndDisposeWritableMeshData.html
- https://docs.unity3d.com/ScriptReference/Mesh.MeshData.html

