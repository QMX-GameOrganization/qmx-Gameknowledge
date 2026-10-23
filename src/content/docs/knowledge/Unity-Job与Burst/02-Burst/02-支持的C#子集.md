---
title: "2.2 支持的 C# 子集（HPC#）"
description: 梳理 Burst 能编译与不能编译的 C# 写法、常见 BC 编译错误，以及把托管写法改成 HPC# 写法的套路，并对照本项目的密度函数对象树。
sidebar:
  order: 2
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x（本文参考 1.8.31 手册）为主线；本项目 Unity 7000.0.0a8 的 Burst 2.0.0 是转发壳包，语言子集的细节在该版本上是否有变化未逐条核对（待核实）。

## 要点

- HPC#（High Performance C#，高性能 C#）是 Burst 能编译的 C# 子集：核心规则是"没有托管对象、没有引用类型"。
- 能用：基元类型、`struct`、指针与 `unsafe`、`ref`/`in`/`out`、`fixed` 缓冲区、NativeContainer、泛型 struct、用泛型约束调用接口、`try/finally`、简单的 `throw`、`FixedString`。
- 不能用：`class`、托管数组、`string`、虚方法、委托/lambda/闭包、反射、装箱、可写静态字段、`try/catch`、LINQ、`async`。
- 改造的总方向：对象树 → 扁平 struct 数组；委托/虚调用 → `switch`、泛型 struct 或函数指针；`List<T>` → `NativeList<T>`。
- 本项目的 `IDensityFunction` 对象树用了 class、接口虚调用和 `Func` 委托，三项都不在子集内，不能直接进 Burst。

## 允许 / 不允许对照表

| 类别 | 允许 | 不允许 |
| --- | --- | --- |
| 基元类型 | `bool` `byte` `sbyte` `short` `ushort` `int` `uint` `long` `ulong` `float` `double` | `char`、`decimal`、`string`（手册列为不支持的内置类型） |
| 结构体 | `struct { public float x; public int y; }` | `class Node { ... }`（引用类型） |
| 数组 | `NativeArray<float>`、`float*`、`fixed float buf[16]`；`static readonly int[]` 的受限只读访问 | `float[] a = new float[8];`（托管数组）、多维数组 `float[,]` |
| 泛型 | `struct Sampler<T> where T : struct, IFn` 且调用处类型已知 | 对 `IEnumerable<T>` 约束的泛型参数做 `foreach`（手册列为边缘不支持） |
| 接口 | 通过泛型约束调用：`void Run<T>(T f) where T : struct, IFn { f.Do(); }` | 把接口当类型存放：`IFn f = ...; f.Do();`（虚调用 / 装箱） |
| 方法 | 静态方法、struct 实例方法、扩展方法、局部函数 | `virtual`/`override` 的类方法 |
| 参数 | `ref` `out` `in`（`in` 在手册的博客中有专门说明） | 以托管类型作参数 |
| 控制流 | `if` `else` `switch` `for` `while` `break` `continue` | `catch`、`await`、`yield` |
| 异常 | `try/finally`、`using`/`foreach` 的 `IDisposable` 模式、简单 `throw new ArgumentException("...")` | `try { } catch (Exception e) { }` |
| 字符串 | `FixedString128Bytes`、字符串字面量传给 `Debug.Log` | 字符串作字段 / 传给自定义方法、`string.Substring` 等 |
| 静态数据 | `static readonly` 常量字段（见 2.8 一章） | 可写 `static int counter;`（用 `SharedStatic<T>`） |
| 数学 | `System.Math` 的方法（`IEEERemainder` 仅在 API 兼容级别为 .NET Standard 2.1 时支持）、`Unity.Mathematics` | `UnityEngine.Random` 这类依赖引擎托管全局状态的 API（应改用 `Unity.Mathematics.Random`，待核实具体报错） |
| 其它 | `System.Threading.Interlocked`（目标地址要自然对齐）、`Volatile` 的非泛型 `Read`/`Write`、`Thread.MemoryBarrier`、`System.HashCode`（结果不保证与 Mono 一致） | 反射、LINQ、装箱到 `object`、`Enum.HasFlag`、泛型版 `Volatile.Read<T>`/`Write<T>`、`HashCode.Add<T>(T, IEqualityComparer<T>)` |

