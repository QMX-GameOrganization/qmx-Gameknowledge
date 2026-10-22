---
title: "1.10 Job 之外的并发方案"
description: 对比 Job+Burst、Task.Run、Thread、协程与 async/await（含 Awaitable）的适用场景，给出选型流程，并客观分析本项目 ChunkGenerationPipeline 的现状与迁移方向。
sidebar:
  order: 10
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x / Collections 2.x / Mathematics 1.3.x 为主线；Unity 6.4 起 Collections 作为核心包随编辑器分发；本项目的 Unity 7000.0.0a8 中 Burst 2.0.0 与 Collections 6.7.0 是转发（shim）壳包，API 仍在 `Unity.Burst` / `Unity.Collections` 命名空间。`Awaitable` 的页面核对自 Unity 6.6（6000.6）文档；该类型随 Unity 2023.1 引入（2023.1 的 Scripting API 已有 `Awaitable` 页），Unity 6（6000.x）起均可用。

## 要点

- Job System 不是 Unity 里唯一的并发手段，但它是唯一能和 Burst 结合、由引擎统一调度线程数的那一个。
- `Task.Run` / `Thread` 跑的是普通托管代码：灵活，可以用任意 C# 类型，但不能用 Burst，也不能碰 Unity API，还会产生 GC 垃圾。
- 协程（Coroutine）不是并发：它只是把主线程上的工作切成多帧。
- `Awaitable` 是 Unity 提供的、对 Unity 友好的 async/await 返回类型，用来在主线程与后台线程之间切换，同样不让托管代码变快。
- 两套线程池（.NET 线程池与 Unity worker 线程）同时吃满 CPU 时会互相争核心，应当有意识地分配并发预算。
- 本项目当前用 `Task.Run` + `ConcurrentQueue` + 背压。纯数据的网格计算适合迁到 Job+Burst，依赖托管密度函数树的采样暂时只能留在 Task 里。

## 各方案速览

### Thread 与 ThreadPool

- `System.Threading.Thread`：自己创建线程，生命周期自己管。适合长期运行的后台循环（如网络、文件监听）。频繁创建销毁代价高，不适合成千上万个小任务。
- `ThreadPool`：.NET 线程池，复用线程。`Task.Run` 默认把委托排到线程池。线程池会按需增减线程数，数量不由 Unity 控制。

### Task 与 Task.Run

`Task.Run(() => ...)` 把一个委托丢给线程池，返回 `Task`，可以 `await`，可以带 `CancellationToken`，异常会被捕获到 `Task` 上（不 `await` 也不检查就会被吞掉）。每个 Task 和闭包是托管堆对象，大量创建会有 GC 压力。

### async / await 与 SynchronizationContext

Unity 手册（Awaitable completion and continuation 一页）说明：Unity 用自定义的 `UnitySynchronizationContext` 取代默认的 `SynchronizationContext`，使 .NET `Task` 的延续（continuation）默认回到主线程。从主线程调用返回 `Task` 的方法，延续会被投递到 `UnitySynchronizationContext`，在下一帧的 `Update` 阶段于主线程运行；从后台线程调用，则在线程池线程上完成。所以 `await Task.Run(...)` 之后可以安全地回到主线程访问 Unity API（前提是这个 `async` 方法本身是在主线程上开始的），但要等到下一次主线程更新。反过来，在 `Task.Run` 的委托内部不能碰 Unity API。

### Awaitable

`UnityEngine.Awaitable`（Scripting API 已核对）：自定义的可 `await` 类型，也可以作为 `async` 方法的返回类型。文档说明它通常是 Unity 中 .NET `Task` 的更优替代，但有一个重要区别：`Awaitable` 实例是池化的，不能在同一个方法里多次 `await` 同一个实例。

API 里与并发相关的静态方法：

| 方法 | 作用 |
|---|---|
| `Awaitable.BackgroundThreadAsync()` | 切换到线程池后台线程继续执行；已在后台线程则立即完成 |
| `Awaitable.MainThreadAsync()` | 切回 Unity 主线程继续执行；已在主线程则立即完成 |
| `Awaitable.NextFrameAsync()` / `EndOfFrameAsync()` / `FixedUpdateAsync()` | 等到下一帧、帧末、下一次固定更新 |
| `Awaitable.WaitForSecondsAsync(float)` | 等待若干秒 |
| `Awaitable.FromAsyncOperation(AsyncOperation)` | 把 `AsyncOperation` 包装成 `Awaitable` |

