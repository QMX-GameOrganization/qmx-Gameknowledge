---
title: "1.4 NativeContainer 容器"
description: 讲清 NativeArray、NativeList、哈希容器、Unsafe 容器的区别、命名变化与选型，并结合体素区块数据说明改用 NativeArray 的收益。
sidebar:
  order: 4
---

> 适用版本：以 Unity 6000.x 的 Collections 2.x 为主线；Unity 6.4 起 Collections 作为核心包随编辑器分发；本项目的 Unity 7000.0.0a8 中 Collections 6.7.0 是转发（shim）壳包，类型仍在 `Unity.Collections` 命名空间，文档迁到了 Unity Manual。

## 要点

- `NativeContainer` 是原生（非托管）内存的托管包装，自带安全检查，是 Job 与主线程共享数据的标准方式。
- Job 的字段只能是 unmanaged 数据（值类型且不含引用）和 `NativeContainer`；`byte[]`、`List<T>`、`class` 引用都不行。
- 最常用的三个：`NativeArray<T>`（定长）、`NativeList<T>`（可变长）、`NativeParallelHashMap<K,V>`（并行写哈希表）。
- Collections 2.1 起哈希容器改名：原 `NativeHashMap` 变成 `NativeParallelHashMap`，新的 `NativeHashMap` 是单线程友好的版本。读旧教程时要特别注意。
- `Unsafe*` 容器没有安全检查，但可以嵌套、可以放进别的 unmanaged 结构，适合底层实现，代价是出错没有提示。
- 容器内不能再放 `NativeContainer`（`NativeArray<NativeArray<T>>` 不行；官方的说法是安全系统不支持 Job 里的嵌套容器，违规在"调度 Job"时被拒绝），用 `UnsafeList<T>` 或"展平 + 偏移表"替代。
- 多数 `Native*` 容器只是对 `Unsafe*` 版本的封装外加安全句柄；关掉检查后两者性能没有显著差别，所以优先选 `Native*`，只有嵌套等必须场景才用 `Unsafe*`。
- 排序、查找、拷贝等常用操作在扩展类 `NativeSortExtension`、`NativeArrayExtensions`、`ListExtensions` 里；多数容器有 `GetEnumerator`，但枚举器属于"视图"，容器扩容或释放后即失效。

## 为什么 Job 里只能用它们

Job 在工作线程上运行，托管堆对象受垃圾回收（GC）管理，GC 可能移动或回收对象，线程间共享也没有任何保护。因此 Job 结构体必须是 blittable/unmanaged 的：字段只能是数值、`float3` 之类的值类型、固定大小结构，以及 `NativeContainer`。

`NativeContainer` 做了两件事：

- 数据放在原生内存里，不受 GC 影响，Job 与主线程指向同一块内存，不是复制品。
- 内部带 `AtomicSafetyHandle`（见"安全系统与竞争条件"一章），在编辑器和开发构建里检查读写冲突、越界和释放后使用。

```
托管世界(GC)            原生世界(手动管理)
 byte[] / List<T>   ->   NativeArray<byte> / NativeList<T>
 (Job 不可用)             (Job 可用, 须 Dispose)
```

官方手册对 `NativeContainer` 的定义是"原生内存的线程安全 C# 包装"；引擎自带的只有 `NativeArray<T>` 与 `NativeSlice<T>`，其余在 Collections 里（Unity 6.4 起 Collections 随编辑器分发）。

## NativeArray&lt;T&gt;

### 构造与 Allocator

```csharp
using Unity.Collections;

// 长度 1024，TempJob 分配，默认清零（NativeArrayOptions.ClearMemory）
var a = new NativeArray<byte>(1024, Allocator.TempJob);

// 不清零：自己保证每个元素在读之前都被写过，省一次 memset
var b = new NativeArray<byte>(1024, Allocator.Persistent,
                              NativeArrayOptions.UninitializedMemory);

// 从托管数组拷贝创建
byte[] managed = new byte[1024];
var c = new NativeArray<byte>(managed, Allocator.Persistent);

a.Dispose(); b.Dispose(); c.Dispose();
```

