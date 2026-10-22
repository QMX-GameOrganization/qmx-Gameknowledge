---
title: "2.5 Burst Inspector 与调试"
description: 用 Burst Inspector 读汇编、判断内联与向量化，并掌握原生调试、Debug.Log 限制与 Burst/Mono 结果对比的调试流程。
sidebar:
  order: 5
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x 为主线（本章界面与选项名取自 Burst 1.8.31 手册）；本项目 Unity 7000.0.0a8 中 Burst 2.0.0 是转发到引擎内置模块的壳包，类型仍在 `Unity.Burst` 命名空间，菜单与选项名是否有变化待核实。

## 要点

- 菜单路径：`Jobs > Burst > Open Inspector`。它列出所有 Burst 可编译目标，并展示 .NET IL、LLVM IR 与最终汇编。
- 判断"有没有被 Burst 编译、有没有向量化、有没有内联"，最快的办法是读 Inspector 里的汇编，而不是猜。
- 调试 Burst 代码有两条路：挂托管调试器（下断点时 Burst 对该代码路径自动关闭），或关优化后挂原生调试器。
- Burst 里的字符串只支持字面量、插值字面量和 `FixedString`，`Debug.Log` 是唯一能直接接收托管 `string` 的调用。
- 对比"Burst 结果"与"托管结果"是最可靠的正确性验证，但要注意浮点差异（见 2.6）。

## Burst Inspector 界面

### 打开方式与左侧列表

在菜单中选 `Jobs > Burst > Open Inspector`。窗口左侧是 Compile Targets 面板，按字母序列出项目里 Burst 能编译的 Job 与静态方法目标：

- 默认隐藏 Unity 命名空间下的目标，以及名字里带 `.Generated` 的目标；用 `Show Unity Namespace` 和 `Show ".Generated"` 两个开关可以显示。
- 列表里灰掉的条目表示没有 `[BurstCompile]` 属性，所以不会被编译。
- 点选一个目标后，右侧显示该目标的代码。

### 视图标签页

手册列出的视图（以 1.8.31 为准）：

| 标签页 | 内容 | 用途 |
| --- | --- | --- |
| Assembly | Burst 生成的最终优化后原生汇编 | 看向量化、内联、分支 |
| .NET IL | 从 Job 方法提取的原始 IL | 确认 C# 编译器产出了什么 |
| LLVM IR (Unoptimized) | 优化前的 LLVM IR | 看 Burst 前端的翻译结果 |
| LLVM IR (Optimized) | 优化后的 LLVM IR | 对照看哪些操作被合并或删除 |
| LLVM IR Optimization Diagnostics | LLVM 优化过程的诊断，成功或失败 | 查"为什么循环没向量化" |

### 顶部显示选项

- Output 下拉：`Plain Without Debug Information`、`Plain With Debug Information`、`Enhanced with Minimal Debug Information`、`Enhanced With Full Debug Information`、`Coloured With Minimal Debug Information`、`Coloured With Full Debug Information`。后四种只在 Assembly 视图可用，会把源码行与汇编交错显示。
- `Safety Checks`：勾选后生成带容器访问安全检查的代码（例如检测往只读容器写入）。读汇编评估性能时应关闭它，否则会多出大量检查分支。
- `Font Size`、`Focus on Code`（折叠指令以外的伪指令和数据）、`Expand all`。
- `Show Branch Flow`：用箭头画出跳转流向，便于识别循环。
- `Highlight SIMD Scalar vs Packed`：用不同颜色区分标量与打包（packed）SIMD 指令，是快速评估向量化质量的工具。
- Architecture 下拉：选择目标架构。具体选项（Auto、各 SSE/AVX 档位、ARM 目标）的完整名称待核实；手册只写"选择构建目标架构"。

编辑器菜单 `Jobs > Burst` 下还有 `Enable Compilation`、`Enable Safety Checks`（Off / On / Force On）、`Synchronous Compilation`、`Native Debug Mode Compilation`、`Show Timings`。注意：这些只影响编辑器内的 Burst，玩家构建在 Burst AOT 设置里单独配置。

> 手册提到：`Enable Safety Checks` 设为 Off 后，重载编辑器会重置回 On；`Force On` 会连带 `DisableSafetyChecks = true` 的代码一起强制检查。

## 如何读汇编

不需要会写汇编，只要会识别几类模式。以下以 x86-64（Intel 语法习惯）为例，ARM 的寄存器名不同（`x0`、`v0`、`s0`），思路一样。

### 寄存器与指令后缀

