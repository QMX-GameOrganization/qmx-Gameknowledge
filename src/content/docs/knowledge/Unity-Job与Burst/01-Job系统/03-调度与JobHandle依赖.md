---
title: "1.3 调度与 JobHandle 依赖"
description: 讲解 Schedule 与 JobHandle、依赖链与扇出扇入、跨帧完成策略、容器释放与 IsCompleted 轮询，并对照本项目的 ChunkGenerationPipeline。
sidebar:
  order: 3
---

> 适用版本：以 Unity 6000.x 为主线；`JobHandle` 位于引擎核心 `Unity.Jobs`，`Dispose(JobHandle)` 等容器 API 来自 Collections（本项目 Collections 6.7.0 为转发壳包，命名空间不变）。

## 要点

- `Schedule` 立刻返回 `JobHandle`，Job 不一定已开始。`Complete()` 才保证完成并让主线程安全访问数据。
- 依赖通过 `Schedule(..., dependsOn)` 传递；多个依赖用 `JobHandle.CombineDependencies` 合并。
- 两个 Job 通过同一个 `NativeContainer` 交接数据时，必须显式写依赖，否则安全系统报错。
- `Complete` 越晚越好；用 `IsCompleted` 轮询可以避免阻塞主线程。
- `Allocator.TempJob` 要在 4 帧内释放，跨帧的 Job 用 `Allocator.Persistent`。
- 容器的 `Dispose(JobHandle)` 返回新的 `JobHandle`，可把释放接在依赖链末尾。
- 退出 Play Mode、`OnDestroy`、Domain Reload 之前，必须把在途 Job `Complete` 并释放容器。

## JobHandle 基础

`JobHandle` 是 `Unity.Jobs` 里的 struct，API 文档描述为"唯一标识一个已调度的 Job"。已核实的成员：

| 成员 | 说明 |
|---|---|
| `Complete()` | 确保该 Job 完成。Job System 会把它及依赖排到队列前面，并尝试在调用线程上执行 |
| `IsCompleted` | 属性：Job 已完成返回 true，仍在跑返回 false |
| `CombineDependencies(a, b)` | 静态，合并两个 |
| `CombineDependencies(a, b, c)` | 静态，合并三个 |
| `CombineDependencies(NativeArray<JobHandle>)` | 静态，合并数组 |
| `CombineDependencies(NativeSlice<JobHandle>)` | 静态，合并切片 |
| `CompleteAll(ref a, ref b)` / `(ref a, ref b, ref c)` / `CompleteAll(NativeArray<JobHandle>)` | 静态，一次完成多个 |
| `ScheduleBatchedJobs()` | 静态，让已调度的 Job 对 worker 线程可见 |

最小用例：

```csharp
JobHandle h = job.Schedule();
// ... 做点别的 ...
if (h.IsCompleted) { /* 已完成，Complete 不会阻塞 */ }
h.Complete();   // 即使已完成也要调用，用来清理安全系统状态
```

手册明确：`Complete` 同时清理安全系统状态，不调用会造成泄漏。所以"轮询到 `IsCompleted` 为 true"之后仍然要调用 `Complete()`。

## 依赖

### 链式 A -> B -> C

```csharp
JobHandle a = jobA.Schedule();
JobHandle b = jobB.Schedule(a);     // B 在 A 完成后才会运行
JobHandle c = jobC.Schedule(b);
c.Complete();                        // 完成 c 会先保证 a、b 完成
```

手册指出：完成一个依赖其它 Job 的 Job，必须先完成它依赖的所有 Job。

### 扇出与扇入

```csharp
JobHandle gen   = generate.Schedule();                 // 产出共享数据
JobHandle left  = meshLeft.Schedule(gen);              // 扇出：两个读同一数据的 Job 可并行
JobHandle right = meshRight.Schedule(gen);
JobHandle both  = JobHandle.CombineDependencies(left, right);  // 扇入
JobHandle merge = mergeJob.Schedule(both);
merge.Complete();
```

