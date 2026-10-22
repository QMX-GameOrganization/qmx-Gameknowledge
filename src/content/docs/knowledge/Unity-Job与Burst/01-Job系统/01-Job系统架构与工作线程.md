---
title: "1.1 Job 系统架构与工作线程"
description: 讲清 Unity Job 系统的线程模型、原生任务队列、工作窃取、worker 数量控制与 Job 生命周期。
sidebar:
  order: 1
---

> 适用版本：以 Unity 6000.x 为主线；本项目 Unity 7000.0.0a8 中 Collections 6.7.0 / Burst 2.0.0 为转发壳包，`Unity.Jobs` 命名空间下的核心 API（`JobHandle`、`IJob` 等）仍可直接使用。涉及版本差异处已标注，核实不了的标"待核实"。

## 要点

- Job 不是线程。Unity 启动时创建一组固定数量的 worker 线程，所有 Job 以任务的形式进入原生（native）任务队列，由这些线程取走执行。
- worker 数量约等于 CPU 核心数相关的值，由引擎决定，你可以调低（`JobsUtility.JobWorkerCount`）但不能超过上限（`JobWorkerMaximumCount`，只读）。
- 负载均衡靠工作窃取（work stealing）：空闲线程去其它线程的队列里拿活。
- 只有主线程能 `Schedule` 和 `Complete`。Job 内部不能再调度 Job。
- 调用 `JobHandle.Complete()` 时，主线程不是干等，而是会尝试亲自执行这个 Job 及其依赖。
- Job 一旦开始就会跑完，不会像线程那样被抢占或让出，所以单个 Job 要短小。

## Unity 的线程模型

一个典型的 Unity 应用里有以下几类线程：

| 线程 | 职责 | 能否调用 Unity API |
|---|---|---|
| 主线程（Main Thread） | 运行 `MonoBehaviour` 的 `Update` 等回调、游戏逻辑、调度 Job | 可以 |
| 渲染线程（Render Thread） | 把渲染命令提交给图形 API（平台相关，是否独立线程取决于图形 Jobs 设置，待核实） | 不直接面向脚本 |
| 工作线程（Worker Thread） | 执行 Job System 队列里的任务，也被引擎自身的原生任务使用 | 基本不可以 |

官方手册对 Job System 的描述是：Unity 用自己的原生 Job System 在多个 worker 线程上处理原生代码，线程数取决于设备 CPU 核心数。你的 C# Job 与引擎内部的任务（如部分物理、动画、渲染剔除）共享同一批 worker，因此你的 Job 太长会挤占引擎自己的工作。

## 队列、worker 与工作窃取

```
          主线程                       原生 Job 队列 / worker 线程
   ┌────────────────────┐        ┌──────────────────────────────────┐
   │ job.Schedule()     │ ────►  │ worker0 队列: [A][D]...           │
   │ 返回 JobHandle     │        │ worker1 队列: [B]                 │
   │                    │        │ worker2 队列: (空) ──偷取──► B/D  │
   │ handle.Complete()  │ ◄────  │ 完成后唤醒/返回                    │
   └────────────────────┘        └──────────────────────────────────┘
```

要点说明：

- `Schedule` 先把 Job 放进主线程本地的待提交队列（"batched"），并不立刻唤醒 worker。`JobHandle.ScheduleBatchedJobs()` 才会让这些任务对 worker 可见。官方 API 文档解释：唤醒 worker 线程的开销不小，所以引擎有意延迟，建议在循环里连续调度完再统一 flush。引擎自身何时会自动 flush（例如帧末或 `Complete` 时），文档未明确，待核实，所以不要假设"调度后马上开始跑"。
- 每个 worker 有自己的队列。某个 worker 做完自己队列里的任务后，会去看其它 worker 的队列并拿走任务来做，这就是工作窃取，用来平衡不同 worker 速度不一的情况。
- 对 `IJobParallelFor` 这类并行 Job，手册说明：调度时引擎把工作切成批次（batch），为每个 CPU 核心在原生层调度一个原生 Job，并把批次分给它们。某个原生 Job 提前做完，就从其它原生 Job 偷批次；每次只偷对方剩余批次的一半，以保持缓存局部性。