实例方法 `Cancel()`：取消后，正在 `await` 它的代码会收到 `System.OperationCanceledException`；`LogExceptionsAndForget()` 用于不显式检查结果时记录异常。

延续规则（同一手册页）：`Awaitable` 默认在主线程调用就回主线程续，否则在 .NET 线程池线程续；`MainThreadAsync` / `BackgroundThreadAsync` 的切换效果只对当前方法有效，调用方 `await` 这个方法时仍按调用方所在线程续。从后台线程 `await Awaitable.MainThreadAsync()` 回主线程，要等到主线程下一次帧更新才会继续，不是立即。退出 Play 模式时 Unity 不会自动停掉后台代码，需要时用 `Application.exitCancellationToken` 取消。手册还特别说明：`Awaitable` 适合异步 I/O、卸载超过一帧的长任务、取代协程；不建议用它并行化计算密集型算法，那类工作应交给 Job System。

```csharp
async Awaitable GenerateAsync()
{
    await Awaitable.BackgroundThreadAsync();   // 后台线程：纯 C# 计算，不碰 Unity API
    var data = ComputeSomethingHeavy();

    await Awaitable.MainThreadAsync();         // 回到主线程（要等到下一次主线程帧更新才继续）：可以创建 Mesh、改 Transform
    ApplyToScene(data);
}
```

第三方的 UniTask 是社区实现的零分配 async/await 方案，功能面比 `Awaitable` 更广；本项目没有使用，本章不展开。

### 协程（Coroutine）

`StartCoroutine` + `yield return` 是主线程上的"分帧"机制：每次 `yield` 把控制权交还给引擎，下一帧继续。它不产生第二个执行线程，也不会加速计算，只是避免一帧里卡太久。本项目 `VoxelWorldPreview.GenerateOverFrames` 就是一个协程，它每帧调用 `pipeline.Pump(chunksPerFrame)` 限制主线程上传数量，真正的并行工作在 `Task.Run` 里。

### 线程安全工具

| 工具 | 用途 |
|---|---|
| `ConcurrentQueue<T>` | 多生产者多消费者队列，常用于"后台产出、主线程消费" |
| `ConcurrentBag<T>` | 无序集合，适合对象池（线程各自取放） |
| `Interlocked` | 对整数做原子加、比较交换 |
| `lock` / `Monitor` | 互斥保护临界区，竞争时会阻塞线程 |
| `AutoResetEvent` / `ManualResetEvent` | 线程间信号通知 |
| `CancellationTokenSource` / `CancellationToken` | 协作式取消：任务自己定期检查 `IsCancellationRequested` 并退出 |

`CancellationToken` 是"协作"的：它只是个标志，任务不检查就不会停。给 `Task.Run(action, token)` 传 token 只保证"尚未开始执行时"可以直接取消排队，已经开始的委托仍要自己检查。

## 与 Job System 的冲突与限制

### 两套线程池争核心

Unity 的 worker 线程（Job System）和 .NET 线程池（`Task.Run`）是各自独立的两组线程，操作系统看到的是一堆平级的线程。如果你同时：

- 用 `Task.Run` 同时放出 `processorCount - 1` 个重计算任务，并且
- 又调度了大量 Job 在 Unity worker 线程上跑，

总线程数会超过物理核心数，操作系统要来回切换线程，缓存被反复冲刷，整体吞吐可能不升反降，主线程和渲染线程也可能被挤占，帧时间抖动。对策：

- 给每个子系统分配并发预算（例如 Task 最多 N 个在飞，其余核心留给 Job）。
- 不要在同一阶段同时全速运行两套线程池。
- 用 Profiler 的 Timeline 观察所有线程，确认没有大面积的"被抢占"空洞。

### Task 里不能调用 Unity API

`Task.Run` 的委托在线程池线程上运行，访问 `Transform`、`GameObject`、`Mesh` 实例方法等同于线程不安全访问，在开发构建里会抛 `UnityException`（形如 `Internal_CreateGameObject can only be called from the main thread.`）。非开发构建出于性能考虑不做这个检查，不会报错，后果是崩溃或不可预测的错误（Unity 手册 Awaitable 一节明确这样说明）。需要产出 Unity 对象，就把纯数据结果交回主线程，由主线程创建（本项目的 `uploadMesh` 回调就是这个做法）。

