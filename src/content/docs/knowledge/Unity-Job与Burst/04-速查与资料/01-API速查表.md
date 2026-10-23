---
title: "4.1 API 速查表"
description: Job 接口、JobHandle、容器、分配器、安全属性、Burst 特性、Mathematics、MeshData 流程、菜单路径、报错对照与版本改名的一页速查
sidebar:
  order: 1
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x / Collections 2.x / Mathematics 1.3.x 为主线；本项目 Unity 7000.0.0a8 中 Burst 2.0.0 与 Collections 6.7.0 为转发到引擎内置模块的壳包。

## 使用说明

- 本页只汇总已有章节的结论，不新增事实。每行末尾的“见 x.y”指向详细章节，细节、代码与坑以原章节为准。
- 带“（待核实）”的条目沿用原章节的标记，表示写作时没能从官方来源确认，使用前请自行验证。
- 菜单路径与设置名取自 6000.5、6000.7 手册和 Burst 1.8.31 手册，7000.0.0a8 未逐项实测（待核实）。
- API 名保持英文原样。示例代码没有在 Unity 内编译。

## 1 Job 接口与调度

| 名称 | 作用与签名要点 | 注意 | 见 |
| --- | --- | --- | --- |
| `IJob` | `Execute()` 只执行一次，在一个 worker 上运行 | 适合一整段串行逻辑；可 `Schedule()` 或 `Run()` | 1.2 |
| `IJobFor` | `Execute(int index)`；`Run(len)`、`Schedule(len, dep)`、`ScheduleParallel(len, innerloopBatchCount, dep)`，各有 `ByRef` 版 | 新代码做逐下标计算的默认选择；`Schedule` 是单 worker 顺序，要并行必须 `ScheduleParallel` | 1.2 |
| `IJobParallelFor` | `Execute(int index)`；`Schedule(arrayLength, innerloopBatchCount, dependsOn = default)`，另有 `ScheduleByRef`、`Run`、`RunByRef` | 官方说明主要为向后兼容；`Schedule` 本身就是并行；顺序不保证，下标须彼此独立 | 1.2 |
| `IJobParallelForBatch` | `Execute(int startIndex, int count)`；`ScheduleBatch(arrayLength, indicesPerJobCount, dependsOn)`，另有 `RunBatch`、`Run`、`Schedule`、`ScheduleParallel` | 来自 Collections；最后一批 `count` 可能偏小；各重载在并行度上的细微差别文档描述不足（待核实） | 1.2 |
| `IJobParallelForDefer` | `Schedule(NativeList<U> list, int innerloopBatchCount, dependsOn)`，数组字段用 `list.AsDeferredJobArray()` | 长度在前序 Job 完成后才确定；调度前不要读 `list.Length`；另有 `int* forEachCount` 的不安全版 | 1.2、1.4 |
| `IJobParallelForTransform` | `Execute(int index, TransformAccess transform)`，数据源是 `TransformAccessArray` | 调度扩展方法的签名未核对（待核实）；`TransformAccessArray` 须在主线程构造和增删 | 1.2、1.9 |
| `IJobFilter` | `bool Execute(int index)`；`ScheduleAppend(indices, arrayLength, dep)`、`ScheduleFilter(indices, dep)`，同步版 `RunAppend`、`RunFilter` | 旧名 `IJobParallelForFilter` 已改名，不再存在 | 1.2 |
| 已移除的哈希表遍历 Job | `IJobNativeMultiHashMapVisitKeyValue` 等一批 | Collections 0.12.0 的 Removed 列表中；遍历哈希表的最佳实践（待核实） | 1.2 |

### Run、Schedule、ScheduleParallel

| 方法 | 在哪里执行 | 阻塞主线程 | 用途 |
| --- | --- | --- | --- |
| `Run` | 主线程 | 是 | 调试、断点、Burst 测试、小数据；异常堆栈在主线程 |
| `Schedule` | 单个 worker（`IJobParallelFor.Schedule` 例外，它是并行的） | 否 | 把串行逻辑后台化 |
| `ScheduleParallel` | 多个 worker | 否 | 大数据并行（`IJobFor`） |

### innerloopBatchCount

- 含义：并行 Job 的批大小，批次是工作窃取的单位；空闲的原生 Job 每次偷对方剩余批次的一半。
- 手册做法：从 1 开始，逐步增大，直到性能收益可以忽略。轻量 Job（几个 `float3` 相加）可取 32 到 128，很重的 Job 取 1。
- 批次总数 `ceil(arrayLength / batch)` 应明显多于 worker 数，否则吃不满核心。批大小取 64 的倍数只能降低相邻批次共享缓存行的概率，不是保证。
- 本项目 `BuildWithJobs` 默认批大小 64，只是起点，要用扫描实验验证。见 1.2、1.8。

### Job 粒度与 ECS 的关系

- 官方设计准则：把 Job 设计成在一帧以内完成。Job 不会让出执行权，worker 开始后必须做完；过长的 Job 应拆成彼此依赖的多个小 Job，否则会推迟主线程显式等待的重要 Job。无法拆分的 `IJobParallelFor` 可增大批大小来限制参与的 worker 数。跨帧流水线是"一条 Job 依赖链"跨帧，与"单个 Job 一帧内完成"不冲突（这一点是 1.3 的推断，不是官方原话）；多小才算"一帧内"官方没给数字，需 Profiler 实测。见 1.3、1.8。
- DOTS 五个主要部分：Entities、Job system、Burst、Collections、Mathematics；本项目未引用 Entities。ECS 系统里的 `Dependency` 按组件读写自动推导，容器依赖仍要手动 `JobHandle.CombineDependencies`；Job 内的结构性变更要用 `EntityCommandBuffer`。见 0.4。

## 2 JobHandle 与 JobsUtility

| 名称 | 作用与签名要点 | 注意 | 见 |
| --- | --- | --- | --- |
| `Schedule(...)` | 立刻返回 `JobHandle`，Job 不一定已开始；依赖通过 `dependsOn` 参数传入 | 只能在主线程调用，Job 内不能再调度 Job；Job 一旦开始就跑完，不会让出 | 1.1、1.3 |
| `handle.Complete()` | 保证 Job 完成，并让安全系统释放对容器的占用；会把该 Job 及依赖排到队列前面并尝试在调用线程执行 | 轮询到 `IsCompleted` 为 true 后仍要调用；不调用会泄漏安全系统状态 | 1.1、1.3 |
| `handle.IsCompleted` | 属性，已完成为 true | 只是查询，不替代 `Complete` | 1.3、3.5 |
| `JobHandle.CombineDependencies` | 重载：`(a, b)`、`(a, b, c)`、`(NativeArray<JobHandle>)`、`(NativeSlice<JobHandle>)` | 扇入用；两个 Job 若都写同一容器，即使依赖同一前序也会冲突 | 1.3 |
| `JobHandle.CompleteAll` | `(ref a, ref b)`、`(ref a, ref b, ref c)`、`(NativeArray<JobHandle>)` | 一次完成多个 | 1.3 |
| `JobHandle.ScheduleBatchedJobs()` | 让本地待提交队列里的 Job 对 worker 可见 | 唤醒 worker 开销大，循环里调度完再统一调用；引擎何时自动 flush 文档未明确（待核实） | 1.1、1.3 |
| `container.Dispose(JobHandle)` | 返回新的 `JobHandle`，在输入依赖完成后释放内存与安全句柄 | 释放接在依赖链末尾；结果容器若主线程还要读，先 `Complete` 再 `Dispose()` | 1.3、1.5 |
| `JobsUtility.JobWorkerCount` | 当前可用 worker 数，默认等于上限，可写，范围 0 到 `JobWorkerMaximumCount` | 手动设置后 Unity 停止自动调整，用 `ResetJobWorkerCount()` 恢复；设为 0 的实际行为文档未直接说明（待核实） | 1.1 |
| `JobsUtility.JobWorkerMaximumCount` | worker 上限，只读 | 命令行 `-job-worker-count value` 可设置，超过平台默认值会被忽略 | 1.1 |
| `JobsUtility.ThreadIndex` / `ThreadIndexCount` / `MaxJobThreadCount` | Job 内的线程下标 / 同时处理同一 Job 的最大 worker 数 / Job 系统可创建的最大线程数 | 前两者在 Job 外读取 `ThreadIndex` 返回 0；`ThreadIndexCount` 与 `MaxJobThreadCount` 的数值关系以实测为准（待核实），拿不准取较大者 | 1.6、1.7 |
| `JobsUtility.CacheLineSize` | 引擎认为的缓存行大小，常见 64 字节 | 每线程槽位间距至少一个缓存行，避免伪共享 | 1.7、1.8 |
| `JobsUtility.JobCompilerEnabled` / `JobDebuggerEnabled` / `IsExecutingJob` | Job 跑 Mono 还是 Burst / 运行时是否启用 Jobs Debugger / 当前是否在 Job 内 | 运行时属性，对应编辑器菜单开关 | 1.1、1.8 |

## 3 Native 容器选型