`T` 必须是 `unmanaged`（Collections 2.1 起约束从 `struct` 收紧为 `unmanaged`）。Allocator 的含义见"内存分配器与生命周期"一章。

### 常用成员

| 成员 | 说明 |
|---|---|
| 索引器 `a[i]` | 读写单个元素；索引器返回的是元素副本（不是 `ref`），元素是 struct 时 `a[i].x = 1` 无法编译，要"取出、修改、写回" |
| `Length` / `IsCreated` | 长度；是否已创建（默认构造或 `Dispose` 后为 false） |
| `Dispose()` / `Dispose(JobHandle)` | 立即释放 / 在 Job 之后释放 |
| `CopyFrom(T[])`、`CopyTo(T[])` | 与托管数组互拷，长度须匹配 |
| `ToArray()` | 拷出一个新托管数组，会产生 GC 分配 |
| `GetSubArray(start, length)` | 不拷贝的子视图，仍是 `NativeArray<T>`，共享同一块内存 |
| `Reinterpret<U>()` | 按另一种 unmanaged 类型重新解释同一块内存（如 `byte` 当 `uint` 用），元素大小须整除 |
| `AsReadOnly()` | 返回只读包装 `NativeArray<T>.ReadOnly` |
| `GetUnsafePtr` / `GetUnsafeReadOnlyPtr` | 在 `NativeArrayUnsafeUtility` 中，取原始指针，绕过安全检查 |

```csharp
using Unity.Collections;
using Unity.Collections.LowLevel.Unsafe;

var arr = new NativeArray<byte>(16, Allocator.Temp);

// 取出、修改、写回
byte v = arr[3];
v += 1;
arr[3] = v;

// 子视图：不拷贝，改动会影响原数组
NativeArray<byte> head = arr.GetSubArray(0, 4);

// 重新解释：16 个 byte 当作 4 个 uint
NativeArray<uint> asUint = arr.Reinterpret<uint>(sizeof(byte));

// 指针访问（unsafe 上下文，须开启 Allow unsafe code，安全系统不再保护）
unsafe
{
    byte* p = (byte*)NativeArrayUnsafeUtility.GetUnsafePtr(arr);
    p[0] = 1;
}
arr.Dispose();
```

### 与 Span、NativeSlice 的关系

- `NativeSlice<T>`：对 `NativeArray` 的一段视图，可带步长（stride），是引擎自带的 `NativeContainer`，能用于 Job。
- `Span<T>` / `ReadOnlySpan<T>`：ref struct，只能在栈上使用，不能做 Job 字段。`NativeArray` 有 `AsSpan()` / `AsReadOnlySpan()` 之类的转换（具体可用版本待核实），用于在主线程或 Burst 函数里做高效切片。
- 遇到需要放进 Job 字段的"切片"，用 `GetSubArray` 或 `NativeSlice`，不要用 `Span`。

## NativeList&lt;T&gt;

可变长列表，有容量（Capacity）与长度（Length）之分。容量不够时自动扩容，扩容要重新分配并拷贝，所以预估大小能避免抖动。

```csharp
var list = new NativeList<int>(256, Allocator.TempJob); // 初始容量 256
list.Add(1);
list.AddRange(new NativeArray<int>(4, Allocator.Temp));
list.ResizeUninitialized(100);  // 把 Length 设为 100，新增元素不清零
NativeArray<int> view = list.AsArray(); // 当前内容的数组视图
list.Dispose();
```

要点：

- `AsArray()`：返回指向列表当前缓冲区的 `NativeArray` 视图。列表扩容后旧视图失效，别长期持有。
- `AsDeferredJobArray()`：Job 调度时列表长度还没确定（要等前一个 Job 往里写完），用这个"延迟数组"传给后续 Job。它要配合 `IJobParallelForDefer` 使用（见 1.2），后者在 Collections 的类型转发列表里存在。
- `AsParallelWriter()` 返回 `NativeList<T>.ParallelWriter`，多线程可调用 `AddNoResize` / `AddRangeNoResize`：不能扩容，容量必须事先留够，否则会报错。

