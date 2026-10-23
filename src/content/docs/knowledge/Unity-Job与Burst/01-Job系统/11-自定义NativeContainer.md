---
title: "1.11 自定义 NativeContainer"
description: 讲清何时需要自己写 NativeContainer，如何用 AtomicSafetyHandle 做使用跟踪、用 MallocTracked 做泄漏跟踪，以及相关特性与 JobProducerType 的作用。
sidebar:
  order: 11
---

> 适用版本：以 Unity 6000.x 手册（页面核对于 6000.6）为主线；Collections 2.x 的 `CollectionHelper` 等辅助 API 以 2.5 文档为准。本项目的 Unity 7000.0.0a8 中 Collections 6.7.0 是转发壳包，`[NativeContainer]` 等特性与 `AtomicSafetyHandle` 属于引擎核心模块，7000 上未逐项实测（待核实）。代码为教学用，未在 Unity 内编译。

## 要点

- 绝大多数项目用不着自己写容器：`NativeArray`、`NativeList`、哈希容器和 `NativeStream` 已覆盖常见需求。只有现有容器的数据结构不合用，又想继续享受安全系统和 Job 集成时才值得写。
- 自定义容器要做两件事：使用跟踪（让 Unity 知道哪些已调度的 Job 在用它，从而发现冲突）和泄漏跟踪（发现没有 `Dispose` 的容器）。
- 结构要标 `[NativeContainer]`，且必须有一个名为 `m_Safety` 的 `AtomicSafetyHandle` 字段，名字不能改。
- 读写前调用 `AtomicSafetyHandle.CheckReadAndThrow` / `CheckWriteAndThrow`；这些代码用 `ENABLE_UNITY_COLLECTIONS_CHECKS` 包起来，只在编辑器和开发构建里生效。
- 用 `UnsafeUtility.MallocTracked` / `FreeTracked` 分配和释放内存，泄漏跟踪由此自动生效；`NativeLeakDetection.Mode` 控制是否记录分配栈。
- `SetNestedContainer` 的作用是"阻止调度使用嵌套容器的 Job"，不是阻止你创建这种容器。
- 写错了可能直接让 Unity 崩溃而不是抛异常，官方要求为所有场景（尤其是与 Job 的集成）补测试。

## 何时需要自定义

自己写容器值得考虑的情形：

- 需要一种内置没有的数据结构，例如本项目里"按区块分段、只追加、之后只读"的变长体素缓冲，并希望它能放进 Job、被安全系统检查。
- 想给现有思路加专用的安全规则（比如只允许追加、不允许改写已有元素）。

不值得写的情形：只是想嵌套容器（用 `UnsafeList` 等，见 1.4）、只是想池化（用池管理 `NativeArray`，见 1.5）、只是想少写几行（扩展方法就够了）。

如果容器没有正确接入安全系统，就失去了 Job 调试器的保护，错误会变成随机崩溃或脏数据。所以先问自己：`Unsafe*` 加一套自己的不变量是否更便宜？

## 两大要素

官方自定义容器手册（Implement a custom native container）把工作分成两块：

| 要素 | 作用 | 靠什么实现 |
|---|---|---|
| 使用跟踪（usage tracking） | 让 Unity 跟踪使用该容器的已调度 Job，发现并阻止冲突，比如两个 Job 同时写同一个容器 | `AtomicSafetyHandle` |
| 泄漏跟踪（leak tracking） | 发现没有被正确释放的容器；泄漏意味着这块内存在程序剩余生命周期里都不可用 | `UnsafeUtility.MallocTracked` / `FreeTracked`，较早版本用 `DisposeSentinel` |

## 使用跟踪：AtomicSafetyHandle 与 m_Safety

`AtomicSafetyHandle` 保存着对安全系统为这个容器维护的中心信息的引用，是容器方法与安全系统交互的主要入口。官方硬性要求：每个 `NativeContainer` 实例必须有一个名为 `m_Safety` 的 `AtomicSafetyHandle` 字段（官方的 `NativeContainerAttribute` 示例注释写的是：启用 `ENABLE_UNITY_COLLECTIONS_CHECKS` 时必须有，且名字必须是这个）。