| 容器 | 作用与要点 | ParallelWriter | 注意 | 见 |
| --- | --- | --- | --- | --- |
| `NativeArray<T>` | 定长，引擎自带；`Length`、`IsCreated`、`GetSubArray`、`Reinterpret<U>`、`AsReadOnly()`、`CopyFrom`/`CopyTo`、`ToArray()` | 无；并行时每个 index 写自己的槽 | 索引器返回副本；`ToArray()` 产生 GC 分配；`T` 须为 `unmanaged`；`UninitializedMemory` 后先写后读 | 1.4、1.5 |
| `NativeSlice<T>` | 对 `NativeArray` 的一段视图，可带步长 | 无 | 可作 Job 字段；`Span<T>` 不能做 Job 字段 | 1.4 |
| `NativeList<T>` | 可变长，`Capacity` 与 `Length`；`AsArray()`、`AsDeferredJobArray()`、`ResizeUninitialized` | 有：`AsParallelWriter()`，`AddNoResize`、`AddRangeNoResize` | 不扩容，容量不足抛 `InvalidOperationException`；`AsArray()` 视图在扩容后失效 | 1.4、1.7 |
| `NativeQueue<T>` | 先进先出，可扩容 | 有：`Enqueue` | 写入顺序不确定 | 1.4、1.7 |
| `NativeRingQueue<T>` | 固定容量环形缓冲 | 无 | 容量固定 | 1.4 |
| `NativeStream` | 一组只追加缓冲，每个 foreach 下标一块；`AsWriter()`、`AsReader()`、`ToNativeArray<T>` | 无 `ParallelWriter` 类型；`NativeStream.Writer` 每个下标独立写 | `BeginForEachIndex` 后写入器须按引用传；写完才能读；构造参数是 buffer 数量 | 1.4、1.7 |
| `NativeReference<T>` | 单个值的引用，等价长度为 1 的数组 | 无 | Job 里回传一个结果 | 1.4 |
| `NativeBitArray` | 任意长度位数组；`BitField32`/`BitField64` 为固定 32/64 位 | 无 | 每个标记占 1 位 | 1.4 |
| `NativeText` | UTF-8 可变字符串 | 无 | | 1.4 |
| `NativeHashMap<K,V>`、`NativeHashSet<T>` | 单线程场景，内存开销较低（2.x 新增，名字与旧名相同但实现不同） | 无；官方 API 注明不适合并行写入 | 并行写请用 `NativeParallelHashMap` | 1.4 |
| `NativeParallelHashMap<K,V>` | 多线程场景，内存开销较高 | 有：`AsParallelWriter()`，`TryAdd`（key 已存在返回 false）；2.6.0-pre.3 起补充 `Add` | 不扩容，容器已满时写入抛异常；不要依赖带线程下标参数的重载 | 1.4、1.7 |
| `NativeParallelHashSet<T>`、`NativeParallelMultiHashMap<K,V>` | 并行集合 / 一键多值 | 有 | 读取与删除放在另一个 Job 阶段 | 1.4 |
| `UnsafeList<T>`、`UnsafeHashMap`、`UnsafeParallelHashMap`、`UnsafeStream`、`UnsafeBitArray`、`UnsafeText` 等 | 无 `AtomicSafetyHandle`，可嵌套、可放进别的 unmanaged 结构；与 `Native*` 一一对应（`NativeList` 对应 `UnsafeList`），多数 `Native*` 是对 `Unsafe*` 加安全句柄的封装 | `UnsafeParallelHashMap.ParallelWriter` 存在；其余资料未逐个核对 | 不检查读写冲突与释放后使用；`TempJob` 超 4 帧也不提醒；释放时嵌套容器要逐个 `Dispose`；关闭安全检查后两类性能无显著差别，优先 `Native*`，必须嵌套时才用 `Unsafe*`（`NativeList<UnsafeList<T>>` 可以，`NativeList<NativeList<T>>` 不行）；用 `Unsafe*` 别名 `Native*` 会绕开冲突检查 | 1.4、1.5、1.6 |
| `UnsafeAtomicCounter32`/`64` | 指向一个整数的原子计数器；`Add`/`Sub` 返回原值，`AddSat`/`SubSat`，`Reset` 非原子 | 不适用 | 通常比分块部分和慢得多，只适合冲突很少的场合 | 1.7 |
| `FixedString32Bytes` 等 | 固定大小字符串，32/64/128/512/4096 字节，含 3 字节开销 | 无；值类型 | 内联在结构体里，不需要 `Dispose`；容量固定，超出会失败 | 1.4 |
| `FixedList32Bytes<T>` 等 | 固定大小列表，32/64/128/512/4096 字节，含 2 字节开销 | 无；值类型 | 同上；大型栈结构有栈溢出风险 | 1.4、2.12 |
| `NativeSortExtension`（`Sort`、`SortJob`、`SortJobDefer`、`BinarySearch`） | `Unity.Collections` 下的扩展方法：同步 `Sort<T>()` / `Sort<T, U>(comp)`，可调度的 `SortJob`，列表长度运行时才定的 `SortJobDefer`，二分查找；有 `NativeArray`/`NativeList`/`NativeSlice`/`UnsafeList`/指针重载 | 不适用；是官方"确定性读写"三手段之一（写后排序） | 默认比较要求 `T : unmanaged, IComparable`（待核实）；`SortJob` 的调度方式与是否内部并行未核对（待核实）；排序键不唯一时相同键的顺序仍不确定 | 1.4、1.7 |
| `NativeArrayExtensions` | `ArraysEqual`、`Contains`、`IndexOf`（找不到返回 -1）、`CopyFrom`（长度不等抛 `ArgumentException`）、`Reinterpret<T, U>()` | 不适用 | `Reinterpret<T, U>()` 两个类型都要 `unmanaged`，容量不能被 `sizeof(U)` 整除时抛 `InvalidOperationException`；别名机制见第 4 节 | 1.4、1.5 |
| `ListExtensions`（托管 `List<T>`） | `RemoveAtSwapBack`、`RemoveSwapBack`、`ToNativeArray`、`ToNativeList` | 不适用 | 针对托管 `List<T>`，不是 `NativeList`；`SwapBack` 会打乱顺序 | 1.4 |
| 容器枚举器 `GetEnumerator()` | 返回 `MoveNext` / `Current` 的枚举器；第一次 `MoveNext` 才移到第一个元素；哈希表另有 `GetKeyArray`、`GetValueArray`、`GetKeyValueArrays`（复制成新数组，顺序不确定） | 不适用 | 枚举器属于"视图"：容器 `Dispose` 或大小变化后失效；枚举期间不要增删、扩容；失效时抛哪种异常官方没写（待核实） | 1.4、1.6 |
| `ParallelWriter` / `ParallelReader` | 容器的嵌套类型，用于并行 Job 读或写；`NativeList<T>.ParallelWriter` 共享原列表的安全句柄，只能 `AddNoResize` | 见各容器 | 只支持集合功能的子集；顺序不确定。官方页只给了 `ParallelWriter` 示例，哪些容器有名为 `ParallelReader` 的类型没有列出（待核实）；只读访问通常用 `[ReadOnly]` 或 `AsReadOnly()` | 1.7 |

### 按场景选容器

| 场景 | 推荐 | 见 |
| --- | --- | --- |
| 长度固定的数据块（体素、噪声缓存），输出与输入一一对应 | `NativeArray<T>`，每 index 写自己的槽 | 1.4、1.7 |
| 结果数量不确定，单线程追加 | `NativeList<T>` | 1.4 |
| 多线程并行追加，上限已知，顺序无所谓 | `NativeList<T>.ParallelWriter` 或 `NativeQueue<T>.ParallelWriter` | 1.7 |
| 紧凑输出且顺序要可复现 | 两遍法：计数、前缀和、并行写入 | 1.7 |
| 多线程各自输出变长记录 | `NativeStream` 或每线程一个 `NativeList` | 1.4、1.7 |
| 键值映射，单线程或单 Job | `NativeHashMap<K,V>` | 1.4 |
| 键值映射，多线程写入 | `NativeParallelHashMap<K,V>.ParallelWriter` | 1.4 |
| 计数、求和 | 分块部分和，再由一个合并 Job 汇总 | 1.7 |
| 需要嵌套或放进别的 unmanaged 结构 | `Unsafe*` 系列，或展平加偏移表 | 1.4 |

`NativeArray<NativeArray<T>>` 不能用于 Job：容器本身可以被创建，被安全系统拒绝的是"调度使用它的 Job"（`AtomicSafetyHandle.SetNestedContainer` 的作用），具体异常类型与文本待核实。见 1.4、1.11。

## 4 Allocator 速查

| 分配器 | 速度 | 生命周期与限制 | 能传给 Job | 释放 | 见 |
| --- | --- | --- | --- | --- | --- |
| `Allocator.Temp` | 最快 | 主线程上帧内有效，Job 内在 Job 结束前有效；最小对齐 64 字节 | 否（主线程分配的 Temp 不能放进 Job 字段） | 调用 `Dispose` 无实际效果，但对 `Native*` 容器仍会释放安全句柄，习惯上照写 | 1.5 |
| `Allocator.TempJob` | 较快 | 须在创建后 4 帧内释放；最小对齐 16 字节 | 是 | 必须；`Native*` 容器超期抛异常，`Unsafe*` 容器同样必须在 4 帧内释放但不检查 | 1.3、1.5 |
| `Allocator.Persistent` | 最慢，近似 `malloc` | 不限，安全检查发现不了超期；最小对齐 16 字节 | 是 | 必须；跨帧、时长不确定的 Job 一律用它，热路径别频繁分配，宜池化 | 1.5 |
| `Allocator.Invalid` | 无 | 默认值；`AsDeferredJobArray()` 返回的数组用它标记列表模式 | 不适用 | 不适用 | 1.5 |
| `Allocator.None` | 无 | 不拥有内存，用于包装别人分配的内存 | 不适用 | `Dispose` 不会释放 | 1.5 |
| `Allocator.AudioKernel` | 无 | 音频内核专用，具体用途与可用范围（待核实） | 不适用 | 不适用 | 1.5 |
| 自定义分配器 | 视实现 | 通过 `AllocatorManager` 注册，句柄隐式转换为 `Allocator`；结构需含 `AllocatorManager.AllocatorHandle` 字段并实现 `AllocatorManager.IAllocator`；怎样把自定义分配器注册进全局表官方在另一页讲，资料未读到（待核实） | 视实现 | 销毁顺序：先释放分配器自己的内存块，再 `AllocatorHelper.Dispose()` 注销并释放本体 | 1.5 |
| `RewindableAllocator` | 类似线性分配器，快、线程安全；预分配块，最小对齐 64 字节；块用完再分配，块大小翻倍到上限后线性增长；`Rewind()` 一次性释放所有分配（保留用过的块） | 视容器 | 单个 `Free` / `Dispose` 默认是空操作；创建时开启 enable block free 后，才在释放某块的最后一个分配时回绕该块。创建推荐 `AllocatorHelper<RewindableAllocator>`，`Initialize(int initialBlockSize, bool enableBlockFree = false)`；`NativeArray` 必须经 `CollectionHelper.CreateNativeArray` 创建，`NativeList` 用 `rwd.Handle` 构造；`Rewind` 后旧容器访问抛 `ObjectDisposedException`（需检查开启的构建）；`Rewind` 前必须保证没有 Job 还在用 | 1.5 |
| 别名（alias）与 `Reinterpret<T, U>()` | 别名共享另一个集合的分配，不自己分配；`Reinterpret<T, U>()` 是数组重解释这种特殊别名（10 个 `int` 变 20 个 `short`） | 不适用 | 别名无需释放，对别名 `Dispose` 什么也不做；原件释放后别名不能再用（`ObjectDisposedException`）；`Unsafe*` 别名 `Native*` 绕开安全检查，别名最好仍用 `Native*` 视图 | 1.4、1.5 |