## 逐项展开

### 类型

- 内置类型：手册给出的支持清单是 `bool`、`byte`/`sbyte`、`double`、`float`、`int`/`uint`、`long`/`ulong`、`short`/`ushort`。
- 结构体：普通 struct 以及含 `fixed` 数组字段的 struct 都支持。布局支持 `LayoutKind.Sequential`、`LayoutKind.Explicit`、`Pack`、`Size`；`Explicit` 布局可能生成非最优的原生代码。`LayoutKind.Auto` 不支持，这也是 `ValueTuple` 不能跨越托管与 Burst 边界的原因。
- 枚举：支持，包括指定底层类型如 `enum E : short`。`Enum` 的方法（如 `HasFlag`）不支持。
- 指针：支持任何指向受支持类型的指针。
- 向量：`Unity.Mathematics` 的 `bool2/3/4`、`uint2/3/4`、`int2/3/4`、`float2/3/4` 有一等公民优化；手册建议优先用 4 宽的类型。
- `Span<T>`/`ReadOnlySpan<T>`：在支持它们的编辑器中可用，但只能在 Job 或函数指针内部使用，不能出现在托管与 Burst 的接口上。

### 异常与 `try/finally`

- Burst 支持 `try`/`finally`，但行为与 .NET 不同：Burst 里抛出异常时，表现得像不存在 `finally` 块。
- 只支持简单的 `throw` 模式，如 `throw new ArgumentException("Invalid argument")`，Burst 会提取静态消息字符串。
- 编辑器里抛出的异常能被托管代码捕获并在 Console 报告；Player 构建中任何异常都会让应用 abort。所以异常只该用于"不该发生"的情况。
- 若在没有 `[Conditional("ENABLE_UNITY_COLLECTIONS_CHECKS")]` 保护的方法里 `throw`，Burst 发出警告 `BC1370`。有意崩溃时可用 `[IgnoreWarning(1370)]` 压制。

### 字符串与 `Debug.Log`

- 手册允许的字符串用法：`Debug.Log`/`LogWarning`/`LogError`、赋给 `Unity.Collections` 的 `FixedString` 系列，以及 `[CallerLineNumber]` 等特性（只能直接传给 `Debug.Log`）。
- 字符串必须是字面量，或字面量格式串的插值字符串 / `string.Format`；插值参数只能是内置值类型和 `Unity.Mathematics` 向量（`half` 向量除外）。
- 要传递或存储字符串，用 `FixedString128Bytes` 之类。

```csharp
using Unity.Burst;
using Unity.Collections;
using UnityEngine;

[BurstCompile]
public static class LogDemo
{
    [BurstCompile]
    public static void Log(int value)
    {
        Debug.Log($"value = {value}");            // 允许：字面量插值
        FixedString128Bytes text = $"v={value}";  // 允许：赋给 FixedString
        Print(text);
    }

    private static void Print(in FixedString128Bytes s) => Debug.Log(s);
}
```

### 静态字段

- 只支持 `static readonly`，Burst 在编译期求值静态字段与静态构造函数；非只读静态字段在 Burst 编译的 struct 中会导致编译错误。
- 对只读数组有有限支持（`static readonly int[] T = { 1, 2, 3 };`），限制：只能直接使用，不能当参数传递；不支持多维数组；用不支持的静态构造函数会得到 `BC1361`。
- 需要可写的共享静态数据时用 `SharedStatic<T>`（本章不展开）。

### `System` 命名空间的支持范围

