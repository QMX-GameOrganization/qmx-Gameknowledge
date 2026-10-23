---
title: "2.1 Burst 原理与启用方式"
description: 讲清 Burst 把 C# 编译成原生代码的流程、[BurstCompile] 的标记位置、编辑器 JIT 与 Player AOT 的区别，以及如何确认 Job 真的被 Burst 编译。
sidebar:
  order: 1
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x 为主线；本项目 Unity 7000.0.0a8 中的 Burst 2.0.0 是转发（shim）到引擎内置模块的壳包，API 仍在 `Unity.Burst` 命名空间。涉及版本差异处已注明，核实不了的标"待核实"。

## 要点

- Burst 是基于 LLVM 的编译器，把一个受限的 C# 子集（HPC#）的 IL 编译成针对目标 CPU 优化过的原生机器码。
- 它不是"让所有 C# 变快"，只处理你标记了 `[BurstCompile]` 的 Job、静态方法和函数指针，以及它们调用到的代码。
- 编辑器里是 JIT（Play 模式下首次用到时编译），Player 构建时是 AOT（构建时一次性编译成原生库随游戏发布）。
- 加了 `[BurstCompile]` 不等于一定生效：代码里有 Burst 不支持的写法会编译失败并回退到 Mono，必须验证。
- 对数值密集、数据连续的循环（体素密度采样、噪声、网格生成），Burst 通常能带来明显的提升，但具体倍数取决于代码、数据规模和硬件，需要自己测。

## 原理：从 IL 到机器码

Burst 的输入不是 C# 源码，而是 Unity 已经编译好的 .NET 中间语言（Intermediate Language，IL）。官方手册的描述是：Burst 使用 LLVM 把 IL 翻译成针对目标 CPU 架构优化的代码。

```
C# 源码
  │  Roslyn（Unity 脚本编译）
  ▼
.NET IL（程序集 .dll）
  │  Burst 前端（Front end）：方法发现 + IL → LLVM IR
  ▼
LLVM IR（未优化）
  │  Burst 中端（Middle end）：特化、内联、向量化等优化
  ▼
LLVM IR（已优化）
  │  Burst 后端（Back end）：生成目标代码
  ▼
原生机器码（x64 SSE/AVX、ARM NEON ...）
```

这四段划分与 Burst 菜单里 `Show Timings` 的输出分段一致：Method discovery、Front end、Middle end、Back end。手册说明前端与优化器的耗时与要编译的操作数量成线性关系，泛型越多前端越慢；后端耗时随入口点（entry point）数量增长，因为每个入口点是一个独立的目标文件。

Burst 能做激进优化，是因为 HPC# 子集排除了托管对象、垃圾回收和虚调用，且 Job 结构体里的 NativeContainer 之间不会别名（细节见 2.10 编译器提示与别名 一章）。

## 编辑器 JIT 与 Player AOT

| 场景 | 编译时机 | 说明 |
| --- | --- | --- |
| 编辑器 Play 模式 | JIT（即时编译） | 第一次调用被标记的代码时编译；默认异步 |
| Player 构建 | AOT（提前编译） | 构建时编译成原生库，随应用发布 |

手册（Burst compilation in Play mode）对两种 Play 模式编译方式的描述：

- 异步（Asynchronous，默认）：等待 Burst 编译完成期间，标记了 `[BurstCompile]` 的代码可以先作为托管（Mono）JIT 代码运行。
- 同步（Synchronous）：这部分代码只能跑 Burst 编译后的原生版本，应用要等编译完成。

这意味着刚进入 Play 模式的头几帧，你的 Job 可能还在跑慢速的托管版本，之后才无缝切换到原生版本。做性能测试要先预热（warm up）。

### 同步编译的开关

两种方式：

```csharp
// 只对这个 Job 同步编译（只影响 JIT，即编辑器）
[BurstCompile(CompileSynchronously = true)]
public struct MyJob : IJob
{
    public void Execute() { }
}
```

或在菜单 `Jobs > Burst > Synchronous Compilation` 全局打开。手册提醒同步编译会阻塞当前帧，造成卡顿，只建议用于：运行一次的长任务、需要测 Burst 代码的性能分析、对比托管与 Burst 行为差异。

## `[BurstCompile]` 标在哪里