### Dispose 的几种写法

| 写法 | 适用 | 注意 | 见 |
| --- | --- | --- | --- |
| `using` 或 `try/finally` | 同步场景，同帧调度并 `Complete` | `Complete()` 必须在作用域内完成，否则 Job 还在跑内存就被释放 | 1.5 |
| `h = array.Dispose(h)` | 异步，不想阻塞主线程 | 之后仍需有人对 `h` 调用 `Complete` 或把它作为后续依赖 | 1.3、1.5 |
| `[DeallocateOnJobCompletion]` | 容器是 `NativeArray`、想少写一行 | 6.6 页面确认仍存在且未标记弃用；新代码更推荐 `Dispose(JobHandle)` | 1.5 |
| 池化 `Persistent` 缓冲 | 区块缓冲复用 | 归还须在对应 `JobHandle` 完成之后；`UninitializedMemory` 的缓冲带旧数据 | 1.5 |

- `IsCreated` 只反映被调用的那份拷贝，对同一容器的两个拷贝都 `Dispose` 会二次释放。
- 容器是值类型，拷贝的是"指针加 `AtomicSafetyHandle`"而不是数据，所有拷贝指向同一块内存和同一条安全中心记录。对任一份拷贝 `Dispose`，`Release()` 把中心记录的版本号加一，其它拷贝下次访问时抛 `ObjectDisposedException`。见 1.6。
- 退出 Play Mode、`OnDestroy`、Domain Reload 之前，先 `Complete` 在途 Job，再释放容器。见 1.3、1.5。

## 5 Job 与安全相关特性

| 特性 | 作用 | 状态与注意 | 见 |
| --- | --- | --- | --- |
| `[ReadOnly]` | 声明字段只读，允许多个 Job 并发读同一容器 | 默认容器字段是读写权限，会占用写锁；不写的字段务必加 | 1.6 |
| `[WriteOnly]` | 声明只写不读旧值 | 对其读取会被安全系统拒绝；用于 `NativeArray` 等容器 | 1.6 |
| `[NativeDisableParallelForRestriction]` | 关闭 `IJobParallelFor` 按 index 的写范围限制 | 之后不再有保护，重叠写是静默的真数据竞争；需要算法不变式并配写入计数测试 | 1.6、1.7、3.3 |
| `[NativeDisableContainerSafetyRestriction]` | 关闭该容器字段上的容器安全限制，如调度时的读写冲突与别名检查 | 与上一条不是同一开关，两者精确覆盖范围官方描述很少（待核实）；Burst 会认为带它的成员可与其他成员别名 | 1.6、2.10 |
| `[NativeDisableUnsafePtrRestriction]` | 允许 Job 字段持有裸指针 | 绕过安全系统 | 1.6、1.7 |
| `[NativeSetThreadIndex]` | 把当前工作线程下标注入 Job 里的 `int` 字段 | 下标与其它并行运行的 Job 不重复；不保证从 0 连续；槽间距要隔开缓存行 | 1.6、1.7 |
| `[DeallocateOnJobCompletion]` | Job 完成时自动释放容器 | 见第 4 节 | 1.5 |
| `[NativeContainer]` | 标记自定义 native container 类型 | 必须内嵌名为 `m_Safety` 的 `AtomicSafetyHandle`（启用检查时）；调用 `MallocTracked` 时泄漏跟踪自动生效；实现不当可能直接让 Unity 崩溃，要为所有场景补测试 | 1.11 |
| `[NativeContainerSupportsMinMaxWriteRestriction]` | 声明容器可把可写范围限制在最小/最大下标之间；要在 `IJobParallelFor` 里写入容器必须标 | 必须有 `int m_Length`、`int m_MinIndex`、`int m_MaxIndex` 三个成员，按此顺序且中间不能有别的成员；容器自己对范围外写入抛异常 | 1.11、1.6 |
| `[NativeContainerIsReadOnly]` | 标记容器类型只读，去掉调度时"读还是写"的歧义 | 不会阻止代码去写，约束要容器自己执行 | 1.11 |
| `[NativeContainerIsAtomicWriteOnly]` | 声明容器只允许写，且只在安全的并行上下文里写；可作可写参数传给并行 Job，不限制下标，表示各部分互不重叠 | 容器必须强制只写；具体哪些内置类型采用（待核实） | 1.11 |
| `[NativeContainerSupportsDeferredConvertListToArray]` | 声明容器可传给 `IJobParallelForDefer` 的 `Schedule` | 页面只有这一句，没有其它字段要求 | 1.11、1.4 |
| `[NativeContainerSupportsDeallocateOnJobCompletion]` | 声明容器可配合 `[DeallocateOnJobCompletion]` 在 Job 完成时自动释放 | 必须有名为 `m_Buffer` 的指针字段和名为 `m_AllocatorLabel` 的 `Allocator` 字段 | 1.11、1.5 |
| `[NativeSetClassTypeToNullOnSchedule]` | 用在 Job 结构的字段上：传给 Job 的拷贝里该类引用被置为 null | 官方示例是旧版容器的 `DisposeSentinel` 字段（类，Job 不能带托管引用） | 1.11 |
| `[JobProducerType(typeof(...))]` | 标在 Job 接口上，指明包含静态 `Execute` 方法的 producer 类型；所有 Job 接口都必须标，Burst 靠它编译 `Execute` | 自定义新的 Job 类型才用得到；`JobsUtility.CreateJobReflectionData` 等用法未核对（待核实） | 1.11 |
| `[Conditional("ENABLE_UNITY_COLLECTIONS_CHECKS")]` | 保护 Burst 代码里的 `throw` | 否则触发 `BC1370`；Player 里 `throw` 会变成 abort | 2.2、2.10 |

### 自定义容器用到的 AtomicSafetyHandle 与分配 API

| 名称 | 作用 | 注意 | 见 |
| --- | --- | --- | --- |
| `AtomicSafetyHandle.CheckReadAndThrow` / `CheckWriteAndThrow` | 读、写之前检查当前上下文是否有权限且容器未释放 | 不满足抛 `InvalidOperationException`（官方示例注释）；已释放时 Rewindable 页测试抛的是 `ObjectDisposedException`，两处不一致，以实测为准（待核实）；代码要用 `ENABLE_UNITY_COLLECTIONS_CHECKS` 包起来 | 1.11、1.6 |
| `AtomicSafetyHandle.Create()` / `Release()` / `CheckDeallocateAndThrow` | 创建句柄 / 释放时递增版本号使所有拷贝失效 / 检查是否还有 Job 占用 | 当前示例不再用 `DisposeSentinel`（旧写法） | 1.11、1.6 |
| `AtomicSafetyHandle.UseSecondaryVersion`、`CheckWriteAndBumpSecondaryVersion`、`SetBumpSecondaryVersionOnScheduleWrite`、`CheckGetSecondaryDataPointerAndThrow` | 次级版本号：让视图（枚举器、`AsArray()`）在扩容或调度写 Job 后失效 | 改变大小的操作用 `CheckWriteAndBumpSecondaryVersion` 代替 `CheckWriteAndThrow` | 1.6、1.11 |
| `AtomicSafetyHandle.NewStaticSafetyId`、`SetStaticSafetyId` | 把容器类型名登记到安全系统，让报错带上容器名 | 安全 ID 创建一次复用，存静态字段 | 1.11 |
| `AtomicSafetyHandle.SetCustomErrorMessage` | 对特定违反安全约束的情形覆盖报错文本 | 参数形式未逐个核对（待核实） | 1.11 |
| `AtomicSafetyHandle.SetNestedContainer(handle, true)` | 把含其它 `NativeContainer` 的容器标记为嵌套容器 | 拦的是"调度使用它的 Job"，不是创建 | 1.11、1.4 |
| `AtomicSafetyHandle.GetTempMemoryHandle`、`GetTempUnsafePtrSliceHandle` | 临时容器的特殊句柄：前者随临时内存作用域结束自动失效，后者是全局句柄 | 用后者的容器不能传进 Job | 1.6 |
| `UnsafeUtility.MallocTracked` / `FreeTracked` | 带泄漏跟踪的分配与释放 | 用 `Malloc` 则泄漏跟踪不生效 | 1.11 |
| `NativeLeakDetection.Mode` | 控制是否记录分配栈，对应 `Preferences > Jobs > Leak Detection Level` | | 1.11、1.5 |

读写规则：多个只读可并行；任何写与同一容器上的其它读写冲突，必须用 `JobHandle` 依赖排序；主线程在 Job 未完成时访问被占用的容器会抛 `InvalidOperationException`，先 `Complete()`。检查在编辑器中启用，发布版没有；开发构建是否保留这些检查，1.6 称启用，1.1 与 2.11 标为待核实（待核实）。见 1.6。

## 6 Burst 特性与参数

### `[BurstCompile]` 标在哪里

| 位置 | 写法要点 | 见 |
| --- | --- | --- |
| Job 的 struct | 标在 struct 上，Burst 编译其中所有内容 | 2.1 |
| 静态方法 | 方法和它所在的类型都要标 | 2.1 |
| 函数指针目标 | 同静态方法，再用 `BurstCompiler.CompileFunctionPointer<T>` 取得指针 | 2.1、2.7 |
| 程序集 | `[assembly: BurstCompile(...)]` 为整个程序集的 Job 与函数指针设默认选项，如 `OptimizeFor = OptimizeFor.FastCompilation`、`FloatMode = FloatMode.Deterministic` | 2.1、2.6、2.10 |
| 托管代码直接调用 | 方法和所在类型都标 `[BurstCompile]`，从 `MonoBehaviour` 等托管代码直接调用，IL 后处理改写成函数指针调用 | 2.1、2.7 |