| 形式 | 含义 |
| --- | --- |
| `rax`、`rcx`、`edi` 等 | 通用整数寄存器（`e` 开头为 32 位，`r` 开头为 64 位） |
| `xmm0`..`xmm15` | 128 位 SIMD 寄存器，标量浮点也用它 |
| `ymm0`..`ymm15` | 256 位寄存器（AVX/AVX2） |
| 指令以 `ss` 结尾，如 `addss`、`mulss` | scalar single：只算一个 float |
| 指令以 `sd` 结尾，如 `addsd` | scalar double：只算一个 double |
| 指令以 `ps` 结尾，如 `addps`、`mulps` | packed single：同时算 4 个（xmm）或 8 个（ymm）float |
| 指令以 `pd` 结尾，如 `addpd` | packed double：同时算 2 个或 4 个 double |
| `vaddps` 等带 `v` 前缀 | VEX 编码（AVX），语义同上 |

### 判断向量化

- 循环体里大量 `...ps` 且寄存器是 `ymm`/`xmm`，说明做了向量化；如果全是 `...ss`，是标量循环。
- 打开 `Highlight SIMD Scalar vs Packed`，标量与打包指令会染成不同颜色，一眼可见。
- 向量化后的循环常带一个"尾部"标量循环处理剩余元素，所以同一个循环里同时出现两种指令是正常的。
- 如果期望向量化却没有，到 `LLVM IR Optimization Diagnostics` 页签看诊断，常见原因是别名（两个指针可能重叠）、循环内有函数指针调用、依赖链或浮点严格模式下无法重排求和（见 2.6）。

### 判断内联与调用

- `call` 指令表示这里发生了一次真实调用，目标没被内联。调用的符号名通常能看出是哪个函数。
- 没有 `call`、被调函数的指令直接出现在当前函数里，说明已内联。
- 对 `math.sin`、`math.pow` 之类，常见到 `call` 一个数学库函数，这是正常现象，不代表你的代码没内联。
- 通过函数指针的调用表现为 `call rax` 之类的间接调用（寄存器目标），见 2.7。

### 分支与循环

- `jmp` 无条件跳转；`je`/`jne`/`jl`/`jg`/`jb`/`ja` 等是条件跳转，前一条通常是 `cmp` 或 `test`。
- 往回跳（目标标号在上方）的条件跳转就是循环的回边。`Show Branch Flow` 开启后，向回的箭头很容易辨认。
- 循环里多余的比较与跳转，往往来自安全检查（容器越界检查）。关掉 `Safety Checks` 再看一遍可以确认。
- 整数除法 `idiv`、浮点 `sqrtss`/`divss` 延迟较高，出现在热点循环里值得关注。

## 原生调试

### 托管调试器

挂 Visual Studio 或 Rider 的托管调试器时，只要在 Burst 编译的代码路径里放了断点，Unity 就会自动对这条路径关闭 Burst，让你用托管版本调试；断点全部移除后 Burst 恢复。手册建议先按"Debug C# code in Unity"的步骤打开编辑器的脚本调试，并保持 Debug 脚本编译模式，Release 模式下断点可能被跳过、局部变量可能看不到。

### 原生调试器（Visual Studio、Xcode）

要看真正的 Burst 生成代码，需要先关优化，有两种方式：

- 菜单 `Jobs > Burst > Native Debug Mode Compilation`：对所有 Burst 代码关优化，影响整体性能。
- 在单个目标上加标记，只关这一个：

```csharp
using Unity.Burst;
using Unity.Jobs;

[BurstCompile(Debug = true)]
public struct MyJob : IJob
{
    public void Execute() { /* ... */ }
}
```

然后把原生调试器附加到编辑器进程。玩家构建也会读取 `Debug = true`。玩家构建还需要符号：开 Development Build 或在 Burst AOT 设置里打开 `Force Debug Information`，并关掉 `Enable Optimizations`（或用单个 Job 的 `Debug = true`）；调试工具需要指向存放 `lib_burst_generated` 文件的目录（通常在 `Plugins`）。

此外，`System.Diagnostics.Debugger.Break()` 在 Burst 里生成一个调试陷阱（debug trap），可当代码内断点用；手册提醒不论是否附加调试器它都会触发，所以更推荐用调试器的条件断点。

原生调试里嵌套类型按 C++ 风格命名，如 `Pillow::Spot::SubSpot`。`LayoutKind.Explicit` 且字段重叠的结构体，调试器里会隐藏其中一个重叠字段。

## Job 里的日志与断言

### Debug.Log

