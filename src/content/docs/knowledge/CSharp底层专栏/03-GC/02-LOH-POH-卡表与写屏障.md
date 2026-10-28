---
title: "3.2 LOH、POH、卡表与写屏障"
description: 解释 85000 字节阈值与 LOH 碎片、POH 的设计动机、写屏障与卡表如何让分代回收成立，以及 GC 暂停时线程如何到达安全点、终结队列如何拖累回收。
sidebar:
  order: 2
---

> 适用版本：.NET 5 起有 POH，.NET 7 起 64 位默认 regions；卡表与写屏障的结构在各版本间保持稳定，但具体实现细节（card 大小、card bundle 层次、write barrier 变体）随平台与版本变化，文中数字标"典型值"。Unity 的 Boehm GC 没有 LOH/POH/卡表，对应机制见 3.3。

## 要点

- 对象大小 `>= 85,000` 字节（不是 KB）进入 LOH；LOH 只随 gen2 回收，默认不压缩，因此靠空闲链表分配，会产生外部碎片。
- LOH 阈值可调（`GCLOHThreshold`），LOH 压缩可以按需一次性开启（`GCSettings.LargeObjectHeapCompactionMode`），但这是应急手段，不是优化策略。
- POH（Pinned Object Heap，.NET 5）专门放"一创建就要长期固定"的数组，避免固定对象把 gen0/gen1/gen2 切碎。
- 分代回收靠写屏障 + 卡表成立：每次把引用写进堆对象字段，JIT 插入的 helper 判断"目标是否在年轻代范围"，是则把对应卡标脏；局部回收时只扫描脏卡对应的老对象。
- 写屏障是每一次引用字段写入都要付的运行时税；值类型字段与局部变量写入没有这个税。
- 暂停的下限由"让所有线程停在安全点"决定，紧循环里没有轮询点的代码会拖长暂停。
- 带终结器的对象需要至少两次 GC 才能回收，并把对象图拖进更老的代。

## LOH：为什么要有，为什么麻烦

回收 gen0 要付出"拷贝存活对象"的成本，对小对象这是合理的；对一个 1 MB 的数组，拷贝成本很高，而且对象越大越不容易死得快。.NET 的折中是：`>= 85,000` 字节的对象直接分配到 LOH，不参与 gen0/gen1 的拷贝，只在 gen2 GC 时回收，并且默认原地清扫、不压缩。

这个阈值是 BOTR 文档给出的 "small objects (< 85,000 bytes)" 与 "large objects (>= 85,000 bytes)"。注意它指的是对象本身的字节数，数组对象含对象头与长度字段。一个 `double[10600]` 是 `10600 * 8 = 84,800` 字节数据加头部约 24 字节，刚好越线进 LOH；`float[]`、`int[]` 大约在 21,250 个元素附近越线。很多"我才分配了 80 KB 怎么就进 LOH 了"的疑惑来自这里。

### 后果

1. 不压缩 + 空闲链表：释放后留下大小不一的洞，新的大对象只能放进足够大的洞，否则申请新内存。表现为 LOH 总量远大于存活量。
2. 只随 gen2 回收：反复分配临时大数组（读文件的 buffer、`List<T>` 扩容、`MemoryStream`、`string.Concat` 大字符串）会让 gen2 GC 变频繁，而 gen2 GC 是最贵的。
3. 分配本身也慢：大对象分配需要持有堆锁，并且必须清零整块内存。

### 应对

| 做法 | 说明 |
|---|---|
| 池化大数组 | `ArrayPool<T>.Shared`，借用归还；注意归还时的内容残留，见 3.5 |
| 预分配并复用 | `List<T>` 设置 `Capacity`，避免倍增时反复生成 LOH 数组 |
| 切块 | 把 100 MB 的大数组换成块链表（每块小于阈值），代价是索引复杂度 |
| 上调阈值 | `System.GC.LOHThreshold`（runtimeconfig）或环境变量 `DOTNET_GCLOHThreshold`（十六进制值），让更大的对象留在 gen0，适合短命中型缓冲；会增加 gen0 拷贝成本 |
| 一次性压缩 | `GCSettings.LargeObjectHeapCompactionMode = GCLargeObjectHeapCompactionMode.CompactOnce; GC.Collect();` 下一次阻塞式 gen2 GC 会压缩 LOH，之后自动恢复默认 |

```csharp
using System;
using System.Runtime;

static class LohTools
{
    public static void CompactLohOnce()
    {
        GCSettings.LargeObjectHeapCompactionMode = GCLargeObjectHeapCompactionMode.CompactOnce;
        GC.Collect(2, GCCollectionMode.Forced, blocking: true, compacting: true);
    }
}
```

注意：`GC.GetGeneration` 对 LOH 对象返回 2（最大代），没有"LOH"这个返回值。要确定某对象在 LOH，可以用 `GC.GetGCMemoryInfo().GenerationInfo[3]`（LOH）的大小变化来推断，或直接看 dotnet-gcdump / PerfView 的堆视图。

### Unity 里的 LOH