手册（C#/.NET System namespace support）把 `System` 命名空间里的支持按类型列出，Burst 把它们转换成自己的兼容版本：

- `System.Math`：支持 `Math` 声明的所有方法，唯一例外是 `IEEERemainder(double, double)`，只有 API 兼容级别设成 .NET Standard 2.1 时才支持。
- `System.IntPtr` 与 `System.UIntPtr`：所有方法都支持，包括静态字段 `IntPtr.Zero` 和 `IntPtr.Size`。
- `System.Threading.Thread`：支持 `MemoryBarrier`。
- `System.Threading.Interlocked` 与 `System.Threading.Volatile`：见下面两小节。
- `System.HashCode`：见下面一小节。

#### `Interlocked` 的自然对齐要求

Burst 为 `System.Threading.Interlocked` 的所有方法（例如 `Interlocked.Increment`）提供原子内存指令。手册特别提醒：要保证 `Interlocked` 操作的目标地址是自然对齐（naturally aligned）的，也就是指针地址是被指向类型大小的整数倍。

手册给出的反例是 `LayoutKind.Explicit` 的结构体：

```csharp
using System.Runtime.InteropServices;
using System.Threading;

[StructLayout(LayoutKind.Explicit)]
struct Foo
{
    [FieldOffset(0)] public long a;
    [FieldOffset(5)] public long b;   // 偏移 5：不是 8 的倍数，没有自然对齐

    public long AtomicReadAndAdd()
    {
        return Interlocked.Read(ref a) + Interlocked.Read(ref b);
    }
}
```

手册的说明：如果指向 `Foo` 的指针对齐到 8（`long` 的自然对齐），`a` 位于自然对齐的地址上，`Interlocked.Read` 可以成功；`b` 的偏移是 5，没有自然对齐，对 `b` 的加载会产生未定义行为（undefined behavior）。所以：

- 不要在 `LayoutKind.Explicit` 里把会被原子操作的字段放在错位的偏移上。
- 对原始指针做原子操作时，先确认地址对齐，别把一块字节缓冲区里任意偏移当成 `long*` 去 `Interlocked`。
- 未定义行为不会报错，可能只在某些 CPU 或优化级别下出错，所以这类写法即使"在我机器上能跑"也不能算正确。

对体素生成而言，常见的原子用途是多个 Job 线程往同一个计数器里累加（例如统计区块里的方块数或网格顶点数）。计数器用普通的 `int` 或 `long` 字段（默认的顺序布局），不要为它写 `Explicit` 偏移，就不会触到这个陷阱。`NativeArray<T>` 首地址的对齐保证没有在手册里核实到（见 2.4 SIMD 与自动向量化 的对齐小节，待核实），做原子操作前不要想当然。

#### `Volatile` 只支持非泛型版本

手册写明：Burst 支持 `System.Threading.Volatile` 提供的 `Read` 与 `Write` 的非泛型（non-generic）变体，没有说支持泛型版本（`Volatile.Read<T>(ref T)` 一类），所以不要在 Burst 代码里用泛型形式。具体有哪些非泛型重载（`int`、`long` 等），手册没有逐个列出，用之前到 .NET 文档确认某个类型有对应重载（待核实）。

#### `System.HashCode`：结果与 Mono 不保证一致

手册写明：Burst 支持 `HashCode` 的所有方法，除了 `HashCode.Add<T>(T, IEqualityComparer<T>)`。同时手册特别说明：Burst 不保证结果与 .NET 实现兼容，所以 `HashCode` 的函数在 Burst 里运行与在其它运行环境（例如 Mono）里运行，可能产生不同的结果。

这对种子可复现的世界是个陷阱：同一份代码，托管路径和 Burst 路径得到不同的哈希，生成的地形就可能不同。需要稳定哈希时，自己写整数哈希，或用 `math.hash`，并加 golden test。完整的讨论见 2.6 浮点模式与确定性 的"不要用 `System.HashCode` 派生种子"一节。