### 为什么不是"每个 Job 一个线程"

- 线程创建、销毁和上下文切换有成本；几千个小 Job 各开一个线程会让系统被调度开销淹没。
- 手册强调：Job System 保证线程数匹配 CPU 核心数，因此你可以随意调度任务而不用知道核心数。线程池方案则容易建出比核心数更多的线程，造成低效。
- Job 之间的依赖由 `JobHandle` 描述，由队列按依赖顺序放行，而不是靠线程阻塞等待。

## worker 线程数

`Unity.Jobs.LowLevel.Unsafe.JobsUtility`（位于 `Unity.Jobs.LowLevel.Unsafe` 命名空间，名字里的 Unsafe 表示这是低层 API）提供了以下成员，均已在 Unity 6.6 脚本 API 页面核实：

| 成员 | 含义 | 可写 |
|---|---|---|
| `JobWorkerCount` | 当前 JobQueue 可用的 worker 数，默认等于 `JobWorkerMaximumCount` | 可写，范围 0 到 `JobWorkerMaximumCount`，越界抛出范围异常 |
| `JobWorkerMaximumCount` | worker 数上限 | 只读；可用命令行参数 `-job-worker-count value` 设置（编辑器或 Player），超过平台默认值会被忽略 |
| `ResetJobWorkerCount()` | 恢复为 Unity 调整后的值 | 方法 |
| `MaxJobThreadCount` | Job 系统最多能创建的线程数 | 只读 |
| `ThreadIndex` | 在 Job 内执行时当前线程的索引，否则为 0 | 只读 |
| `ThreadIndexCount` | 能同时处理同一个 Job 的最大 worker 数 | 只读 |
| `IsExecutingJob` | 当前是否在 Job 内 | 只读 |

要点：

- 手动设置 `JobWorkerCount` 后，Unity 停止自动调整（例如 Android 在省电模式下核心数变化时会自动调整），要恢复自动调整需调用 `ResetJobWorkerCount`。
- 用途主要是省电、或在共享机器上避免独占 CPU。普通游戏不需要改。
- 把 `JobWorkerCount` 设为 0 的实际行为（所有 Job 都由主线程在 `Complete` 时执行？）文档未直接说明，待核实。
- 想估算并行度时，读 `JobsUtility.JobWorkerCount` 即可。注意官方手册页面中那段"用一半 worker"的示例代码把 `const` 用在运行时值上并给 `Schedule` 传了三个参数，不能照抄；`IJobParallelFor.Schedule` 的签名是 `(arrayLength, innerloopBatchCount, dependsOn)`。

## Complete 时主线程会参与执行

`JobHandle.Complete` 的 API 文档说明：Job System 会把该 Job 及其依赖优先排到队列前面，并尝试在调用 `Complete` 的线程上执行它们（如果它们还没在 worker 上开始执行）。手册的"创建 Job"一页也说：Job System 通常在后台线程上跑 Job，但主线程闲下来时可能选择主线程。因此：

- 主线程调用 `Complete` 不是纯粹的休眠。但如果 Job 已经在某个 worker 上跑，主线程只能等。
- Profiler 中主线程上出现的等待类标记（常见名字如 `WaitForJobGroupID`，具体标记名随版本变化，待核实）表示在等 Job，需要去查是哪个 `JobHandle.Complete` 造成了数据依赖。
- 手册还提到：单线程 WebGL 构建中不能对代表网络传输的 Job 使用 `Complete`。WebGL 上 Job 的整体执行方式（是否都在主线程）待核实。

## Job 内能不能再调度 Job

