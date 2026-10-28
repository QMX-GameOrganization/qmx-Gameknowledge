---
title: "2.4 Span、Memory 与 ref struct"
description: Span<T> 的内存布局与 ref struct 的限制成因(结构撕裂、托管指针、状态机提升),stackalloc、ref 返回与 ref 局部变量,以及 Unity 中的可用范围。
sidebar:
  order: 4
---

> 适用版本:语言特性以 C# 7.2~C# 9 为准(Unity 6000.x 的 C# 版本是 9.0);`ref` 字段、`allows ref struct` 泛型约束、`params Span<T>` 属于 C# 11~13,Unity 6000.x 中不可用。`Span<T>` 在 Unity 中依赖 .NET Standard 2.1 API 兼容级别,起始版本待核实(据记忆为 Unity 2021.2)。

## 要点

- `Span<T>` 是对一段连续内存的视图,可以指向托管数组、栈内存(`stackalloc`)、原生内存。它是 `ref struct`:CoreCLR 里布局是"一个托管指针(`ref T`)加一个 `int` 长度",总共 16 字节(64 位)。
- `ref struct` 的所有限制(不能装箱、不能做类字段、不能被 lambda 捕获、不能跨 `await`、不能做数组元素、不能做泛型实参)都来自同一个原因:它里面有一个只能活在栈上的托管指针,并且这个"指针加长度"对必须原子地一起可见。
- `Memory<T>` 是能放堆上的对应物:它存的是"对象引用 + 偏移 + 长度",通过 `.Span` 才得到 `Span<T>`。要跨 `await`、要存进字段,用 `Memory<T>`。
- 切片(`Slice`)、`AsSpan` 都是 O(1),不拷贝。用 `ReadOnlySpan<char>` 解析字符串,比 `Substring`/`Split` 少一堆分配。
- Unity 6000.x 的 C# 9.0 支持 `ref struct`、`stackalloc` 赋给 `Span<T>`、`ref` 返回/局部变量,不支持 `SkipLocalsInit`(手册列为不支持项),所以 `stackalloc` 总会清零。

## Span<T> 的布局

CoreCLR 中(简化):

```csharp
public readonly ref struct Span<T>
{
    internal readonly ref T _reference;   // 托管指针,可以指向数组元素、栈上、原生内存
    private readonly int _length;
}
```

`ref T _reference` 是 CLR 的 byref:它可以指向对象内部(数组中间某个元素)、栈上局部、静态区或非托管内存;对 GC 来说它是内部指针(interior pointer),GC 会把它所指的对象视为存活,并在压缩时更新它,所以不需要固定。

`Span<T>` 与 `T*` 的区别:带长度、带边界检查、不要求 `unsafe`,同时能指向 GC 堆。`Span<T>` 与 `T[]` 的区别:数组是堆对象,有对象头、方法表指针、长度字段;`Span<T>` 只是一个 16 字节的栈上值,可以指向数组的任意子段。