`AttributeUsage` 为 `Assembly`、`Class`、`Struct`、`Method`；构造函数有无参与 `(FloatPrecision, FloatMode)` 两个。程序集级写法取自手册 Defining Burst options for an assembly（2.10 第 17 节）。

设置优先级（手册原文给出的顺序）：编辑器菜单设置（如 `Native Debug Compilation`）最优先；其次是 Job 或函数指针上的 `BurstCompile` 特性（如 `CompileSynchronously = true`）；其余设置才从程序集级特性取。其它程序集不受影响，可逐个程序集控制。见 2.10。

从托管代码直接调用 Burst 静态方法：泛型方法与泛型类型中的方法不支持；参数和返回值受与函数指针相同的 `DllImport` / 内部调用类型限制，结构体不能按值传，所以手册示例用 `in float4` 输入、`out float4` 输出；函数体很小时互操作开销可能抵消收益；`DisableDirectCall = true` 可关闭该转换。见 2.1、2.7、2.10。

### `[BurstCompile]` 的全部参数

| 参数 | 类型 | 作用 | 注意 | 见 |
| --- | --- | --- | --- | --- |
| `FloatPrecision` | `FloatPrecision` | 数学函数（`sin`、`cos`、`exp`、`log`、`pow` 等）的精度 | 见下表 | 2.6、2.10 |
| `FloatMode` | `FloatMode` | 浮点运算的重排与特殊值处理 | 见下表 | 2.6、2.10 |
| `CompileSynchronously` | `bool` | 首次使用时立即编译，不在后台编译 | 只对 JIT 有意义；会阻塞当前帧；1.8.31 的 Function pointers 手册页写成 `SynchronousCompilation`，API 页没有这个名字，以 API 为准 | 2.1、2.7 |
| `DisableSafetyChecks` | `bool` | 对当前 Job 或函数指针关闭 Burst 安全检查 | 全局 `Force On` 时仍然开启 | 2.10 |
| `Debug` | `bool` | 以可调试方式编译，关闭该方法的优化 | 同时影响 `Aliasing.Expect*`、`Constant.IsConstantExpression` 的行为 | 2.5、2.10 |
| `DisableDirectCall` | `bool` | 关闭“托管代码调用 Burst 静态方法时改为直接调用原生方法”的 IL 后处理转换 | 默认会转换 | 2.10 |
| `OptimizeFor` | `OptimizeFor` | 入口点的优化目标 | 逐版本差异待核实 | 2.10 |

### 枚举取值

| 枚举 | 取值 | 含义 | 见 |
| --- | --- | --- | --- |
| `FloatPrecision` | `Standard` | 默认，等同 `Medium`，3.5 ULP | 2.6 |
| | `High` | 1.0 ULP | 2.6 |
| | `Medium` | 3.5 ULP | 2.6 |
| | `Low` | 按函数而定；`sin`、`cos`、`exp`、`exp2`、`exp10`、`log`、`log2`、`log10`、`pow`、`fmod` 为 350 ULP，其余沿用 `Medium` | 2.6 |
| `FloatMode` | `Default` | 等同 `Strict` | 2.6 |
| | `Strict` | 不重排计算，遵守 NaN、非规格化数 | 2.6 |
| | `Fast` | 允许重排、乘加融合、假定无 NaN 与 Inf | 2.6、2.10 |
| | `Deterministic` | 跨平台一致，仅 64 位架构；非规格化数刷成 0，不保证 NaN 位模式；有性能代价；自 Burst 1.8.25（2025-09-16）起正式支持，此前只是早期预览 | 2.6 |
| `OptimizeFor` | `Default`（0） | 等同 `Balanced` | 2.10 |
| | `Performance`（1） | 追求最优二进制 | 2.10 |
| | `Size`（2） | 追求最小二进制 | 2.10 |
| | `FastCompilation`（3） | 编译最快；不做向量化、内联和循环优化 | 2.4、2.11 |
| | `Balanced`（4） | 兼顾性能与编译时间 | 2.10、2.11 |

旧名对应：枚举 `Accuracy` 现为 `FloatPrecision`；`BurstCompilerOptions.EnableFastMath` 已弃用，改用 `FloatMode.Fast`。见 2.6。

### 其它特性与编译器提示

| 名称 | 作用与用法 | 风险或注意 | 见 |
| --- | --- | --- | --- |
| `[NoAlias]` | 位置：`Struct`、`Field`、`Parameter`、`ReturnValue`；断言指针不与其它指针重叠 | 指针其实重叠时是未定义行为；`NativeArray` 字段多余，Burst 已推断 | 2.10 |
| `[BurstDiscard]` | 方法在 Burst 下整个调用被丢弃，只在托管下执行 | 不能有返回值，用 `ref`/`out` 回传；常用于探测当前是否在 Burst；`BurstDiscardAttribute` 不在壳包转发清单里，所在程序集待核实 | 2.1、2.5 |
| `[SkipLocalsInit]` | 位置：`Method`；去掉 `stackalloc` 的清零 | 读到未初始化内存；是 Burst 自己的特性，不是 `System.Runtime.CompilerServices` 那个 | 2.10 |
| `[IgnoreWarning(int)]` | 位置：`Method`，可多次；抑制指定编号警告；标在 `[BurstDiscard]` 方法上可一次抑制 `BC1371` | 少用，别用来掩盖 `BC1370` | 2.10 |
| `[AssumeRange(min, max)]` | 位置：`Parameter`、`ReturnValue`；闭区间；仅标量整数，区间类型与被标类型一致 | 值越界时未定义行为 | 2.10 |
| `Hint.Likely(cond)` / `Hint.Unlikely(cond)` | 调整分支布局与优化投入 | 判错只会变慢，安全 | 2.10 |
| `Hint.Assume(cond)` | Burst 当条件恒为真，可删分支、完美向量化 | 条件为假时未定义行为，风险最高 | 2.10 |
| `Aliasing.ExpectNotAliased(a, b)` / `ExpectAliased(a, b)` | 编译期断言，证明不了就报编译错误；接受 `void*` 或 `in` 泛型参数 | 只在启用优化时有效，不改变生成的代码 | 2.4、2.10 |
| `Constant.IsConstantExpression(x)` | 询问参数此刻是否已被视为常量 | 随内联而变，关优化时恒为 `false`；两条分支结果必须相同 | 2.10 |
| `Loop.ExpectVectorized()` / `ExpectNotVectorized()` | 声明循环应（不应）向量化 | 实验性，需定义 `UNITY_BURST_EXPERIMENTAL_LOOP_INTRINSICS`；不满足报 `BC1321`；不能放进 `if` | 2.4 |
| `[Alias]` | 退出 Job 内的不别名保证 | 实验性，需定义 `UNITY_BURST_EXPERIMENTAL_ALIAS_ATTRIBUTE` | 2.10 |
| `FunctionPointer<T>` | `BurstCompiler.CompileFunctionPointer<T>(method)` 得到指针，Job 里 `.Invoke(...)`；委托类型非泛型 | 不能内联、不能向量化、不能直接传容器；按批调用；只编译一次并缓存；IL2CPP 下目标方法要 `[MonoPInvokeCallback]` | 2.7 |
| `SharedStatic<T>` | `SharedStatic<T>.GetOrCreate<TContext, TSubContext>()`，通过 `.Data` 读写 | 先在 C# 里初始化再在 Burst 里用；线程安全自负；关闭域重载时值会残留 | 2.8 |
| `RegisterGenericJobType` | 位于 `Unity.Jobs`：`[assembly: RegisterGenericJobType(typeof(MyJob<int>))]` | 登记的是 Job 反射数据，不是 Burst 编译清单；官方补救办法只有用完全确定的类型实参直接调度泛型 Job | 2.9 |
| `BurstCompiler.IsEnabled` | 静态属性，Burst 开关是否打开 | 不能证明某个具体 Job 编译成功 | 2.1 |
| `X86.*.IsXxxSupported`、`Arm.Neon.IsNeonSupported` | 编译期求值的特性检测，用来分支 | 从新到旧排列；Burst 关闭时全返回 `false` | 2.4 |
| `Common.Pause()` | `Unity.Burst.Intrinsics.Common`，各目标共享，不需要 `IsXXXSupported` 保护；提示 CPU 暂停当前线程一下，x86 映射 `pause`、ARM 映射 `yield` | 用于自旋锁一类循环；不是操作系统层面的线程让出 | 2.4 |
| `Common.umul128(ulong a, ulong b, out ulong high)` | 128 位无符号乘法，返回低 64 位，高 64 位通过 `out` 给出 | 可用于 64 位混合哈希；示意写法质量未评估，真用来做世界种子先写 golden test | 2.4 |
| `Common.Prefetch`、`Common.InterlockedAnd` / `InterlockedOr` | 预取内存到缓存 / 对 `int`、`uint`、`long`、`ulong` 的原子与、原子或 | 均为实验性 | 2.4 |
| System 命名空间支持 | `Interlocked` 全部方法有原子指令，`Volatile` 只支持 `Read` / `Write` 的非泛型版本，`Thread.MemoryBarrier`，`HashCode` 除 `Add<T>(T, IEqualityComparer<T>)` 外都支持 | `Interlocked` 目标地址必须自然对齐，否则未定义行为；不要用泛型 `Volatile.Read<T>`；`HashCode` 结果不保证与 .NET / Mono 一致，不要用来派生种子（用自己写的整数哈希或 `math.hash` 并加 golden test） | 2.2、2.6 |
| `DllImport` 与内部调用的允许类型 | 内置整数 / `float` / `double` / `IntPtr` / `UIntPtr` / `v64` / `v128` / `v256`，指向它们的指针与 `ref`，以及只含一个指针字段或一个整数字段的句柄结构体 | `bool` 不在清单里，用 `byte` 或 `int` 表示真假；`char`、`decimal`、`string`、`enum`、多字段结构体也不在清单（`enum` 为保守处理）；多字段结构体不能按值传，用指针或 `ref`；`DllImport` 只支持原生插件 | 2.7、2.1 |
| `ProfilerMarker.Auto()` | Burst 代码里用静态 `ProfilerMarker` 配 `using (marker.Auto())`，或手动 `Begin` / `End` | 外部原生分析工具（Instruments、Superluminal）针对 Player 构建，要指向存放 `lib_burst_generated` 的 `Plugins` 文件夹找符号，符号需 Development Build 或 `Force Debug Information` | 2.5 |
| `BurstRuntime.LoadAdditionalLibrary(path)` | 运行时加载额外的 Burst 编译库（Modding），要在第一次用到 Burst 方法之前加载 | 仅 Play 模式或独立 Player；手册正文一处写成 `LoadAdditionalLibraries`，以示例代码的单数为准；编译这些库仍需编辑器；本项目用不到 | 2.11 |