每个句柄带一组标志，表示在当前上下文里对该容器能做哪些操作。容器被放进 Job 时，Job System 自动按这个容器在该 Job 中的用法（只读还是读写）配置句柄的标志。

读写时的检查：

- 要读：Job System 在读之前调用 `CheckReadAndThrow`，确认当前上下文有读权限。
- 要写：写之前调用 `CheckWriteAndThrow`，确认有写权限。
- 不满足条件（没有权限，或容器已经被释放）就抛 `InvalidOperationException`（官方示例注释）。

同一个容器分给两个 Job 时，两个 Job 各有各的 `AtomicSafetyHandle`：它们引用同一份中心信息，但各自的标志可以不同，表示各自对容器有什么读写权限。这和 1.6 讲的"容器拷贝语义"是同一件事。

### 静态安全 ID 与自定义报错

安全系统的报错信息里会出现容器的名字。为了让提示更清楚，可以向安全系统登记容器类型的名字：

- `AtomicSafetyHandle.NewStaticSafetyId` 返回一个安全 ID，传给 `AtomicSafetyHandle.SetStaticSafetyId` 设置到句柄上。安全 ID 创建一次即可复用于该容器的所有实例，常见做法是存在容器类的静态成员里（官方示例就是 `s_staticSafetyId` 静态字段，用 `NewStaticSafetyId<NativeAppendOnlyList<T>>()` 取得）。
- `AtomicSafetyHandle.SetCustomErrorMessage` 可以对特定的违反安全约束的情形覆盖报错文本。该方法的参数形式我没有逐个核对，待核实。

### 次级版本号与 SetBumpSecondaryVersionOnScheduleWrite

官方示例里还出现了一组和"视图"相关的调用：`SetBumpSecondaryVersionOnScheduleWrite`、`CheckWriteAndBumpSecondaryVersion`、`CheckGetSecondaryDataPointerAndThrow`、`UseSecondaryVersion`。它们的原理见 1.6 "容器拷贝语义与 AtomicSafetyHandle 版本号机制"，在下面的示例里能看到各自用在哪里。

## 泄漏跟踪：MallocTracked 与 FreeTracked

官方说明：泄漏跟踪主要由 Unity 原生代码实现。容器用 `UnsafeUtility.MallocTracked` 分配存放数据的内存，释放时用 `UnsafeUtility.FreeTracked`。官方 `NativeContainerAttribute` 页也写明：只要调用了 `MallocTracked`，泄漏跟踪就自动生效。

较早的 Unity 版本里由 `DisposeSentinel` 类做泄漏跟踪：垃圾回收器回收 `DisposeSentinel` 对象时，Unity 就报告泄漏；用它的 `Create` 方法创建时会同时初始化 `AtomicSafetyHandle`，释放容器时 `Dispose` 一并释放两者。当前版本的官方示例已不再使用它（构造函数里直接 `AtomicSafetyHandle.Create()`，`Dispose` 里 `AtomicSafetyHandle.Release`）。读旧教程时遇到 `DisposeSentinel` 要知道它属于旧写法。

想知道泄漏的容器是在哪创建的，可以抓分配时的调用栈：用 `NativeLeakDetection.Mode` 属性设置；编辑器里对应 `Preferences ▸ Jobs ▸ Leak Detection Level`（见 1.5 泄漏检测）。

## 嵌套容器：SetNestedContainer 的真实作用

官方说明：安全系统不支持 Job 里的嵌套容器，因为 Job System 无法为大容器里的每个内层 `NativeContainer` 正确配置各自的 `AtomicSafetyHandle`。`SetNestedContainer` 的用途是"防止调度使用嵌套容器的 Job"：把含有其它 `NativeContainer` 的容器标记为嵌套容器。