## 常见编译错误

Burst 的错误以 `BC` 加四位数字出现在 Console。下面只列有来源可查的几个；措辞可能随版本微调，以你看到的为准。

| 编号 | 含义 | 典型触发 | 怎么改 |
| --- | --- | --- | --- |
| `BC1016` | 调用了托管函数，不被支持（社区报错常见形如 "Managed function `System.String.get_Length` is not supported"） | 在 Burst 代码里调用 string 方法、访问托管对象或 `World` 之类的类 | 把托管调用移出 Burst 路径，改用 unmanaged 数据 |
| `BC1042` | 托管 class 类型不被支持；读取非 readonly 静态字段时也会报这个码 | 如 `The managed class type X is not supported. Loading from a non-readonly static field Y is not supported`（社区 issue 里的报错原文） | 把 class 改成 struct，或把数据放进 NativeContainer；静态数据改成 `static readonly` 或 `SharedStatic<T>` |
| `BC1361` | 静态构造函数 / 静态只读数组初始化不被支持 | 用了 Burst 无法在编译期求值的静态构造 | 简化成数组初始化器，或把数据传入 Job 字段 |
| `BC1370` | 警告：`throw` 所在方法没有 `[Conditional("ENABLE_UNITY_COLLECTIONS_CHECKS")]` 保护 | 在 Burst 方法里随手 `throw` | 放进带该特性的检查方法，或有意崩溃时 `[IgnoreWarning(1370)]` |
| `BC1371` | 警告：对 `[BurstDiscard]` 方法的调用（及其实参里的调用）被丢弃 | 把有计算的结果只传给 `[BurstDiscard]` 方法 | 保证变量有其它用途，或在丢弃方法上加 `[IgnoreWarning(1371)]` |
| `BC1321` | 循环没有被向量化，但用 `Loop.ExpectVectorized` 声明了期望 | 循环里加了 `break` 等控制流 | 见 2.4 一章 |

另外手册提到一类错误文本：对泛型集合参数 `T : IEnumerable<U>` 做 `foreach` 时，会报"Can't call the method ... on the generic interface object type ..."。解决办法是用具体容器类型（如 `NativeArray<int>`）作参数。

`BC1016`、`BC1042` 的措辞来自社区报错与 issue，官方手册没有收录这两个编号的专页；`BC1361`、`BC1370`、`BC1371`、`BC1321` 来自官方手册。其它编号这里不列，避免写错。

## 改写：托管写法 → HPC# 写法

### 对象树 → 扁平数组

```csharp
// 托管写法：每个节点是 class，靠引用相连
public abstract class Node { public abstract float Eval(float x); }
public sealed class Add : Node
{
    public Node L, R;
    public override float Eval(float x) => L.Eval(x) + R.Eval(x);
}
```

HPC# 写法：节点是 struct，放在 `NativeArray` 里，用整数下标代替引用，用 `switch` 代替虚调用。

```csharp
using Unity.Collections;

public enum Op : byte { Const, X, Add, Mul }

public struct FlatNode
{
    public Op Op;
    public int Left;     // 子节点下标，-1 表示无
    public int Right;
    public float Value;  // Const 用
}

public static class FlatEval
{
    // 简单的递归求值；递归深度大时可改成显式栈（待按需测试）
    public static float Eval(in NativeArray<FlatNode> nodes, int i, float x)
    {
        FlatNode n = nodes[i];
        switch (n.Op)
        {
            case Op.Const: return n.Value;
            case Op.X:     return x;
            case Op.Add:   return Eval(nodes, n.Left, x) + Eval(nodes, n.Right, x);
            case Op.Mul:   return Eval(nodes, n.Left, x) * Eval(nodes, n.Right, x);
            default:       return 0f;
        }
    }
}
```

递归在 Burst 中是否总能被良好优化没有在手册中核实，对性能敏感时应改成后序遍历 + 预分配的值栈。

