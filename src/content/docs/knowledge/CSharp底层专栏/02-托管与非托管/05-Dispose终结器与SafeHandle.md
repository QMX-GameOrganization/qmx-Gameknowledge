---
title: "2.5 Dispose、终结器与 SafeHandle"
description: 终结队列与 f-reachable 队列的工作方式、复活、Dispose 模式、SafeHandle 解决的竞态,以及 Unity 中 UnityEngine.Object 托管壳与原生对象的双生命周期。
sidebar:
  order: 5
---

> 适用版本:终结机制以 CoreCLR(.NET 5+)为准;Unity 部分以 6000.x(Boehm GC,C# 9.0)为准。`SafeHandle` 在 Unity IL2CPP P/Invoke 签名中的支持细节待核实。

## 要点

- 终结器(`~T()`,编译为重写 `Finalize`)是 GC 的"最后通知",不是析构函数。执行时机不确定、线程不确定、顺序不确定,甚至进程退出时不保证执行(.NET Core 起不再在退出时运行终结器)。
- 有终结器的对象在分配时就被登记进终结队列。GC 发现它不可达时,不回收,而是移到 f-reachable 队列,由终结器线程执行 `Finalize`。因此它至少多活一次 GC,并会被提升到更老的一代。
- 需要确定性释放时用 `IDisposable`,`Dispose()` 里调用 `GC.SuppressFinalize(this)`,让对象不再走 f-reachable 路径,第一次 GC 就能回收。
- 直接持有原生句柄的类,不要自己写终结器,用 `SafeHandle` 派生类。它解决了三个手写难以保证的问题:终结器一定会运行、句柄在 P/Invoke 进行期间不会被释放、句柄值回收复用导致的竞态。
- Unity 里 `UnityEngine.Object` 子类的 C# 对象只是原生对象的托管壳。`Destroy` 销毁原生对象,C# 壳活到没人引用时才被 GC 回收。重载的 `==` 让被销毁对象表现得像 null("fake null"),但 `?.`、`??`、`is null` 会绕过这个重载。

## 终结机制

CoreCLR 的做法:

1. **分配。** 类型带终结器时,`new` 路径(慢路径分配器)把对象登记到 GC 的终结队列(finalization queue)。这就是为什么带终结器的类型分配比普通类型慢:不能走纯 bump pointer 的快速路径。
2. **GC 标记阶段后。** 对终结队列中每个对象检查是否已标记存活。没有标记的(不可达),从终结队列移到 f-reachable 队列,并且把它标记为存活(连同它引用的一切对象)。此刻对象"被救回",仅为了让终结器能执行。
3. **终结器线程。** 专门的线程不断从 f-reachable 队列取对象调用 `Finalize`。执行完后对象不再登记在任何队列里。
4. **下一次 GC。** 如果对象仍不可达,这次才被真正回收。

后果:

- 终结对象的存活期至少多一次 GC,并且会随 GC 的提升而进入 Gen1、Gen2。它引用的子图在第一次 GC 里都被一起救活,即使子图本身没有终结器。把一整棵对象树的根放个终结器,整棵树都要熬过多一轮 GC。
- 终结器线程是单线程串行,终结器里阻塞会拖死所有后续对象的释放;终结器里抛异常会导致进程终止(未处理异常)。
- 终结器之间没有顺序保证,A 引用 B 时,A 的终结器里 B 可能已经被终结。所以终结器里不要访问其他托管对象(除非是 `CriticalFinalizerObject` 这类有顺序约定的)。
- 进程退出:.NET Framework 会在关闭时尝试运行终结器,.NET Core 起不会。不要依赖终结器刷盘、发送网络消息。

### 复活

终结器里把 `this` 存进静态字段,对象重新变为可达,即"复活"。复活后对象默认不再终结(它已经从队列移出),除非调用 `GC.ReRegisterForFinalize(this)`。这被用于对象池、"必须最终释放"的补偿场景,但容易造成难以推理的状态,正常代码应避免。`WeakReference(obj, trackResurrection: true)`(对应 `GCHandleType.WeakTrackResurrection`)能观察到复活后的对象,普通弱引用在对象进入 f-reachable 时已经清空。

## Dispose 模式

标准写法(基类持有托管资源和非托管资源):

```csharp
public class ResourceHolder : IDisposable
{
    IntPtr _handle;                               // 非托管资源
    Stream _stream;                                // 托管资源(自己有 Dispose)
    bool _disposed;

    ~ResourceHolder() => Dispose(false);          // 兜底

    public void Dispose()
    {
        Dispose(true);
        GC.SuppressFinalize(this);                 // 已经显式释放,不用终结
    }

    protected virtual void Dispose(bool disposing)
    {
        if (_disposed) return;
        if (disposing)
        {
            _stream?.Dispose();                    // 只在显式路径里触碰托管对象
        }
        if (_handle != IntPtr.Zero)
        {
            Native.close(_handle);
            _handle = IntPtr.Zero;
        }
        _disposed = true;
    }
}
```

规则:

- `Dispose()` 必须幂等、可重复调用、不抛异常。
- `Dispose(bool disposing)` 里,`disposing == true` 才可以访问其他托管对象;`false` 表示来自终结器,别的托管对象可能已被终结。
- 没有非托管资源时,不需要写终结器。大多数只持有其他 `IDisposable` 的类,只实现 `Dispose` 即可。
- 派生类持有新的非托管资源时,覆盖 `Dispose(bool)` 并调用 `base.Dispose(disposing)`。
- `GC.SuppressFinalize` 的实现:在对象头(同步块索引字段)上置位"终结器已运行/不需要运行"标记,GC 在处理终结队列时看到这个标记就不会把对象移到 f-reachable。所以调用它能省掉一轮额外 GC 和一次终结器线程调度。
- `using` 语句、`using var` 声明是语言级的 `try/finally { Dispose() }`,相当于 C++ 的 scope guard / RAII 的手动版本。

## SafeHandle

`SafeHandle`(抽象类,继承自 `CriticalFinalizerObject`)封装一个 `IntPtr handle`,提供:

1. **保证释放。** `CriticalFinalizerObject` 的终结器在其他普通终结器之后执行,且运行时会在加载时预先准备好终结器相关代码(避免内存不足时 JIT 失败),使得句柄不会因为终结阶段失败而泄漏。
2. **引用计数防竞态。** P/Invoke 封送器看到参数是 `SafeHandle`,调用前调用 `DangerousAddRef`,调用后调用 `DangerousRelease`。另一线程在调用期间调用 `Dispose`/`Close` 时,实际的 `ReleaseHandle` 推迟到引用计数归零。避免"线程 A 正在用句柄做 I/O,线程 B 关闭了句柄"。
3. **防句柄回收复用攻击。** 原生句柄值(如文件描述符)关闭后会被系统复用。裸 `IntPtr` 版本里,旧句柄值在别处可能意外指向新资源;`SafeHandle` 每次释放后将句柄标记为无效(`SetHandleAsInvalid`),并且托管侧只引用 `SafeHandle` 对象。

```csharp
sealed class NativeSession : SafeHandle
{
    NativeSession() : base(IntPtr.Zero, ownsHandle: true) { }
    public override bool IsInvalid => handle == IntPtr.Zero;
    protected override bool ReleaseHandle()        // 不要分配内存,不要抛异常,不要阻塞
    {
        Native.session_destroy(handle);
        return true;
    }
}

static class Native
{
    [DllImport("mylib")] public static extern NativeSession session_create();   // 返回值直接封送为 SafeHandle
    [DllImport("mylib")] public static extern int session_poll(NativeSession s);
    [DllImport("mylib")] public static extern void session_destroy(IntPtr s);
}
```

`ReleaseHandle` 在终结线程上执行,要尽量简单:不能分配、不能依赖托管对象、不能抛异常。

### GC.KeepAlive 与 this 的提前死亡

```csharp
class Legacy
{
    IntPtr _h;
    ~Legacy() { Native.close(_h); }

    public int Read()
    {
        // 优化后的 JIT 可能认为 this 在读出 _h 之后就不再被使用
        return Native.read(_h);                     // 此刻终结器可能已在另一线程执行 close
    }
}
```

CoreCLR 的 JIT 对优化代码按活跃性分析,`this` 在最后一次使用后即视为死亡(见 2.1 节),所以 `Read` 正在原生里执行时,GC 可以判定对象不可达并启动终结器。解决方法:在调用后加 `GC.KeepAlive(this)`,或者改用 `SafeHandle`(封送器的引用计数天然覆盖了这个问题)。Debug 构建不做这种缩短,问题只在 Release 里偶现。

Unity 的 Boehm 是保守扫描,`this` 通常仍留在栈或寄存器里,所以此类 bug 平时不现形;迁移到精确 GC 的运行时才会暴露。

## 弱引用与终结的关系

- `WeakReference`(短弱引用)在对象不可达的一次 GC 里就清零,即使对象带终结器、尚未执行终结。
- 长弱引用(`trackResurrection: true`)直到对象真正被回收才清零。
- `ConditionalWeakTable<TKey, TValue>` 用来给对象附加数据,键存活则值存活,键被回收则条目消失,适合缓存和"依附"信息,不会泄漏键。

## Unity:Native 对象的双生命周期

`UnityEngine.Object`(`GameObject`、`Component`、`Texture2D`、`Mesh`、`Material` 等)在托管侧是一个 C# 对象,内部有指向原生对象的指针字段(历史上叫 `m_CachedPtr`)。两个生命周期:

| 生命周期 | 由谁管 | 何时结束 |
|---|---|---|
| 原生对象 | Unity 引擎 | `Destroy`/`DestroyImmediate`、场景卸载、`Resources.UnloadUnusedAssets` 对无引用资源的卸载 |
| 托管壳 | GC | 没有任何托管引用,下一次 GC 回收 |

后果:

- `Destroy(obj)` 后,托管壳仍然存在(你的字段还引用着它),只是内部原生指针失效。重载的 `operator ==`/`bool` 转换检查原生对象是否存活,所以 `obj == null` 返回 true,这就是 "fake null"。但 `obj?.Foo()`、`obj ?? other`、`obj is null`、`ReferenceEquals(obj, null)` 不走重载,仍然把它当非空,访问时抛 `MissingReferenceException`。需要判空时用 `obj == null` 或 `!obj`;在泛型里还要小心:不要用 `object` 或 `EqualityComparer<T>.Default` 比较。
- 原生内存不归 GC 管。`new Texture2D(...)`、`new Mesh()`、`new Material(...)` 创建的资源,即使 C# 壳被回收,原生部分也要靠 `Destroy` 或 `Resources.UnloadUnusedAssets` 清理(以单个场景模式 `LoadScene` 时,Unity 会隐式执行一次)。运行时动态创建的资源,用完要显式 `Destroy`,否则内存只增不减。
- `Resources.UnloadUnusedAssets` 需要遍历托管侧引用来判断资源是否被使用,所以它依赖托管引用图的准确性;托管引用没清除,原生资源就不能卸载。典型泄漏是静态字典、事件订阅、缓存里还拿着贴图壳。
- 需要显式释放的原生封装:`NativeArray`/`NativeList` 等容器的 `Dispose`、`ComputeBuffer`/`GraphicsBuffer` 的 `Release`、`RenderTexture` 的 `Release`、`UnityWebRequest` 的 `Dispose`、`Texture2D` 的 `Destroy`。这些是 Unity 里的"手动 RAII",忘记就泄漏;终结器做兜底的力度因类型而异,不能依赖。
- 终结器线程不是 Unity 主线程。大多数 Unity API 只能在主线程调用,在终结器里调用会抛异常或崩溃。想在终结器里释放 Unity 资源,要把句柄入队,由主线程的 Update 统一处理。

对照 C++:Unity 的 Native 对象更接近 C++ 里由引擎持有所有权的对象,托管壳相当于一个 `weak_ptr` 加一层"已销毁"检查;C++ 自己写的 RAII 类(`unique_ptr`、自定义析构)在作用域结束时确定性释放,而 C# 要靠 `using` 或手动 `Dispose`。

## 常见坑

- 写了终结器却不实现 `Dispose` 与 `SuppressFinalize`,所有实例都白白多活一轮 GC。
- 终结器里访问其他托管对象、调 Unity API、取锁。
- `Dispose` 不幂等,二次调用抛异常。
- 把 `Dispose(bool disposing)` 里 `disposing == false` 路径也去释放托管字段。
- `?.` 或 `??` 判断 `UnityEngine.Object` 是否已销毁。
- 静态字典、全局事件持有已销毁对象的壳,阻止 `UnloadUnusedAssets` 回收贴图与网格。
- 依赖终结器回收 `NativeArray`:根本没有终结器兜底,泄漏后只有编辑器泄漏检测会提示。

## 面试追问

1. **终结器和析构函数有什么区别?为什么说终结器会延长对象寿命?** 要点:C# 的 `~T()` 是 `Finalize`,由终结器线程在 GC 之后执行,时机不确定;对象第一次不可达时被移入 f-reachable 队列并被当作根,所以至少多活一次 GC 并被提升代龄;其引用的子图也被一起救活。
2. **`GC.SuppressFinalize` 做了什么?** 要点:在对象头上置标记,告诉 GC 不需要执行终结器,对象第一次不可达时即可回收;要在 `Dispose()` 中、资源已被确定性释放后调用。
3. **为什么推荐 `SafeHandle` 而不是自己写终结器加 `IntPtr`?** 要点:`CriticalFinalizerObject` 保证终结器执行与预先准备;P/Invoke 期间引用计数,避免 `Dispose` 与调用竞态;避免句柄复用带来的误操作;`this` 提前死亡的问题被一并解决。
4. **什么是复活?有什么用?风险是什么?** 要点:终结器里让对象重新可达;默认不再终结,需 `ReRegisterForFinalize`;用于特殊的池化或兜底场景,但状态难以推理,一般避免;只有长弱引用能观察到复活。
5. **Unity 里 `Destroy` 一个对象后为什么 `obj == null` 为 true,而 `obj?.x` 还会访问?** 要点:`UnityEngine.Object` 重载了 `==` 检查原生对象存活;`?.`、`??`、`is null` 编译为引用比较,不走重载;壳还在,原生对象已没了,访问会抛 `MissingReferenceException`。
6. **动态创建的 `Texture2D` 不 `Destroy` 会怎样?** 要点:C# 壳可被 GC 回收,但原生内存由引擎管理,需要 `Destroy` 或 `UnloadUnusedAssets` 才会释放;静态引用会阻止后者生效,造成长期泄漏。
7. **和 C++ RAII 比,C# 为什么需要两套机制(Dispose 与终结器)?** 要点:GC 的回收时机非确定,只能保证"最终"释放;`Dispose` 提供确定性释放点,终结器作为遗漏时的兜底;RAII 用栈展开保证析构,没有这个矛盾。

## 参考资料

- Microsoft Learn,Implement a Dispose method:https://learn.microsoft.com/en-us/dotnet/standard/garbage-collection/implementing-dispose
- Microsoft Learn,Finalizers(C# 编程指南):https://learn.microsoft.com/en-us/dotnet/csharp/programming-guide/classes-and-structs/finalizers
- Microsoft Learn,SafeHandle 类:https://learn.microsoft.com/en-us/dotnet/api/system.runtime.interopservices.safehandle
- dotnet/runtime,GC 设计与终结文档(botr/garbage-collection.md):https://github.com/dotnet/runtime/blob/main/docs/design/coreclr/botr/garbage-collection.md
- Unity 手册,Resources.UnloadUnusedAssets 与托管内存说明:https://docs.unity3d.com/ScriptReference/Resources.UnloadUnusedAssets.html
- Unity 手册,C# compiler and language version reference(GC 说明):https://docs.unity3d.com/6000.2/Documentation/Manual/csharp-compiler.html