## 7 Unity.Mathematics 常用函数分类速查

Mathematics 从 Unity 6.5 起是内置模块，`Unity.Mathematics` 命名空间默认可用。下表函数中，`remap`、`bitmask`、`tzcnt`、`hash`、`select`、`smoothstep`、`unlerp`、`sign` 已核对过 API 页，其余是 HLSL 惯例名，未逐个查阅，以 IDE 补全为准。见 2.3。

| 类别 | 函数 | 注意 |
| --- | --- | --- |
| 绝对值与范围 | `abs` `clamp` `saturate` `min` `max` `sign` | `saturate` 对应 `Mathf.Clamp01`；`math.sign(0)` 返回 0，`Mathf.Sign(0)` 返回 1 |
| 插值与映射 | `lerp` `unlerp` `remap` `smoothstep` `step` | `lerp`、`unlerp` 不钳制；`remap(srcStart, srcEnd, dstStart, dstEnd, x)` 非钳制；`smoothstep(min, max, x)` 参数含义与 `Mathf.SmoothStep` 不同 |
| 取整 | `floor` `ceil` `round` `frac` `trunc` | 取整转 `int` 写 `(int)math.floor(x)`；越界或 NaN 转 `int` 未指定 |
| 条件 | `select` `any` `all` | `select(falseValue, trueValue, condition)`，顺序与三元运算符相反；两个分支都会求值，不短路 |
| 向量 | `dot` `cross` `length` `lengthsq` `normalize` `distance` | |
| 乘加与倒数 | `mad` `rcp` `rsqrt` `sqrt` | `mad(a, b, c)` 是 `a * b + c`，可映射到 FMA，取决于 CPU 目标和 `FloatMode` |
| 超越函数 | `sin` `cos` `tan` `exp` `log` `pow` | 精度受 `FloatPrecision` 影响 |
| 位运算 | `tzcnt` `lzcnt` `countbits` `bitmask` | `bitmask(bool4)` 返回 `int`，`x` 在第 0 位；`tzcnt` 返回尾部 0 的个数 |
| 归约 | `csum` `cmin` `cmax` | |
| 哈希 | `hash` | 返回 `uint`，对各种向量、矩阵类型有重载，另有 `hash(void* pBuffer, int numBytes, uint seed = 0)` |

### 类型与其它

| 名称 | 要点 | 注意 | 见 |
| --- | --- | --- | --- |
| 向量类型 | `float2/3/4`、`double2/3/4`、`int2/3/4`、`uint2/3/4`、`bool2/3/4`、`half`/`half2/3/4`；运算符逐分量；标量隐式广播；支持 swizzle（`a.zyx`） | `half` 向量不能用于字符串插值 | 2.2、2.3 |
| 矩阵与旋转 | `float2x2`、`float3x3`、`float4x4`（及 double 版）、`quaternion` | `float4x4` 的 `*` 是逐分量乘，矩阵乘法用 `math.mul`；`math.mul(float4x4, float4)` 把 `float4` 当列向量，`math.mul(float4, float4x4)` 当行向量 | 2.3 |
| `quaternion` 构造与运算 | `quaternion.AxisAngle(float3 axis, float angle)`、`quaternion.Euler(x, y, z)`，角度都是弧度；四元数相乘用 `math.mul`；`math.rotate(quaternion, float3)` 旋转向量；`math.slerp`、`math.nlerp` 插值 | 手册没说明 `math.mul(q1, q2)` 的组合顺序与 `Euler` 三参数重载的默认旋转顺序（待核实）；`slerp` / `nlerp` 的 `t` 是否钳制未给出（待核实） | 2.3 |
| `RigidTransform` | 只含旋转与平移（字段 `rot`、`pos`、`identity`），构造 `(quaternion, float3)`、`(float3x3, float3)`、`(float4x4)`；静态方法 `AxisAngle`、`Euler*`、`RotateX/Y/Z`、`Translate`；配套 `math.transform`、`math.rotate`、`math.inverse` | 不含缩放，非均匀缩放仍用 `float4x4`；`float4x4` 构造假定矩阵正交归一 | 2.3 |
| `MinMaxAABB` | 在 `Unity.Mathematics.Geometry` 命名空间；构造 `(float3 min, float3 max)`；字段 `Min`、`Max`；`Center`、`Extents`、`HalfExtents`、`SurfaceArea`、`IsValid`；`Contains`、`Overlaps`、`Encapsulate`、`Expand`、`CreateFromCenterAndExtents` | 需要 `using Unity.Mathematics.Geometry;`；边界点是否算包含未展开（待核实）；7000.0.0a8 中命名空间是否不变未核对（待核实） | 2.3 |
| 位模式重解释与位运算 | `asuint`、`asint`、`asfloat`、`aslong`、`asulong`、`asdouble`（只重解释位，不做数值转换）；`reversebits`、`rol`、`ror`、`ceilpow2`、`ceillog2`、`floorlog2`、`sincos`、`shuffle` | 已对照 1.3.2 API 页；`ShuffleComponent` 成员名未逐个核对（待核实） | 2.3 |
| 与 UnityEngine 类型互转 | `float3` 与 `Vector3` 等之间有隐式转换 | 细节未逐项核对（待核实） | 2.3 |
| `noise` | `cnoise`（Perlin）、`pnoise`（周期版）、`snoise`（Simplex）、`srnoise`/`srdnoise`、`psrnoise`/`psrdnoise`、`cellular`、`cellular2x2`、`cellular2x2x2`（Worley，返回 `float2`，F1 在 `x`，F2 在 `y`） | 无种子参数，给坐标加偏移；各函数返回值区间 API 页未给出（待核实）；与 `ValueNoiseFunction` 不是同一算法，换用会改变地形 | 2.3 |
| `Random` | 32 位状态 xorshift；`new Random(uint seed)` 种子须非零；`CreateFromIndex(uint)` 先哈希，index 不能是 `uint.MaxValue`；`NextFloat()` 在 `[0, 1)` | 是 struct，按值复制会得到相同序列，传递用 `ref`；与 `using UnityEngine;` 并用时要写全名 | 1.9、2.3 |
| `Mathf` 对照 | `Clamp01`→`saturate`，`Lerp`→`lerp`（`Mathf` 钳制），`InverseLerp`→`unlerp`，`FloorToInt`→`(int)math.floor`，`Deg2Rad`→`math.radians(x)`，`PerlinNoise`→`noise.cnoise`（值域与算法不同，不可互换） | 逐个核对 | 2.3 |
| 整数除法 | `/` 向零截断，`%` 跟随被除数；体素分区块需要 floor 除法；除数为 2 的幂时用 `>>` 与 `&`（`-1 >> 4 == -1`，`-1 & 15 == 15`） | 向量版 `int4` 的 `>>`、`&` 逐分量 | 2.3、3.3 |
| `float` 精度 | `float` 只有 24 位有效数字，坐标到 `1e6` 量级噪声出现抖动 | 大世界用区块局部坐标或 `double` | 2.3 |
| Burst 对向量的优化 | `float2/3/4`、`int2/3/4`、`uint2/3/4`、`bool2/3/4` 有一等公民优化，建议优先 4 宽 | | 2.2、2.3 |

## 8 MeshData 写入流程速查

可写 `MeshData` 的流程（1.9 的最小示例与 3.4 的区块骨架合并）。示例都没有在 7000.0.0a8 里编译运行（待核实）。

| 步骤 | 线程 | 做什么 | 注意 | 见 |
| --- | --- | --- | --- | --- |
| 1 数面 | Job 加主线程 | 计数 Job 统计每个区块的暴露面数 `F`，`Complete` 后读取 | 缓冲大小要在写入前定好，所以必须两遍；每面 4 个顶点（`V = 4F`）、6 个索引（`I = 6F`） | 3.4 |
| 2 分配 | 主线程 | `Mesh.AllocateWritableMeshData(n)` 得到 `Mesh.MeshDataArray` | 一次申请多个比多次各申请一个高效 | 1.9、3.4 |
| 3 声明顶点 | 主线程 | `data.SetVertexBufferParams(vertexCount, descriptors)` | 同一流内属性按固定顺序，结构体字段顺序与描述符一致；结构体用 `LayoutKind.Sequential` | 1.9、3.4 |
| 4 声明索引 | 主线程 | `data.SetIndexBufferParams(indexCount, IndexFormat)` | `UInt16` 仅在 `4F <= 65536` 时可用，否则 `UInt32`；高度 128 时最坏顶点数远超 65536 | 3.4 |
| 5 子网格 | 主线程或 Job | `data.subMeshCount = 1`，`data.SetSubMesh(0, new SubMeshDescriptor(indexStart, indexCount), flags)` | 见下方两种写法；引擎几乎不校验 `indexStart`/`indexCount` 与拓扑，子网格范围不能重叠 | 1.9、3.4 |
| 6 写入 | Job | `data.GetVertexData<T>()`、`data.GetIndexData<T>()` 返回 `NativeArray<T>` 并写入 | 区块私有缓冲只需区块内计数器；合并网格才需要跨区块前缀和，并要 `[NativeDisableParallelForRestriction]` | 1.9、3.4 |
| 7 完成 | 主线程 | `handle.Complete()` | Apply 前忘了 `Complete` 会应用未写完的数据 | 1.9 |
| 8 应用 | 主线程 | `Mesh.ApplyAndDisposeWritableMeshData(array, mesh 或 Mesh[] 或 List<Mesh>, flags)` | 之后 `MeshDataArray` 已释放不能再用；数组长度须与 `MeshDataArray` 一致 | 1.9、3.4 |
| 9 包围盒 | 主线程 | Apply 之后 `mesh.RecalculateBounds()`，或显式 `mesh.bounds = chunkBounds` | `SetSubMesh` 只管子网格包围盒；Apply 带 `DontRecalculateBounds` 后 `Mesh.bounds` 是否保持需在 Unity 里验证（待核实） | 1.9、3.4 |
| 10 收尾 | 主线程 | 空区块 Apply 后 `Destroy` 空 `Mesh` 或提前排除；只读 `MeshData` 用完也要 `Dispose` | Apply 后是否还需要 `UploadMeshData(true)`、Apply 出来的 `Mesh` 默认是否可读，文档未写明（待核实） | 1.9、3.4 |