```
          ┌──► left ──┐
 gen ─────┤           ├─► Combine ─► merge
          └──► right ─┘
```

注意：`left` 与 `right` 若都要写同一个容器，即使它们都依赖 `gen`，安全系统仍会报并发写冲突。必须把一个依赖于另一个，或让它们写不同容器。

### 为什么必须写显式依赖

当 Job A 写 `NativeArray`、Job B 读同一个，B 的 `Schedule` 没有把 A 的句柄作为依赖时，编辑器里的安全系统会抛出异常，指出该容器正被另一个 Job 使用。手册要求：调度依赖其它 Job 的 Job 时，必须通过依赖参数告诉 Job System。该检查只在启用安全检查的环境里存在（见 1.1），Player 里没有保护，所以必须靠自己写对。

## ScheduleBatchedJobs 何时需要

`Schedule` 默认只把 Job 放进本地队列。官方文档：引擎有意推迟到你手动调用 `ScheduleBatchedJobs`，因为唤醒 worker 的开销大，建议攒几个 Job 再统一调用；在循环里调度时放到循环结束后。如果在调度两个 Job 之间主线程要做大量工作，则可以在两次调度之间 flush。

```csharp
for (int i = 0; i < chunks.Length; i++)
    handles[i] = MakeJob(chunks[i]).Schedule();
JobHandle.ScheduleBatchedJobs();   // 循环后一次性让 worker 开工
```

不调用时引擎在何时自动 flush，文档没有给出完整规则，待核实；`Complete` 本身会主动推进所需的 Job（见上）。

## 帧内调度模式

手册建议的模式：尽早 `Schedule`、尽晚 `Complete`。

```csharp
void Update()      { handle = job.Schedule(); }          // 一有数据就调度
void LateUpdate()  { handle.Complete(); Consume(); }     // 帧内较晚再完成
```

| 模式 | 优点 | 代价 |
|---|---|---|
| `Update` 调度，`LateUpdate` 完成 | 结果当帧可用，容器可用 `TempJob` | 并行时间窗短，主线程可能阻塞 |
| 跨帧 `Complete`（下一帧才取结果） | 给 Job 更长时间，主线程基本不阻塞 | 结果延迟一帧或多帧；要用 `Persistent`；要管理在途状态 |
| 帧末调度、下帧使用 | 利用帧间空档（手册提到过这种用法） | 要接受一帧延迟 |

Profiler 里主线程上的等待类标记（常见名字如 `WaitForJobGroupID`，具体名称随版本变化）就是在等 Job，说明某处 `Complete` 过早或存在数据依赖，需要拆分。

## 阻塞成本与规避

- `Complete` 在 Job 未完成时会阻塞（或帮忙执行），耗时计入主线程帧时间。
- 规避方式：把 `Complete` 推后；把长 Job 拆成相互依赖的小 Job；用 `IsCompleted` 轮询，完成了再 `Complete`。
- 手册提示：Job 不会让出执行权，worker 一旦开始 Job 就会做完，所以过长的 Job 会阻塞别的独立 Job，进一步拖长主线程等待。

### 官方设计准则：Job 应在一帧内完成

Unity 手册 Create and run a job 页（6000.6 版核对）有一句设计准则：Job System 从队列取出 Job 后，在单个线程上把 `Execute` 运行一次；通常在后台线程上跑，但主线程空闲时也可能被选来运行 Job。"因此，你应该把 Job 设计成在一帧以内完成"（原文大意，用自己的话转述）。同一页的 "Avoid using long running jobs" 一节进一步解释：Job 不像线程那样会让出执行权，worker 开始后必须做完才能处理别的 Job；所以应把耗时长的 Job 拆成彼此依赖的多个小 Job，这样 Job System 同时运行的多条依赖链才有机会都推进；若 worker 全被长 Job 占满，会把主线程显式等待的重要 Job 推迟，造成本不该有的主线程停顿。对 `IJobParallelFor`，官方还建议：无法拆分时增大批大小，限制有多少 worker 参与这个长 Job。