### 托管对象与 GC

Task、闭包、`List<T>`、`new VoxelChunk(...)` 里的 `byte[]` 都是托管堆对象。GC 回收时会占用 CPU，可能引起帧时间尖峰。常见缓解：对象池（本项目用 `ConcurrentBag` 池化采样器与 `ChunkMeshData`）、复用缓冲、预分配容量。

### Task 与 Burst 不兼容

Burst 编译的入口主要是：实现了 Job 接口且打了 `[BurstCompile]` 的结构体，以及带 `[BurstCompile]` 的静态方法（经 `BurstCompiler.CompileFunctionPointer` 取得函数指针后调用，见 2.7 函数指针与间接调用）。`Task.Run` 的委托是托管闭包，Burst 不会编译它。所以"想让 Task 里的计算更快"的路径是把计算抽成 Job，而不是给 Task 加特性。

## 对照表

| 维度 | Job + Burst | Task.Run | Thread | Coroutine | async/await（含 Awaitable） |
|---|---|---|---|---|---|
| 适用场景 | 数据并行的重计算（体素、噪声、网格） | 一次性后台任务、托管逻辑、IO | 长期后台循环 | 主线程上分帧执行、等待事件 | 主线程与后台之间串联异步流程 |
| 能否 Burst | 能 | 不能 | 不能 | 不能 | 不能 |
| 能否碰 Unity API | 不能（Mesh 等走专用数据接口） | 不能 | 不能 | 能（在主线程） | `await` 回主线程后能；后台段不能 |
| GC 压力 | 低（Native 容器、值类型） | 有（Task、闭包、托管数据） | 有 | 迭代器分配少量对象 | `Task` 有；`Awaitable` 池化，较低 |
| 取消 | 无法中途取消已运行的 Job；只能不调度或忽略结果 | `CancellationToken`（协作式） | 自己实现标志位 | `StopCoroutine` | `CancellationToken`；`Awaitable.Cancel()` |
| 复杂度 | 中高：需要 Native 容器、依赖管理、数据拆分 | 低 | 高：同步、关闭、异常都要自己管 | 低 | 低到中 |

## 选型流程

```
任务是否要访问 Unity 对象（Transform/Mesh 实例方法/物理）?
 ├─ 是 ──> 在主线程做；耗时长就用协程或 async 分帧；
 │          若只是批量查询/变换，看有没有批处理 API（RaycastCommand、TransformAccessArray）
 └─ 否 ──> 数据能否表示为值类型 + Native 容器、逻辑能否写成 HPC#?
            ├─ 能 ──> Job + Burst（数据并行用 IJobParallelFor）
            └─ 不能（需要托管对象、虚调用、第三方库、复杂类图）
                 ├─ 一次性/短任务 ──> Task.Run + CancellationToken
                 ├─ 长期后台循环 ──> Thread 或长生命周期 Task
                 └─ 需要和主线程来回切换 ──> async 方法 + Awaitable.BackgroundThreadAsync / MainThreadAsync
```

## 对应本项目：ChunkGenerationPipeline

下面只描述 `ChunkGenerationPipeline.cs` 目前的实现（已阅读，未修改），再讨论迁移方向。

### 现状

- 调度模型：所有调度状态（`loaded`、`meshScheduled`、`meshDone`、`pendingMesh`、`nextToSample`、各 `InFlight` 计数）只在主线程由 `Pump(maxUploads)` 修改。后台任务只通过并发队列回传结果。
- 后台工作：`ScheduleSample` 与 `ScheduleMesh` 内用 `Task.Run(..., token)` 排任务。
  - 采样任务：从 `ConcurrentBag<ChunkDensitySampler>` 取采样器（没有就用 `samplerFactory` 新建），`new VoxelChunk(...)` 后 `sampler.Fill(...)`，结果入 `sampledQueue`。
  - 网格任务：从 `ConcurrentBag<ChunkMeshData>` 取缓冲，调用 `VoxelMeshBuilder.BuildChunkData(center, posX, negX, posZ, negZ, size, data)`，结果入 `meshedQueue`。