不能。手册"创建 Job"一页写明：只能从主线程调用 `Schedule`；"Jobs 概述"一页写明：只有主线程能调度和完成 Job。早期 Jobs 包文档给出的理由是，在 Job 里调度别的 Job 而不 `Complete` 无法保证确定性。

替代做法：

- 主线程用 `JobHandle` 依赖把多个 Job 串起来（见 1.3）。
- 需要"动态数量的后续工作"时，让前一个 Job 把结果写进 `NativeList`，后一个用 `IJobParallelForDefer` 按实际长度并行处理（见 1.2）。

## 与 C# Thread / Task 的区别

| 对比项 | C# `Thread` / `Task.Run` | Unity Job |
|---|---|---|
| 线程来源 | 自建线程或 .NET 线程池 | Unity 固定的 worker 线程 |
| 数据共享 | 任意引用类型，自己加锁 | 值拷贝加 `NativeContainer`，安全系统检查 |
| 调度者 | 任何线程 | 只能主线程 |
| 依赖 | `ContinueWith` / `await` | `JobHandle` 依赖 |
| Burst | 不适用 | 可用 `[BurstCompile]` 编译 |
| 托管对象 | 可用 | 不可用（`class`、`string`、托管数组） |
| 适合 | I/O、长耗时、托管对象多的任务 | 短小、数据并行、可 Burst 的计算 |

长时间运行或需要阻塞等待 I/O 的任务不应放进 Job，否则会占满 worker（手册建议把长 Job 拆成相互依赖的小 Job）。本项目的 `ChunkGenerationPipeline` 目前正是用 `Task.Run` 在 .NET 线程池上跑采样与网格计算，并通过 `ConcurrentQueue` 回传结果，这是 Task 方案的典型形态；1.10 会拿它与 Job 方案对照，3.5 讲具体替换。

## 为什么需要安全系统（简述）

Job 在 worker 上运行，主线程可能同时读写同一块数据，这是竞态条件（race condition）。手册说明：Job System 给每个 Job 发送的是它所需数据的副本，而不是主线程数据的引用，因此 Job 里只能使用 blittable 类型；要拿回结果，必须写进 `NativeContainer`，副本和原件指向同一块内存。安全系统会在编辑器中检测未声明的并发访问，细节见 1.6。

## 编辑器与 Player 的差异

- 编辑器里默认启用安全检查（`NativeContainer` 的读写追踪、越界检查、泄漏检测）。`JobsUtility.JobDebuggerEnabled` 可以控制是否在运行时使用 Jobs Debugger。
- `JobsUtility.JobCompilerEnabled` 控制 Job 在 Mono 还是 Burst 下运行（官方 API 描述为 "Set whether to run jobs in Mono or Burst"）。
- 发布版 Player 通常不带这些检查，所以编辑器里能跑的代码在 Player 里如果有数据竞争，不会被报出来。Development Build 是否保留检查，本资料各章的说法并不完全一致（1.4、1.6 写作"开发构建启用"，具体宏与默认定义待核实），遇到问题以你当前 Unity 版本的实际行为为准。
- 编辑器里 Burst 的编译模式（同步或异步）以及对首帧性能的影响属于 Burst 章节内容。

## Job 的生命周期

```
 创建 Job 结构体并填字段
        │
        ▼
 Schedule()  ── 主线程，拷贝 Job 数据，进入本地待提交队列，返回 JobHandle
        │
        ▼
 (可选) ScheduleBatchedJobs() / 引擎自动 flush ── 对 worker 可见
        │
        ▼
 排队 ── 等待 dependsOn 完成；在 worker 队列里等待
        │
        ▼
 执行 ── 某个 worker（或在 Complete 时的主线程）调用 Execute
        │
        ▼
 完成 ── JobHandle.IsCompleted == true
        │
        ▼
 Complete() ── 主线程确认完成，清理安全系统状态，之后可访问 NativeContainer
```