与本项目跨帧流水线的关系（以下是我的推断，不是官方原话）：3.5 的流水线让区块生成跨多帧完成，这和"一个 Job 在一帧内完成"并不冲突。区别在于单位：一帧内完成的约束针对单个 Job，而跨帧的是"一条 Job 依赖链"或"一个区块的整个生产过程"。所以做法应是把一个区块的任务拆成"采样密度 -> 面可见性 -> 建网格数据"等多个小 Job，用 `JobHandle` 串起来，再用 `IsCompleted` 轮询跨帧收割，而不是写一个要跑很多帧的大 Job。"每个小 Job 到底该多小才算'一帧内'"，官方没有给数字，需要用 Profiler 实测（见 1.8）。

## 分配器与释放

### Allocator.TempJob 与 Persistent

根据 Collections 手册与 `Allocator` 文档：

- `Allocator.Temp` 最快，主线程上分配的 Temp 内存不能传给 Job（Job 内部可以自己做 Temp 分配）；每帧末或 Job 结束时整体丢弃，手动 `Dispose` 无效果。
- `Allocator.TempJob`：可传给 Job 的短期分配。官方规则是必须在创建后 4 帧内释放。`Native*` 容器的释放安全检查会在超过 4 帧时抛异常；`Unsafe*` 容器同样必须在 4 帧内释放，但不做检查（引自 Collections 2.1 手册，已核实；6.x 手册措辞未单独核对）。引擎本身也可能打印 "JobTempAlloc has allocations that are more than 4 frames old" 一类的警告，具体措辞随版本变化。
- `Allocator.Persistent`：最慢，但生命周期不受限，可传给 Job。

跨帧、时长不确定的 Job（例如区块生成，可能跑好几帧）一律用 `Persistent`。

### Dispose(JobHandle)

容器的 `Dispose(JobHandle inputDeps)` 返回新的 `JobHandle`：在 `inputDeps` 完成后释放容器内存与安全句柄（已在 `NativeArray<T>.Dispose` 文档核实，`NativeList<T>` 同样提供）。这样释放可以接在依赖链末尾，不用主线程等待。

```csharp
JobHandle h = job.Schedule();
JobHandle disposed = input.Dispose(h);           // 释放也成了依赖链的一环
disposed = output.Dispose(disposed);
// 之后只需要保留 disposed；或直接 JobHandle.ScheduleBatchedJobs
```

注意：结果容器如果主线程还要读，就不能提前用这种方式释放。先 `Complete`、读完、再 `Dispose()`。

## 在途 Job 与生命周期

`MonoBehaviour` 销毁、退出 Play Mode、脚本重新编译触发 Domain Reload 时，仍在运行或排队的 Job 持有对原生内存的引用。如果不处理：

- 容器没有 `Dispose`，会得到内存泄漏警告（Persistent 分配尤其明显）。
- Job 仍在读写已释放的内存，会导致崩溃或安全系统报错。具体报错文本与是否保证出现，待核实。

规范写法：

```csharp
public sealed class ChunkJobRunner : MonoBehaviour
{
    JobHandle handle;
    NativeArray<byte> solid;
    bool inFlight;

    void OnDisable()      // 也可放在 OnDestroy，二者都要保证走到
    {
        if (inFlight) handle.Complete();   // 先完成，再释放
        if (solid.IsCreated) solid.Dispose();
        inFlight = false;
    }
}
```

要点：`Complete` 先于 `Dispose`；用 `IsCreated` 防止重复释放；Domain Reload 前的 `OnDisable` 会被调用，可借此清理。

## 轮询（Pump）模式与本项目的 ChunkGenerationPipeline

