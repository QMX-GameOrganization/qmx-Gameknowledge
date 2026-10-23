---
title: "1.2 Job 类型详解"
description: 逐个讲解 IJob、IJobFor、IJobParallelFor、IJobParallelForBatch、IJobParallelForDefer、IJobFilter 等 Job 类型的规则、调度方式与选型。
sidebar:
  order: 2
---

> 适用版本：以 Unity 6000.x 的 Collections 2.x 为主线；`IJob`、`IJobFor`、`IJobParallelFor`、`IJobParallelForTransform` 在引擎核心 `Unity.Jobs` 中，`IJobParallelForBatch`、`IJobParallelForDefer`、`IJobFilter` 来自 Collections（本项目 Collections 6.7.0 的 `AssemblyTypeForwarders.cs` 确认它们仍转发到 `Unity.Jobs` 命名空间）。

## 要点

- 所有 Job 都是实现了某个 Job 接口的 `struct`，字段只能是 unmanaged（blittable）类型或 `NativeContainer`。
- Job 拿到的是字段的副本。改标量字段不会回写，要把结果交出来必须写进 `NativeContainer`。
- 新代码做"对每个下标做同一件事"优先用 `IJobFor`；`IJobParallelFor` 官方说明主要为向后兼容保留。
- 元素数量在调度时还不知道，用 `IJobParallelForDefer` 配 `NativeList`。
- `Run` 在主线程同步执行，用于调试和 Burst 测试。

## Job 的基本规则

1. 必须是 `struct`，实现 `IJob`、`IJobFor` 等接口。
2. 字段类型：`int`/`float`/`bool` 等 blittable 值类型、`Unity.Mathematics` 类型、`NativeArray<T>` 等 `NativeContainer`、unmanaged `struct`。不能含 `class` 引用、`string`、托管数组、`List<T>`。手册说明，Job System 用 `memcpy` 拷贝 blittable 数据，因此只能访问 blittable 数据。
3. 值拷贝语义：调度时 Job 结构体被拷贝，Job 对标量字段的修改只在副本上，调用方看不到。
4. `NativeContainer` 例外：Job 内的副本与原件指向同一块内存，所以数据能被主线程读到。手册的意思是：Job 结束后只有写进 `NativeContainer` 的数据才能被调用方拿到。
5. 静态可变数据没有任何保护，不要在 Job 里访问。
6. 想让 Burst 编译，在 struct 上加 `[BurstCompile]`（Burst 章节详述）。

```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;

[BurstCompile]
public struct SumJob : IJob
{
    [ReadOnly] public NativeArray<int> Input;
    public NativeArray<int> Output;      // 长度为 1，用来取回结果
    public int Offset;                   // 标量：只是副本

    public void Execute()
    {
        int sum = 0;
        for (int i = 0; i < Input.Length; i++) sum += Input[i];
        Output[0] = sum + Offset;
        Offset = 999;                    // 无效：不会回写到调用方
    }
}
```

## 各 Job 类型

### IJob

只执行一次 `Execute()`，在一个 worker 上运行。适合"一整段串行逻辑"，例如对小数据排序、把多个结果合并。

```csharp
var output = new NativeArray<int>(1, Allocator.TempJob);
var input  = new NativeArray<int>(100, Allocator.TempJob);
var job = new SumJob { Input = input, Output = output, Offset = 5 };
JobHandle h = job.Schedule();            // 或 job.Run() 在主线程直接执行
h.Complete();
int result = output[0];
input.Dispose(); output.Dispose();
```

### IJobFor

`void Execute(int index)`，对 `0..arrayLength-1` 各执行一次。同一个 Job 类型有三种执行方式：

| 方法 | 行为 |
|---|---|
| `Run(arrayLength)` / `RunByRef` | 主线程立即顺序执行 |
| `Schedule(arrayLength, dependency)` / `ScheduleByRef` | 调度到一个 worker 顺序执行（单线程，但不在主线程） |
| `ScheduleParallel(arrayLength, innerloopBatchCount, dependency)` / `ScheduleParallelByRef` | 分到多个 worker 并行执行 |

`ByRef` 变体按引用传 Job，避免大结构体的按值拷贝。官方说明：`Run` 与 `Schedule` 保证 `Execute` 按顺序调用，`ScheduleParallel` 不保证。同一个 Job 既能顺序也能并行，代码只写一份，便于切换对比。