Burst 支持 `Debug.Log(object)`、`Debug.LogWarning(object)`、`Debug.LogError(object)`。可用的字符串形式：

- 字符串字面量：`Debug.Log("hello");`
- 插值字符串或 `string.Format`，格式串必须是字面量，参数最多 3 个直接重载，更多时用 `object[]`（要求长度固定、参数不含控制流）。
- 参数必须是值类型内置类型（`int`、`float`、`bool`、`long` 等）与 `Unity.Mathematics` 向量（不含 `half` 向量）。结构体的 `ToString()` 不支持，只会打出类型全名。
- 支持有限的格式说明符，如 `{value,5}`、`{value:X4}`、`{value:D4}`。

托管 `string` 不能传给自己写的方法，也不能放进结构体字段。要传递文本，用 `Unity.Collections` 的 `FixedString128Bytes` 等：

```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;
using UnityEngine;

[BurstCompile]
public struct LogJob : IJob
{
    public int Value;

    public void Execute()
    {
        FixedString128Bytes text = $"Value is {Value}";
        Report(text);
    }

    static void Report(in FixedString128Bytes message)
    {
        Debug.Log(message);
    }
}
```

> 注意：手册同一段示例里用 `FixedString128`，较新的 Collections 中名称为 `FixedString128Bytes`，写代码时以你项目里存在的类型为准。

日志代价不小，且会阻碍优化。热循环里不要留 `Debug.Log`，调试完删掉，或用 `[Conditional]`/`[BurstDiscard]` 隔离。

### 断言

`UnityEngine.Assertions.Assert` 与 `Debug.Assert` 在 Burst 中的具体行为（是否仅在启用 `UNITY_ASSERTIONS` 的编辑器与开发构建中生效、失败时如何报错）本文未能在手册中核实，待核实。可确认的是：静态只读字段初始化里允许有限的 `UnityEngine.Debug.Assert` 与 `NUnit.Framework.Assert.AreEqual/AreNotEqual`。不要在断言表达式里写有副作用的代码，因为发布构建可能整个移除它。

### BurstDiscard

`[BurstDiscard]` 标在方法上，表示该方法在 Burst 编译的代码里被整个丢弃（调用点当作空操作），只在托管执行时运行。典型用途是仅托管的调试辅助，例如在托管路径上打开计数器或检查：

```csharp
using Unity.Burst;

[BurstCompile]
public struct CountJob : Unity.Jobs.IJob
{
    public void Execute()
    {
        bool managed = false;
        MarkManaged(ref managed);   // Burst 下被丢弃，managed 保持 false
        // managed 为 true 说明这次是托管（Mono）路径在跑
    }

    [BurstDiscard]
    static void MarkManaged(ref bool flag) => flag = true;
}
```

这个技巧能在运行时自检"我现在是 Burst 还是 Mono"。被丢弃的方法不能有返回值依赖（返回值会是默认值），所以用 `ref`/`out` 参数承载结果。本项目 Burst 2.0.0 壳包的转发列表（`TypeForwarders.cs`）里没有直接看到 `BurstDiscardAttribute` 一项，该特性在 Burst 2.0 / Unity 7 下的所在程序集待核实。

## 对比 Mono 与 Burst 结果

目标：同一算法，Burst 路径和托管路径输出一致（或在容差内）。

推荐做法：把核心算法写成不依赖 Burst 的静态纯函数（输入值类型、输出值类型），Job 里调用它，测试里也直接调用它。这样"托管路径"就是普通 C# 调用，不依赖任何开关：

```csharp
// 被测算法：Job 和测试共用
public static class Hash
{
    public static uint Mix(uint h)
    {
        h = (h ^ (h >> 13)) * 1274126177u;
        return h ^ (h >> 16);
    }
}

[BurstCompile]
struct HashJob : IJobParallelFor
{
    [ReadOnly] public NativeArray<uint> Input;
    [WriteOnly] public NativeArray<uint> Output;
    public void Execute(int i) => Output[i] = Hash.Mix(Input[i]);
}

// NUnit 测试
[Test]
public void BurstMatchesManaged()
{
    var input = new NativeArray<uint>(1024, Allocator.TempJob);
    var burstOut = new NativeArray<uint>(1024, Allocator.TempJob);
    try
    {
        for (int i = 0; i < input.Length; i++) input[i] = (uint)(i * 2654435761u);
        new HashJob { Input = input, Output = burstOut }.Schedule(input.Length, 64).Complete();
        for (int i = 0; i < input.Length; i++)
            Assert.AreEqual(Hash.Mix(input[i]), burstOut[i], $"index {i}");
    }
    finally { input.Dispose(); burstOut.Dispose(); }
}
```