```csharp
[BurstCompile]
struct CollectJob : IJobParallelFor
{
    public NativeList<int>.ParallelWriter Output; // 容量须事先足够
    public void Execute(int i) { if (i % 2 == 0) Output.AddNoResize(i); }
}
```

## 其它常用容器

| 容器 | 用途 | 并行写 |
|---|---|---|
| `NativeQueue<T>` | 先进先出队列，可扩容 | `AsParallelWriter()`，多线程 `Enqueue` |
| `NativeRingQueue<T>` | 固定容量环形缓冲 | 否 |
| `NativeStream` | 一组只追加的无类型缓冲，每个并行索引一个缓冲，适合"多线程各自输出、之后统一读取" | 每个 foreachIndex 独立写 |
| `NativeReference<T>` | 单个值的引用，等价长度为 1 的数组，Job 里用来回传一个结果 | 否 |
| `NativeBitArray` | 任意长度位数组；`BitField32` / `BitField64` 是固定 32/64 位 | 否 |
| `NativeText` | UTF-8 可变字符串 | 否 |
| `FixedString32Bytes` 等 | 固定大小字符串，32/64/128/512/4096 字节，含 3 字节开销 | 值类型，随结构拷贝 |
| `FixedList32Bytes<T>` 等 | 固定大小列表，32/64/128/512/4096 字节，含 2 字节开销 | 值类型 |

`FixedString*` / `FixedList*` 内联在结构体里，不分配堆内存，所以不需要 `Dispose`，也能出现在任何 unmanaged 结构中。容量固定，超出会失败。

`NativeStream` 的典型用法：并行 Job 里每个 index 写入自己的缓冲，之后另一个 Job 读取。它比"多线程抢同一个 `NativeQueue`"更少竞争。

```csharp
var stream = new NativeStream(chunkCount, Allocator.TempJob);
// 写入 Job: var w = stream.AsWriter(); w.BeginForEachIndex(i); w.Write(item); w.EndForEachIndex();
// 读取 Job: var r = stream.AsReader(); int n = r.BeginForEachIndex(i); ... r.EndForEachIndex();
```

## 哈希容器的命名与区别

Collections 2.1.0-exp.4 的更新日志里有一次关键改名（我在本地包的 CHANGELOG.md 中核实）：

| 旧名（Collections 1.x） | 新名（2.x） |
|---|---|
| `NativeHashMap<K,V>` | `NativeParallelHashMap<K,V>` |
| `NativeHashSet<T>` | `NativeParallelHashSet<T>` |
| `NativeMultiHashMap<K,V>` | `NativeParallelMultiHashMap<K,V>` |
| （Unsafe 同理：`UnsafeHashMap` 等） | `UnsafeParallelHashMap` 等 |

同一版本还"新增"了面向单线程的 `NativeHashMap<K,V>`、`NativeHashSet<T>`、`UnsafeHashMap`、`UnsafeHashSet`，名字与旧名相同但实现不同，网上老教程里的 `NativeHashMap` 在新版里应写成 `NativeParallelHashMap`。

| 容器 | 特点 | 并行写 |
|---|---|---|
| `NativeHashMap<K,V>` | 单线程场景、内存开销较低 | 否（官方 API 文档注明不适合并行写入，没有 `ParallelWriter`，并行写入请改用 `NativeParallelHashMap`） |
| `NativeHashSet<T>` | 同上，集合 | 否 |
| `NativeParallelHashMap<K,V>` | 多线程场景，内存开销较高 | `AsParallelWriter()`，可 `TryAdd` |
| `NativeParallelHashSet<T>` | 并行集合 | 有 `ParallelWriter` |
| `NativeParallelMultiHashMap<K,V>` | 键可重复，一键多值 | 有 `ParallelWriter` |