```csharp
[BurstCompile]
public struct ScaleJob : IJobFor
{
    public NativeArray<float> Data;
    public float Factor;
    public void Execute(int i) => Data[i] *= Factor;
}

var job = new ScaleJob { Data = data, Factor = 2f };
JobHandle h1 = job.Schedule(data.Length, default);               // 单 worker 顺序
JobHandle h2 = job.ScheduleParallel(data.Length, 64, default);   // 并行，每批 64
```

### IJobParallelFor

`void Execute(int index)`。调度签名：`Schedule(int arrayLength, int innerloopBatchCount, JobHandle dependsOn = default)`，另有 `ScheduleByRef` 与 `Run`/`RunByRef`。API 文档明确：该类型主要为向后兼容，新代码应使用 `IJobFor`。

本项目的 `VoxelFaceVisibilityJob` 就是这一类型：每个下标处理一个体素，输出面可见性位掩码。

```csharp
[BurstCompile]
public struct AddJob : IJobParallelFor
{
    [ReadOnly] public NativeArray<float> A;
    [ReadOnly] public NativeArray<float> B;
    [WriteOnly] public NativeArray<float> Result;
    public void Execute(int i) => Result[i] = A[i] + B[i];
}

JobHandle h = new AddJob { A = a, B = b, Result = r }.Schedule(r.Length, 64);
```

#### 索引范围与批次切分

- `Execute` 对 `0..arrayLength-1` 每个下标调用一次，顺序不保证，必须彼此独立。
- 引擎把范围切成每批至少 `innerloopBatchCount` 个下标的批次，批次是工作窃取的单位。
- 手册建议：批大小从 1 开始增大，直到收益可以忽略。轻量 Job（几个 `float3` 相加）可取 32 到 128；很重的 Job 取 1。
- 并行 Job 里默认只能写自己下标处的元素：安全系统会限制对 `NativeArray` 的越界写，这就是"每个线程有独占下标"的含义。

### IJobParallelForBatch

`void Execute(int startIndex, int count)`：每次拿到一段连续区间，适合需要在批内做局部累积、或想用 SIMD/内层循环的场景。来源于 Collections（CHANGELOG 记录 "IJobParallelForBatch from com.unity.jobs"）。API 文档列出的调度方法有 `ScheduleBatch(arrayLength, indicesPerJobCount, dependsOn)`，以及 `Schedule`、`ScheduleParallel`、`RunBatch(arrayLength)`、`Run(arrayLength, indicesPerJobCount)` 等；各重载之间在并行度上的细微差别文档描述不足，待核实，示例用 `ScheduleBatch`。

最后一批的 `count` 可能小于 `indicesPerJobCount`。

```csharp
[BurstCompile]
public struct BatchSumJob : IJobParallelForBatch
{
    [ReadOnly] public NativeArray<int> Values;
    [NativeDisableParallelForRestriction] public NativeArray<int> PartialSums; // 每批一个槽
    public int BatchSize;

    public void Execute(int startIndex, int count)
    {
        int s = 0;
        for (int i = startIndex; i < startIndex + count; i++) s += Values[i];
        PartialSums[startIndex / BatchSize] = s;
    }
}

int batches = (values.Length + 63) / 64;
var partial = new NativeArray<int>(batches, Allocator.TempJob);
new BatchSumJob { Values = values, PartialSums = partial, BatchSize = 64 }
    .ScheduleBatch(values.Length, 64).Complete();
```

这里用 `[NativeDisableParallelForRestriction]` 是因为每批写自己的槽、而不是下标 `startIndex` 处，需要手动关闭并行写限制；使用前先确认槽不重叠。

### IJobParallelForDefer

当循环次数在调度时还不知道（例如前一个 Job 往 `NativeList` 里塞了不定数量的元素），用 `IJobParallelForDefer`。来自 Collections，文档称它是"元素数在 Schedule 时未知时对 `IJobParallelFor` 的替代"。

真实调度 API（Collections 2.5 文档核实）：

```csharp
// 安全版本：按 NativeList 的长度（dependsOn 完成之后的长度）迭代
JobHandle Schedule<T, U>(this T jobData, NativeList<U> list, int innerloopBatchCount,
                         JobHandle dependsOn = default)
// 不安全版本：传入 int* forEachCount，文档建议优先用 NativeList 版本
```