`SetSubMesh` 的两种写法：

- 1.9 示例：Job 内写完顶点与索引之后调用 `Data.SetSubMesh(0, new SubMeshDescriptor(0, 6))`，默认自动计算子网格的 `bounds`、`firstVertex`、`vertexCount`，`Mesh` 自身包围盒靠最后的 `RecalculateBounds()`。
- 3.4 骨架：主线程在写入之前就调用，带 `MeshUpdateFlags.DontRecalculateBounds`，手动填 `firstVertex`、`vertexCount`、`bounds`；`MeshData.SetSubMesh` 对这几项的计算时机文档没有细说（待核实）。

`MeshUpdateFlags` 成员：`Default`、`DontValidateIndices`、`DontResetBoneBounds`、`DontNotifyMeshUsers`、`DontRecalculateBounds`、`DontValidateLodRanges`，可用 `|` 组合。`DontValidateIndices` 在 Apply 路径上是否生效文档没有明说（待核实）。见 3.4。

### 顶点格式选项

| 选项 | 每顶点字节 | 布局 | 对材质的影响 | 见 |
| --- | --- | --- | --- | --- |
| A 朴素：Position `float3` 加 Normal `float3` | 24 | `Position, Float32, 3` 与 `Normal, Float32, 3`，同一 stream | 与 URP Lit 兼容，不改材质；适合第一步验收 | 3.4 |
| B 去掉法线 | 12 | 只有 Position | URP Lit 需要法线，必须自定义着色器推导法线 | 3.4 |
| C 位置打包进 `uint` | 4 | 一个 `UInt32` 单通道属性，语义放哪个通道（待核实） | 必须自定义着色器；整数顶点属性在部分平台的支持情况（待核实） | 3.4 |

### 面掩码与相关约定

- 面掩码位序：bit 0 到 bit 5 依次是 +X、-X、+Y、-Y、+Z、-Z；线性化 `x + SizeX * (y + SizeY * z)`；遍历顺序 z 外、y 中、x 内，面 0 到 5。见 3.1、3.4。
- 现状每面约 120 字节（位置 48、法线 48、`UInt32` 索引 24），估算，非实测。见 3.4。
- `Mesh` 上传后变成不可读（`UploadMeshData(true)`）时，不能回读顶点，运行时建 `MeshCollider` 通常需要可读网格（待核实）。见 3.4。
- 其它直写路径：`Mesh.SetVertexBufferData`/`SetIndexBufferData` 的 `NativeArray` 重载，参数列表未逐个核对（待核实）；`Texture2D.GetRawTextureData<T>()`、`GraphicsBuffer.LockBufferForWrite<T>` 见 1.9。

## 9 菜单与设置路径速查

路径取自 Burst 1.8.31 手册、6000.5 偏好设置文档与 6000.7 手册，7000.0.0a8 未逐项实测（待核实）。

### 编辑器：Jobs > Burst 菜单（只影响编辑器）

| 菜单项 | 作用 | 注意 | 见 |
| --- | --- | --- | --- |
| `Jobs > Burst > Enable Compilation` | 总开关；关闭后 `[BurstCompile]` 走托管 | 用于对比计时与调试 | 1.6、1.8、2.1 |
| `Jobs > Burst > Enable Safety Checks` | `Off` / `On`（默认）/ `Force On` | 检查包括 Job 依赖和容器越界；`Off` 在重载编辑器后复位为 `On`；`Force On` 连 `DisableSafetyChecks = true` 的代码也检查；测性能设 `Off` | 1.6、1.8、2.1 |
| `Jobs > Burst > Synchronous Compilation` | 同步编译，默认异步（编译完成前先跑托管版本） | 会阻塞当前帧，只用于剖析与对比；测量前要预热 | 1.8、2.1 |
| `Jobs > Burst > Native Debug Mode Compilation` | 对所有 Burst 代码关优化，便于原生调试器 | 别一直开着，性能数据会失真 | 1.8、2.5 |
| `Jobs > Burst > Show Timings` | 把 JIT 编译耗时输出到 Console（前端、中端、后端分段） | 编译慢时用 | 2.1、2.5 |
| `Jobs > Burst > Open Inspector` | 打开 Burst Inspector | 左侧灰色条目表示没有 `[BurstCompile]` | 2.1、2.5 |

### 偏好设置与项目设置

| 路径 | 作用 | 注意 | 见 |
| --- | --- | --- | --- |
| `Edit > Preferences > Jobs > Enable Jobs Debugger` | Job 安全系统的竞争检测 | 6000.5 文档确认；每次重启编辑器后为开启；测性能时关闭；较早版本在顶部 `Jobs` 菜单 | 1.6、1.8 |
| `Edit > Preferences > Jobs > Leak Detection Level` | `Disabled` / `Enabled` / `Enabled With Stack Trace` | 6000.5 文档确认；1.5 引用论坛时标为待核实；最后一档有额外开销 | 1.5、1.6、1.8 |
| `Edit > Preferences > Jobs > Use Job Threads` | 关闭后所有 Job 调度时立即在主线程运行 | 用于排除并行因素 | 1.6、1.8 |
| `Edit > Project Settings > Burst AOT Settings` | Player 构建的 Burst 设置（按平台） | 1.8.31 的 Building your project 页写成 `Edit > Player Settings > Burst AOT Settings`，以编辑器里实际能找到的为准 | 2.1、2.11 |
| `File > Build Profiles` | 切换目标平台（Unity 6 及以上） | 更早版本在 `File > Build Settings` | 2.11 |
| `Project Settings > Editor > Enter Play Mode Options` | 关闭 Domain Reload 后静态数据残留 | 静态字段与 `SharedStatic` 值会保留，要在 `RuntimeInitializeOnLoadMethod` 里重置 | 2.8、2.11 |
| Player Settings 的 Allow unsafe code | 使用 `unsafe` 代码所需 | 或在 `asmdef` 设 `allowUnsafeCode` | 0.1 |

### Burst AOT Settings 选项

| 选项 | 含义 | 见 |
| --- | --- | --- |
| `Enable Burst Compilation` | 按平台的总开关，关闭后该平台完全走托管 | 2.11 |
| `Enable Optimizations` | 关闭会让所有 Job 变慢，仅用于原生调试 | 2.11 |
| `Force Debug Information` | 即使 Release 构建也带符号 | 2.11 |
| `Use Platform SDK Linker` | 仅桌面；开启后关闭交叉编译；6.7 手册未列，在 7000.0.0a8 是否还在（待核实） | 2.11 |
| `Target 32Bit / 64Bit / Arm 64Bit CPU Architectures` | 各架构的 CPU 目标；默认 SSE2 与 SSE4，Arm64 默认 `ARMV8A`；每个目标独立编译一次 | 2.11 |
| `Optimize For` | 全局默认：`Performance`、`Size`、`Fast Compilation`、`Balanced`（默认）；被程序集级与 Job 级设置覆盖 | 2.11 |
| `Floating Point Mode` | 全局默认浮点模式，1.8.24 加入；可被 `[BurstCompile(FloatMode = ...)]` 覆盖 | 2.11 |
| `Disabled Warnings` | 屏蔽的警告编号，分号分隔；只对 Player 构建生效，所有平台共享 | 2.11 |
| `Stack Protector`、`Stack Protector Buffer Size` | 栈保护级别 `Off` / `Basic` / `Strong` / `All`，1.8.21 加入 | 2.11、2.12 |

手册中没有名为 Enable Debug Mode、Force Debug Mode、Disable Warnings 的 AOT 选项，对应的实际选项见上表。Player 构建里没有 `Enable Safety Checks` 选项（1.6.0-pre.3 起移除）。见 2.11。

### Burst Inspector、命令行与脚本符号

| 项目 | 说明 | 见 |
| --- | --- | --- |
| Inspector 视图 | `Assembly`、`.NET IL`、`LLVM IR (Unoptimized)`、`LLVM IR (Optimized)`、`LLVM IR Optimization Diagnostics` | 2.5 |
| Inspector 选项 | Output 下拉、`Safety Checks`（评估性能时关闭）、`Show Branch Flow`、`Highlight SIMD Scalar vs Packed`；Architecture 下拉的完整选项名（待核实） | 2.4、2.5 |
| 设置优先级 | 编辑器菜单设置 > Job / 函数指针上的 `BurstCompile` 特性 > 程序集级 `[assembly: BurstCompile]`；`Optimize For` 的 AOT 全局默认被程序集级与 Job 级覆盖 | 2.10、2.11 |
| 构建产物路径 | Windows 独立 Player 的 Burst 库：`<名>_Data/Plugins/x86_64/lib_burst_generated.dll`，托管程序集在 `<名>_Data/Managed/`；其它架构的子目录名手册未给出（待核实）；外部分析工具与原生调试器都指向存放 `lib_burst_generated` 的 `Plugins` 文件夹 | 2.5、2.11 |
| 命令行 | `--burst-disable-compilation`、`--burst-force-sync-compilation`；环境变量 `UNITY_BURST_DISABLE_COMPILATION`（1.8.18 加入，1.8.22 起同时关闭 IL 后处理） | 2.11 |
| 命令行 | `-job-worker-count value`；`-diag-job-temp-memory-leak-validation` 打印泄漏的 TempJob 分配调用栈（来自论坛，待核实） | 1.1、1.5 |
| 脚本符号 | `ENABLE_UNITY_COLLECTIONS_CHECKS`（容器检查，具体宏列表待核实）、`UNITY_BURST_EXPERIMENTAL_LOOP_INTRINSICS`、`UNITY_BURST_EXPERIMENTAL_ALIAS_ATTRIBUTE` | 1.6、2.4、2.10 |
| 运行时属性 | `BurstCompiler.Options.EnableBurstCompilation`、`EnableBurstCompileSynchronously`、`EnableBurstSafetyChecks`；全局开关，测试里改完要在 `finally` 里恢复 | 2.1、2.5 |

