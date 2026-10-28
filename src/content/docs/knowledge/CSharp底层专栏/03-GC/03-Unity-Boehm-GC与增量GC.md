---
title: "3.3 Unity Boehm GC 与增量 GC"
description: 讲清 Unity Mono 与 IL2CPP 共用的 Boehm 保守式 GC：非分代、非压缩带来的碎片与堆只增不减，增量模式如何切片与写屏障，GCMode 与 time slice 的用法，以及 CoreCLR 迁移的现状与不确定处。
sidebar:
  order: 3
---

> 适用版本：行为描述依据 Unity 6（6000.0）手册的 Managed memory 与 Garbage collection modes 页面（站点构建日期 2026-10-27）。CoreCLR 迁移一节依据 Unity 官方论坛《Path to CoreCLR, 2026: Upgrade Guide》，发布日期等细节请以 Unity 官方路线图与发行说明为准。

## 要点

- Unity 的 Mono 与 IL2CPP 两条脚本后端都使用 Boehm-Demers-Weiser GC；它是保守式、非分代、非压缩的追踪收集器。官方手册原话：默认使用增量模式，且收集器是 non-compacting。
- 没有分代，就没有"短命对象在 gen0 里很便宜"这回事：每次完整标记都要遍历整个托管堆的存活图，成本随存活堆大小增长，与垃圾量关系不大。
- 没有压缩，碎片无法消除；托管堆只增不缩，手册明确写了"虚拟内存只增不减，把空闲页还给操作系统的时机不保证、不可靠"。
- 增量 GC 把标记工作拆到多帧，不让总工作量变小；代价是为托管代码中的引用写入生成写屏障。引用变化太快时标记永远追不上，会退化为一次完整的非增量收集。
- `GarbageCollector.GCMode`（Enabled / Disabled / Manual）与 `CollectIncremental(ns)`、`incrementalTimeSliceNanoseconds` 是把 GC 时机交给游戏循环的接口。
- 网页平台不支持增量 GC。

## Boehm GC 是什么样的收集器

Boehm 是一个可以链接进 C/C++ 程序的通用保守式收集器，Mono 把它作为默认 GC 之一，Unity 的 IL2CPP 运行时同样基于它。它的几个性质决定了 Unity 里的一切 GC 行为：

| 维度 | Unity (Boehm) | .NET CoreCLR |
|---|---|---|
| 根扫描 | 栈与寄存器保守扫描：把疑似指针的字当作指针 | 精确：JIT 的 GC info 指明哪些槽是引用 |
| 对象移动 | 不移动，不压缩 | 压缩 + 重定位 |
| 分代 | 无（全堆同一代） | gen0 / gen1 / gen2 / LOH / POH |
| 分配 | 按大小类的空闲链表（块内按固定大小格子切分） | 线程私有 bump pointer |
| 碎片 | 外部碎片靠合并相邻空闲块缓解，无法消除 | 压缩消除 |
| 内存归还 | 只有整页完全空闲才可能还给 OS，时机不保证 | regions 下可按块 decommit |
| 并发 | 增量切片（Unity 实现），无并发线程回收 | Background GC（gen2 并发） |
| 局部回收 | 做不到：无分代，增量也要最终完成全堆标记 | gen0/gen1 局部回收 |

### 保守扫描的两个后果

1. 误保留（false retention）。栈上残留的整数、寄存器里的旧值，如果恰好等于某个堆对象的地址，该对象及其子图都会被视为存活。这是概率事件，对象图越大、地址空间越"密"，概率越高。实际表现是"明明置了 null，对象还是不释放"。Memory Profiler 里很难追到这样的根（因为它不是任何真实引用）。可以做的有限：减少把大对象图挂在长生命周期方法的栈帧上、避免在分配大图后长时间不返回的深调用栈。具体到 Unity 的 Mono 对堆内对象是否也保守（还是用类型描述符做精确扫描）、IL2CPP 里栈槽的处理，细节无法从公开文档核实，待核实。
2. 不能移动对象。托管对象的地址在整个生命周期内不变，所以 `fixed` 与 `GCHandle` 固定在当前 Unity 里没有压缩要躲避的对象；写出依赖"对象不会移动"的代码，将来换到会移动对象的运行时（CoreCLR）时才会暴露问题，不要依赖这个行为。