要点是它拦的是调度，不是创建。官方示例的构造函数里，当元素类型 `T` 本身是 NativeContainer 类型时调用 `AtomicSafetyHandle.SetNestedContainer(m_Safety, true)`；容器仍然能被创建，只是之后把它交给 Job 调度会被安全系统拒绝。判断 `T` 是否是 NativeContainer 用的是 `UnsafeUtility.IsNativeContainerType<T>()`。这条同时修正了 1.4 里旧稿"创建时被拒绝"的说法。

## 官方示例：只追加的列表 NativeAppendOnlyList&lt;T&gt;

出处：Custom NativeContainer example 页。官方说明它演示了"读写操作的基本保护，以及创建和使视图失效"。下面按官方代码保留结构，中文注释是我改写的，标出了哪些部分只在 `ENABLE_UNITY_COLLECTIONS_CHECKS` 下编译。

```csharp
using System;
using System.Runtime.InteropServices;
using Unity.Collections.LowLevel.Unsafe;
using Unity.Collections;

[NativeContainer]   // 告诉 Job System：这个结构含有 AtomicSafetyHandle
public unsafe struct NativeAppendOnlyList<T> : IDisposable where T : unmanaged
{
    // 裸指针通常不能放进传给 Job 的结构，但这里有安全系统保护，所以关掉这条限制
    [NativeDisableUnsafePtrRestriction]
    internal void* m_Buffer;
    internal int m_Length;
    internal Allocator m_AllocatorLabel;

#if ENABLE_UNITY_COLLECTIONS_CHECKS
    // 字段名必须正好是 m_Safety
    internal AtomicSafetyHandle m_Safety;

    // 用类型名向安全系统登记一个静态 ID，让报错信息带上容器名
    internal static int s_staticSafetyId;
    static void InitStaticSafetyId()
    {
        if (s_staticSafetyId == 0)
            s_staticSafetyId = AtomicSafetyHandle.NewStaticSafetyId<NativeAppendOnlyList<T>>();
    }
#endif

    public NativeAppendOnlyList(Allocator allocator, params T[] initialItems)
    {
        m_Length = initialItems.Length;
        m_AllocatorLabel = allocator;

        // 计算初始缓冲字节数并用 MallocTracked 分配（泄漏跟踪由此生效）
        int totalSize = UnsafeUtility.SizeOf<T>() * m_Length;
        m_Buffer = UnsafeUtility.MallocTracked(totalSize, UnsafeUtility.AlignOf<T>(), m_AllocatorLabel, 1);

        // 把初始数据拷进缓冲
        var handle = GCHandle.Alloc(initialItems, GCHandleType.Pinned);
        try { UnsafeUtility.MemCpy(m_Buffer, handle.AddrOfPinnedObject().ToPointer(), totalSize); }
        finally { handle.Free(); }

#if ENABLE_UNITY_COLLECTIONS_CHECKS
        m_Safety = AtomicSafetyHandle.Create();              // 创建安全句柄
        InitStaticSafetyId();
        AtomicSafetyHandle.SetStaticSafetyId(ref m_Safety, s_staticSafetyId);
        // 每当有写本容器的 Job 被调度时，自动使已有视图失效
        AtomicSafetyHandle.SetBumpSecondaryVersionOnScheduleWrite(m_Safety, true);
        // 元素类型本身是 NativeContainer 时，标记为嵌套容器（阻止调度使用它的 Job）
        if (UnsafeUtility.IsNativeContainerType<T>())
            AtomicSafetyHandle.SetNestedContainer(m_Safety, true);
#endif
    }

    public int Length
    {
        get
        {
#if ENABLE_UNITY_COLLECTIONS_CHECKS
            // 不能读（无读权限或已释放）时抛异常
            AtomicSafetyHandle.CheckReadAndThrow(m_Safety);
#endif
            return m_Length;
        }
    }

    public T this[int index]
    {
        get
        {
#if ENABLE_UNITY_COLLECTIONS_CHECKS
            AtomicSafetyHandle.CheckReadAndThrow(m_Safety);
#endif
            return UnsafeUtility.ReadArrayElement<T>(m_Buffer, index);
        }
        set
        {
#if ENABLE_UNITY_COLLECTIONS_CHECKS
            AtomicSafetyHandle.CheckWriteAndThrow(m_Safety);
#endif
            UnsafeUtility.WriteArrayElement(m_Buffer, index, value);
        }
    }

    public void Add(T value)
    {
#if ENABLE_UNITY_COLLECTIONS_CHECKS
        // 检查写权限，同时递增次级版本号：本方法会换缓冲，旧视图必须作废
        AtomicSafetyHandle.CheckWriteAndBumpSecondaryVersion(m_Safety);
#endif
        // 换成多一个元素空间的新缓冲，拷贝旧数据，释放旧缓冲
        int newTotalSize = (m_Length + 1) * UnsafeUtility.SizeOf<T>();
        void* newBuffer = UnsafeUtility.MallocTracked(newTotalSize, UnsafeUtility.AlignOf<T>(), m_AllocatorLabel, 1);
        UnsafeUtility.MemCpy(newBuffer, m_Buffer, m_Length * UnsafeUtility.SizeOf<T>());
        UnsafeUtility.FreeTracked(m_Buffer, m_AllocatorLabel);
        m_Buffer = newBuffer;

        UnsafeUtility.WriteArrayElement(m_Buffer, m_Length++, value);
    }

    public NativeArray<T> AsArray()
    {
#if ENABLE_UNITY_COLLECTIONS_CHECKS
        // 确认现在可以用缓冲指针构造视图
        AtomicSafetyHandle.CheckGetSecondaryDataPointerAndThrow(m_Safety);

        // 复制句柄，并让这份拷贝使用次级版本号
        AtomicSafetyHandle handleForArray = m_Safety;
        AtomicSafetyHandle.UseSecondaryVersion(ref handleForArray);
#endif
        // 不分配也不拷贝：构造一个指向 m_Buffer 的 NativeArray 别名（视图）
        var array = NativeArrayUnsafeUtility.ConvertExistingDataToNativeArray<T>(m_Buffer, m_Length, Allocator.None);

#if ENABLE_UNITY_COLLECTIONS_CHECKS
        NativeArrayUnsafeUtility.SetAtomicSafetyHandle(ref array, handleForArray);
#endif
        return array;
    }

    public void Dispose()
    {
#if ENABLE_UNITY_COLLECTIONS_CHECKS
        AtomicSafetyHandle.CheckDeallocateAndThrow(m_Safety);   // 能否释放（没有 Job 还占着它）
        AtomicSafetyHandle.Release(m_Safety);                   // 递增版本号，所有拷贝随之失效
#endif
        UnsafeUtility.FreeTracked(m_Buffer, m_AllocatorLabel);
        m_Buffer = null;
        m_Length = 0;
    }
}
```

