---
title: "5.2 RAII、所有权与 GC：三种生命周期管理模型"
description: 对照 C++ 的 RAII 与智能指针、C# 的 GC 加 Dispose 加终结器，以及 UE 的 UObject GC，讲所有权如何表达、析构何时发生、循环引用与池化分配。
sidebar:
  order: 2
---

> 适用版本：C++17；.NET 8/9 CoreCLR 语义，Unity Mono/IL2CPP（Boehm GC）的差异单独标注；UE5 的 UObject GC 为概述，具体 CVar 和函数名随引擎小版本变化，处已标"待核实"。

## 要点

- C++ 把"内存"和"资源"统一用对象生命周期管理：谁拥有，谁在析构里释放，所有权写在类型里（`unique_ptr`、`shared_ptr`、裸指针即借用）。
- C# 把"内存"交给 GC，把"非内存资源"留给 `Dispose`。GC 回答"还有人能访问它吗"，不回答"谁该负责清理它"。所有权在类型系统里没有表达。
- 终结器不是析构函数：它在 GC 之后、由专门的终结器线程调用，时机和顺序都不确定，对象还会因此多存活至少一轮 GC。
- 循环引用在 C++ 的 `shared_ptr` 里是泄漏，在 C# 里不是问题。C# 的"泄漏"来自意外的强引用：静态字段、事件订阅、缓存、未释放的 Native 内存。
- 移动语义解决的是"昂贵拷贝 + 唯一所有权"问题。C# 的引用赋值本来就只拷贝指针，所以没有对应概念，但 `struct` 复制、`ref`、`in`、`Span<T>` 承担了其中一部分借用语义。
- 池化与 arena 在两种语言里的出发点不同：C++ 为避免分配器开销和碎片，C# 为避免触发 GC 和跨代引用。
- UE 的 UObject 是第三种模式：自带反射元数据的标记清除 GC，指针是否被追踪取决于是否经过 `UPROPERTY` 或 `TObjectPtr`。

## 所有权表达：C++ 在类型里，C# 在约定里

### C++

```cpp
struct Texture { /* 持有 GPU 句柄 */ ~Texture() { release(); } };

std::unique_ptr<Texture> a = std::make_unique<Texture>();   // 独占，零额外开销，不可拷贝只可移动
std::shared_ptr<Texture> b = std::make_shared<Texture>();   // 共享，引用计数
std::weak_ptr<Texture>   w = b;                             // 观察，不延长生命周期
Texture* raw = a.get();                                     // 借用，约定不持有
```

要点：

- `unique_ptr` 在优化后与裸指针大小相同（默认 deleter 时）。`shared_ptr` 是两个指针（对象指针加控制块指针），16 字节。
- `make_shared` 把对象与控制块一次分配，减少一次堆分配并让二者相邻；代价是弱引用存在时对象内存要等控制块一起释放。
- 控制块里的强弱引用计数使用原子操作，所以拷贝 `shared_ptr` 有原子读写成本，高频传递时应传 `const shared_ptr&` 或裸引用。多线程下，控制块的计数是线程安全的，但指向的对象本身不是，同一个 `shared_ptr` 变量被多个线程读写也不安全（C++20 的 `atomic<shared_ptr>` 解决后者）。
- 析构顺序是确定的：局部对象反向构造顺序析构，成员反向声明顺序析构。异常发生时栈展开也会析构。这就是 RAII 的核心：资源获取即初始化，释放绑在作用域上。

### C#

```csharp
sealed class Texture : IDisposable
{
    IntPtr _handle;
    public void Dispose() { if (_handle != IntPtr.Zero) { Native.Release(_handle); _handle = IntPtr.Zero; } }
}

using var t = new Texture();    // 作用域结束调用 Dispose：C# 里最接近 RAII 的部分
```

C# 没有办法在类型上声明"这个引用拥有对象"。`using` 只对局部变量生效，一旦对象被存到字段、传给别的方法、放入集合，谁来 `Dispose` 就只能靠约定和文档。常见的约定有：

- 谁创建谁释放；
- 把对象传给构造函数表示转移所有权（`StreamReader` 默认会关闭底层流）；
- 容器类持有子对象时实现自己的 `Dispose` 并级联。

这些约定一旦出错，表现为资源晚释放或双重释放，编译器完全看不出来。分析器（如 CA2000、CA2213）能抓一部分。

## 析构确定性与终结器

C++ 的析构函数在对象生命周期结束的那一刻同步执行。C# 的终结器（`~Foo()`）的实际流程：

1. 对象创建时，如果类型有终结器，运行时把它登记进 finalization queue。
2. GC 发现该对象不可达，不立即回收，而是把它移入 f-reachable 队列，并把它和它引用的所有对象重新标记为存活。
3. 终结器线程取出队列里的对象，逐个调用 `Finalize`。
4. 下一次 GC 才真正回收内存。