### 非分代的代价

没有分代意味着：

- 每次 GC 都是对整个托管堆做标记。堆里放着 200 MB 的配置、缓存与 UI 对象图，那么哪怕你这一帧只产生了 1 KB 垃圾，一次 GC 也要遍历 200 MB 的存活图。优化目标因此是"降低 GC 的频率"和"减小托管堆的存活规模"，而不是"让对象死得快"。
- 触发 GC 的条件取决于堆增长与已分配量，而不是 gen0 预算。分配率高会更频繁触发，每次触发的代价和存活堆大小成正比。因此：**GC 暂停的长度由存活堆决定，GC 的频率由分配速率决定**。这两个旋钮是独立的，分别优化。
- 大规模常驻的托管数据（巨型 `List<Class>`、`Dictionary`）是性能隐患。把它们改成 struct 数组或 `NativeArray`/`NativeList`（不在 GC 管辖范围内，且标记时无需遍历）是常见做法，也是 DOTS/ECS 数据布局与 GC 问题天然契合的原因。

## 堆只增不减与碎片

Unity 手册对托管堆结构的描述：堆由 segment（heap block）构成，页大小一般 4 KB（移动端常见 16 KB）。分配时在空闲块中找符合大小类的位置，找不到则：

1. 若本周期未跑过 GC，则先跑一次 GC，试图腾出空间。
2. 仍不足则扩堆。手册写明：在大多数平台上，每次扩堆量是上一次的两倍；若请求的分配比这更大，则做一次额外的"周期外"扩堆，下一次常规扩堆仍以上次常规值为基础。
3. 扩张后的内存不会立即归还。手册说在多数平台上，Unity "最终"会把堆中完全空闲的页还给 OS，但时间点不保证，不可靠，并且要求这些空闲区域由一个或多个完整内存页组成。

这样会产生几个现象：

- Profiler 里 "GC Reserved Memory" 只升不降，是正常的；"GC Used Memory" 才是实际使用量。
- 一次偶发的大分配（加载时的临时大数组、一次性反序列化）会把堆撑大，之后即使释放，保留量仍在，物理内存压力是否随之上升取决于脏页是否被回收。手册也提醒：虚拟内存增长不一定带来物理内存增长；但被 GC 标为可复用的脏页，OS 仍认为是脏页，OOM 压力仍在。
- 外部碎片：空闲空间有 200 MB，但最大连续块只有 4 MB，分配 8 MB 数组仍会失败后扩堆。这就是 3.2 中提到的"大数组问题在 Unity 里的表现"。

对策：

- 启动或关卡加载时一次性预分配大缓冲，之后复用，不要用"用完即扔"的大数组。
- 把大的、长期存活的数据放到 Native 容器或 `NativeArray` 外，从托管堆拿走。
- 关卡切换时在黑屏阶段调用 `GC.Collect()`（以及 `Resources.UnloadUnusedAssets`），把一次完整回收的暂停放到玩家看不见的地方。

## 增量 GC

### 工作方式（依据官方手册）

默认开启（Player Settings > Other Settings > Configuration > Use Incremental GC）。增量模式把标记阶段拆分为多个小切片，在多帧里分批运行：

- 如果应用使用了 VSync 或设置了 `Application.targetFrameRate`，Unity 会根据帧内剩余时间调整分给 GC 的时间，把 GC 放进本来就在等待的空闲时间里。
- 如果没有 VSync 或目标帧率，可以用 `Scripting.GarbageCollector` 类自己计算本帧剩余时间并交给 GC。
- 它不会让 GC 的总工作量变少，只是把一个大尖峰摊平成多个小切片（手册称为"GC spike"的消除）。

### 为什么需要写屏障

标记被拆成多片，在片与片之间，游戏代码继续运行并修改引用。如果一个已经被标记过（黑）的对象，被写入了指向一个还没被标记的（白）对象的引用，而这个白对象又没有其他路径可达，它就会被错误地回收。解决方法就是写屏障：在每次引用写入时通知 GC "这个对象需要重新扫描"。官方手册原话：Unity 在增量模式下会生成额外的代码（写屏障），在引用变化时通知 GC 需要扫描该对象；这会给修改引用带来一些开销，对托管代码有性能影响。