手册（Marking code for Burst compilation）列出的可标记位置：

| 位置 | 写法要点 |
| --- | --- |
| Job（`IJob`、`IJobParallelFor` 等的 struct） | 标在 struct 上，Burst 编译其中所有内容 |
| 静态方法 | 方法和它所在的类型都要标 `[BurstCompile]` |
| 类 / 普通 struct | 仅当其中含有同样标记了的静态方法时才需要标；Burst 不编译类本身，只编译成员方法 |
| 函数指针 | 用 `BurstCompiler.CompileFunctionPointer` 获取，后续函数指针章节详述 |
| 程序集 | 程序集级 `[assembly: BurstCompile(...)]` 为整个程序集的 Job 和函数指针设置选项，与菜单、Job 上属性的优先级见 2.10 编译器提示与别名 末尾的小节 |

手册还强调：从托管代码切换到 Burst 代码的方法叫 Burst 入口点（entry point）。如果静态入口点方法标了 `[BurstCompile]`，它调用的其它方法即使没标也会被一起编译。

```csharp
using Unity.Burst;
using Unity.Mathematics;

[BurstCompile]                       // 类型要标
public static class DensityMath
{
    [BurstCompile]                   // 方法也要标
    public static float Smooth(float t) => t * t * (3f - 2f * t);
}
```

`[BurstCompile]` 还接受参数，常用的有：

- `FloatPrecision`（`Standard`/`High`/`Medium`/`Low`）和 `FloatMode`（`Default`/`Strict`/`Fast`/`Deterministic`），例如 `[BurstCompile(FloatPrecision.Medium, FloatMode.Fast)]`。`Fast` 允许重排浮点运算，`Deterministic` 追求跨平台一致（仅 64 位架构，见 2.6 浮点模式与确定性）。
- `CompileSynchronously`：见上文。
- `DisableSafetyChecks`：关闭 Burst 的容器安全检查代码。
- `Debug = true`：关闭该 Job 的优化并便于原生调试。
- `OptimizeFor = OptimizeFor.FastCompilation`：编译更快、优化更少。

这些选项的完整讨论放在后续的编译选项章节，这里只需知道它们存在。

## 从托管代码直接调用 Burst 静态方法

除了 Job，你还可以从普通托管代码（比如 `MonoBehaviour`）直接调用一个标了 `[BurstCompile]` 的静态方法，不必手写函数指针。手册（Calling Burst-compiled code）的描述是：可以直接从托管代码调用 Burst 编译的方法，规则与函数指针相同，但不需要函数指针那套额外的样板代码。

### 写法

方法和它所在的类型都要标 `[BurstCompile]`。手册示例：

```csharp
using Unity.Burst;
using Unity.Mathematics;

[BurstCompile]
public static class MyBurstUtilityClass
{
    [BurstCompile]
    public static void BurstCompiled_MultiplyAdd(in float4 mula, in float4 mulb, in float4 add, out float4 result)
    {
        result = mula * mulb + add;
    }
}

// 在 MonoBehaviour.Start 等托管代码里：
// MyBurstUtilityClass.BurstCompiled_MultiplyAdd(mula, mulb, add, out var result);
```

手册说明运行这个示例会在日志里打印 `float4(98f, 2f, -3f, 4f)`。这段调用在托管代码里看起来就是一次普通的静态方法调用。

### 原理：IL 后处理

手册写明：Burst 通过 IL 后处理（IL Post Processing）自动把这类调用改写成"函数指针加调用"。也就是说，托管代码调用这个静态方法时，实际走的是 Burst 编译出来的原生版本，而不是方法体本身的托管 IL。细节可对照 2.7 函数指针与间接调用 里的 `CompileFunctionPointer` 流程，两者共享同一套机制和限制。

### 限制

- 泛型方法不支持，声明方法的类型本身是泛型时也不支持。
- 其余规则与函数指针相同，所以参数和返回值类型受 `DllImport` 与内部调用同一套限制（见 2.7 函数指针与间接调用 的"DllImport 与内部调用允许的参数类型"）。
- 手册示例里的 `in` 与 `out`：手册说明因为用了结构体（`float4`），按函数指针的规则要通过引用传递。结构体不能按值传，所以示例用 `in` 传输入、`out` 传输出，而不是直接返回一个 `float4`。（单字段的句柄结构体是例外，见 2.7。）
- 因为经过一层原生互操作，函数体很小时调用开销可能抵消 Burst 的收益，2.7 里对此有说明；手册这一页没有给出具体数据。