结果：有终结器的对象至少多活一轮 GC，通常因此被提升一代（gen0 的对象被带进 gen1，有可能再进 gen2）；终结器线程只有一个；多个对象之间的终结顺序不保证，所以终结器里不能安全访问其他有终结器的托管对象；终结器里对象可以"复活"（把 `this` 存到静态字段）。

标准做法是 Dispose 模式：显式 `Dispose()` 做清理并调用 `GC.SuppressFinalize(this)`，终结器只作为遗忘调用时的兜底。对包装非托管句柄的类，更推荐继承 `SafeHandle`，它保证句柄在 P/Invoke 期间不会被提前终结，并且用关键终结器（CriticalFinalizerObject）降低失败概率。

Unity 里的 Mono 与 IL2CPP 使用 Boehm GC，也有终结器线程，语义与上面一致，但没有分代，所以"提升一代"的说法对 Unity 不成立，终结器对象只是多存活一轮回收。实践上，Unity 项目里对象的释放大多靠显式 `Dispose`、`Destroy` 与引擎对象的生命周期回调，不依赖终结器。

## 移动语义与引用拷贝

C++ 11 的移动语义：

```cpp
std::vector<int> make() { std::vector<int> v(1000); return v; }   // RVO 或移动，不拷贝元素
auto a = make();
auto b = std::move(a);          // std::move 只是转成右值引用，真正的转移发生在移动构造里
// a 此时处于"有效但未指定"状态，通常为空，可以重新赋值或析构
```

- 目的：在"唯一所有者"前提下，把资源（堆内存、句柄）的所有权从一个对象转给另一个，避免深拷贝。
- `noexcept` 的移动构造会影响 `std::vector` 扩容：强异常安全要求下，只有移动构造不抛异常，才会在扩容时移动元素，否则退回拷贝（`std::move_if_noexcept`）。

C# 引用赋值只复制 8 字节指针，两个变量指向同一个对象：

```csharp
var a = new List<int>(1000);
var b = a;          // 没有拷贝，两个别名
b.Add(1);           // a 同时看到
```

差异：

| 项 | C++ | C# |
|---|---|---|
| 默认赋值 | 值拷贝（对象本身） | class：引用拷贝；struct：值拷贝 |
| 表示"转移所有权" | 移动构造、`unique_ptr` | 无，靠约定与置空 |
| 表示"借用" | `T&`、`const T&`、裸指针 | `ref`/`in`/`ref struct`/`Span<T>`，仅限栈上生命周期 |
| 编译器保证借用不悬垂 | 不保证（悬垂引用是 UB） | 保证（`ref` 不能逃出作用域，GC 保证被引用对象不被回收） |
| 复制昂贵对象 | 需要显式 Clone 或拷贝构造 | 需要显式 Clone 或拷贝构造函数 |

C# 用 GC 取代了悬垂指针的可能性，代价是不能确定地回收；用 `ref` 规则限制借用范围，代价是借用只能存在于栈帧，不能存进字段（`ref struct` 字段也受限，C# 11 起 `ref` 字段仅限于 `ref struct`）。

## 循环引用与泄漏

C++：

```cpp
struct Node { std::shared_ptr<Node> next; std::weak_ptr<Node> prev; };
// next 与 prev 若都是 shared_ptr，则互相持有，引用计数永远不归零 -> 泄漏
```

C#：A 与 B 互相引用，只要根不可达就都会被回收，无需 `weak_ptr`。C# 里真实的泄漏模式是：

- 静态字段或单例持有对象引用，例如全局事件总线；
- 事件订阅未取消：`publisher.OnEvent += subscriber.Handler` 让 publisher 持有 subscriber，publisher 活得久则 subscriber 不会被回收；
- 缓存字典无淘汰策略；
- 闭包捕获了大对象，委托又被长期持有；
- `Native*` 容器、`UnsafeUtility.Malloc`、`ComputeBuffer`、`RenderTexture` 等非托管资源没有释放；
- Unity 特有：`UnityEngine.Object` 在 C# 侧是个壳，Native 侧对象不由 C# GC 管理，需要 `Destroy`；C# 引用被置 null 不会销毁 GameObject，而 `Destroy` 后 C# 引用仍然存在但 `== null` 返回 true（重载了相等运算符）。

`WeakReference` 与 `weak_ptr` 的区别：`WeakReference` 基于 GC 句柄，创建与访问都比普通引用贵，大量使用会给 GC 增加句柄扫描负担；`weak_ptr::lock()` 则是对控制块的原子操作。

## 池与 arena

C++ 中常用的方式：

```cpp
std::pmr::monotonic_buffer_resource arena(buffer, sizeof buffer);
std::pmr::vector<int> v{&arena};   // 在 arena 中分配，arena 销毁时一次性释放，不调用逐对象 free
```

好处是分配只是移动一个指针、释放整体归零、数据局部性好。游戏里的帧分配器、线性分配器就是这个模式。

C# 里的池化目标不同：

- `ArrayPool<T>.Shared`：复用大数组，避免进入 LOH 与反复触发 GC。
- `Microsoft.Extensions.ObjectPool`、`UnityEngine.Pool.ObjectPool<T>`：复用对象，使其生命周期稳定，不产生新垃圾。
- `Allocator.Temp/TempJob/Persistent` 与 `NativeArray`：完全绕开 GC（见 Job 与 Burst 专栏 1.5）。