并行版本的 `ParallelWriter` 只能添加（`TryAdd`/`Add`），读取与删除应放在另一个 Job 阶段。Collections 2.6.0-pre.3 的更新日志还提到给 `NativeParallelHashMap.ParallelWriter` 与 `UnsafeParallelHashMap.ParallelWriter` 补充了 `Add` 方法。

本项目的使用场景可以这样选：区块坐标表（`int2` 到区块索引）在主线程更新，用 `NativeHashMap`；多个 Job 并行登记"需要重建网格的区块"，用 `NativeParallelHashSet` 的 `ParallelWriter`。

## Unsafe* 容器

`UnsafeList<T>`、`UnsafeHashMap<K,V>`、`UnsafeParallelHashMap`、`UnsafeStream`、`UnsafeAppendBuffer`、`UnsafeBitArray`、`UnsafeText`、`UnsafePtrList<T>`、`UnsafeRingQueue<T>`、`UnsafeAtomicCounter32/64` 等都存在于类型转发列表中。

特点：

- 没有 `AtomicSafetyHandle`，不检查读写冲突、也不检查是否已释放；Collections 手册说明，`TempJob` 超 4 帧不释放时，`Unsafe-` 容器也不会有提醒。
- 本身是纯 unmanaged 结构（内含指针和分配器句柄），因此可以放进另一个结构、嵌套，或存进 `NativeArray` 的元素里。
- 并行访问全靠自己约定；常搭配 `[NativeDisableContainerSafetyRestriction]` 或把整个结构当 Job 字段。

```csharp
// 需要 using Unity.Collections.LowLevel.Unsafe;
// 嵌套 Unsafe 容器：每个区块一个 UnsafeList<byte>，外层 NativeArray 存它们
var lists = new NativeArray<UnsafeList<byte>>(chunkCount, Allocator.Persistent);
for (int i = 0; i < lists.Length; i++)
    lists[i] = new UnsafeList<byte>(98304, Allocator.Persistent);
// 释放时要逐个 Dispose 内层，再 Dispose 外层
```

## Native 容器与 Unsafe 容器的关系

Collections 手册的 Collections overview 页把这两类容器的关系讲得很明确（2.5 版核实）：

- 命名空间与前缀：带安全检查的在 `Unity.Collections`，名字以 `Native` 开头；不带检查的在 `Unity.Collections.LowLevel.Unsafe`，名字以 `Unsafe` 开头。另有一批不分配内存也不含指针的小类型（如 `FixedString*`、`BitField32`），释放与线程安全都不是问题。
- 检查内容：`Native*` 会检查释放与线程安全，并检查传入方法的下标是否越界；`Unsafe*` 没有这些检查。
- 一一对应：`NativeList` 对应 `UnsafeList`，`NativeHashMap` 对应 `UnsafeHashMap`，依此类推。
- 建议：优先用 `Native*`。只有在必须嵌套时才用 `Unsafe*`，例如 `NativeList<UnsafeList<T>>` 或 `UnsafeList<UnsafeList<T>>` 可以，`NativeList<NativeList<T>>` 不行。
- 性能：如果关闭了安全检查，`Native*` 与对应 `Unsafe*` 没有显著性能差别；多数 `Native*` 容器本身就是对 `Unsafe*` 的封装，例如 `NativeList` 由一个 `UnsafeList` 加上安全检查用的句柄组成。

这解释了前面"误以为 `Unsafe*` 更快"那条坑：差别只在检查，而检查在 Release 构建里本来就被去掉了（见 1.6 安全系统与竞争条件）。开发阶段保持 `Native*`，才能让编辑器替你抓竞争条件。

## bool 在 NativeArray 中

`NativeArray<bool>` 可以编译并在 Job/Burst 中使用，bool 在 Unity 的 Job 与 Burst 里按 1 字节处理。但 .NET 层面 `bool` 不是严格的 blittable 类型，而且在 `Reinterpret`、写 GPU 缓冲、跨语言交换数据时容易出现取值不是 0/1 的问题。建议（经验性，Burst 对 bool 的官方说明待核实）：