因此：

- 引用写入频繁的代码（遍历并替换对象数组、频繁给字段赋新对象）在增量模式下更慢。手册对 CPU 受限项目的参考数字是每帧最多约 1 ms 的差距，建议对关键段分别在开启和关闭增量 GC 的情况下录制 Profiler，用 Profile Analyzer 比较。
- 写 `int`、`float`、struct 内的值类型字段不需要写屏障。

### 它的失败模式：退化为完整 GC

手册明确说明：如果引用变化太多，增量 GC 会"被压垮"，标记阶段因为总有新活要做而永远结束不了；此时收集器会退回到完整的、非增量的收集。表现为：增量切片看起来一直在跑（每帧都有 GC.Collect 切片），但某一帧突然出现一个很长的 GC 尖峰。

触发条件：分配率过高，或每帧大量改写引用。对策仍是减分配、减引用改写，而不是调大 time slice。

### 非增量的 stop-the-world

关闭增量 GC 后，GC 在一次长暂停里处理整个托管堆。手册说这个延迟可能达数百毫秒，取决于要处理的分配量与平台。

### 其他事实

- `System.GC.Collect()` 无论是否开启增量，都是完整的阻塞式回收。
- 网页平台不支持增量 GC。
- 增量 GC 只影响托管堆，不影响 Native 内存。

## GCMode 与手动控制

`UnityEngine.Scripting.GarbageCollector`（命名空间 `UnityEngine.Scripting`）：

| API | 作用 |
|---|---|
| `GarbageCollector.GCMode = Mode.Enabled` | 默认，自动触发 |
| `Mode.Disabled` | 完全禁用，`GC.Collect()` 也无效，堆会持续增长，直到被 OS 杀掉 |
| `Mode.Manual` | 禁止自动触发，但 `GC.Collect()` 仍然可以执行完整回收 |
| `GarbageCollector.CollectIncremental(ulong nanoseconds)` | 在给定纳秒内做增量回收，返回值表示是否还有剩余工作（待核实具体语义，以 ScriptReference 为准） |
| `GarbageCollector.incrementalTimeSliceNanoseconds` | 增量模式下每次切片的时间上限（默认值与平台相关，待核实） |
| `GarbageCollector.isIncremental` | 当前是否运行在增量模式 |
| `GarbageCollector.GCModeChanged` | 模式变更事件 |

官方建议：只在短且性能敏感、并且你能估算并控制分配量的阶段禁用 GC，之后重新开启；或者在关卡加载前一次性分配好，整关 Disabled，通关后再启用并 `GC.Collect()`。

```csharp
using UnityEngine;
using UnityEngine.Scripting;

public sealed class GcFrameBudget : MonoBehaviour
{
    [SerializeField, Min(0f)] float budgetMs = 1.5f;

    void OnEnable()
    {
        // 自己掌握 GC 时机：禁止自动触发，每帧给一个固定预算做增量回收。
        GarbageCollector.GCMode = GarbageCollector.Mode.Manual;
    }

    void OnDisable()
    {
        GarbageCollector.GCMode = GarbageCollector.Mode.Enabled;
    }

    void LateUpdate()
    {
        if (!GarbageCollector.isIncremental) return;
        // 注意：Manual 模式下必须保证堆不会被撑爆，需要在 Profiler 里观察 GC Used / Reserved。
        GarbageCollector.CollectIncremental((ulong)(budgetMs * 1_000_000.0));
    }
}
```

这段代码的风险是：预算太小，回收速度追不上分配速度，堆会持续膨胀。只在你确认分配率很低、并且知道每帧垃圾量级时才这样做。

## Mono 与 IL2CPP 的 GC 差异

两者都是 Boehm，GC 行为一致；区别在于代码生成：

- IL2CPP 把 IL 转成 C++，由 C++ 编译器生成本机代码；栈布局、寄存器分配由 C++ 编译器决定，保守扫描的"栈上残留值"表现与 Mono 的 JIT 不同。
- 写屏障的插入方式也由各自的代码生成路径负责。
- 泛型共享、值类型泛型实例化的内存与代码体积差异，见 Mono 与 IL2CPP 章节。

## 迁移到 CoreCLR