- 回传与错误：`sampledQueue`、`meshedQueue`（`ConcurrentQueue`）回传结果；异常放进 `errors` 队列，下一次 `Pump` 在主线程重新抛出并 `Cancel()`。
- 同步与取消：`AutoResetEvent workCompleted` 让同步生成循环用 `WaitForWork` 阻塞等待而不空转；`CancellationTokenSource`：采样任务在开始处和入队前各检查一次 `IsCancellationRequested`，网格任务只在开始处检查；`Dispose` 里只 `Cancel()`，不释放等待句柄与 CTS，因为后台任务可能仍引用它们。
- 耗时统计：用 `Interlocked.Add(ref sampleTicks, ...)` / `meshTicks` 累加所有线程的耗时，`SampleMilliseconds` / `MeshMilliseconds` 是 CPU 时间总和。
- 背压（backpressure）：并发上限 `maxSamplingInFlight = workerCount * 2`，`maxMeshingInFlight = workerCount * 2`；已加载区块上限 `maxLoadedChunks = chunksX * 4 + maxSamplingInFlight`，派发新采样的条件是 `loaded.Count + samplingInFlight < maxLoadedChunks`，网格任务受 `maxMeshingInFlight` 限制，超出的放进 `pendingMesh` 等 `RetryPendingMeshes` 补发。区块在自身和四邻居都完成网格后由 `TryRelease` 释放，因此驻留量只与世界宽度有关。
- 主线程上传：`uploadMesh` 回调（预览脚本里是 `VoxelMeshBuilder.CreateMesh`，随后 `AddChunkObject`）是唯一用 Unity API 的步骤，每次 `Pump` 受 `maxUploads` 限制。
- 工作线程数：`VoxelWorldPreview.CreatePipeline` 里 `workers = workerThreads > 0 ? workerThreads : Math.Max(1, SystemInfo.processorCount - 1)`。注意这个数用来算"在飞任务数上限"，真正执行任务的是 .NET 线程池，线程池线程数不由此直接限制。

### 哪些部分适合迁移到 Job + Burst

适合迁移的特征：输入输出都是纯数据、不依赖托管对象图、计算重且可并行。

- 网格顶点计算（`VoxelMeshBuilder.BuildChunkData`）：输入是中心区块和四个邻居的 `byte` 体素数组，输出是顶点、法线、索引，不调用任何 Unity API。要迁移需要：把 `VoxelChunk` 内部的 `byte[]` 换成 `NativeArray<byte>`（邻居缺失时用标志或空数组表示世界外），把 `ChunkMeshData` 的 `List<Vector3>` / `List<int>` 换成 `NativeList` 或《并行写入与归约模式》一章所述的两遍法（count - scan - write），并考虑直接写 `MeshData`（见 Job 与 Unity API 交互一章），省掉主线程 `SetVertices` 的拷贝。`VoxelFaceVisibilityJob` 已经是这个方向的第一步。
- 区块内的统计（实心体素计数）：天然可用分块部分和。
- 体素数据的填充循环（`ChunkDensitySampler.Fill` 的 cell 内三线性插值部分）：这部分只读 8 个角点值、写 `byte`，本身是纯数据计算。但它的上游是"计算角点"。

### 哪些暂时只能留在 Task

- 密度采样的上游：`ChunkDensitySampler` 持有的是 `IDensityFunction` 接口引用，而函数图由 `ConstantFunction`、`BinaryFunction`、`ColumnCacheFunction`、`OctaveNoiseFunction`、`CubicSplineFunction` 等 `sealed class` 节点组成，通过虚调用 `Sample(DensityContext)` 递归求值。Burst 不支持托管类对象和接口虚调用，这棵树不能直接放进 Job。预览脚本里的注释也写明函数图里的列缓存带可变状态，不能跨线程共享，所以每个采样器要有自己的 `WorldFields` 实例。
- 要把它搬到 Burst，需要改成数据导向的表示：例如把函数图"编译"成扁平的节点结构体数组（节点类型枚举 + 参数 + 子节点下标），噪声表放进 `NativeArray`，用一个 `switch` 解释器求值；或为固定的几种地形配置手写专门的 Job。这是一项独立的重构，不是给现有类加个特性就能完成，本章不展开。
- 在这之前，采样阶段继续用 `Task.Run` 是合理选择。迁移网格阶段的同时保留采样阶段在 Task 里，就会出现"Task 线程池 + Job worker"同时工作，需要像前文说的那样限制两边并发预算。

