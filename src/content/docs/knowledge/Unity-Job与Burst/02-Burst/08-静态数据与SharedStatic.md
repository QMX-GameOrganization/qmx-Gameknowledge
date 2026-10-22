---
title: "2.8 静态数据与 SharedStatic"
description: 说明 Burst 对 static 字段的限制，static readonly 数组与 SharedStatic 的用法，以及把大表放进 NativeArray 传给 Job 的模式。
sidebar:
  order: 8
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x / Collections 2.x 为主线（本章取自 Burst 1.8.31 手册 "Static read-only fields" 与 "SharedStatic struct"、"C#/.NET type support"）；本项目 Unity 7000.0.0a8 的 Burst 2.0.0 是转发壳包，`TypeForwarders.cs` 确认 `Unity.Burst.SharedStatic<>` 仍被转发。Burst 2.0 对静态数据支持有无变化，待核实。

## 要点

- Burst 里不能有可写的静态字段：非 `readonly` 的 `static` 字段在被 Burst 编译的结构体里会导致编译错误。
- 只读静态数据可以用：`static readonly` 基元、`const`、枚举，以及有限条件下的 `static readonly` 托管数组。
- 需要"C# 与 Burst 共享的可变静态数据"，用 `SharedStatic<T>`，初始化和线程安全由使用者负责。
- 噪声排列表、样条控制点这类较大的数据，最通用的做法是放进 `NativeArray`，作为 Job 字段传入，加 `[ReadOnly]` 共享。
- 编辑器里关闭域重载（Enter Play Mode 选项）时静态数据会残留，初始化要写成可重复执行。

## Burst 对 static 的限制

手册的描述：Burst 在编译期计算所有静态字段与静态构造函数，并且对同一个结构体的静态字段和构造函数一起计算。

- 只支持 `readonly` 的静态字段；非只读的静态字段会编译报错。
- 任何一个静态字段或静态构造函数在编译期求值失败，该结构体的全部静态字段与构造函数都失败。
- 编译期求值失败时，Burst 退而把所有静态初始化代码编译成一个在运行时调用一次的初始化函数。这意味着静态初始化代码本身也必须是 Burst 兼容的，否则编译失败。
- 静态构造函数里不支持调用外部函数和函数指针；允许托管数组、字符串、有限的内置函数（`BurstCompiler.IsEnabled`、`BurstRuntime.GetHashCode32/64`、向量类型构造）、有限的断言（`UnityEngine.Debug.Assert`、`NUnit.Framework.Assert.AreEqual/AreNotEqual`）以及简单的 `throw`（求值时抛出会变成编译错误）。

## 只读静态数据的几种形式

### 基元、const 与枚举

```csharp
using Unity.Burst;

[BurstCompile]
public struct Params
{
    public const int ChunkSize = 16;                 // 编译期常量，直接内联
    public static readonly float Scale = 0.01f;      // 只读静态基元，编译期求值
    public enum Biome : byte { Plains, Forest, Desert }   // 枚举可用，但 Enum 的方法（如 HasFlag）不支持
}
```

`const` 与 `static readonly` 基元最稳妥，会被常量折叠。

### static readonly 数组

手册给出的示例：

```csharp
[BurstCompile]
public struct MyJob : IJob
{
    private static readonly int[] _preComputeTable = new int[] { 1, 2, 3, 4 };

    public int Index { get; set; }

    public void Execute()
    {
        int x = _preComputeTable[0];
        int z = _preComputeTable[Index];
    }
}
```

条件与限制（手册）：

- 只能直接使用这个只读静态数组，不能把它当参数传来传去；
- 非 Job 的 C# 代码不应该修改它的元素，因为 Burst 在编译时拷贝了一份只读数据；
- 不支持多维数组；
- 初始化形式只有有限支持：数组初始化器 `{ 1, 2, 3 }` 或 `new int[10]`；
- 静态构造函数不被支持时报错 `BC1361`。

关于数组大小的上限、是否随表变大而显著拖慢编译：手册没有给出数字，待核实。Burst 更新日志里有一条 "Fixed BC1361 error when trying to compile large static readonly arrays"，说明过去超大数组确实触发过 `BC1361`，后续版本已修复。表很大（几千项以上）时更稳妥的做法是 NativeArray（见下文）。

### ReadOnlySpan<byte> 静态数据技巧

C# 里 `static ReadOnlySpan<byte> Table => new byte[] { ... };` 会被编译器放进程序集的只读数据段，零分配。手册说明 Burst 在支持 `Span<T>` 的编辑器版本里支持 `Span<T>` 与 `ReadOnlySpan<T>`，但只能在 Job 或函数指针内部使用，不能跨越 Burst 边界传递。这个"属性表达式绑定常量数据"的写法在 Burst 里是否能被识别成静态数据，本文未能核实，待核实；不要在没有在 Inspector 与测试里验证过之前依赖它。