### 示例解读

- 在编辑器和开发构建里（`ENABLE_UNITY_COLLECTIONS_CHECKS` 开启）才会编译的部分：`m_Safety` 字段、静态安全 ID、构造函数末尾对安全句柄的创建与配置、每个方法里的 `Check*` 调用、`AsArray` 里复制并改写句柄的部分、`Dispose` 里的 `CheckDeallocateAndThrow` 与 `Release`。官方注释明确说，最终构建里安全系统被关闭以换取性能，这些 API 在那里不可用，所以必须用该宏包起来。
- 始终编译的部分：`m_Buffer`、`m_Length`、`m_AllocatorLabel`，以及 `MallocTracked` / `FreeTracked` 的分配释放、读写元素的实际操作。
- `Add` 每次追加都重新分配一块新缓冲，是为演示"改变大小会使视图失效"而写的，不是好实现；实际容器会按容量倍增。
- `AsArray()` 返回的 `NativeArray` 别名了 `m_Buffer`，句柄用次级版本号；之后 `Add`（扩容）或调度写本容器的 Job，都会递增次级版本号，旧视图再访问就会被安全系统拒绝。
- 官方示例里有一句注释写"Create the AtomicSafetyHandle and DisposeSentinel"，但代码只调用 `AtomicSafetyHandle.Create()`，没有 `DisposeSentinel`；这是官方注释遗留，按代码为准。
- 另一个官方示例见 `NativeContainerAttribute` 的 ScriptReference 页：`NativeCustomArray<T>`，它标了 `[NativeContainerSupportsMinMaxWriteRestriction]`，用 `AllocatorManager.Allocate` / `Free` 配合自定义分配器，用 `CollectionHelper.CreateSafetyHandle(allocator)` / `CollectionHelper.SetStaticSafetyId` / `CollectionHelper.DisposeSafetyHandle` 管理句柄（Collections 2.x 的写法），并实现了 `DebuggerTypeProxy` 调试视图。上面这些 `CollectionHelper` 方法的签名我没有在 API 页里逐个核对，待核实。