## 10 常见报错与症状对照

报错文本取常见形式，类型名、字段名随代码而变，版本间可能略有差别（待核实）。`BC` 编号中，`BC1016`、`BC1042` 及部分编号的消息原文来自论坛或 GitHub，不是官方手册；先读完整报错、文件行号和调用栈，再动手。见 1.6、2.12。

### Job 与安全系统

| 报错或症状 | 常见原因 | 处理 | 见 |
| --- | --- | --- | --- |
| `ObjectDisposedException`（已释放），但自己明明没再 `Dispose` | 通过另一份拷贝 `Dispose` 过：所有拷贝共享同一条安全中心记录，释放使版本号加一 | 找到所有持有同一容器的拷贝，谁创建谁释放；`IsCreated` 只反映被调用的那份拷贝 | 1.6 |
| 访问 `AsArray()`、枚举器等视图时抛异常 | 视图创建后容器扩容，或调度了写该容器的 Job，次级版本号已变化（异常措辞待核实） | 变更后重新取视图，不要长期保存视图 | 1.4、1.6 |
| 嵌套容器（如 `NativeArray<NativeArray<T>>`）的 Job 无法调度 | 安全系统无法给内层容器单独配置 `AtomicSafetyHandle`，`SetNestedContainer` 拦截调度（异常文本待核实） | 展平加偏移表，或用 `Unsafe*`，或 `NativeStream` | 1.4、1.11 |
| 已 `Rewind()` 的 `RewindableAllocator` 之后访问旧容器抛 `ObjectDisposedException` | `Rewind` 使所有子安全句柄失效 | `Rewind` 之前保证没有 Job 还在用，之后不要再访问 | 1.5 |
| 自定义容器在 Player 构建里编译失败，或带着不该有的开销 | 安全代码没用 `ENABLE_UNITY_COLLECTIONS_CHECKS` 包起来 | 把 `m_Safety` 相关代码都包进去 | 1.11 |
| 自定义容器内存泄漏没有警告 | 用了 `Malloc` 而不是 `MallocTracked`，或释放没配 `FreeTracked` | 改用 `MallocTracked` / `FreeTracked` | 1.11 |
| 并行 Job 里对自定义容器写入越界无报错 | 标了 `[NativeContainerSupportsMinMaxWriteRestriction]` 却没有按序相邻的 `m_Length`、`m_MinIndex`、`m_MaxIndex`，或没在范围外抛异常 | 补齐字段并在容器里检查范围 | 1.11 |
| `InvalidOperationException: The previously scheduled job A writes to ... You are trying to schedule the new job B ...` | A 还没完成，B 就读或写同一容器，缺依赖 | `B.Schedule(..., handleOfA)`，或先 `A.Complete()` | 1.3、1.6 |
| `InvalidOperationException: ... You must call JobHandle.Complete() on the job A, before you can read from the ... safely.` | 主线程在 Job 完成前读写被占用的容器 | 先 `Complete()` | 1.6 |
| `... has not been assigned or constructed. All containers must be valid when scheduling a job.` | Job 字段里有没赋值或默认构造的容器 | 给每个字段赋值，可选字段也用空容器；检查 `IsCreated` | 1.6、3.1 |
| `ObjectDisposedException: ... has been deallocated, it is not allowed to access it.` | 释放后继续用，或 Job 还在跑就 `Dispose` | 改 `Dispose(JobHandle)`，或 `Complete` 之后再释放 | 1.3、1.6 |
| `IndexOutOfRangeException: Index N is out of restricted IJobParallelFor range [a...b] in ReadWriteBuffer.` | `Execute(i)` 访问了别人的元素 | 只访问 `i`；确有分区约定再加 `[NativeDisableParallelForRestriction]`；或双缓冲 | 1.6、3.3 |
| `A Native Collection has not been disposed, resulting in a memory leak.` | 分配了没释放 | `Leak Detection Level` 设为 `Enabled With Stack Trace` 定位分配位置，补 `Dispose` | 1.5、1.6 |
| `JobTempAlloc has allocations that are more than 4 frames old`（较新版本措辞可能不同） | `TempJob` 分配超过 4 帧才释放 | 改 `Persistent` 或缩短生命周期 | 1.5、1.6 |
| 写入 `[ReadOnly]` 字段或 `AsReadOnly()` 视图抛异常 | 对只读容器写入 | 去掉写入或去掉 `[ReadOnly]`；措辞待核实 | 1.6 |
| 并行 Job 里对 `NativeList` 直接 `Add` 被安全系统拒绝 | `Add` 会改长度字段，多线程竞争 | 用 `AsParallelWriter()` 加 `AddNoResize`，或两遍法 | 1.7 |
| `AddNoResize` 抛 `InvalidOperationException` | 超过容量，写入器不会扩容 | 并行写入前在主线程把 `Capacity` 设够 | 1.4、1.7 |
| `NativeStream` 抛 `ArgumentException` | `BeginForEachIndex` 之后写入器按值拷贝传递 | 按引用传递写入器 | 1.7 |
| 无报错但结果偶发错误 | 用了 `Unsafe*`、指针或 `[NativeDisable...]`，真正的数据竞争 | 逐项核对读写区域是否重叠；用 `Run()` 与关闭 Burst 对照复现 | 1.6、3.3 |
| `FaceMask` 在区块接缝处多出面 | 现有 Job 的边界判断基于整个体积，邻居被当成空气 | 用带邻居边界的单区块版本 | 3.1 |
| 渲染错乱或崩溃，`SetSubMesh` 无报错 | `indexCount` 与实际写入量不符，Apply 路径几乎不校验 | 核对面数与掩码中 1 的个数 | 1.9、3.4 |
| `new Random(0)` 永远输出同一个值 | 种子为零，状态为 0 | 用非零种子或 `CreateFromIndex` | 2.3 |
| 浮点求和每次结果不同 | 浮点加法不满足结合律，每线程槽位或 `Fast` 改变了求和顺序 | 固定块划分与合并顺序；分块部分和天然满足 | 1.7、2.6 |

### Burst 编译错误与构建问题

| 报错或症状 | 常见原因 | 处理 | 见 |
| --- | --- | --- | --- |
| `BC1016` The managed function `...` is not supported | 在 Burst 里调用托管方法，如 `string.IsNullOrEmpty`、`List<T>` 方法 | 换成 unmanaged 等价物，或移出 Burst 路径；原因常在库代码的调用栈里 | 2.2、2.12 |
| `BC1028` Creating a managed array `T[]` is not supported | Job 里 `new int[n]` | 用 `NativeArray<T>`、`stackalloc` 或 `FixedList` | 2.12 |
| `BC1033` Loading a managed string literal is not supported | 出自较老版本；现在多半是字符串被传进自定义方法或存进字段 | 用 `FixedString128Bytes` 等 | 2.12 |
| `BC1042` The managed class type `X` is not supported | 用了 class，或读取了非 `readonly` 的静态字段 | class 改 struct；静态数据改 `static readonly`、`SharedStatic<T>` 或 Job 字段 | 2.2、2.8、2.12 |
| `BC1045` Struct with auto layout is not supported | `LayoutKind.Auto` 的结构体，如 `ValueTuple` | 自定义 `Sequential` 结构体 | 2.12 |
| `BC1051` Invalid managed type found for the field | 结构体字段是 `int[]`、class、委托 | 字段改成 `NativeArray<T>` 等 unmanaged 类型 | 2.12 |
| `BC1091` External and internal calls are not allowed inside static constructors | 静态初始化里调用了外部函数或分配 | 改成运行时显式初始化，或用 `SharedStatic` | 2.12 |
| `BC1361` 不被支持的静态构造 | `static readonly` 数组用了不可求值的初始化；曾因超大数组触发，后续版本已修复 | 简化成数组初始化器，或把数据作为 Job 字段传入 | 2.2、2.8、2.12 |
| `BC1370` 警告 | `throw` 所在方法没有 `[Conditional("ENABLE_UNITY_COLLECTIONS_CHECKS")]` 保护，Player 里会 abort | 放进带该特性的检查方法；有意崩溃用 `[IgnoreWarning(1370)]` | 2.2、2.10、2.12 |
| `BC1371` 警告 | 对 `[BurstDiscard]` 方法的调用被丢弃 | 让变量有其它用途，或 `[IgnoreWarning(1371)]` | 2.2、2.12 |
| `BC1321` | `Loop.ExpectVectorized()` 的循环没有被向量化 | 去掉 `break` 等阻碍向量化的控制流，或去掉断言 | 2.4、2.12 |
| `BC1054`、`BC1055` | 编译器内部问题（泛型加指针字段、含 `in` 参数的方法），日志称已修复 | 升级 Burst | 2.12 |
| `Can't call the method ... on the generic interface object type ...` | 参数为 `T : IEnumerable<U>` 的泛型方法里 `foreach` | 用具体集合类型或自己写索引循环 | 2.2、2.12 |
| `InvalidOperationException: Burst failed to compile the function pointer ...` | 函数指针目标编译失败，真因在它之前的 `Burst error` | 先修前面的错误；泛型委托不能用于函数指针 | 2.7、2.9、2.12 |
| `The type initializer for 'X$BurstDirectCall' threw an exception` | 内层异常就是上一行的函数指针编译失败 | 看内层异常和它之前的 `Burst error` | 2.12 |
| 泛型 Job 编辑器里很快，Player 里很慢 | 类型实参来自泛型方法或泛型类的参数，构建时 Burst 发现不了该实例 | 用完全确定的类型实参直接创建并调度；`RegisterGenericJobType` 不是官方补救办法 | 2.9、2.12 |
| `AotLinkerException: The native link step failed` | 平台链接器、NDK、Xcode 或 SDK 问题 | 检查平台工具链；桌面上先关掉 `Use Platform SDK Linker` | 2.11、2.12 |
| `Failed to find entry-points` | 1.8.30 修复的一个竞态 | 升级 Burst，或重启编辑器 | 2.12 |
| 构建成功但没有 Burst 效果，无报错 | 平台工具链缺失（Burst 被静默跳过）、`Enable Burst Compilation` 被关、被裁剪 | 确认 Plugins 下有 `lib_burst_generated`，检查构建日志与裁剪级别 | 2.11、2.12 |
| 刚进 Play 模式时 Job 很慢，之后变快 | 异步 JIT 编译完成前跑的是托管版本 | 预热，或开 `Synchronous Compilation` 验证 | 1.8、2.1 |
| Burst 版没变快 | 开关被关、缺 `[BurstCompile]`、`Safety Checks`、调试器、`Debug = true`、数据太小或受内存带宽限制等 | 按 2.12 的 16 项清单逐项排查，Inspector 里看汇编 | 2.5、2.12 |
| 结果与 Mono 不同 | 未初始化内存、浮点模式、数据竞争、越界这四类占绝大多数 | `UninitializedMemory` 先写后读；用默认 `Strict`；逐项核对写区域 | 2.6、2.12 |
| 只在 Player 崩溃或闪退 | 编辑器检查掩盖了指针越界；`throw` 在 Player 里是 abort | 检查异常路径与指针；用 `Native Debug Mode Compilation` 或 `Debug = true` 挂原生调试器 | 2.12 |
| 栈溢出 | 大的 `stackalloc`、大型栈结构、递归过深、循环里反复 `stackalloc` | 大块数据放 `NativeArray`；递归改迭代；Job 线程栈大小（待核实） | 2.12 |
| 编辑器编译时卡死、内存暴涨 | 1.8.25 记录：带 `AggressiveInlining` 的（间接）递归方法 | 去掉强制内联并升级 Burst | 2.12 |