## SharedStatic<T>

需要一个 C# 和 Burst 代码都能读写的静态变量，用 `SharedStatic<T>`（`Unity.Burst`）。手册示例：

```csharp
using Unity.Burst;

public abstract class MutableStaticTest
{
    public static readonly SharedStatic<int> IntField =
        SharedStatic<int>.GetOrCreate<MutableStaticTest, IntFieldKey>();

    // 用来标识这个字段的 key 类型
    private class IntFieldKey { }
}

// C# 或 Burst 里都可以
MutableStaticTest.IntField.Data = 5;
var value = 1 + MutableStaticTest.IntField.Data;
```

要点：

- `T` 是数据类型，API 页的约束是 `where T : struct` 且不能含引用类型（即必须是 Burst 支持的非托管数据）。
- 上下文类型参数用来唯一标识这个静态字段。1.8.31 的 API 页列出的重载有：`GetOrCreate<TContext>(uint alignment = 0)`（单类型参数）、`GetOrCreate<TContext, TSubContext>(uint alignment = 0)`（双类型参数，手册示例用的就是这个）、以及基于反射的 `GetOrCreate(Type, uint)` 和 `GetOrCreate(Type, Type, uint)`；API 页说明 `GetOrCreate(Type, uint)` 只能在 C# 中使用，不能在 HPC# 中使用。此外还有 `GetOrCreateUnsafe` 等带 hash 的底层重载，一般用不到。手册示例的做法是第一个参数用包含它的类型，第二个参数用一个专属的 key 类。这些签名取自 1.8.31，Burst 2.0.0 壳包里 `SharedStatic<>` 已确认被转发，但重载是否有变化未核对。
- 取到的是指向静态存储的句柄，通过 `.Data` 读写。因为是 `static readonly` 字段，句柄本身不变，Burst 可以编译期解析它。
- 手册要求：务必先在 C# 里从静态构造函数初始化，再在 Burst 里访问，否则初始化状态未定义。
- 线程安全完全由使用者负责。多个 Job 线程同时写 `.Data` 是数据竞争；`SharedStatic` 不提供锁。

适合放：全局开关、计数器（配合 `Interlocked`）、指向长期数据的指针。不适合放：每帧都变且被多线程写的数据。

## 把大表放进 NativeArray

最常用的模式是：不做静态，而是作为 Job 字段传入。

```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;

[BurstCompile]
struct NoiseJob : IJobParallelFor
{
    [ReadOnly] public NativeArray<byte> Perm;     // 512 项的排列表，多个 Job 共享只读
    [WriteOnly] public NativeArray<float> Output;

    public void Execute(int i) { /* 用 Perm[...] 查表 */ }
}
```

好处：数据可由运行时生成（依赖种子）、可以任意大、安全系统保证只读共享。`[ReadOnly]` 允许多个 Job 同时读同一块数据而不触发依赖冲突。生命周期自己管：用 `Allocator.Persistent` 分配的表，在世界卸载时 `Dispose`。

BlobAsset 是 ECS（Entities）里的只读数据格式，本项目不使用 Entities，这里只提一句。

## 示例：Perlin 排列表的三种放法

| 放法 | 写法 | 优点 | 缺点 |
| --- | --- | --- | --- |
| 1. `static readonly byte[]` | 在 Job 结构体里写 256 项（或 512 项）常量数组 | 无需管理生命周期，代码最简单 | 内容固定，不能随种子变；编译期求值，表大了编译变慢（待核实上限）；只能在 Burst 代码里直接索引，不能当参数传 |
| 2. `NativeArray<byte>` 字段 | 初始化时用种子洗牌生成，作为 `[ReadOnly]` 字段传入 | 可随种子变化，表任意大，安全系统保护 | 要 `Dispose`；每个 Job 都要传 |
| 3. `SharedStatic<IntPtr>` 指向表 | 持久分配后，把指针存进 `SharedStatic`，Burst 里随处可读 | 不必在每个 Job 里传字段，全局可见 | 绕开安全系统，指针悬空风险大，生命周期和域重载都要自己管，不推荐 |

建议：固定经典排列表用放法 1；依赖种子的用放法 2；放法 3 仅在传参实在不便（如函数指针里需要访问全局表）时再考虑。完全不要表也是一个选项：用整数哈希直接得到格点值，本项目 `ValueNoiseFunction.Lattice` 就是这样做的。

## 初始化与生命周期

- 默认情况下，脚本重载（Domain Reload）会重置所有静态字段，`SharedStatic` 也随之重建，静态构造函数重新执行。
- 开启 `Project Settings > Editor > Enter Play Mode Options` 并关闭 Domain Reload 后，进入播放模式不再重置静态数据：`SharedStatic.Data` 会保留上一次运行的值，静态构造函数也不再重新执行。
- 对策：把初始化写成显式函数，在 `[RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]` 的静态方法里重新赋值与重置；持久分配的 `NativeArray` 在退出播放模式时释放（可订阅 `Application.quitting`，或用 `EditorApplication.playModeStateChanged`），避免泄漏和旧指针残留。