### 委托 → 泛型 struct

委托（`Func<>`）是引用类型。需要"可替换的运算"时，用泛型 struct 实现接口，Burst 会为每个具体类型生成特化代码并可内联：

```csharp
public interface IUnaryOp { float Apply(float v); }

public struct Square : IUnaryOp { public float Apply(float v) => v * v; }
public struct Negate : IUnaryOp { public float Apply(float v) => -v; }

public static class Ops
{
    public static float Run<T>(T op, float v) where T : struct, IUnaryOp
        => op.Apply(v);                 // 约束调用，不是虚调用
}
// 用法：Ops.Run(new Square(), 3f);
```

运行时才决定的操作，则用 `switch` 枚举，或函数指针（`FunctionPointer<T>`，后续章节讲）。

### `List<T>` → `NativeList<T>`

```csharp
using Unity.Collections;
using Unity.Jobs;
using Unity.Burst;

[BurstCompile]
struct CollectJob : IJob
{
    public NativeList<int> Output;   // 替代 List<int>
    public void Execute()
    {
        for (int i = 0; i < 10; i++) Output.Add(i);
    }
}
```

`Dictionary<K,V>` 同理改 `NativeHashMap<K,V>`，托管 `string` 键改 `FixedString`。`NativeList` 等的完整说明属于集合章节。

## 条件编译与 `[BurstDiscard]`

- `[BurstDiscard]` 让某个方法在 Burst 下被整个丢弃，只在托管下执行；方法不能有返回值。适合 Burst 做不到的日志、调试检查。
- 条件编译符号：手册（本次读过的页面）没有给出 Burst 专用的条件编译符号清单，本资料不依赖这类符号（`ENABLE_BURST_AOT` 之类的名字待核实）。隔离仅托管代码时优先使用 `[BurstDiscard]`。
- 用 `Unity.Burst.BurstCompiler.IsEnabled` 在静态只读初始化里判断（手册列为静态只读字段中支持的有限内联函数之一）。

## 本项目对照：为什么现有密度函数不能直接进 Burst

先读 `Assets/Scripts/WorldGen/Density/` 下的真实代码：

```csharp
// IDensityFunction.cs
public interface IDensityFunction
{
    double Sample(in DensityContext context);
}

// UnaryFunction.cs
internal sealed class UnaryFunction : IDensityFunction
{
    private readonly IDensityFunction input;
    private readonly Func<double, double> operation;
    public double Sample(in DensityContext context) => operation(input.Sample(context));
}

// BinaryFunction.cs
internal sealed class BinaryFunction : IDensityFunction
{
    private readonly IDensityFunction left;
    private readonly IDensityFunction right;
    private readonly Func<double, double, double> operation;
    public double Sample(in DensityContext context)
        => operation(left.Sample(context), right.Sample(context));
}
```

逐条对应到子集规则：

1. `sealed class`：`UnaryFunction`、`BinaryFunction` 都是引用类型，Burst 不能持有它们（对应 `BC1042` 一类错误）。
2. 字段是接口类型（`IDensityFunction input/left/right`）：把接口当字段类型存放，运行时调用 `input.Sample(...)` 是接口虚调用，不是"泛型约束调用"，HPC# 不支持。
3. 字段是 `Func<double, double>`、`Func<double, double, double>` 委托：委托是引用类型且调用是间接调用；lambda 还可能带闭包。
4. 构造函数里的 `?? throw new ArgumentNullException(nameof(...))`：这部分属于构造期的托管逻辑，进不了 Burst，需要放在 Job 之外。
5. 整棵树以引用相连，天然是托管对象图，不能作为 Job 字段；Job 字段只能是 unmanaged 值和 NativeContainer。