手册特别提醒：`Complete` 同时会清理安全系统里的状态，不调用会造成内存泄漏。

## 示意：一个区块从调度到完成经过哪些线程

假设用 Job 方案生成一个区块（本项目当前并未这样做，仅作示意）：

```
 主线程                        worker 线程 A/B/C                  渲染线程
 ───────                       ─────────────────                  ────────
 分配 NativeArray(TempJob/Persistent)
 密度 Job.Schedule ─────────►  排队 → worker A 执行采样
 面可见性 Job.Schedule(dep) ─► 依赖满足后 → 多 worker 并行执行
 ScheduleBatchedJobs
 (几帧内继续跑 Update)
 轮询 handle.IsCompleted
 handle.Complete()  (已完成则立即返回)
 读 NativeArray，填充 Mesh
 mesh.SetVertexBufferData / Apply ───────────────────────────────► 提交绘制
 Dispose 容器
```

对照本项目：`VoxelFaceVisibilityJob`（`Assets/Scripts/WorldGen/Voxels/VoxelFaceVisibilityJob.cs`）是一个带 `[BurstCompile]` 的 `IJobParallelFor`，每个工作项处理一个体素，输出六个面的可见性位掩码，字段使用 `[ReadOnly] NativeArray<byte> Solid` 与 `[WriteOnly] NativeArray<byte> FaceMask`，正是上图中第二个 Job 的形态。

## 常见坑

- 以为 `Schedule` 之后 Job 立刻在后台运行。实际可能还在本地队列里，需要 `ScheduleBatchedJobs` 或引擎 flush。
- 在 Job 里访问静态可变数据：手册指出这没有任何保护，会绕过所有安全系统，可能让应用或编辑器崩溃。
- 一个超长 Job 占满所有 worker，导致主线程要等的关键 Job 迟迟不能开始。
- 在非主线程（包括 `Task.Run` 里）调用 `Schedule`，会报错（线程限制，具体异常文本待核实）。
- 手动改小 `JobWorkerCount` 后忘记 `ResetJobWorkerCount`。

## 小结

Job System 是一组固定数量的 worker 线程加原生任务队列，调度只在主线程，负载均衡靠工作窃取。`Complete` 时主线程会帮忙执行。Job 要短、要无托管对象、要通过 `NativeContainer` 交换数据。

## 自测题

1. 为什么不为每个 Job 创建一个线程？答：线程创建与切换开销大，且线程数超过核心数会低效；Job System 用固定数量 worker 配队列。
2. `JobWorkerCount` 和 `JobWorkerMaximumCount` 哪个可写？范围是什么？答：前者可写，0 到后者；后者只读，可用 `-job-worker-count` 命令行设置。
3. 工作窃取对 `IJobParallelFor` 的具体做法是什么？答：空闲的原生 Job 每次偷其它原生 Job 剩余批次的一半。
4. 能否在 Job 的 `Execute` 里调用另一个 Job 的 `Schedule`？答：不能，只有主线程能调度和完成 Job。
5. 调用 `Complete` 时主线程是否一定在阻塞睡眠？答：不一定，它会尝试亲自执行尚未开始的该 Job 及其依赖。

## 参考

- https://docs.unity3d.com/Manual/job-system.html
- https://docs.unity3d.com/Manual/job-system-overview.html
- https://docs.unity3d.com/Manual/job-system-jobs.html
- https://docs.unity3d.com/Manual/job-system-creating-jobs.html
- https://docs.unity3d.com/Manual/job-system-parallel-for-jobs.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerCount.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobsUtility.JobWorkerMaximumCount.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.JobHandle.ScheduleBatchedJobs.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.JobHandle.Complete.html
- https://docs.unity3d.com/Packages/com.unity.jobs@0.1/manual/scheduling_a_job_from_a_job.html
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelFaceVisibilityJob.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkGenerationPipeline.cs