## 容器与 Job 相关的特性

以下各项都读过对应的 ScriptReference 页（6000.6 版），都在 `Unity.Collections.LowLevel.Unsafe` 命名空间。

| 特性 | 作用 | 对容器的要求 |
|---|---|---|
| `[NativeContainer]` | 标记自定义 native container 类型。容器不分配 GC 内存、显式控制分配，数据必须可 blittable，可用于 Job | 必须内嵌 `AtomicSafetyHandle`（启用检查时字段名必须是 `m_Safety`）；调用 `MallocTracked` 时泄漏跟踪自动生效。官方警告：自定义容器实现不当可能直接让 Unity 崩溃而不抛异常，要为所有场景补测试，尤其是和 Job 的集成 |
| `[NativeContainerSupportsMinMaxWriteRestriction]` | 声明容器可以把可写范围限制在最小/最大下标之间。要在 `IJobParallelFor` 里写入容器，必须标它：并行 Job 用这个限制保证每个并行实例只写自己被分配的范围 | 必须有 `int m_Length`、`int m_MinIndex`、`int m_MaxIndex` 三个成员，按这个顺序且中间不能有别的成员；容器自己对范围外的写入抛异常。`m_MinIndex` / `m_MaxIndex` 由 Job 调度器在 `Execute` 之前设置。可以用 `[NativeDisableParallelForRestriction]` 对单个实例放宽，代价是不再防止并行实例覆盖同一元素 |
| `[NativeContainerIsReadOnly]` | 标记容器类型是只读的，用来定义容器数据的只读接口。去掉调度 Job 时"是读还是写"的歧义，利于高效使用容器 | 容器只能允许读。官方特别说明：标这个特性并不会阻止使用该容器的代码去尝试写，约束要容器自己执行 |
| `[NativeContainerIsAtomicWriteOnly]` | 声明容器只允许写，且只能在安全的并行上下文里写。容器可以作为可写参数传给 `IJobParallelFor` 这类并行 Job，且不限制能写哪些下标，并表示各部分互不重叠 | 容器必须强制只写访问。官方指出另一种支持并行写入的方式是 `[NativeContainerSupportsMinMaxWriteRestriction]` |
| `[NativeContainerSupportsDeferredConvertListToArray]` | 声明容器可以传给 `IJobParallelForDefer` 的 `Schedule` | 页面只有这一句，没有其它字段要求；与 1.4 的 `AsDeferredJobArray()` 相呼应 |
| `[NativeContainerSupportsDeallocateOnJobCompletion]` | 声明容器可以配合 `[DeallocateOnJobCompletion]` 在 Job 完成时自动释放（见 1.5） | 必须有名为 `m_Buffer` 的指针类型字段，以及名为 `m_AllocatorLabel` 的 `Allocator` 类型字段；Job System 用这两个字段的值自动释放容器 |
| `[NativeSetClassTypeToNullOnSchedule]` | 用在 Job 结构的字段上。Job 系统不允许 Job 结构里有托管引用，但有时必须放一个在 Job 上下文里始终为 null 的类引用；标了它，传给 Job 的结构拷贝里该引用被置为 null | 官方 `DeallocateOnJobCompletion` 相关示例里就是把旧版容器的 `DisposeSentinel m_DisposeSentinel` 字段标上它：`DisposeSentinel` 是类，Job 不能带托管引用，置 null 后 Job 才能接受这个容器 |