配套的 `NativeList<T>.AsDeferredJobArray()` 返回一个"别名数组"，其长度会在前序 Job 更新列表长度之后才确定。

```csharp
[BurstCompile]
struct CollectJob : IJob            // 前序 Job：产出不定数量结果
{
    public NativeList<int> Found;
    public void Execute() { for (int i = 0; i < 1000; i++) if (i % 7 == 0) Found.Add(i); }
}

[BurstCompile]
struct ProcessJob : IJobParallelForDefer
{
    [ReadOnly] public NativeArray<int> Items;   // 由 AsDeferredJobArray() 赋值
    public void Execute(int index) { /* 使用 Items[index] */ }
}

var found = new NativeList<int>(Allocator.TempJob);
JobHandle h1 = new CollectJob { Found = found }.Schedule();
JobHandle h2 = new ProcessJob { Items = found.AsDeferredJobArray() }
                   .Schedule(found, 32, h1);    // 长度在 h1 完成后才确定
h2.Complete();
found.Dispose();
```

注意：此时不要在主线程读 `found.Length` 来决定调度参数，因为 Job 还没跑。`NativeList` 本身使用方式见 Collections 章节。

### IJobParallelForTransform 与 TransformAccessArray（简述）

`IJobParallelForTransform` 的 `Execute(int index, TransformAccess transform)` 让每个 worker 独占处理层级中的一个 `Transform`，数据源是 `TransformAccessArray`。手册说明它用于在 Job 里高效操作 Transform。调度方法为 `IJobParallelForTransformExtensions.Schedule(transformAccessArray, dependsOn)`（签名待核实，我未取到该页面）。底层 `JobsUtility` 另有 `ScheduleParallelForTransform` 与 `ScheduleParallelForTransformReadOnly`，说明存在只读访问变体。

### IJobFilter

过滤下标。`bool Execute(int index)` 返回是否保留。来自 Collections，CHANGELOG 记录 "IJobParallelForFilter renamed to IJobFilter"，所以旧名字 `IJobParallelForFilter` 已不存在。调度 API（Collections 2.5 文档核实）：

- `ScheduleAppend(NativeList<int> indices, int arrayLength, JobHandle dependsOn = default)`：对 `0..arrayLength-1` 过滤，通过的下标追加到 `indices`。
- `ScheduleFilter(NativeList<int> indices, JobHandle dependsOn = default)`：就地过滤已有列表，只保留 `Execute` 返回 true 的。
- 同步版本：`RunAppend`、`RunFilter`；以及对应的 `ByRef` 版本。

```csharp
[BurstCompile]
struct IsSolidFilter : IJobFilter
{
    [ReadOnly] public NativeArray<byte> Solid;
    public bool Execute(int index) => Solid[index] != 0;
}

var indices = new NativeList<int>(Allocator.TempJob);
new IsSolidFilter { Solid = solid }.ScheduleAppend(indices, solid.Length).Complete();
```

### Collections 里已移除的 HashMap 遍历 Job

`IJobNativeMultiHashMapVisitKeyValue`、`IJobNativeMultiHashMapMergedSharedKeyIndices`、`IJobUnsafeMultiHashMapVisitKeyValue` 等一批 Job 类型，在 Collections 的 CHANGELOG 中记录于 0.12.0（2020-08-04）的 Removed 列表里。本项目的 Collections 6.7.0 的 `AssemblyTypeForwarders.cs` 里也找不到它们，所以不要再使用，旧教程里出现的这些名字属于过时内容。遍历哈希表有两条路，均已按 Collections 2.5 的 `NativeParallelHashMap<K,V>` API 页核实：一是直接用枚举器，`GetEnumerator()` 返回 `NativeParallelHashMap<K,V>.Enumerator`，在单个 Job 或主线程里顺序遍历键值对（枚举器是视图，容器释放或扩容后失效，见 1.4 容器枚举器与 GetEnumerator）；二是用 `GetKeyArray(allocator)`、`GetValueArray(allocator)` 或 `GetKeyValueArrays(allocator)` 把键值复制成数组（顺序不确定），再配合 `IJobFor` / `IJobParallelFor` 并行处理。官方没有给出"哪种更适合并行遍历"的结论，这一点仍待核实；复制数组要多一次分配与拷贝。

### ECS 的 Job