- 只在 Job 内部使用、不做 `Reinterpret` 时，`bool` 可用。
- 需要 `Reinterpret`、上传 GPU 或持久化时，用 `byte`（0/1），语义清晰。
- 大量布尔标记且只关心存在性时，`NativeBitArray` 每个标记占 1 位，省 8 倍内存。

## 容器不能嵌套 NativeContainer

`NativeArray<NativeArray<T>>` 不能用于 Job：每个 `Native*` 容器带安全句柄，嵌套后安全系统无法给内层容器单独配置 `AtomicSafetyHandle`。

这里要区分"创建"与"调度"。官方自定义容器手册的说法是：安全系统不支持 Job 中的嵌套容器，用 `AtomicSafetyHandle.SetNestedContainer` 把"装着别的 NativeContainer 的容器"标记为嵌套容器，目的是阻止调度使用它的 Job。官方示例 `NativeAppendOnlyList<T>` 的构造函数里，当 `T` 本身是 NativeContainer 类型时调用 `SetNestedContainer(m_Safety, true)`，说明容器本身是可以被创建出来的，被拒绝的是"把它交给 Job 调度"这一步（见 1.11 自定义 NativeContainer）。所以旧稿里"创建时被拒绝"不准确，应理解为"调度时被安全系统拒绝"；具体异常类型与文本待核实。Collections 手册另有一句："`Native` 容器不能包含其它 `Native` 容器，因为 Unity 实现 `Native` 安全检查的方式如此"，并举例 `NativeList<UnsafeList<T>>` 与 `UnsafeList<UnsafeList<T>>` 可以，`NativeList<NativeList<T>>` 不行。替代方案：

- 展平加偏移表：一个大 `NativeArray<T>` 存全部数据，另一个 `NativeArray<int2>`（start, length）记录每段位置。适合只读/一次写入的静态数据。
- `UnsafeList<T>` 数组：外层 `NativeArray<UnsafeList<T>>`，如上例。Collections 2.1 更新日志提到加入了对嵌套容器的支持（面向 Unsafe 容器）。
- `NativeStream` / `NativeParallelMultiHashMap`：本质是"一键多值/多段缓冲"，天然表达嵌套关系。

## 排序与扩展方法

Collection types 页末尾点名了三个扩展类：`NativeArrayExtensions`、`ListExtensions`、`NativeSortExtension`，都在 `Unity.Collections` 命名空间。下面的签名来自 Collections 2.5 的 API 页（逐个核对过）。

### NativeSortExtension

静态类，提供排序、并行排序用的 Job 和二分查找。要点：

| 方法（均为扩展方法） | 说明 |
|---|---|
| `Sort<T>(this NativeArray<T> array)` | 同步排序，用默认比较；另有 `NativeList<T>`、`NativeSlice<T>`、`UnsafeList<T>` 和 `Sort<T>(T* array, int length)` 重载 |
| `Sort<T, U>(this NativeArray<T> array, U comp)` | 用自定义比较器 `comp` 排序，同样有 `NativeList` / `NativeSlice` / `UnsafeList` / 指针重载 |
| `SortJob<T>(this NativeArray<T> array)` | 返回 `SortJob<T, DefaultComparer<T>>`，一个可以调度的排序 Job；同样有 `NativeList` / `NativeSlice` / `UnsafeList` / 指针重载 |
| `SortJob<T, U>(this NativeArray<T> array, U comp)` | 带自定义比较器的 `SortJob` |
| `SortJobDefer<T>(this NativeList<T> list)` | 返回 `SortJobDefer<T, DefaultComparer<T>>`，用于列表长度要到 Job 执行时才确定的场景；另有带比较器 `U comp` 的重载 |
| `BinarySearch<T>(...)`、`BinarySearch<T, U>(...)` | 在已排序容器里二分查找，有多个重载，这里不逐个展开 |

约束：默认比较的重载要求 `T : unmanaged, IComparable`（泛型参数的具体形式以 API 页为准，待核实）。`SortJob` 返回的只是 Job 结构，怎么调度（`Schedule` 的签名与是否内部并行）我没有逐项核对，待核实，使用前请查对应的 `SortJob` API 页。