### 迁移时的结构变化

| 方面 | 现在（Task） | 迁到 Job 后 |
|---|---|---|
| 调度 | `Task.Run` | `Schedule()` 得到 `JobHandle`，主线程每帧检查 `IsCompleted` |
| 回传 | `ConcurrentQueue` | 完成后直接读 `NativeArray`，无需队列 |
| 背压 | 在飞计数 + `loaded.Count` 上限 | 同样需要，对象换成"未完成的 `JobHandle` 数量"和 Native 缓冲占用 |
| 取消 | `CancellationToken`，开始前与入队前检查 | Job 不能中途取消；以区块为粒度，Cancel 后不再调度新 Job，并 `Complete` 后丢弃已调度的结果 |
| 异常 | 放进 `errors` 队列，主线程重抛 | Burst Job 里的错误以日志或安全检查报错呈现，不走 .NET 异常传播 |
| 内存 | 托管数组 + 对象池 | `Allocator.Persistent` 的池化 Native 缓冲，必须显式 `Dispose`，`Dispose` 前要确保 Job 已完成 |
| 观测 | `Interlocked` 累加耗时 | `ProfilerMarker` + Profiler |

建议路径（仅为方向，不是唯一方案）：先保持现有管线结构，把 `BuildChunkData` 换成"拷贝为 `NativeArray` -> Job 网格化 -> 主线程应用 `MeshData`"，用《调度粒度与性能调优》一章的方法测前后对比；确认收益后再考虑密度函数的数据化。

## 常见坑

- 以为协程是多线程：协程里做重计算依然卡主线程。
- 在 `Task.Run` 里访问 `Transform` / `Mesh`：线程错误。
- `await Task.Run` 后在后台线程继续用 Unity API：确认延续回到了主线程；用 `Awaitable` 时显式 `MainThreadAsync()`。
- 在同一个方法里重复 `await` 同一个 `Awaitable` 实例：它被池化，行为不可靠。
- `Task` 异常没人观察：被吞掉，工作静默失败。本项目用 `errors` 队列在主线程重抛，就是为了避免这一点。
- 两套线程池全速并发：总线程数超核心数，吞吐下降、帧时间抖动。
- 用 `lock` 保护热路径：竞争时线程阻塞；优先改成每线程独立数据或无锁队列。
- 取消只发信号不检查：`CancellationToken` 需要任务自己配合。

## 小结

- 数据并行重计算首选 Job + Burst；需要托管对象或第三方库的后台任务用 Task；协程只用来分帧。
- `Awaitable` 让后台与主线程切换更顺手，但不会让托管代码被 Burst 编译。
- 两套线程池并存时要明确谁占多少核心。
- 本项目的 `ChunkGenerationPipeline` 用 `Task.Run` + 并发队列 + 背压，是正确且自洽的托管方案；网格阶段是迁移 Job + Burst 的自然候选，密度函数树需要先数据化。

## 自测题

1. 协程为什么不算并发？
   答：它仍在主线程上执行，只是跨多帧分段运行，没有第二个执行线程。
2. `await Task.Run(...)` 之后的代码在哪个线程继续，原因是什么？
   答：在主线程调用的 `async` 方法里，延续通过 Unity 的 `UnitySynchronizationContext` 投递回主线程，在下一帧的 `Update` 阶段继续。
3. Task 里的代码为什么不能用 Burst？
   答：Burst 只编译 Job 结构体、`[BurstCompile]` 静态方法与函数指针，Task 的托管闭包不在其中。
4. 为什么 `ChunkGenerationPipeline` 需要 `maxLoadedChunks` 这样的背压条件？
   答：采样可能比网格化和上传快，不限制的话已采样的区块会在内存里堆积。
5. `Awaitable` 与 `Task` 的一个关键使用差别是什么？
   答：`Awaitable` 实例是池化的，不能在同一方法里多次 `await` 同一个实例。

## 参考

- https://docs.unity3d.com/ScriptReference/Awaitable.html
- https://docs.unity3d.com/Manual/async-await-support.html
- https://docs.unity3d.com/Manual/job-system-parallel-for-jobs.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-language-support.html
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkGenerationPipeline.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelWorldPreview.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelMeshBuilder.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelChunk.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkDensitySampler.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Density\（目录下各 IDensityFunction 实现的类声明）