阻塞等待的替代做法是：主线程每帧检查 `handle.IsCompleted`，完成了才 `Complete`、取结果、上传 Mesh、释放，同时限制在途数量。

本项目的 `ChunkGenerationPipeline`（`Assets/Scripts/WorldGen/Voxels/ChunkGenerationPipeline.cs`）就是这个思路的 Task 版本，可当作对照例子，注意它目前并不使用 Job：

- 类注释写明流程：后台线程采样密度，主线程在某区块自身与 ±X/±Z 四邻居都采样完后派发建网格任务，后台线程算顶点数据，主线程上传 Mesh 并释放不再被依赖的区块。
- 后台任务由 `Task.Run` 启动（`ScheduleSample` 与 `ScheduleMesh`），结果通过 `ConcurrentQueue`（`sampledQueue`、`meshedQueue`）和一个异常队列 `errors` 回传。
- 主线程每帧调用 `Pump(int maxUploads)`：先取回采样结果并尝试派发建网格；再最多上传 `maxUploads` 个 Mesh；再 `RetryPendingMeshes`；最后在 `samplingInFlight < maxSamplingInFlight` 且已加载区块数低于 `maxLoadedChunks` 的前提下派发新采样。`maxSamplingInFlight` 与 `maxMeshingInFlight` 都是 `workerCount * 2`，这是背压（限制在途任务数）。
- 取消靠 `CancellationTokenSource`；`Dispose` 里只调用 `Cancel()`，因为后台任务可能仍引用等待句柄。

换成 Job 时的对应关系：

| ChunkGenerationPipeline（Task） | Job 版本 |
|---|---|
| `Task.Run` 派发 | `Schedule(dependsOn)` 返回 `JobHandle` |
| `ConcurrentQueue` 回传结果 | 主线程轮询 `handle.IsCompleted`，再 `Complete` 读 `NativeContainer` |
| 异常队列 | Job 里的异常处理受限，错误码要写进容器 |
| `CancellationToken` | Job 无法中途取消，只能让 Job 尽快结束或丢弃结果 |
| `maxSamplingInFlight` 背压 | 同样需要限制在途 Job 数，否则 `Persistent` 内存积压 |
| 对象池 `ConcurrentBag` | 容器池或 `Allocator.Persistent` 复用 |

Job 方案的限制：只能使用 unmanaged 数据和 `NativeContainer`，且 `Schedule` 只能从主线程调用。当前 `ChunkDensitySampler` 使用函数图（采样器通过 `samplerFactory` 创建，每个线程一个），是否容易改成 unmanaged 数据，我没有阅读其实现，待核实。`VoxelFaceVisibilityJob` 展示了项目里已有的 Burst Job 形态。

## 完整示例：多区块流水线（伪代码）

```csharp
// 每个在途区块的状态：Persistent 容器 + 依赖链末端句柄
struct ChunkWork
{
    public int Index;
    public NativeArray<byte> Solid;      // Persistent
    public NativeArray<byte> FaceMask;   // Persistent
    public JobHandle Handle;             // 采样 -> 面可见性 的链
}

readonly List<ChunkWork> inFlight = new();
const int MaxInFlight = 8;               // 背压：限制在途区块数

void Update()
{
    // 1) 收割：轮询，不阻塞
    for (int i = inFlight.Count - 1; i >= 0; i--)
    {
        var w = inFlight[i];
        if (!w.Handle.IsCompleted) continue;
        w.Handle.Complete();             // 已完成，立即返回并清理安全状态
        UploadMesh(w.Index, w.Solid, w.FaceMask);   // 主线程独占的 Unity API
        w.Solid.Dispose();
        w.FaceMask.Dispose();
        inFlight.RemoveAt(i);
    }

    // 2) 派发：在途数量未满才发新任务
    while (inFlight.Count < MaxInFlight && TryNextChunkIndex(out int idx))
    {
        var solid = new NativeArray<byte>(VolumeSize, Allocator.Persistent);
        var mask  = new NativeArray<byte>(VolumeSize, Allocator.Persistent);

        JobHandle sample = new SampleDensityJob { Solid = solid, /*...*/ }
                               .ScheduleParallel(VolumeSize, 256, default);
        JobHandle faces  = new VoxelFaceVisibilityJob { Solid = solid, FaceMask = mask,
                                  Width = W, Height = H, Depth = D }
                               .Schedule(VolumeSize, 256, sample);   // 依赖 sample

        inFlight.Add(new ChunkWork { Index = idx, Solid = solid, FaceMask = mask, Handle = faces });
    }
    JobHandle.ScheduleBatchedJobs();     // 本帧派发完统一 flush
}

void OnDestroy()
{
    foreach (var w in inFlight) { w.Handle.Complete(); w.Solid.Dispose(); w.FaceMask.Dispose(); }
    inFlight.Clear();
}
```