Unity 当前脚本运行时的 Boehm GC 没有 LOH 的概念，也不压缩，所有对象一视同仁地在同一个堆里按大小类分配。大数组的问题体现为：分配时找不到足够大的连续空闲块，只能触发 GC，再不行就扩堆（见 3.3）。池化大数组的建议同样适用，原因不同。

## POH：给固定对象一个窝

固定（pin）一个对象意味着 GC 在压缩时必须绕开它。固定对象散布在 gen0 中，会让 plan 阶段把可压缩的区间切碎，gen0 无法整齐压缩，甚至出现 "gen0 被钉住导致无法回收空间，堆越来越大" 的情形。典型来源是异步 I/O：socket 的接收 buffer 要在整个读操作期间固定。

.NET 5 引入 POH：

```csharp
byte[] buf = GC.AllocateArray<byte>(64 * 1024, pinned: true);
byte[] noZero = GC.AllocateUninitializedArray<byte>(64 * 1024, pinned: true);

// 可以直接取地址，且永远不会被移动
unsafe
{
    byte* p = (byte*)System.Runtime.CompilerServices.Unsafe.AsPointer(ref buf[0]);
}
```

- POH 对象按定义不会被移动，所以不用 `fixed` 也不必申请 `GCHandle`，可以长期把指针交给原生代码。
- `GC.AllocateArray<T>(pinned: true)` 要求 `T` 不是引用类型、也不含对象引用字段，否则抛 `ArgumentException`；这样 POH 对象不会成为指向年轻代的跨代引用来源。
- POH 与 LOH 一样随 gen2 回收，所以不要频繁创建，应创建一次长期复用。

C++ 对照：这相当于直接 `malloc` 一块不会被搬动的内存给 native 用。在 C++ 里所有对象都"自带固定"，C# 把固定当作例外，并为它设了一个专门区域。

## 写屏障与卡表

### 为什么需要

回收 gen0 时，只想遍历 gen0 的存活对象。但 gen2 里一个老对象可能刚刚写入了对 gen0 新对象的引用，如果只看栈和静态根，会把这个新对象误判为死亡。解决方法：记录"哪些老对象可能指向年轻对象"，作为额外的根。这个记录就是卡表，写入时的记录动作就是写屏障。

### 结构

- 卡（card）：堆被切成固定大小的小块，典型值在 64 位上是 256 字节（待核实不同版本），每块在卡表中对应一个标记位或字节来表示"此块内有对象字段可能指向年轻代"。
- card bundle：卡表之上再加一层摘要，表示"这一组卡里有没有被置位的"，让 GC 快速跳过大片干净区域。
- 写屏障 helper：JIT 在每次"向堆中的引用字段赋值"处调用，伪代码如下：

```text
JIT_WriteBarrier(dst_field_address, src_object):
    *dst_field_address = src_object          // 先完成写入
    if src_object in [ephemeral_low, ephemeral_high):   // 目标是否属于年轻代范围
        card = dst_field_address >> card_shift
        if card_table[card] != 0xFF:
            card_table[card] = 0xFF           // 标脏，并可能更新 card bundle
```

关键点：

1. 判断依据是被写入的引用指向年轻代范围，而不是"写入者是老对象"。所以对年轻对象字段的写入也会付这笔判断成本，只是通常不置位后续动作。
2. 每次引用字段写入都有一次函数调用开销（实际是汇编 stub，按处理器与 GC 配置选择不同变体，如 regions 下需要多一层 region 代号查找）。这就是为什么高频写引用字段的热路径，用 struct 数组或索引代替对象引用，会明显更快。
3. 只在写 **堆里** 的引用时才有屏障；写局部变量、写栈上 `ref struct` 字段、写 `int` 不需要。
4. 局部回收时，GC 扫描脏卡对应的老对象，把其中指向年轻代的字段加入根；回收结束后，如果这些引用已经不再指向年轻代（比如目标晋升了），卡会被清除。

### 带来的现象

- 一个老的大数组 `Foo[] arr`（在 LOH 或 gen2）里频繁替换元素为新分配的对象，每次替换都会标脏对应的卡，下一次 gen0 GC 就要扫描这些卡。如果数组很大、脏卡很多，gen0 GC 的暂停会被明显拉长，即使存活对象很少。这是"静态大缓存里放引用类型 + 每帧更新"的隐性成本。
- 解决：把可变的热数据放进值类型数组（`struct Particle[]`），数组里没有引用就没有跨代引用，卡表不参与。
- 同理，`List<T>` 里存 struct，比存 class 在 GC 上友好得多。

### Unity 增量 GC 的写屏障

Unity 开启增量 GC 时，会在托管代码中为引用写入生成额外的写屏障，目的是在 GC 切片之间追踪引用变化（见 3.3）。它的目的和 CoreCLR 的卡表不同：CoreCLR 为了分代，Unity 为了增量标记不漏。因此关闭增量 GC 在某些项目里能省下可观的脚本开销（Unity 手册称 CPU 受限项目差异最高约每帧 1 ms，来源：Configuring garbage collection 页面）。

## 暂停：线程如何停下来