池化的副作用：被池长期持有的对象会晋升到老年代，之后若它们引用新分配的年轻对象，每次写入都要触发写屏障把卡表标脏，下一次年轻代 GC 要额外扫描这些卡。所以池化对象内部再持有频繁更换的引用对象，会削弱分代 GC 的收益。池化的对象还必须在归还时重置状态，漏重置是典型 bug 来源。

## UE 的 UObject GC：第三种模式

UE 的 GC 既不是引用计数，也不是 .NET 那种扫描全部对象图的分代收集，主要特征：

- 以根集（root set）为起点，沿反射元数据遍历。`UPROPERTY` 标记的 `UObject*` 成员、`TObjectPtr`、`TArray<UObject*>` 等才会被 GC 看到，没有标记的裸指针是"看不见"的，对象被回收后会变成悬垂指针。
- 采用标记清除，不移动对象，不分代（与 .NET 相反）。可达性分析可以并行，清除阶段按时间片分帧推进（增量清理）。
- 对象销毁分两步：先标记为待销毁（旧版本叫 PendingKill，UE5 起引入 `MarkAsGarbage` 一类的新语义，待核实），GC 确认不可达后调用 `BeginDestroy`/`FinishDestroy` 完成异步清理。
- 非 `UObject` 的 C++ 对象用 `TSharedPtr`/`TUniquePtr` 等引用计数或独占指针；`TWeakObjectPtr` 是观察 `UObject` 的弱引用，访问前用 `IsValid` 检查；`TStrongObjectPtr` 用来在非 `UObject` 里让 GC 看见强引用。
- 默认有周期性 GC（间隔为秒级，可由 CVar 调整，待核实具体变量与默认值），加载关卡等时机也会强制 GC。

比较：

| 项 | C++ RAII | .NET / Unity GC | UE UObject GC |
|---|---|---|---|
| 回收依据 | 作用域、引用计数 | 可达性（根集追踪） | 可达性（反射遍历 + 根集） |
| 释放时机 | 确定 | 不确定 | 不确定，可手动 `CollectGarbage` |
| 移动对象 | 否 | .NET 可压缩移动，Unity Boehm 不移动 | 否 |
| 谁被追踪 | 不涉及 | 所有托管引用 | 仅反射可见的指针 |
| 典型坑 | 循环引用、悬垂指针 | 意外强引用、GC 卡顿、装箱 | 漏标 `UPROPERTY` 导致悬垂、GC 峰值 |

## 常见坑

- 以为把 C# 对象置 `null` 就释放了资源。置空只影响可达性，资源释放必须 `Dispose`。
- 在终结器里访问其他托管对象。它们可能已经被终结。
- `Dispose` 不是幂等的：重复调用抛异常或重复释放句柄。
- 把 `shared_ptr` 当作默认选项。每次拷贝都是原子操作，且所有权不清晰。
- 在 Unity 里用 `WeakReference` 缓存 `UnityEngine.Object`，引用本身还在，但底层已经被 `Destroy`。
- 在 UE 里把 `UObject*` 存在普通 `std::vector` 里，GC 看不到，对象会被回收。

## 面试追问

1. RAII 为什么能做到异常安全？要点：资源绑定在栈对象上，栈展开时自动调用析构，不依赖调用者显式清理。
2. 为什么 C# 需要 Dispose 模式，而不是只靠终结器？要点：终结器时机不确定、需要多活一轮 GC、运行在单独线程，稀缺资源（句柄、显存、连接）不能等。
3. `shared_ptr` 的循环引用如何解决？C# 为什么没这个问题？要点：其中一环改 `weak_ptr`；C# 用可达性追踪，根不可达则整个环一起回收。
4. 终结器为什么会让对象晋升？要点：GC 为了执行终结器要重新标记对象存活，该对象在这轮 GC 中被当作存活，因此晋升。
5. 池化在 C# 里的副作用？要点：老年代对象引用年轻对象触发写屏障与卡表扫描，池内对象需重置状态，池大小需要上限。
6. UE 里为什么裸 `UObject*` 成员会悬垂？要点：GC 通过反射元数据遍历，未标 `UPROPERTY` 的指针不在可达图中。

## 参考资料

- C++ Core Guidelines，资源管理（R 部分）：https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines
- Microsoft Learn，Implement a Dispose method：https://learn.microsoft.com/dotnet/standard/garbage-collection/implementing-dispose
- Microsoft Learn，Finalizers：https://learn.microsoft.com/dotnet/csharp/programming-guide/classes-and-structs/finalizers
- cppreference，`std::shared_ptr`：https://en.cppreference.com/w/cpp/memory/shared_ptr
- Epic 文档，Unreal Engine 的对象处理与垃圾回收：https://dev.epicgames.com/documentation/en-us/unreal-engine/objects-in-unreal-engine