对应关系：`[NativeContainerSupportsMinMaxWriteRestriction]` 就是 1.6 里 `NativeArray` 在 `IJobParallelFor` 中"只能访问自己 index"这条限制的来源；`[NativeContainerIsAtomicWriteOnly]` 对应"并行写入器"这类允许任意下标写但不能读的容器（官方描述，具体哪些内置类型采用我没有逐个核对，待核实）。

## JobProducerTypeAttribute：自定义 Job 类型的机制

出处：ScriptReference `JobProducerTypeAttribute`（`Unity.Jobs.LowLevel.Unsafe`）。

官方描述很短：它标明一个 Job 接口的 `Execute` 方法可以被 Burst 编译；所有 Job 接口类型都必须标 `JobProducerType`，Burst 汇编检查器靠它来编译 `Execute`。属性 `ProducerType`：包含 Job System 调用的静态 `Execute` 方法的那个类型；构造函数用来指明"哪个类型是 JobProducerType"。

可以这样理解：`IJob`、`IJobParallelFor` 这类接口本身不含调度逻辑。接口上标 `[JobProducerType(typeof(XxxProducer<>))]`，真正在工作线程上被调用的是 producer 类型里的静态 `Execute` 方法，由它去调用你写的结构的 `Execute`。自定义新的 Job 类型就是自己定义接口和 producer。这些接口之间怎么串起来（例如 `JobsUtility.CreateJobReflectionData`、`JobsUtility.Schedule` 的具体用法与签名）我没有读对应页面，待核实；除非要做新的 Job 类型，一般用不到。

## 对应本项目

若真要给体素项目写一个容器，比较合理的候选是"按区块分段的只追加缓冲"：`[NativeContainer]` 加 `m_Safety`、`MallocTracked` 分配，写入用 `CheckWriteAndBumpSecondaryVersion`，读出视图用 `AsArray()` 式的别名。在动手之前建议先试 `NativeStream`（按下标分缓冲，见 1.7）或 `NativeList` 加 `ParallelWriter`，它们已经做好了安全接入；自定义容器要自己补全覆盖 Job 集成场景的测试。

## 常见坑

- 字段名不叫 `m_Safety`：启用检查时安全系统找不到句柄，官方明确要求名字固定。
- 安全相关代码没有用 `ENABLE_UNITY_COLLECTIONS_CHECKS` 包起来：最终构建里这些 API 不可用，会编译失败或带着不该有的开销。
- 只有读写检查，没有给会改变大小的操作用 `CheckWriteAndBumpSecondaryVersion`：扩容后旧视图仍然"有效"，读到被释放的内存。
- 忘了 `SetBumpSecondaryVersionOnScheduleWrite`：调度写 Job 后旧视图不会自动失效。
- 用 `Malloc` 而不是 `MallocTracked` 分配，或释放时配错 `FreeTracked`：泄漏跟踪不生效，漏了也没有警告。
- 把 `SetNestedContainer` 理解成"禁止创建嵌套容器"：它拦的是调度使用嵌套容器的 Job。
- 以为 `[NativeContainerIsReadOnly]` 会自动阻止写：官方说明它不阻止，约束要自己实现。
- 标了 `[NativeContainerSupportsMinMaxWriteRestriction]` 却没有 `m_Length` / `m_MinIndex` / `m_MaxIndex` 按序相邻，或没有在范围外抛异常：并行写保护形同虚设。
- 已释放容器被访问时抛哪种异常：官方自定义容器示例的注释写的是 `InvalidOperationException`（读/写不被允许或容器已释放），而 Rewindable allocator 页的测试里已释放的 `NativeArray` 抛 `ObjectDisposedException`。两处措辞不一致，以你所用版本在编辑器里实测为准（待核实）。
- 自己写的容器没有测试就上线：官方明确警告写错可能让 Unity 崩溃而不是抛异常。