### 用 `DisableDirectCall` 关闭改写

在 `[BurstCompile]` 上加 `DisableDirectCall = true`，后处理器就不再处理这个方法，托管代码调用它时走原来的托管版本：

```csharp
[BurstCompile]
public static class MyBurstUtilityClass
{
    [BurstCompile(DisableDirectCall = true)]
    public static void BurstCompiled_MultiplyAdd(in float4 mula, in float4 mulb, in float4 add, out float4 result)
    {
        result = mula * mulb + add;
    }
}
```

手册的原话是这会阻止后处理器在这段代码上运行，也就是托管调用不再被自动改写成 Burst 版本。典型用途是：想让某个方法在托管代码里保持托管行为（比如做 Burst 与托管结果对比，见 2.5 Burst Inspector 与调试），或者排查直接调用带来的问题。2.10 编译器提示与别名 的 `[BurstCompile]` 参数表里也有这一项。

本项目目前的 `Density` 代码不是 Burst 代码，这一节是为之后把采样函数迁到 Burst 后，从托管侧（例如一次性的初始化或测试）调用做准备。

## 菜单与设置

编辑器菜单位于 `Jobs > Burst`（Burst 1.8.31 手册 Burst menu reference）：

| 菜单项 | 作用 |
| --- | --- |
| `Enable Compilation` | 总开关。关闭后所有 `[BurstCompile]` 都走托管 |
| `Enable Safety Checks` | `Off` / `On`（默认）/ `Force On`。检查包括 Job 依赖和容器索引越界；`Off` 在重载编辑器后会重置为 `On` |
| `Synchronous Compilation` | 同步编译，见上文 |
| `Native Debug Mode Compilation` | 对所有 Burst 代码关闭优化，便于原生调试器 |
| `Show Timings` | 把 JIT 编译耗时输出到 Console |
| `Open Inspector` | 打开 Burst Inspector 窗口 |

这些设置只影响编辑器。Player 构建的 Burst 设置在 Project Settings 的 Burst AOT Settings 里（Edit > Project Settings > Burst AOT Settings），可选目标 CPU、是否开启优化、`Force Debug Information` 等，细节放在 2.11 一章。Player 构建的产物是 `lib_burst_generated` 原生库，通常出现在 `Plugins` 目录。

本项目所用的 Unity 7000.0.0a8 菜单位置与名称未逐项在该版本中核对（待核实），以 1.8.x/6000 文档为准。

## 如何确认 Job 真的被 Burst 编译了

按可靠程度从高到低：

1. Burst Inspector：`Jobs > Burst > Open Inspector`。左侧 Compile Targets 列出所有 Burst 可编译的目标；手册说明列表中灰掉（disabled）的项是没有 `[BurstCompile]` 的。选中后能看 Assembly、.NET IL、LLVM IR 等视图。能看到汇编，说明确实生成了原生代码。
2. 计时对比：同一份 Job 开/关 `Enable Compilation` 各跑一次（先预热）。对数值密集的 Job，差距通常很明显，具体幅度取决于代码。
3. 运行时探测：用 `[BurstDiscard]` 标记的方法只在托管下执行这一特性来探测。手册给出的写法：

```csharp
using Unity.Burst;

[BurstDiscard]
private static void SetIfManaged(ref bool b) => b = false;

private static bool IsBurst()
{
    var b = true;
    SetIfManaged(ref b);   // 在 Burst 下这个调用被丢弃，b 保持 true
    return b;
}
```

注意：`[BurstDiscard]` 方法不能有返回值，只能用 `ref`/`out` 参数回传。

4. `BurstCompiler.IsEnabled`：`Unity.Burst.BurstCompiler` 的静态属性，API 页描述为 "Gets a value indicating whether Burst is enabled"（`TypeForwarders.cs` 确认 `BurstCompiler` 类型存在）。它反映的是"开关"，不能证明某个具体 Job 编译成功。`BurstCompiler.Options`（`BurstCompilerOptions`）上还有 `EnableBurstCompilation`、`EnableBurstCompileSynchronously`、`EnableBurstSafetyChecks` 等可读写的编辑器期选项。
5. Profiler 中是否带 Burst 标识：待核实。