`IJobEntity`、`IJobChunk` 属于 Entities 包，不在本资料范围。

## Run、Schedule 与 ScheduleParallel

| 方法 | 在哪里执行 | 是否阻塞主线程 | 典型用途 |
|---|---|---|---|
| `Run` | 主线程 | 是 | 调试、断点、Burst 测试、小数据 |
| `Schedule` | 单个 worker（`IJobParallelFor.Schedule` 例外，见下） | 否 | 串行逻辑后台化 |
| `ScheduleParallel` | 多个 worker | 否 | 大数据并行 |

特别注意命名陷阱：`IJobParallelFor.Schedule(length, batch)` 本身就是并行的；而 `IJobFor.Schedule(length, dep)` 是单线程顺序的，要并行必须用 `ScheduleParallel`。

`Run` 能让你在 Burst 开启时用 Profiler 看 Burst 版本耗时，也能暂时关闭 Burst 后下断点调试。调试时优先用 `Run`，因为异常堆栈就在主线程。

## 选型决策表

| 需求 | 选择 |
|---|---|
| 一段串行逻辑 | `IJob` |
| 对 N 个元素做独立计算，长度已知 | `IJobFor` + `ScheduleParallel` |
| 同上但想用旧 API | `IJobParallelFor` |
| 需要按段处理、批内累积 | `IJobParallelForBatch` |
| 长度由前序 Job 决定 | `IJobParallelForDefer` + `NativeList` |
| 从下标集合里挑出满足条件的 | `IJobFilter` |
| 并行读写 `Transform` | `IJobParallelForTransform` |
| 同一份代码要在串行与并行间切换 | `IJobFor` |

## 常见坑

- 以为改了 Job 里的 `int` 字段就能把结果带出来；实际要写进 `NativeArray`。
- 在 `IJobParallelFor` 里写 `result[otherIndex]`，安全系统会抛并行写越界异常；确需如此用 `[NativeDisableParallelForRestriction]` 并自己保证不重叠。
- 把 `IJobFor.Schedule` 当并行用。
- 批大小设得太小，工作窃取的原子操作开销超过收益；设得太大，负载不均。
- `IJobParallelForDefer` 里仍用调度时读到的 `list.Length`，会得到 0。
- 在 Job 里使用 `class`/`string`，Burst 编译会报错。

## 小结

选型的核心是三问：是否并行、长度何时确定、是否需要批内处理。`IJobFor` 是新代码的默认选择，`IJobParallelForDefer` 解决延迟长度，`Run` 是调试利器。

## 自测题

1. Job 里把 `public int Offset` 改成 999，调用方能看到吗？答：不能，Job 持有副本。
2. `IJobFor.Schedule` 与 `ScheduleParallel` 区别？答：前者单 worker 顺序，后者多 worker 并行。
3. 前序 Job 往 `NativeList` 加了不定数量元素，后序如何并行处理？答：`IJobParallelForDefer`，`Schedule(list, batch, dep)`，数组字段用 `AsDeferredJobArray()`。
4. `IJobParallelForFilter` 现在叫什么？答：`IJobFilter`。
5. 为什么调试 Job 常用 `Run`？答：同步在主线程执行，便于断点和看异常。

## 参考

- https://docs.unity3d.com/Manual/job-system-jobs.html
- https://docs.unity3d.com/Manual/job-system-creating-jobs.html
- https://docs.unity3d.com/Manual/job-system-parallel-for-jobs.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.IJobFor.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.IJobForExtensions.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.IJobParallelFor.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.IJobParallelForExtensions.Schedule.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/api/Unity.Jobs.IJobParallelForDefer.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/api/Unity.Jobs.IJobParallelForDeferExtensions.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/api/Unity.Jobs.IJobParallelForBatch.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/api/Unity.Jobs.IJobParallelForBatchExtensions.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/api/Unity.Jobs.IJobFilter.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/api/Unity.Jobs.IJobFilterExtensions.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/api/Unity.Collections.NativeList-1.html
- D:\UnityHub\Project\程序化生成\Library\PackageCache\com.unity.collections@28abc463ca66\CHANGELOG.md
- D:\UnityHub\Project\程序化生成\Library\PackageCache\com.unity.collections@28abc463ca66\Unity.Collections\AssemblyTypeForwarders.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelFaceVisibilityJob.cs