Unity 的 Mono 类库(netstandard2.1 profile)里 `Span<T>` 的内部实现未必是上述 `ref T` 字段形态(语言级 `ref` 字段是 C# 11 的特性,旧实现用 `Pinnable<T>` 加偏移的方式表达),但对使用者的语义一致,待核实具体布局。

对照 C++:`std::span<T>` 是指针加长度的非拥有视图,同样不管生命周期。区别在于 C# 编译器通过 ref struct 规则和"安全逃逸范围"(safe-to-escape)分析,在编译期阻止你把指向栈上的 Span 返回给调用者或存进堆;C++ 把这件事留给程序员。

## 为什么 ref struct 有这些限制

| 限制 | 原因 |
|---|---|
| 不能装箱,不能转 `object`/接口 | 装箱要在堆上复制一份值,等于把托管指针放进堆对象 |
| 不能作为类的字段,或非 ref struct 的字段 | 同上:持有它的对象可能在堆上 |
| 不能被 lambda/本地函数捕获 | 捕获变量会提升成闭包类的字段,在堆上 |
| 不能在 `async` 方法、迭代器方法中做局部变量(跨 `await`/`yield`) | 状态机把跨暂停点的局部提升成状态机字段,状态机可能被装箱到堆 |
| 不能做数组元素类型,不能做泛型实参(C# 13 前) | 数组在堆上;泛型实例化可能装箱或存到堆里 |
| 不能实现接口(C# 13 前) | 调用接口方法通常要装箱 |

根因分两层:

1. **GC 与类型系统的约束。** byref 类型在 CLR 类型系统里本身就是"byref-like",CLR 禁止它们出现在堆上的字段里。堆上存放内部指针需要对象布局、写屏障、卡表对它们的专门支持,代价与复杂度都很高;而栈上的 byref 只需 JIT 在 GC info 里标记即可(见 2.1 节)。
2. **结构撕裂(struct tearing)。** `Span<T>` 是"指针加长度"的双字结构。如果它能放到堆上并被多线程读写,一个线程可能读到新指针加旧长度,导致越界读写,破坏内存安全。限制在栈上则只被当前线程访问,不存在撕裂。这也是为什么需要跨线程、跨 await 共享视图时要用 `Memory<T>`:它的字段是普通引用加两个 int,语义上允许撕裂但访问时再经 `.Span` 做一致性检查(取 `.Span` 时才真正按数组类型验证偏移与长度)。

## stackalloc

```csharp
Span<byte> buf = stackalloc byte[256];      // C# 7.2 起,无需 unsafe
buf[0] = 1;

// 超过阈值回退到堆或池
const int Threshold = 512;
Span<char> chars = len <= Threshold
    ? stackalloc char[Threshold]
    : new char[len];
```

要点:

- `stackalloc` 对应 IL 指令 `localloc`,在当前栈帧上分配,方法返回时自动释放。IL 的 `.locals init` 标志会让运行时在分配时清零。CoreCLR 上可用 `[SkipLocalsInit]` 跳过清零;Unity 6000.2 手册把"Suppress emitting localsinit flag"列为 C# 9 的不支持项,所以 Unity 中 `stackalloc` 总会清零,大块 `stackalloc` 的成本包括清零。
- 不要在循环里 `stackalloc`:栈内存要到方法返回才释放,循环里每次迭代都会累加,迅速栈溢出。
- 栈大小有限:Windows 主线程默认 1 MB,Linux 默认 8 MB 左右(取决于 `ulimit`),子线程栈往往更小;Unity 主线程栈大小与各平台线程栈大小不同,大块数据不要放栈上。栈溢出在 .NET 里无法捕获,进程直接终止。
- 栈内存没有 GC 开销,也不会产生碎片,最适合小的、短命的、定长的临时缓冲(解析、格式化、小批量排序)。

## ref 返回与 ref 局部变量

```csharp
ref int Find(int[] arr, int key)
{
    for (int i = 0; i < arr.Length; i++)
        if (arr[i] == key) return ref arr[i];     // 返回元素本身的别名,不是拷贝
    throw new KeyNotFoundException();
}

ref int slot = ref Find(data, 42);
slot = 100;                                         // 直接改数组元素
```

- `ref` 返回的对象必须能活过调用方:可以返回数组元素、类字段、静态字段、通过 `ref` 参数传入的位置;不能返回局部变量的引用。编译器用"ref-safe-to-escape"分析来检查。
- `ref readonly` 返回大 struct 时避免拷贝,配合 `in` 参数使用。注意 `in` 参数在遇到非 readonly struct 时编译器会生成防御性拷贝(见 1.3 节),`readonly struct` 才能彻底避免。
- C# 7.3 起 `ref` 局部可以重新赋值:`slot = ref other;`。
- `ref` 字段(C# 11)与 `scoped` 关键字:Unity 6000.x 不可用。需要在 struct 中保存引用,Unity 里还是要用指针(`unsafe`)或索引。

## Memory<T> 与 ReadOnlySpan<char> 实务

```csharp
// 零分配的 CSV 行解析:只切片,不 Substring
static int ParseFirstInt(ReadOnlySpan<char> line)
{
    int comma = line.IndexOf(',');
    var first = comma < 0 ? line : line.Slice(0, comma);
    return int.Parse(first);                      // netstandard2.1 提供 ReadOnlySpan<char> 重载
}

// 需要跨 await 时用 Memory<T>
async Task WriteAsync(Stream s, Memory<byte> data)
{
    await s.WriteAsync(data);                     // 内部再 .Span 访问
}
```

- `Memory<T>` 内部是 `object _object; int _index; int _length`,其中 `_object` 可以是数组、字符串或 `MemoryManager<T>`。`Memory<T>.Span` 在需要时才取 `Span`。
- 需要自己管理生命周期的内存(池化、原生内存)实现 `MemoryManager<T>` 或 `IMemoryOwner<T>`。
- `Span<T>` 对引用类型数组有协变检查:`Span<object> s = stringArr;` 会在运行时抛 `ArrayTypeMismatchException`,因为 Span 构造时要求数组的实际元素类型与 `T` 完全一致,否则通过它写入会破坏类型安全。对值类型数组没有这个问题。
- JIT 对 `Span<T>` 的索引、遍历有内建优化(索引器是 intrinsic,`for (i < span.Length)` 能消除边界检查)。

## Unity 中的可用范围

- Unity 6000.2 手册:C# 语言版本为 C# 9.0,支持 `ref struct`(7.2)、`stackalloc` 到 `Span`(7.2)、`ref` 返回与局部(7.x)。
- `Span<T>`/`ReadOnlySpan<T>`/`Memory<T>` 等类型来自类库,需要 API Compatibility Level 设为 .NET Standard 2.1;早于该版本的 Unity 可以通过 `System.Memory` 包引入,行为有差异。起始版本待核实。
- 与 NativeArray 互通:`new Span<T>(NativeArrayUnsafeUtility.GetUnsafePtr(array), array.Length)`(`T` 需为不含引用的类型)。注意这条路径绕过了 NativeContainer 的安全系统:Job 读写冲突检查、已释放检查在 Span 上失效,`Dispose` 之后继续访问是悬垂指针。新版 Collections 包提供更安全的转换(例如 `AsSpan`),具体可用版本待核实。
- Burst 对 `Span<T>` 的支持有限,按所装 Burst 版本的手册为准。Job 里更常用的是 `NativeSlice<T>`、`NativeArray<T>.GetSubArray`、`UnsafeList<T>`。
- Unity 的 `List<T>`、`Array` 没有 .NET 5+ 的 `CollectionsMarshal.AsSpan`,从 `List<T>` 取 Span 需要拷贝或借助反射/包装。需要零拷贝时优先用数组或自己的池化容器。

## 常见坑

- 把 `stackalloc` 放进循环,或者分配不定长且不设阈值,造成栈溢出。
- 在 Unity 里默认认为 `stackalloc` 不清零,把"未初始化"当优化依据。
- 用 `Span` 包装 NativeArray 后忘记它绕过了安全检查。
- 把 `Span` 局部变量带进 `async`/迭代器方法,得到编译错误,解决办法是拆成同步的 helper 方法并在其中使用 Span,或改用 `Memory<T>`。
- 把 `in` 参数配非 readonly struct,结果是编译器悄悄拷贝,性能反而更差。
- 以为 `Span<T>` 比数组一定快。小数据量下收益主要来自"避免分配",而不是访问速度;JIT 对数组的 `for` 循环同样能消除边界检查。

## 面试追问

1. **Span<T> 为什么必须是 ref struct?** 要点:内部是托管指针(byref)加长度,byref 只能活在栈上,不能进堆;如果放堆上还会有多线程下"新指针旧长度"的结构撕裂,破坏内存安全。
2. **ref struct 不能用在 async 方法里,为什么?** 要点:编译器把跨 await 的局部变量提升成状态机的字段,状态机会被装箱到堆;ref struct 不能存在堆上,故编译报错。可拆成同步辅助方法,或改用 Memory<T>。
3. **Span 和 Memory 的区别?** 要点:Span 栈上,指针加长度,限制多;Memory 可存字段、跨 await,内部是对象引用加偏移加长度,使用时通过 `.Span` 取视图。
4. **stackalloc 有什么风险?** 要点:栈大小有限且栈溢出不可捕获;循环里累加到方法返回才释放;默认清零(Unity 上无法 SkipLocalsInit);只适合小而短命的缓冲,大块用池或原生内存。
5. **`ref` 返回有什么限制?** 要点:不能返回局部变量引用;编译器做安全逃逸分析;大 struct 可用 `ref readonly` 避免拷贝;配 `in` 参数和 readonly struct 才能避免防御性拷贝。
6. **和 C++ 的 `std::span` 比有什么异同?** 要点:都是非拥有的指针加长度视图;C# 的 Span 带边界检查,且编译器通过 ref struct 规则在编译期阻止其逃逸出所指内存的生命周期,C++ 无此保证。

## 参考资料

- Microsoft Learn,Memory- and span-related types 与 Span<T> 用法指南:https://learn.microsoft.com/en-us/dotnet/standard/memory-and-spans/
- Microsoft Learn,ref struct 类型:https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/builtin-types/ref-struct
- Unity 手册,C# compiler and language version reference(6000.2):https://docs.unity3d.com/6000.2/Documentation/Manual/csharp-compiler.html
- Unity 手册,API compatibility levels:https://docs.unity3d.com/6000.0/Documentation/Manual/dotnet-profile-support.html