## 冷启动与首次编译延迟

- 编辑器 JIT：每个 Burst 入口点第一次用到时需要编译，异步模式下期间回退到托管。`Show Timings` 可以看每个库的编译耗时；耗时异常长时可对该入口点使用 `OptimizeFor.FastCompilation`，用优化程度换编译速度，需要自己对比性能。
- 修改脚本触发域重载后，Burst 需要重新编译受影响的代码。编辑器是否持久化缓存编译结果、缓存位置与失效规则，我没有在手册中核实到，标为待核实。
- Player 的 AOT 把编译成本移到构建阶段，运行时没有首次编译延迟，但构建时间会变长。

## Burst 版本与 Unity 版本

- Unity 6000.x 主线使用 Burst 1.8.x 包（本文参考的手册是 1.8.31）。
- 本项目 `Library/PackageCache` 中的 `com.unity.burst` 的 `package.json` 写着 `"version": "2.0.0"` 和 `"type": "shim"`，说明它是壳包；包内 Runtime 只有 `TypeForwarders.cs` 和 `Unity.Burst.asmdef`，前者用 `[assembly: TypeForwardedTo(...)]` 把类型转发到引擎内置实现。
- 转发的类型有：`Unity.Burst` 下的 `BurstCompileAttribute`、`BurstCompiler`、`BurstCompilerOptions`、`BurstExecutionEnvironment`、`BurstRuntime`、`FloatMode`、`FloatPrecision`、`OptimizeFor`、`IFunctionPointer`、`FunctionPointer<>`、`NoAliasAttribute`、`SharedStatic<>`；`Unity.Burst.CompilerServices` 下的 `Aliasing`、`AssumeRangeAttribute`、`Constant`、`Hint`、`IgnoreWarningAttribute`、`SkipLocalsInitAttribute`；以及 `Unity.Burst.Intrinsics` 下的 `v64`/`v128`/`v256`（其中 `v64`、`v128` 另有 `x2`/`x3`/`x4` 变体，`v256` 没有）、`Common`、`X86`、`Arm`。清单里没有 `BurstDiscardAttribute`，它在 7000.0.0a8 中的归属待核实。
- 所以你的代码仍写 `using Unity.Burst;`，不用改。区别只在包的实现和文档位置：Burst 文档迁到了 Unity Manual。
- 同理，本项目的 `com.unity.collections` 为 6.7.0，其 `package.json` 描述写明"现已移入引擎模块，只做转发"。Unity Mathematics 手册则说明：从 Unity 6.5 起 Mathematics 是核心编辑器和引擎的内置模块，`Unity.Mathematics` 命名空间默认可用。
- 在 7000.0.0a8 上，Burst 行为与 1.8.x 文档的细微差异无法逐条核对，遇到差异以实机为准（待核实）。

## 最小示例：加上 `[BurstCompile]` 前后

一个对数组求和的 Job：

```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;

// 前：没有 [BurstCompile]，在 Mono/IL2CPP 的托管代码里跑
public struct SumJobManaged : IJob
{
    [ReadOnly] public NativeArray<float> Input;
    public NativeArray<float> Result;

    public void Execute()
    {
        float sum = 0f;
        for (int i = 0; i < Input.Length; i++)
            sum += Input[i];
        Result[0] = sum;
    }
}

// 后：只多一行属性，其余代码完全相同
[BurstCompile]
public struct SumJobBurst : IJob
{
    [ReadOnly] public NativeArray<float> Input;
    public NativeArray<float> Result;

    public void Execute()
    {
        float sum = 0f;
        for (int i = 0; i < Input.Length; i++)
            sum += Input[i];
        Result[0] = sum;
    }
}
```

调度与计时：