说明：`SampleDensityJob` 是假想的 Job；`VoxelFaceVisibilityJob` 在项目里是 `internal`，若在其它程序集使用需要考虑可见性。邻居区块的面可见性（跨区块边界）在项目里由 `VoxelMeshBuilder.BuildChunkData` 以邻居区块参与计算，示例为简化未体现。

## 常见坑

- 忘记在轮询到完成后调用 `Complete()`，安全系统状态不清理。
- 用 `TempJob` 容器放跨多帧的 Job，4 帧后触发警告或异常。
- 在 Job 仍在跑时 `Dispose` 容器，或在 `Complete` 之前读写。
- `OnDestroy` 里漏掉在途区块，退出 Play Mode 时报泄漏。
- 同一个容器同时被两个无依赖关系的 Job 写，安全系统报错。
- 每个 Job 后立刻 `Complete`，把并行变回串行。
- 从 `Task.Run` 的线程里调用 `Schedule`（只能主线程）。

## 小结

`JobHandle` 把"调度、依赖、完成、释放"串成一条链。优先让主线程晚点 `Complete`、用 `IsCompleted` 轮询、用 `Dispose(JobHandle)` 把释放接入链条，同时限制在途数量并保证所有退出路径都先 `Complete` 再释放。`ChunkGenerationPipeline` 的 `Pump` 与背压结构可以直接迁移到 Job 版本。

## 自测题

1. 为什么轮询到 `IsCompleted == true` 后仍要调用 `Complete()`？答：`Complete` 会清理安全系统状态，不调用会泄漏；此时它不会阻塞。
2. `JobHandle.CombineDependencies` 有哪几种重载？答：两个句柄、三个句柄、`NativeArray<JobHandle>`、`NativeSlice<JobHandle>`。
3. `Allocator.TempJob` 的释放期限？跨多帧的 Job 该用什么？答：4 帧内；用 `Allocator.Persistent`。
4. `array.Dispose(handle)` 返回什么，有什么好处？答：返回新的 `JobHandle`，释放在依赖完成后进行，不阻塞主线程。
5. `ScheduleBatchedJobs` 的作用？答：让本地队列中的 Job 对 worker 可见，推迟到批量调度后调用以减少唤醒开销。

## 参考

- https://docs.unity3d.com/Manual/job-system-creating-jobs.html
- https://docs.unity3d.com/Manual/job-system-job-dependencies.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.JobHandle.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.JobHandle.Complete.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.JobHandle.IsCompleted.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.JobHandle.CombineDependencies.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.JobHandle.CompleteAll.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.JobHandle.ScheduleBatchedJobs.html
- https://docs.unity3d.com/ScriptReference/Unity.Collections.NativeArray_1.Dispose.html
- https://docs.unity3d.com/ScriptReference/Unity.Collections.Allocator.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.1/manual/allocator-overview.html
- https://docs.unity3d.com/Packages/com.unity.jobs@0.1/manual/scheduling_a_job_from_a_job.html
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkGenerationPipeline.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelFaceVisibilityJob.cs