## 11 版本差异与改名速查

### 包形态随 Unity 版本的变化

| 时间或版本 | 事实 | 状态 | 见 |
| --- | --- | --- | --- |
| Unity 2018 | C# Job System 随 2018 系列引入，Burst 与 Mathematics 以预览包出现 | 具体小版本（待核实） | 0.1 |
| Unity 6000.x | Burst 1.8.x 为主线（手册显示 1.8.31），Collections 2.x，Mathematics 1.3.x（手册显示 1.3.2） | 已读手册页 | 0.1 |
| Collections 2.6.2（2025-09） | 将 Burst 依赖更新到 1.8.23 | 本地 CHANGELOG 已读 | 0.1 |
| Unity 6.4 | Collections 6.4.0 条目为核心包，随编辑器分发，更新日志不再维护 | 本地 CHANGELOG 已读 | 0.1、1.4 |
| Unity 6.5 | Mathematics 成为内置模块，`Unity.Mathematics` 默认可用，API 文档并入核心 Scripting API | 手册 Important 提示已读 | 0.1、2.3 |
| Unity 6.7（Collections 6.7.0） | 本地 `Documentation~/index.md` 称从 6.7 起 Collections 是编辑器与引擎的内置模块，文档迁到 Unity Manual | 与“6.4 起为核心包”并存，两者关系（待核实）；一种推断是 6.4 先成核心包、之后再并入引擎模块 | 0.1 |
| Unity 7000.0.0a8（本项目） | `com.unity.burst` 2.0.0，`"type": "shim"`；`com.unity.collections` 6.7.0，描述为已移入引擎模块仅作转发；`packages-lock.json` 里来源为 `builtin` | 本地文件已读 | 0.1、2.11 |
| 项目依赖 | `manifest.json` 没有直接列出 `com.unity.burst` 与 `com.unity.collections`，也没有 `com.unity.mathematics` 目录 | 依赖来源（待核实）；Mathematics 在 7000.0.0a8 能否编译需在 Editor 验证（待核实） | 0.1 |

壳包只含 `package.json`、`Runtime/Unity.Burst.asmdef`、`Runtime/TypeForwarders.cs`。确认转发的类型：`Unity.Burst` 下的 `BurstCompileAttribute`、`BurstCompiler`、`BurstCompilerOptions`、`BurstRuntime`、`BurstExecutionEnvironment`、`FloatMode`、`FloatPrecision`、`OptimizeFor`、`NoAliasAttribute`、`SharedStatic<>`、`FunctionPointer<>`、`IFunctionPointer`；`Unity.Burst.CompilerServices` 下的 `Aliasing`、`AssumeRangeAttribute`、`Constant`、`Hint`、`IgnoreWarningAttribute`、`SkipLocalsInitAttribute`；`Unity.Burst.Intrinsics` 下的 `v64`、`v128`、`v256`、`Common`、`X86`、`Arm`。清单里没有 `BurstDiscardAttribute`，其归属（待核实）。类型名存在不代表行为与 1.8.x 相同，行为以 Unity Manual 为准。见 0.1、2.1。

### Collections 2.x 命名与类型变化

| 旧名或旧写法 | 新名或现状 | 来源与说明 | 见 |
| --- | --- | --- | --- |
| `NativeHashMap<K,V>` | `NativeParallelHashMap<K,V>` | Collections 2.1.0-exp.4 CHANGELOG；旧教程里的并行哈希表要改名 | 1.4 |
| `NativeHashSet<T>` | `NativeParallelHashSet<T>` | 同上 | 1.4 |
| `NativeMultiHashMap<K,V>` | `NativeParallelMultiHashMap<K,V>` | 同上；Unsafe 系列同理（`UnsafeParallelHashMap` 等） | 1.4 |
| （新增） | 单线程的 `NativeHashMap`、`NativeHashSet`、`UnsafeHashMap`、`UnsafeHashSet` | 名字与旧名相同但实现不同，没有 `ParallelWriter` | 1.4 |
| `IJobParallelForFilter` | `IJobFilter` | CHANGELOG | 1.2 |
| `IJobParallelForBatch` 在 `com.unity.jobs` | 来自 Collections | CHANGELOG；`IJobParallelForBatch`、`IJobParallelForDefer`、`IJobFilter` 仍转发到 `Unity.Jobs` 命名空间 | 1.2 |
| `IJobNativeMultiHashMapVisitKeyValue` 等 | 已移除 | Collections 0.12.0（2020-08-04） | 1.2 |
| `NativeArray<T>` 的 `T : struct` | `T : unmanaged` | Collections 2.1 起收紧 | 1.4 |
| 带线程下标参数的 `TryAdd` | 曾公开后改为 internal，`m_ThreadIndex` 改名为 `ThreadIndex` | CHANGELOG；直接调用 `TryAdd(key, value)` | 1.7 |
| `NativeParallelHashMap.ParallelWriter` 无 `Add` | 2.6.0-pre.3 起补充 `Add` | CHANGELOG | 1.4、1.7 |
| 嵌套容器 | 2.1 更新日志提到加入嵌套容器支持（面向 Unsafe 容器） | `NativeArray<NativeArray<T>>` 仍不可用 | 1.4 |
| `FixedString128`（手册示例写法） | `FixedString128Bytes` | 较新 Collections 的名称，以项目里存在的类型为准 | 2.5 |

### Burst 变化

| 项目 | 变化 | 见 |
| --- | --- | --- |
| `Accuracy` 枚举 | 现为 `FloatPrecision` | 2.6 |
| `BurstCompilerOptions.EnableFastMath` | 已弃用，改用 `FloatMode.Fast` | 2.6 |
| `FloatMode.Deterministic` | 枚举很早就以早期预览形式存在；Burst 1.8 更新日志写明 1.8.25（2025-09-16）起正式支持 | 2.6、2.12 |
| AOT 的 `Floating Point Mode`、`Stack Protector`、`[Alias]` | 1.8.24、1.8.21、1.8.21 加入 | 2.10、2.11 |
| Player 的 `Enable Safety Checks` 选项 | 1.6.0-pre.3 移除，容器检查只在编辑器存在 | 2.11 |
| `UNITY_BURST_DISABLE_COMPILATION` | 1.8.18 加入，1.8.22 起同时关闭 IL 后处理 | 2.11 |
| Web 平台 | 1.8.26 起有 “Enable Burst on Web Platform”，1.8.30 加入 Wasm64 目标；Web 上的限制（待核实） | 2.11 |
| 1.8.30 / 1.8.31 | 最低编辑器版本提高到 6.0，默认 LLVM 升到 21 / 23 | 2.12 |
| Burst 2.0.0 | 相对 1.8.x 的变更说明（What's new、升级指南）没能核实到，行为变化、错误码增删（待核实）；升级编辑器后要重跑性能基线与结果对比 | 2.12 |
| `[assembly: RegisterGenericJobType]` | 属 `Unity.Jobs`（6.7 Scripting API 页面确认），不属 `Unity.Burst` | 2.9 |

### BC 错误码来源

官方手册只收录 `BC1361`、`BC1370`、`BC1371`、`BC1321`；更新日志里还有 `BC1054`、`BC1055`、`BC1091`；其余编号的消息原文来自论坛与 GitHub。2.0.0 是否增删编号（待核实）。见 2.2、2.12 与本页第 10 节。

### 文档位置速记

| 内容 | 看哪里 | 见 |
| --- | --- | --- |
| Job System | Unity Manual 的 Write multithreaded code with the job system 及子页面 | 0.1 |
| Collections | 6.7 之后看 Unity Manual 的 Collections 章节；较低版本用包手册，如 `Packages/com.unity.collections@2.5/manual/index.html`；`Manual/collections/collections.html` 线上返回 404 | 0.1 |
| Burst | `Packages/com.unity.burst@1.8/manual/index.html` 最全；新版本在 Unity Manual 的 `burst/` 路径下 | 0.1、2.11 |
| Mathematics | 6.5 之前看包手册 1.3；6.5 起看 Scripting API 的 `Unity.Mathematics.math` 与 Manual 的 Unity Mathematics APIs | 0.1 |