```csharp
using System.Diagnostics;
using Unity.Collections;
using Unity.Jobs;

public static class SumBench
{
    public static void Run()
    {
        var input = new NativeArray<float>(1 << 20, Allocator.TempJob);
        var result = new NativeArray<float>(1, Allocator.TempJob);
        for (int i = 0; i < input.Length; i++) input[i] = 1f;

        // 预热一次，丢弃首次调用（可能包含 JIT 编译时间）
        new SumJobBurst { Input = input, Result = result }.Run();

        var sw = Stopwatch.StartNew();
        new SumJobBurst { Input = input, Result = result }.Run();
        sw.Stop();
        UnityEngine.Debug.Log($"Burst: {sw.Elapsed.TotalMilliseconds} ms");

        sw.Restart();
        new SumJobManaged { Input = input, Result = result }.Run();
        sw.Stop();
        UnityEngine.Debug.Log($"Managed: {sw.Elapsed.TotalMilliseconds} ms");

        input.Dispose();
        result.Dispose();
    }
}
```

要点：用 `.Run()` 在主线程同步执行便于对比；Burst 版本更快的可能原因包括去掉托管开销、优化器处理 `NativeArray` 索引，以及循环被向量化（具体原因要看 Inspector 里的汇编，不要预设）。这个归约循环（`sum += ...`）因为浮点加法顺序固定，默认 `FloatMode.Strict` 下不能被重排，所以向量化受限；2.4 一章会解释。

## 常见坑

- 只标了方法没标类型：静态方法 Burst 化需要方法与父类型都标。
- 误以为编译成功：Burst 遇到不支持的写法会报错（如 `BC1016`、`BC1042`，见下一章 HPC# 子集），Job 会静默回退或抛编译错误，要看 Console 和 Burst Inspector。
- 计时包含首次编译：异步 JIT 下首次调用可能走托管路径或包含编译时间，必须预热。
- 编辑器里开着 `Enable Safety Checks` 和 Jobs Debugger：性能数字会偏慢，不代表 Player 表现；要做更接近 Player 的测量，可临时设为 `Off`（手册也这么建议，重载编辑器后会自动恢复 `On`）。
- 只在编辑器验证：AOT 的 CPU 目标和编译选项不同，发布前要在 Player 里再测一次。
- 把 `[BurstDiscard]` 当成逻辑分支：它在 Burst 下整个调用被丢弃，不能返回值，只适合日志、断言、探测。

## 小结

- Burst = IL → LLVM IR → 优化 → 原生码；编辑器 JIT（默认异步，未完成前回退托管），Player AOT。
- `[BurstCompile]` 标 Job 结构体、静态方法加其类型，以及函数指针/程序集。
- 用 Burst Inspector、开关对比计时、`[BurstDiscard]` 探测来验证，不要凭感觉。
- Burst 2.0.0 在本项目是转发壳包，类型清单可在 `TypeForwarders.cs` 查到，命名空间不变。

## 自测题

1. 编辑器里异步 JIT 和同步编译有什么区别？分别什么时候选？
   答：异步下未编译完成前代码用托管版本运行，不阻塞帧；同步会等编译完成再执行，可能卡帧。同步适合性能剖析、对比行为差异、一次性长任务。
2. 一个静态方法要被 Burst 编译，`[BurstCompile]` 需要标在哪里？
   答：方法本身和它所在的类型（类或 struct）。
3. 怎样用代码判断当前是否在 Burst 下运行？
   答：写一个 `[BurstDiscard]` 方法用 `ref bool` 把标志置为 false，调用前先置 true；Burst 下调用被丢弃，标志保持 true。
4. 本项目的 `com.unity.burst` 2.0.0 里有什么？
   答：只有 `TypeForwarders.cs` 和 asmdef，`package.json` 标明 `type` 为 `shim`，把 `Unity.Burst` 等类型转发到引擎内置实现。
5. 为什么测性能要先预热？
   答：首次调用可能包含 JIT 编译时间，或仍在跑托管回退版本，会让数字失真。

## 参考

- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/index.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/compilation-burstcompile.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-calling-burst-code.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/compilation-synchronous.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/compilation-burstdiscard.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/editor-burst-menu.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/editor-burst-inspector.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/debugging-profiling-tools.html
- https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/manual/index.html
- D:\UnityHub\Project\程序化生成\Library\PackageCache\com.unity.burst@626e66ab421b\package.json
- D:\UnityHub\Project\程序化生成\Library\PackageCache\com.unity.burst@626e66ab421b\Runtime\TypeForwarders.cs
- D:\UnityHub\Project\程序化生成\Library\PackageCache\com.unity.collections@28abc463ca66\package.json