## 小结

- 自定义容器 = `[NativeContainer]` + `m_Safety` + 读写检查 + `MallocTracked`/`FreeTracked`；安全相关代码只在 `ENABLE_UNITY_COLLECTIONS_CHECKS` 下存在。
- `NewStaticSafetyId` / `SetCustomErrorMessage` 让报错更清楚；`SetNestedContainer` 阻止调度含嵌套容器的 Job。
- 视图靠次级版本号管理有效性；会改变大小的操作用 `CheckWriteAndBumpSecondaryVersion`。
- `NativeContainerSupportsMinMaxWriteRestriction`、`IsReadOnly`、`IsAtomicWriteOnly`、`SupportsDeferredConvertListToArray`、`SupportsDeallocateOnJobCompletion`、`NativeSetClassTypeToNullOnSchedule` 各自声明一种能力或要求，并非互相替代。
- `JobProducerTypeAttribute` 是自定义 Job 类型的机制，一般项目用不到。

## 自测题

1. 自定义 NativeContainer 里 `AtomicSafetyHandle` 字段的名字有什么要求？
   答：必须叫 `m_Safety`。
2. 泄漏跟踪靠什么实现？旧版本呢？
   答：用 `UnsafeUtility.MallocTracked` / `FreeTracked` 分配释放，泄漏跟踪自动生效；较早版本用 `DisposeSentinel`。
3. `SetNestedContainer` 到底阻止了什么？
   答：阻止调度使用嵌套容器的 Job，不阻止创建容器。
4. 为什么会改变容器大小的方法要用 `CheckWriteAndBumpSecondaryVersion` 而不是 `CheckWriteAndThrow`？
   答：要让以前通过 `AsArray()` 等取得的视图因次级版本号变化而失效，避免视图继续指向被搬走或释放的内存。
5. 要让自定义容器能在 `IJobParallelFor` 中被写入，有哪两种官方途径？
   答：标 `[NativeContainerSupportsMinMaxWriteRestriction]`（并提供 `m_Length`、`m_MinIndex`、`m_MaxIndex`，由容器检查下标范围）；或标 `[NativeContainerIsAtomicWriteOnly]`（容器只写，且各部分互不重叠）。

## 参考

- https://docs.unity3d.com/Manual/job-system-custom-nativecontainer.html
- https://docs.unity3d.com/Manual/job-system-custom-nativecontainer-example.html
- https://docs.unity3d.com/Manual/job-system-copy-nativecontainer.html
- https://docs.unity3d.com/ScriptReference/Unity.Collections.LowLevel.Unsafe.NativeContainerAttribute.html
- https://docs.unity3d.com/ScriptReference/Unity.Collections.LowLevel.Unsafe.NativeContainerSupportsMinMaxWriteRestrictionAttribute.html
- https://docs.unity3d.com/ScriptReference/Unity.Collections.LowLevel.Unsafe.NativeContainerIsReadOnlyAttribute.html
- https://docs.unity3d.com/ScriptReference/Unity.Collections.LowLevel.Unsafe.NativeContainerIsAtomicWriteOnlyAttribute.html
- https://docs.unity3d.com/ScriptReference/Unity.Collections.LowLevel.Unsafe.NativeContainerSupportsDeferredConvertListToArray.html
- https://docs.unity3d.com/ScriptReference/Unity.Collections.LowLevel.Unsafe.NativeContainerSupportsDeallocateOnJobCompletionAttribute.html
- https://docs.unity3d.com/ScriptReference/Unity.Collections.LowLevel.Unsafe.NativeSetClassTypeToNullOnScheduleAttribute.html
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.LowLevel.Unsafe.JobProducerTypeAttribute.html
- https://docs.unity3d.com/Packages/com.unity.collections@2.5/manual/allocator-rewindable.html （已释放容器的异常类型对照）