依据 Unity 官方论坛《Path to CoreCLR, 2026: Upgrade Guide》（2026-03-26）：Unity 计划在 Unity 6.8 中以 CoreCLR 取代 Mono，6.8 不再提供 Mono 选项；6.7 LTS alpha 起提供实验性 CoreCLR 桌面 Player。官方同帖回复还明确了两点：CoreCLR 的 GC 对大对象使用 85 KB 阈值；IL2CPP 使用的 Boehm GC 行为没有变化。

所以 Unity 6.8 之后会同时存在两套 GC：CoreCLR 后端是 .NET 的分代压缩 GC（对应 3.1、3.2 的内容），IL2CPP 后端仍是本篇讲的 Boehm。优化决策要按目标后端区分：

1. CoreCLR 后端：短命小对象便宜（gen0），但大对象、固定对象、跨代引用写屏障仍要关注。
2. IL2CPP 后端：本篇所有结论照旧，尤其是堆只增不减、全堆标记与无压缩。

仍待官方确认的部分（待核实）：具体发布日期、各平台覆盖范围、CoreCLR 下是否有增量 GC 的等价物、`GarbageCollector` API 的行为是否变化。在你确认目标版本和后端之前，不要把 gen0 便宜之类的假设写进优化方案。

## 常见坑

- 以为 Unity 也有 gen0：在 Unity 里"短命对象很便宜"的前提不成立，每次 GC 都要遍历全堆存活图。
- 只看 "GC Reserved" 以为泄漏。预留量只增是预期行为，要看 Used 与 GC.Collect 后是否回落。
- 开启 Manual / Disabled 却没有预算监控，导致堆无限增长被系统杀进程。
- 在增量模式下仍然每帧大量改写引用，既付写屏障税，又可能让增量 GC 退化为完整收集。
- 用 `GC.Collect()` 在运行中"打扫"：它是完整阻塞回收，Unity 手册也提醒在大项目里可能需要数秒。
- Editor 里还有域重载、编辑器自身的托管分配，测出的 GC 尖峰不能代表真机；用开发版 Player 连 Profiler，在目标设备上测。

## 面试追问

1. Unity 的 GC 和 .NET 的 GC 有什么本质区别？ 要点：Boehm 保守、非分代、非压缩，增量切片；CoreCLR 精确、分代、压缩、Background GC。由此推出：Unity 里 GC 暂停与存活堆成正比，分配率决定频率，碎片无法消除。
2. 为什么 Unity 的托管堆只涨不跌？ 要点：不移动对象，因此只有整页完全空闲才可能归还；归还时机不保证；扩堆按倍数增长；偶发大分配会永久抬高保留量。
3. 增量 GC 怎么工作，为什么需要写屏障？ 要点：把标记拆成多片；片间引用修改可能让已标记对象指向未标记对象，需要屏障通知 GC 重新扫描；代价是每次引用写入的开销；引用改写太多时标记追不上，退化为完整收集。
4. 保守式扫描会带来什么问题？ 要点：栈上无法区分整数与指针，可能误保留对象；不能移动对象；表现为"置 null 后仍不释放"。
5. 如何在 Unity 里避免 GC 尖峰进入关键帧？ 要点：减少分配；关键段用 `GCMode.Disabled/Manual` 并预估分配量；加载点主动 `GC.Collect`；使用增量 GC 并配合 VSync/目标帧率或手动 `CollectIncremental`；大数据放 Native 内存。
6. 迁移到 CoreCLR 后，哪些优化经验会失效？ 要点：对象池对短命对象的收益变小（gen0 很便宜），但大对象、固定对象、写屏障仍需关注；这是待核实的未来状态，不能当成当前事实。

## 参考资料

- Unity Manual：Garbage collection modes，https://docs.unity3d.com/6000.0/Documentation/Manual/performance-incremental-garbage-collection.html
- Unity Manual：Configuring garbage collection，https://docs.unity3d.com/6000.0/Documentation/Manual/performance-disabling-garbage-collection.html
- Unity Manual：Managed memory introduction，https://docs.unity3d.com/6000.0/Documentation/Manual/performance-managed-memory-introduction.html
- Boehm-Demers-Weiser Garbage Collector，https://www.hboehm.info/gc/