用法示意（教学用，未在 Unity 内编译）：

```csharp
using Unity.Collections;

var ids = new NativeArray<int>(1024, Allocator.TempJob);
// ... 填充 ...

// 同步排序：在主线程或 Job 内直接调用
ids.Sort();

// 作为 Job 排序：返回的 SortJob 是一个 Job 结构，调度方式见 API 页（待核实）
var sortJob = ids.SortJob();
```

对应本项目：想让网格输出"按稳定顺序"而不是 `ParallelWriter` 的随机顺序时，可以在写完之后对结果排序，这是官方列出的三种确定性手段之一（见 1.7 并行写入与归约模式）。

### NativeArrayExtensions

针对 `NativeArray<T>` 的辅助方法：

- `ArraysEqual<T>(this NativeArray<T> container, NativeArray<T> other)`：长度与内容都相等才返回 true，`T : unmanaged, IEquatable<T>`。
- `Contains<T, U>(this NativeArray<T> array, U value)`：是否包含某个值；另有 `NativeArray<T>.ReadOnly` 与 `void* ptr, int length` 版本。
- `IndexOf<T, U>(this NativeArray<T> array, U value)`：第一次出现的下标，找不到返回 -1；同样有 `ReadOnly` 与指针版本。
- `CopyFrom<T>(this ref NativeArray<T> container, NativeList<T> other)`：把容器内容复制进数组，另有 `NativeHashSet<T>`、`UnsafeHashSet<T>` 版本；数组与容器长度不等时抛 `ArgumentException`。
- `Reinterpret<T, U>(this NativeArray<T> array)`：按另一种元素类型重新解释，容量不能被 `sizeof(U)` 整除时抛 `InvalidOperationException`（别名机制见 1.5 内存分配器与生命周期）。

### ListExtensions

注意这里的 `List<T>` 是托管的 `System.Collections.Generic.List<T>`，不是 `NativeList`：

- `RemoveAtSwapBack<T>(this List<T> list, int index)`：用最后一个元素覆盖该下标并把长度减一，O(1) 但会打乱顺序。
- `RemoveSwapBack<T>(this List<T> list, T value)` 与 `RemoveSwapBack<T>(this List<T> list, Predicate<T> matcher)`：找到第一个匹配项并用同样方式删除，返回是否删除成功。
- `ToNativeArray<T>(this List<T> list, AllocatorManager.AllocatorHandle allocator)` 与 `ToNativeList<T>(...)`：把托管列表复制成 Native 容器，`T : unmanaged`。

## 容器枚举器与 GetEnumerator

Collection types 页说明：大多数集合都有 `GetEnumerator`，返回 `IEnumerator<T>` 的实现，`MoveNext` 前进、`Current` 取当前元素；第一次 `MoveNext` 才会移到第一个元素，越过末尾后返回 false。官方示例：

```csharp
NativeList<int> nums = new NativeList<int>(10, Allocator.Temp);

int sum = 0;
var enumerator = nums.GetEnumerator();
while (enumerator.MoveNext())
{
    sum += enumerator.Current;
}

// 容器释放后，枚举器不能再用
nums.Dispose();
```

哈希表也有：`NativeParallelHashMap<K,V>` 的 2.5 API 页列出 `GetEnumerator()`，返回 `NativeParallelHashMap<K,V>.Enumerator`，遍历键值对；还有 `GetKeyArray(allocator)`、`GetValueArray(allocator)`、`GetKeyValueArrays(allocator)`，会把键或值复制成新数组（顺序不确定）。

什么时候枚举器会失效。官方在 Copying NativeContainer structures 里把枚举器归为"视图"（view，即不拷贝、不持有数据的别名访问），并说明：

- 容器被 `Dispose` 后，枚举器和其它视图都不能再用。
- 动态容器（`NativeList` 这类可变长容器）的大小改变时，Unity 会把数据搬到别处，视图里存的指针随之无效，所以视图在大小变化时"通常不是线程安全的"；安全系统靠次级版本号让旧视图失效（见 1.6 的"容器拷贝语义与 AtomicSafetyHandle 版本号机制"）。