可以保留的部分：`Sample(in DensityContext context)` 的 `in` 参数和 `double` 运算本身是 HPC# 允许的；`DensityContext` 是只含三个 `int` 字段（`X`、`Y`、`Z`）的 `readonly struct`，可以直接作为值传入 Burst 代码。具体怎样把这棵树压平成 `NativeArray` 节点加 `switch`，在 3.2 一章讲，本章只描述原因。

## 常见坑

- 以为只要加了 `[BurstCompile]` 就行：对包含 class/委托的 Job，要么编译报错，要么 Job 根本没法声明那些字段。
- 在 Job 里用 `string` 做日志拼接：只能字面量插值，否则用 `FixedString`。
- 指望 `try/catch`：Burst 不支持 `catch`；错误处理要靠返回码或 `NativeReference<bool>` 之类的输出字段。
- 把可写静态变量当全局状态：编译错误，改用 `SharedStatic<T>` 或把状态放进 Job 数据。
- `throw` 当作流程控制：Player 里会直接 abort。
- 用 `System.HashCode` 派生种子：Burst 与 Mono 的结果可能不同，会破坏可复现性。
- `Interlocked` 用在 `Explicit` 布局里错位的字段上：未定义行为。
- 在 Burst 里用泛型版 `Volatile.Read<T>`：手册只写了非泛型版本受支持。

## 小结

- HPC# 的底线是"全程 unmanaged"：struct、指针、NativeContainer，没有 class、委托、托管数组。
- 异常只有 `try/finally` 和简单 `throw`，没有 `catch`。
- 改造套路：对象树 → 扁平数组 + `switch`；委托 → 泛型 struct / 函数指针；`List<T>` → `NativeList<T>`。
- 本项目的 `UnaryFunction`/`BinaryFunction` 同时踩中 class、接口字段虚调用、`Func` 委托三项，需要重构后才能进 Burst。

## 自测题

1. 下列哪些在 Burst 中不能用：`class`、`float*`、`string` 字段、`NativeArray<int>`、`Func<int,int>`？
   答：`class`、`string` 字段、`Func<int,int>` 不能用；`float*` 和 `NativeArray<int>` 可以。
2. `try { } catch { }` 与 `try { } finally { }` 在 Burst 中的支持情况？
   答：`catch` 不支持；`try/finally` 支持，但抛异常时表现得像没有 `finally`。
3. 为什么 `IDensityFunction input; input.Sample(ctx)` 不行，而 `void Run<T>(T f) where T : struct, IFn` 可以？
   答：前者是接口虚调用且字段是引用；后者在调用处类型已知，Burst 能特化为直接调用。
4. 想在 Burst 里用可变的全局计数器该怎么办？
   答：不能用可写静态字段；用 `SharedStatic<T>`，或把计数器放进 Job 的 NativeContainer 字段。
5. `BC1370` 是什么，什么时候出现？
   答：警告：在没有 `[Conditional("ENABLE_UNITY_COLLECTIONS_CHECKS")]` 保护的方法里 `throw`，因为 Player 里异常会导致 abort。
6. `Interlocked.Read(ref b)` 中 `b` 是 `Explicit` 布局里偏移为 5 的 `long`，会怎样？为什么 `System.HashCode` 不适合派生世界种子？
   答：`b` 没有自然对齐（8 的倍数），对它的原子加载是未定义行为；`HashCode` 在 Burst 下与 Mono 下的结果不保证一致，同一个种子可能生成不同地形。

## 参考

- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-language-support.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-hpc-overview.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-type-support.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-string-support.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-system-support.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-static-read-only-support.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/compilation-warnings.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/compilation-burstdiscard.html
- https://discussions.unity.com/t/exception-burst-error-bc1016-caused-by-state-world-createsystem-t/926734
- https://issuetracker.unity.com/issues/4015/burst-error-bc1042-the-managed-class-type-systemintptr-is-not-supported-error-is-thrown-when-calling-overlapspherecommandschedulebatch
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Density\IDensityFunction.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Density\UnaryFunction.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Density\BinaryFunction.cs