触发 GC 的线程调用 SuspendEE，需要所有执行托管代码的线程停在 **安全点**（safe point），GC 才能确定根集，因为 JIT 的 GC info 只在特定的指令位置有效。CoreCLR 的做法：

1. 对仍在执行托管代码的线程，使用返回地址劫持（hijack）或设置陷入标志，等线程执行到下一个调用返回或轮询点时停下。
2. 对完全可中断（fully interruptible）的代码，可以在大多数指令处挂起线程。
3. 处于 P/Invoke 即"抢占式模式"的线程，GC 认为它不在托管代码中，不需要等待；返回托管代码时线程会检查 GC 是否在进行，并阻塞等待。

实际影响：

- 长时间不返回的紧循环（没有调用、没有分配、被优化为非完全可中断）会让其他线程触发的 GC 卡在 SuspendEE 上，表现为暂停时间远长于标记时间。现代 JIT 对循环会插入轮询或让其完全可中断，但仍应在 Profiler 里区分 "suspension time" 与 "GC time"（PerfView 的 GCStats 有此拆分）。
- 在 P/Invoke 里阻塞很久是安全的（不拖 GC），但回到托管代码时要等 GC 结束。

Boehm 的暂停机制不同：它向所有线程发送信号（或用平台挂起接口）并保守扫描栈，没有精确的安全点概念，因此对线程状态更宽容，但不能移动对象。

## 终结器对 GC 的影响

带终结器（`~Foo()`）的对象在分配时会被登记到终结队列。回收流程：

1. 第一次 GC：对象不可达，但在终结队列里，GC 把它移入 f-reachable 队列，并重新把它及其引用的整个子图标记为存活（复活）。
2. 终结线程异步执行终结器。
3. 第二次 GC：这个对象才真正被回收（`GC.ReRegisterForFinalize` 可再次登记）。

后果：对象至少多活一轮 GC，并且常因此被晋升到 gen1 甚至 gen2；整个子图一起被拖老。因此带终结器的对象应该是"小壳 + 句柄"，而不是持有大图。优先使用 `SafeHandle`，调用 `Dispose()` 后用 `GC.SuppressFinalize(this)` 摘掉登记（详见托管与非托管章节的 Dispose 一篇）。

## 常见坑

- 认为 85,000 是"KB"或"元素数"。它是字节，且含对象头。
- 在 Unity 里照搬 .NET 的"gen0 很便宜"的结论：Boehm 非分代，所有堆对象都在同一代，所谓"短命对象便宜"不成立。
- 在老的大缓存（`Dictionary<int, Foo>`、`Foo[]`）里每帧覆写引用，造成卡表大量置位。
- 使用 `fixed` 固定短命缓冲却在异步操作期间长期固定，造成 gen0 碎片；应改用 POH 数组或 `NativeMemory`。
- 以为 `GC.Collect()` 会压缩 LOH。默认不会，需要显式设置 `LargeObjectHeapCompactionMode`。

## 面试追问

1. 为什么大对象要单独放 LOH，而不是让它也走 gen0 → gen1 → gen2？ 要点：拷贝大对象成本高；它们通常存活较长；因此直接放在 gen2 级别随 full GC 回收，代价是默认不压缩带来的碎片。
2. 写屏障做了什么，代价在哪？ 要点：每次引用字段写入后判断目标是否属于年轻代，是则把目标地址所在卡置脏；代价是每次堆内引用写入多一次 helper 调用与分支，以及脏卡在下次局部 GC 中被扫描。
3. 为什么把 `Foo[]` 换成 `Foo` 的 struct 数组能降低 GC 压力？ 要点：struct 数组内没有引用，不产生跨代引用与脏卡，也不需要逐元素跟踪；同时内存连续、缓存友好；前提是 struct 内不含引用字段。
4. POH 解决什么问题，使用有什么限制？ 要点：把长期固定的对象放到不可移动的区域，避免固定对象切碎 gen0 的压缩；元素必须是不含引用的类型；与 LOH 同样随 gen2 回收，应创建一次长期复用。
5. 终结器为什么昂贵？ 要点：对象需要两次 GC；第一次 GC 对象及其子图被复活并晋升；终结线程异步执行带来不确定性；推荐 Dispose 模式 + `SuppressFinalize` + `SafeHandle`。
6. Unity 开启增量 GC 后，为什么脚本会变慢一点？ 要点：为引用写入生成额外写屏障以跟踪标记切片之间的引用变化；这个开销只和引用写入频率相关，Unity 手册给出的上限量级约每帧 1 ms。

## 参考资料

- BOTR：Garbage Collection Design，https://github.com/dotnet/runtime/blob/main/docs/design/coreclr/botr/garbage-collection.md
- Microsoft Learn：The large object heap on Windows systems，https://learn.microsoft.com/en-us/dotnet/standard/garbage-collection/large-object-heap
- Microsoft Learn：Runtime configuration options for garbage collection，https://learn.microsoft.com/en-us/dotnet/core/runtime-config/garbage-collector
- Unity Manual：Configuring garbage collection，https://docs.unity3d.com/6000.0/Documentation/Manual/performance-disabling-garbage-collection.html