据此的使用规则：枚举期间不要对同一容器增删、扩容；不要把枚举器带出当前作用域长期保存；在 Job 里遍历就让 Job 独占读，不要同时有别的 Job 写它。枚举器失效时具体抛哪种异常、哈希表在枚举中插入的确切行为，官方页面没有写明，待核实。

## 选型表

| 场景 | 推荐容器 |
|---|---|
| 长度固定的数据块（体素、噪声缓存） | `NativeArray<T>` |
| 结果数量不确定，单线程追加 | `NativeList<T>` |
| 多线程并行追加，上限已知 | `NativeList<T>.ParallelWriter`（`AddNoResize`） |
| 多线程各自输出，数量不确定 | `NativeStream` 或每线程一个 `NativeList` |
| 多线程追加、顺序不重要 | `NativeQueue<T>.ParallelWriter` |
| 键值映射，主线程/单 Job 使用 | `NativeHashMap<K,V>` |
| 键值映射，多线程写入 | `NativeParallelHashMap<K,V>.ParallelWriter` |
| 一键多值（如区块到实体） | `NativeParallelMultiHashMap<K,V>` |
| 去重集合 | `NativeHashSet<T>` / `NativeParallelHashSet<T>` |
| 返回单个结果 | `NativeReference<T>` 或长度 1 的 `NativeArray` |
| 大量布尔标记 | `NativeBitArray` |
| 需要嵌套、放进别的 unmanaged 结构 | `Unsafe*` 系列 |
| 小而固定的数据（名字、几个槽位） | `FixedString*` / `FixedList*` |

## 自定义 NativeContainer（概述）

当现有容器不够用，可以自己写：给结构标 `[NativeContainer]`，内含名为 `m_Safety` 的 `AtomicSafetyHandle`（仅在启用检查时编译），并按需用 `[NativeContainerSupportsMinMaxWriteRestriction]` 等属性声明能力，在构造与 `Dispose` 里创建和释放安全句柄、用 `MallocTracked` 分配以便泄漏跟踪。完整步骤、官方示例和各特性的作用见 1.11 自定义 NativeContainer。

## 对应本项目：VoxelChunk

我读过 `Assets/Scripts/WorldGen/Voxels/VoxelChunk.cs`：`VoxelChunk` 是 `sealed class`，体素存在 `private readonly byte[] solid` 中，索引为 `x + SizeX * (y + SizeY * z)`，通过 `Fill(IDensityFunction, int, int, int)` 逐点采样，并以 `internal byte[] RawSolid` 暴露给采样器，`SolidCount` 记录实心数。

若把 `solid` 改成 `NativeArray<byte>`，可得到：

- Job 可直接读写同一块数据，无需 `memcpy` 到别处；`RawSolid` 可作为 `[ReadOnly]` 字段传给网格生成 Job。
- 不进入 GC 堆：按 16×16×384 估算每块 98 304 字节（见"内存分配器与生命周期"），数据量不小，大量托管数组会增加 GC 压力与碎片；改为 Native 内存后不受 GC 管理。
- 方便池化：`Persistent` 缓冲复用，避免反复分配与回收。
- 邻居数据只读共享：构建网格要读四邻区块，多个 Job 可同时以 `[ReadOnly]` 读取。

需要付出的代价：`VoxelChunk` 必须实现 `IDisposable` 并保证释放；现在的类依赖 GC 回收，改动后要补生命周期管理；`Fill` 里调用 `IDensityFunction`（接口/托管对象）也不能直接进 Burst Job，需另行改造成 unmanaged 的采样 Job。这是后续章节的主题。

## 常见坑