## 本项目对照：样条点数组

只讲思路，实现放在 3.2。相关文件在 `D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Density\`。

当前结构：

- `CubicSplinePoint`（`CubicSplinePoint.cs`）是 `readonly struct`，字段为 `double Location`、`double Value`、`IDensityFunction ValueFunction`、`double Derivative`。`ValueFunction` 是对象引用，用于嵌套样条：控制点的值由另一个密度函数求出。
- `CubicSplineFunction`（`CubicSplineFunction.cs`）持有 `IDensityFunction coordinate` 与 `CubicSplinePoint[] points`；构造时校验 `Location` 严格递增并 `Clone` 数组；`Sample` 里用 `FindSegment` 二分查段，再做 Hermite 插值，`EvaluateValue` 在 `ValueFunction == null` 时取 `Value`，否则递归调用 `ValueFunction.Sample`。

不能直接给 Job 用的原因：`IDensityFunction` 是托管接口引用，`CubicSplinePoint[]` 是托管数组，且结构体里含引用字段，不是 blittable。

改造思路：

1. 把数据与行为分开。控制点改成只含数值的非托管结构，例如 `Location`、`Value`、`Derivative` 三个 `double`，外加一个 `int` 表示"子节点索引"（`-1` 表示直接用 `Value`）。引用字段 `ValueFunction` 换成索引。
2. 所有样条的控制点拼成一个大的 `NativeArray<点结构>`，每条样条另用 `(start, length)` 描述它在数组里的区间。数组作为 `[ReadOnly]` 字段传给 Job，对应上文"把大表放进 NativeArray"的模式，而不是 `static readonly`，因为样条数据来自运行时配置。
3. 嵌套样条（`ValueFunction` 本身又是一个样条或其它节点）改为"节点图扁平化"：把整张密度函数图编成一个节点数组，按拓扑顺序存放，子节点用索引引用，求值时用 `switch` 或循环遍历（见 2.7 的方案对比）。
4. 构造时的校验（`Location` 严格递增、非空）留在托管侧的构建阶段完成，Job 里只做查找与插值。`FindSegment` 的二分查找和 Hermite 公式可以原样搬到静态方法里，用索引访问数组。
5. 浮点的确定性风险见 2.6：`Lerp` 形式的乘加在 `Strict` 下不应被融合，迁移后用同一组输入对比 Mono 与 Burst 的逐位哈希。

## 常见坑

- 在 Job 结构体里写非 `readonly` 的 `static` 字段，编译报错。
- 把 `static readonly` 数组当方法参数传，或写多维数组，Burst 不支持。
- 以为 `SharedStatic` 自带线程安全。
- 关闭域重载后 `SharedStatic` 保留了上次运行的值，或持久分配的内存没释放，下次运行读到旧指针。
- 用 `static readonly` 放一个依赖种子的表：静态初始化只执行一次，种子变了表也不会变。

## 小结

静态数据在 Burst 里只能是只读的：基元、`const`、枚举没问题，`static readonly` 数组在直接索引的前提下可用但有限制。要共享可变静态数据用 `SharedStatic<T>`，初始化与同步自己负责。较大或依赖运行时配置的表（排列表、样条点）作为 `[ReadOnly] NativeArray` 传给 Job 最稳妥。

## 自测题

1. Burst 里一个非 `readonly` 的 `static int` 字段会怎样？答：编译错误，Burst 只支持只读静态字段。
2. `static readonly int[]` 数组在 Burst 里使用时有哪些限制？答：只能直接使用不能当参数传；不支持多维；Job 外不应修改其元素；初始化形式有限。
3. `SharedStatic<T>` 的两个类型参数（上下文类型与 key 类型）起什么作用？答：共同标识并区分每一个共享静态字段。
4. 为什么依赖种子的噪声表适合用 `NativeArray` 而不是 `static readonly`？答：静态初始化只执行一次且在编译期求值，不能随种子变；`NativeArray` 在运行时生成。
5. 关闭域重载后，静态数据会出什么问题？答：静态字段与 `SharedStatic` 不会重置，静态构造函数不重跑，旧值或旧指针残留；需要用 `RuntimeInitializeOnLoadMethod` 重新初始化。

## 参考

- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-static-read-only-support.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-shared-static.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-type-support.html
- D:\UnityHub\Project\程序化生成\Library\PackageCache\com.unity.burst@626e66ab421b\Runtime\TypeForwarders.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Density\CubicSplinePoint.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Density\CubicSplineFunction.cs
