---
title: "2.3 unsafe、指针、fixed 与 GCHandle"
description: 托管堆对象如何被固定、固定对 GC 压缩的影响、GCHandle 四种类型、POH,以及 Unity 的 UnsafeUtility、NativeArray 与 GC 的关系。
sidebar:
  order: 3
---

> 适用版本:CoreCLR 部分以 .NET 5~9 为准(POH 自 .NET 5 起);Unity 部分以 6000.x(Boehm GC、C# 9.0)为准,需在 Player 设置里开启 Allow 'unsafe' Code,Collections 包 API 以所装版本为准。

## 要点

- C# 指针 `T*` 只能指向 unmanaged 类型(不含引用字段的值类型)。指向托管堆对象内部的指针必须先固定(pin),否则压缩型 GC 一搬家,指针就悬空。
- `fixed` 语句是栈上的"固定局部变量",零分配、作用域结束即释放;`GCHandle.Alloc(obj, GCHandleType.Pinned)` 是堆外句柄表条目,可以跨方法、跨回调持有,必须手动 `Free`。
- 固定的代价不在 pin 本身,而在它破坏压缩:被固定对象周围留下空洞,Gen0/Gen1 碎片化,严重时 GC 为了绕开固定对象而降低回收效率或提升代龄。CoreCLR 为长期固定的缓冲区提供了 POH(Pinned Object Heap)。
- `GCHandleType` 有四种:`Weak`、`WeakTrackResurrection`、`Normal`、`Pinned`。`Normal` 是强根,`Pinned` 是强根加固定。
- Unity 的 Boehm GC 不移动对象,pin 在当前实现里几乎没有运行时成本;但可移植代码仍必须按规范固定,迁移到会移动对象的运行时时才不会出错。
- `NativeArray<T>` 的缓冲区由 Unity 的分配器管理,不在 GC 堆上,GC 既不扫描也不移动它;它自身是一个只含指针、长度和分配器标签的 struct。

## 为什么需要固定

CoreCLR 的 GC 是精确、分代、压缩式。压缩阶段会把存活对象向前搬移,并更新所有指向它们的引用。托管引用 `ref`/对象引用由 GC 知道并会更新;原生指针 `int*`、`void*`、`IntPtr` 它不认识,不会更新。所以:

```csharp
byte[] buf = new byte[4096];
unsafe
{
    byte* p;
    fixed (byte* q = buf)       // pin 期间 buf 不会被搬移
    {
        p = q;                  // 不要把 p 带出 fixed 作用域
        Native.fill(q, (UIntPtr)buf.Length);
    }
    // 这里使用 p 是未定义行为:buf 可能已被搬移或回收
}
```

`fixed` 的实现:C# 编译器为 `fixed` 变量生成 `pinned` 修饰的局部变量签名(IL 的 `.locals` 里是 `uint8[] pinned`),JIT 在 GC info 里把这个栈槽标为"固定"。GC 在该方法活跃期间遇到这个引用,就不搬移其指向的对象。没有堆分配,没有句柄表操作,进出作用域只是写栈槽。几个细节:

- `fixed (byte* p = arr)` 在数组为空时 `p` 为 null;`fixed (byte* p = &arr[0])` 在数组为空时抛 `IndexOutOfRangeException`。两种写法行为不同。
- `fixed (char* p = str)` 固定字符串,得到指向首字符的指针(以 `\0` 结尾,但不要写入,字符串是不可变的)。
- `fixed` 也能固定对象的字段:`fixed (int* p = &obj.field)`,固定的是整个对象。
- 结构体里的固定大小缓冲区 `fixed int data[16];` 是另一个概念:字段内联在 struct 里,用于和 C 的数组字段对齐布局,访问需要 `unsafe`。

## 固定对 GC 的影响

CoreCLR 压缩时,被固定的对象无法移动,GC 把它们前后的存活对象作为"固定插头"(pinned plug)处理,形成空洞。后果:

1. 空洞被记入 free list,新的分配可以填进去,但碎片仍多。Gen0 的"预算"不能被完整回收成连续区域,下次分配需要更多 Gen0 空间或更早触发 GC。
2. 长期固定的对象散布在年轻代(尤其是 Gen0)时,Gen0 里夹杂着大量空隙。GC 为此做过缓解:demotion(让固定对象留在 Gen0,以便尽快复用它们之间的空闲空间)和 POPO(Promote Only Pinned Objects,把同一个 plug 里固定与未固定的对象拆开,避免一个固定对象把相邻的大块未固定对象一并锁住)。但 dotnet/runtime 的 Pinned Heap 设计文档仍承认,无法消除固定与未固定对象交错的情况,实际 profile 里见过 Gen0 很大、碎片率很高。
3. 异步 I/O 常见模式:把缓冲区固定在 `OVERLAPPED` 操作期间。大量短命缓冲区同时被固定,Gen0 压缩效率下降。

缓解办法:

- 缩短固定时间,用 `fixed` 而不是长期持有的 `GCHandle`。
- 需要长期固定的缓冲区,在 .NET 5+ 用 `GC.AllocateArray<T>(length, pinned: true)` 或 `GC.AllocateUninitializedArray<T>(length, pinned: true)` 分配到 POH。POH 里的对象在分配时就被视为固定,不参与压缩,不污染 Gen0/LOH 的布局;类型 T 必须不含引用。
- 或自己从池里借缓冲(`ArrayPool<byte>`、`MemoryPool<byte>`),让它们在 Gen2 或 POH 里稳定存在。
- 直接用原生内存(`NativeMemory.Alloc`、`Marshal.AllocHGlobal`、Unity 的 `UnsafeUtility.Malloc`),根本不进 GC 堆。

## GCHandle 的四种类型

| 类型 | 是否阻止对象回收 | 是否固定 | 追踪复活 | 典型用途 |
|---|---|---|---|---|
| `Weak` | 否 | 否 | 否(对象进入终结队列后句柄即清零) | 缓存、事件弱订阅 |
| `WeakTrackResurrection` | 否 | 否 | 是(终结后若复活,句柄仍有效) | 需要观察复活对象的特殊场景 |
| `Normal` | 是,强根 | 否 | - | 把托管对象的"身份"交给原生保存 |
| `Pinned` | 是,强根 | 是,地址固定 | - | 把缓冲区地址交给原生长期持有 |

关键细节:

- 句柄存放在 CLR 的句柄表里,每次 GC 都要扫描句柄表,`Normal`/`Pinned` 当作根。数量很多时会拖慢 GC,忘记 `Free` 就是泄漏(对象永不回收,句柄表条目也不释放)。
- `Pinned` 句柄只能用于 blittable 对象:blittable 元素的数组、字符串、blittable struct 的装箱对象;含引用字段的类型会抛 `ArgumentException`。
- 常用模式:把 `GCHandle.ToIntPtr(h)` 作为 `void* userData` 传给原生,回调时用 `GCHandle.FromIntPtr(p)` 取回托管对象。这里用 `Normal` 即可,不需要 `Pinned`,因为原生只保存句柄值,不访问对象内存。

```csharp
sealed class Subscription : IDisposable
{
    delegate void EventCb(IntPtr user, int code);
    static readonly EventCb s_cb = OnEvent;      // 静态字段持有委托,防止被回收(见 2.2 节)
    GCHandle _self;

    public Subscription()
    {
        _self = GCHandle.Alloc(this);             // Normal:强根,防止 this 被回收
        Native.subscribe(Marshal.GetFunctionPointerForDelegate(s_cb), GCHandle.ToIntPtr(_self));
    }

    static void OnEvent(IntPtr user, int code)
    {
        var self = (Subscription)GCHandle.FromIntPtr(user).Target;
        // ...
    }

    public void Dispose()
    {
        if (!_self.IsAllocated) return;
        Native.unsubscribe(GCHandle.ToIntPtr(_self));
        _self.Free();                             // 必须释放,否则对象和句柄表条目都泄漏
    }
}
```

对照 C++:`GCHandle.Normal` 约等于"托管对象的 `shared_ptr` 引用计数 +1,并且是在运行时全局表里登记";`Pinned` 约等于"对象地址保证不变",C++ 的对象天然不移动,没有对应问题;`Weak` 约等于 `weak_ptr`,需要先 `Target` 检查再使用。

## Unity:Boehm 下的固定

Unity 6000.2 手册:Mono 与 IL2CPP 后端都使用 Boehm-Demers-Weiser 垃圾回收器,默认增量模式。Boehm 是保守式、不移动对象的收集器:

- 没有压缩,所以对象地址在其生存期内基本稳定;`fixed` 与 `GCHandleType.Pinned` 在实现上成本很低,甚至可能退化为不做事。
- 保守扫描会把栈、寄存器、静态区里的"像指针的整数"都当作引用。因此一个 `IntPtr` 偶然的位模式可能让一个大对象误保留。
- 这不代表可以省掉 `fixed`:这是实现细节而非语言契约。代码一旦被移植到压缩式运行时(例如 CoreCLR),没有 pin 的代码会立刻出错。Unity 向 CoreCLR 迁移的进度以官方发布为准,待核实。

## Unity:UnsafeUtility 与 NativeArray

`Unity.Collections.LowLevel.Unsafe.UnsafeUtility` 提供的常用能力:

- `Malloc(size, alignment, Allocator)` / `Free(ptr, Allocator)`:Unity 自己的分配器,和 Job 专栏 1.5 节讲的 Temp/TempJob/Persistent 一致。
- `MemCpy`、`MemMove`、`MemClear`、`MemCpyReplicate`、`MemCmp`。
- `AddressOf(ref T)`、`SizeOf<T>()`、`ReadArrayElement<T>`、`WriteArrayElement<T>`、`ArrayElementAsRef<T>`。
- `PinGCArrayAndGetDataAddress` 与 `ReleaseGCObject`:固定一个托管数组并返回数据地址与句柄(内部是 `GCHandle`)。具体签名随版本略有差异,待核实。
- `NativeArrayUnsafeUtility.GetUnsafePtr`、`GetUnsafeReadOnlyPtr`、`ConvertExistingDataToNativeArray`(把一块已有内存包装成 `NativeArray<T>`,需要配合 `AtomicSafetyHandle` 才能在编辑器里通过安全检查)。

`NativeArray<T>` 的结构(示意,字段名随版本变化):

```csharp
public struct NativeArray<T> where T : struct
{
    internal unsafe void* m_Buffer;            // 指向非托管缓冲区
    internal int m_Length;
    internal Allocator m_AllocatorLabel;
#if ENABLE_UNITY_COLLECTIONS_CHECKS
    internal AtomicSafetyHandle m_Safety;       // 仅编辑器/开发构建
#endif
}
```

与 GC 的关系:

- 缓冲区不在托管堆上,GC 既不扫描也不搬移,所以 `NativeArray<T>` 里存什么都不增加 GC 扫描压力。T 实际上要求是不含引用字段的值类型(新版本里是 `unmanaged` 约束),这就保证缓冲区里不可能出现需要 GC 追踪的引用。
- `NativeArray<T>` 本身是 struct,通常在栈或别的 struct 里;它被装箱、存进 `List<NativeArray<T>>`、或放在 class 字段里时,struct 本体会在托管堆上,但缓冲区仍在原生内存。忘记 `Dispose` 泄漏的是缓冲区,GC 回收不了它:没有终结器兜底。
- 与 `T[]` 互转:`CopyFrom/CopyTo/ToArray` 都是拷贝;`ToArray` 分配新托管数组,会产生 GC 压力。想零拷贝地让原生代码读托管数组,要么 `fixed`,要么 `PinGCArrayAndGetDataAddress`,并保证在原生使用期间 pin 不释放。
- Job 里不能访问托管数组或 `GCHandle`,所以要把数据放进 `NativeArray`/`NativeList` 等容器(Burst 也不支持托管类型,见 Burst 专栏)。

## 常见坑

- 把 `fixed` 里取得的指针返回出方法或存入字段。作用域结束后它就不再受保护。
- 用 `GCHandle.Alloc(obj, Pinned)` 却不释放,或在异常路径里漏释放。务必配 `try/finally`、`Dispose` 或终结器兜底。
- 对含引用字段的类型尝试 pin,得到 `ArgumentException`。
- 在 Unity 里因为"Boehm 不移动"就省略 pin,代码迁移或在编辑器之外的运行时测试时才爆。
- 以为 `NativeArray` 会被 GC 回收。忘记 `Dispose` 在编辑器里会收到泄漏警告,在 Player 里是静默泄漏。
- 大量短命 `fixed` 嵌套造成 CoreCLR 上的 Gen0 碎片。服务端工作负载里这是真实的性能问题,Unity 客户端上目前不是主要矛盾。

## 面试追问

1. **`fixed` 和 `GCHandle.Alloc(Pinned)` 有什么区别?各自适合什么场景?** 要点:`fixed` 是栈上的 pinned 局部,零分配,仅限当前作用域;`GCHandle` 是句柄表条目,可跨作用域与回调,需要手动释放,且每次 GC 要扫描。短调用用 `fixed`,原生长期持有地址用 `GCHandle` 或 POH。
2. **固定对象为什么会拖慢 GC?POH 解决什么?** 要点:压缩被打断,留下碎片,Gen0 难以整块回收;POH 把需要长期固定的对象放到独立区域,不参与 Gen0/Gen1 压缩,避免它们污染普通分代堆。
3. **`GCHandleType` 四种类型的区别?** 要点:Weak 不阻止回收且终结后清零;WeakTrackResurrection 复活后仍可用;Normal 强根;Pinned 强根且固定地址(仅 blittable)。
4. **Unity 里 `NativeArray` 为什么不会引起 GC?什么情况下仍然会?** 要点:缓冲区在原生内存,T 是 unmanaged;但 `ToArray()`、`foreach` 非泛型接口装箱、把 NativeArray 放入 class 字段(struct 本体在堆上但缓冲区不在)等路径仍可能产生托管分配或泄漏。
5. **Boehm GC 为什么不需要 pin?这样写代码安全吗?** 要点:Boehm 不移动对象,所以地址稳定;但这是实现行为而非保证,换运行时会出错,所以仍应按规范 pin。
6. **和 C++ 比,C# 的 pin 是为了解决什么问题?** 要点:C++ 对象不移动,指针永远有效,代价是堆碎片由分配器处理;C# 用压缩换取快速分配与局部性,需要通过 pin 把"可移动的世界"与"固定地址的世界"接起来。

## 参考资料

- Microsoft Learn,fixed statement:https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/statements/fixed
- Microsoft Learn,GCHandle 与 GCHandleType:https://learn.microsoft.com/en-us/dotnet/api/system.runtime.interopservices.gchandle
- dotnet/runtime,Pinned Object Heap 提案:https://github.com/dotnet/runtime/blob/main/docs/design/features/PinnedHeap.md
- Unity 手册,C# compiler and language version reference(含 GC 说明):https://docs.unity3d.com/6000.2/Documentation/Manual/csharp-compiler.html
- Unity Scripting API,UnsafeUtility 与 NativeArrayUnsafeUtility:https://docs.unity3d.com/ScriptReference/Unity.Collections.LowLevel.Unsafe.UnsafeUtility.html