- 忘记 `Dispose`：`NativeArray` 离开作用域不会自动释放，编辑器会报泄漏警告。
- `ToArray()` 在热路径里调用：每次都产生托管分配与拷贝。
- 把 `NativeList.AsArray()` 的结果长期保存：列表扩容后视图指向旧缓冲。
- 把旧教程里的 `NativeHashMap` 当并行容器用：在 2.x 里并行版是 `NativeParallelHashMap`。
- `NativeList.ParallelWriter.AddNoResize` 超过容量：不会扩容，会报错；调用前先 `list.Capacity` 留足。
- `UninitializedMemory` 后直接读：读到的是垃圾数据，必须保证先写后读。
- `Reinterpret<U>` 的元素大小不匹配：长度换算要整除，否则抛异常。
- 在 Job 里使用 `byte[]`、`List<T>`、`string`：托管类型不能进 Job（Burst 下直接报错）。
- 误以为 `Unsafe*` 更"快"所以到处用：它们快的部分只是少了检查，真正的性能来自 Burst 与数据布局；失去检查后出错更难查。

## 小结

- `NativeContainer` 是 Job 与主线程共享数据的方式，自带安全检查，须手动 `Dispose`。
- 定长用 `NativeArray`，可变长用 `NativeList`，并行写哈希表用 `NativeParallelHashMap`；单线程哈希表用 `NativeHashMap`（2.x 命名）。
- `Unsafe*` 容器无检查、可嵌套；`NativeContainer` 不能嵌套，用展平+偏移表或 `UnsafeList` 数组。
- `bool` 可用但跨边界建议用 `byte`；大量标记考虑 `NativeBitArray`。
- `VoxelChunk` 的 `byte[]` 改 `NativeArray<byte>` 能直接进 Job、避开 GC，但需要补生命周期管理与 unmanaged 采样。

## 自测题

1. 为什么 Job 里不能用 `byte[]`？
   答：它是托管堆对象，受 GC 管理且线程间无保护；Job 只允许 unmanaged 数据与 `NativeContainer`。
2. Collections 2.x 里，要在 Job 里并行写入哈希表，应该用哪个类型？
   答：`NativeParallelHashMap<K,V>` 的 `ParallelWriter`（旧版叫 `NativeHashMap`）。
3. `NativeArray<NativeArray<int>>` 不行，给出两种替代。
   答：展平数组加偏移表；`NativeArray<UnsafeList<int>>`。
4. `NativeList<T>.ParallelWriter.AddNoResize` 的前提是什么？
   答：容量事先足够，因为它不会扩容。
5. `NativeArray<T>.GetSubArray` 与 `ToArray` 的区别？
   答：前者是共享内存的视图，不拷贝；后者拷贝成托管数组。
6. 关闭安全检查后，`NativeList<T>` 和 `UnsafeList<T>` 的性能有明显差别吗？
   答：官方说没有显著差别，`NativeList` 本身就是 `UnsafeList` 加安全句柄的封装。
7. `NativeList` 的枚举器在什么情况下失效？
   答：容器被释放，或容器大小变化导致数据被搬走时；枚举期间不要增删、扩容。
8. `NativeArray<NativeArray<int>>` 是在创建时还是调度时被拒绝？
   答：按官方自定义容器手册，被拒绝的是调度使用它的 Job（`SetNestedContainer` 的作用）；具体异常文本待核实。

## 参考

- https://docs.unity3d.com/Manual/job-system-native-container.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/manual/collection-types.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/manual/allocator-overview.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/manual/collections-overview.html （Native 与 Unsafe 对比）
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/api/Unity.Collections.NativeSortExtension.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/api/Unity.Collections.NativeArrayExtensions.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/api/Unity.Collections.ListExtensions.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/api/Unity.Collections.NativeParallelHashMap-2.html （GetEnumerator 与 GetKeyArray 等）
- https://docs.unity3d.com/Manual/job-system-custom-nativecontainer.html （SetNestedContainer）
- 本地：D:\UnityHub\Project\程序化生成\Library\PackageCache\com.unity.collections@28abc463ca66\CHANGELOG.md（改名与嵌套容器条目）
- 本地：D:\UnityHub\Project\程序化生成\Library\PackageCache\com.unity.collections@28abc463ca66\Unity.Collections\AssemblyTypeForwarders.cs（确认类型存在）
- 本地：D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelChunk.cs