另一种做法是用 `BurstCompiler.Options.EnableBurstCompilation`（属性存在，见 `BurstCompilerOptions` API：Gets or sets a boolean to enable or disable compilation of burst jobs）在测试里先置 `false` 跑一遍、再置 `true` 跑一遍，对比两次的输出。风险：

- 它是全局开关，会影响同一编辑器会话里所有 Job，测试结束必须在 `finally` 里恢复原值。
- 已经 JIT 编译完的 Job 是否在切换后立即回退到托管执行、以及异步编译的时序，本文未核实，待核实。需要稳定复现时配合 `EnableBurstCompileSynchronously` 或 `[BurstCompile(CompileSynchronously = true)]`。
- 浮点算法两条路径可能相差几个 ULP，断言应使用容差；若要求逐位相同，需要 `FloatMode.Deterministic`（见 2.6）。

## 常用调试流程清单

1. 先确认 Burst 确实在跑：`Jobs > Burst > Enable Compilation` 已勾选，Inspector 左侧该目标不是灰色（有 `[BurstCompile]`）。
2. 出错信息以 `BC` 开头的编译错误（如 `BC1361` 静态构造不支持）先按错误码查原因，再改代码。
3. 结果不对：先写 Burst 与托管对比测试，缩小到具体输入。
4. 能复现且怀疑逻辑错误：在 Job 代码里下断点，用托管调试器调试（Burst 对该路径自动关闭）。
5. 怀疑 Burst 本身或内存问题：开 `Native Debug Mode Compilation` 或在该 Job 上写 `Debug = true`，挂原生调试器。
6. 性能不对：关 `Safety Checks`，在 Assembly 视图看有没有 `call`、有没有 `ps` 向量指令、热点循环里有没有多余分支；再看 LLVM IR Optimization Diagnostics。
7. 编译慢：开 `Show Timings` 看前端、中端、后端耗时；必要时 `OptimizeFor = OptimizeFor.FastCompilation` 换编译速度。
8. 最后在 Profiler 里实测，用 `ProfilerMarker` 给 Burst 代码打点。汇编只能说明"看起来"，不能代替测量。

## 常见坑

- 在 Release 脚本编译模式下调试，断点被跳过。先切到 Debug。
- 只关了 `Safety Checks` 就拿编辑器计时当最终成绩：编辑器里还有 JIT 与域重载影响，应以 Development 或 Release 构建为准。
- 把 `Native Debug Mode Compilation` 一直开着，之后的性能数据全部失真。
- 在 Job 里拼接字符串或传托管 `string`，编译直接报错；改用 `FixedString`。
- 依赖 `[BurstDiscard]` 方法的返回值，得到的是默认值。
- 对比测试里要求浮点逐位相等，却没有设 `FloatMode.Deterministic`。

## 小结

Inspector 是核对 Burst 行为的第一工具：Assembly 看向量化与内联，LLVM IR Optimization Diagnostics 看优化失败原因。调试分托管和原生两条路径，托管路径下断点会自动关闭 Burst，原生路径要关优化。日志只能用字面量与 `FixedString`，`[BurstDiscard]` 用来隔离仅托管代码。验证正确性靠"共用静态函数 + 两路径对比测试"。

## 自测题

1. 想让汇编里更接近真实性能，Inspector 上应当关掉哪个开关？答：`Safety Checks`，它会插入容器访问检查。
2. `addps` 与 `addss` 的区别？答：前者是打包（packed）指令，一次算多个 float；后者是标量指令，一次算一个。
3. 只想对单个 Job 关掉优化以便原生调试，怎么写？答：`[BurstCompile(Debug = true)]`。
4. 为什么不能把托管 `string` 作为参数传给 Burst 里自己写的方法？答：`string` 是托管类型，Burst 不支持；应使用 `FixedString128Bytes` 等值类型。
5. `[BurstDiscard]` 方法在 Burst 路径与 Mono 路径下的行为差异？答：Burst 下调用被丢弃，Mono 下正常执行，因此可用 `ref` 参数检测当前执行路径。

## 参考

- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/editor-burst-inspector.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/editor-burst-menu.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/debugging-profiling-tools.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-string-support.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-static-read-only-support.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/api/Unity.Burst.BurstCompilerOptions.html
- D:\UnityHub\Project\程序化生成\Library\PackageCache\com.unity.burst@626e66ab421b\Runtime\TypeForwarders.cs
