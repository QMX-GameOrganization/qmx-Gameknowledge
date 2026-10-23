---
title: "2.4 SIMD 与自动向量化"
description: 讲解 SIMD 概念、Burst 自动向量化的条件与阻碍、用 float4/int4 手写向量化、Burst Intrinsics，以及在 Burst Inspector 里确认向量化的方法和体素场景的 SoA 思路。
sidebar:
  order: 4
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x（本文参考 1.8.31 手册）/ Mathematics 1.3.x 为主线；Burst 2.0.0 在本项目中是转发壳包，`Unity.Burst.Intrinsics` 下的 `v64`/`v128`/`v256`/`Common`/`X86`/`Arm` 在 `TypeForwarders.cs` 中确认存在。Burst 2.0 在向量化行为上相对 1.8 有无变化，未核对（待核实）。

## 要点

- SIMD（Single Instruction, Multiple Data，单指令多数据）：一条指令同时处理一组数据。x86 的 SSE2 寄存器 128 位（4 个 float），AVX/AVX2 是 256 位（8 个 float），Arm NEON 是 128 位。
- 大多数情况下你不用手写 SIMD：Burst 的 LLVM 后端会自动向量化（auto-vectorization）简单循环。你的工作是写出"容易被向量化"的循环，并用 Burst Inspector 验证。
- 自动向量化依赖：无循环携带依赖、内存不别名、循环体简单、无提前退出、分支能转成 select、被调函数能内联。
- 想要可预期的向量化（不靠编译器猜），用 `float4`/`int4` 加 `math.*` 把数据按 SoA 组织，一次处理 4 个元素；极端情况才用 `Unity.Burst.Intrinsics`。
- 体素场景里，"一次比较 4/8 个密度值、位掩码打包 8 个 bool"是典型收益点。

## SIMD 概念

```
标量（scalar）：一次一个
  a:  [ a0 ]     b:  [ b0 ]      add  →  [ a0+b0 ]

向量（packed，128 位 = 4 × float32）：一次四个
  a:  [ a0 | a1 | a2 | a3 ]
  b:  [ b0 | b1 | b2 | b3 ]
  add →[ a0+b0 | a1+b1 | a2+b2 | a3+b3 ]    一条指令
```

| 指令集 | 寄存器宽度 | 一次可处理（float32 / int32） | 备注 |
| --- | --- | --- | --- |
| SSE2 / SSE4.x | 128 位（`xmm`） | 4 | x64 基线 |
| AVX / AVX2 | 256 位（`ymm`） | 8 | 需要 CPU 支持，且 Burst 目标 CPU 设置要允许 |
| Arm NEON | 128 位 | 4 | Armv7/Armv8；Burst 的 Neon 内部函数仅支持 Armv8（64 位） |

汇编里怎么辨认：

- 浮点指令的后缀：`ss`/`sd`（scalar single / scalar double）是标量，如 `addss`、`mulsd`；`ps`/`pd`（packed single / packed double）是打包向量，如 `addps`、`mulpd`。
- 整数指令有自己的命名，例如手册示例里的 `vpaddd`（256 位寄存器上打包的 32 位整数加法）。
- 看寄存器：`xmm0..` 是 128 位，`ymm0..` 是 256 位；只在标量指令里用 `xmm` 低位的话，仍然是标量。

Burst 目标 CPU 由 Project Settings 的 Burst AOT Settings 决定（细节见 2.11 一章）；编辑器 JIT 具体针对哪个 CPU 级别生成代码，我没有在手册中核实到（待核实）。

## 自动向量化

手册（Loop vectorization）的例子：

```csharp
[MethodImpl(MethodImplOptions.NoInlining)]
private static unsafe void Bar([NoAlias] int* a, [NoAlias] int* b, int count)
{
    for (var i = 0; i < count; i++)
    {
        a[i] += b[i];
    }
}
```

Burst 把这个标量循环展开并向量化，AVX2 目标上生成的汇编是 4 条 `vpaddd ymm`，每条处理 8 个 `int`，一次循环迭代共 32 个加法。

### 向量化的条件

| 条件 | 含义 |
| --- | --- |
| 无循环携带依赖 | 第 `i` 次迭代不依赖第 `i-1` 次的结果（如 `a[i] = a[i-1] + 1` 就不行） |
| 无别名 | 编译器要能证明读写的内存区域不重叠 |
| 循环体简单 | 没有复杂控制流、没有未内联的函数调用 |
| 无提前退出 | 循环里的 `break`/`return` 会破坏向量化 |
| 分支可转 select | `if/else` 只是选值时，可转为逐 lane 的 blend/select |
| 调用被内联 | 循环里调用的小函数要能内联，否则打断优化 |
| 迭代数可确定 | 循环次数在进入循环前就能确定 |

### 常见阻碍

1. 别名：这是最常见的问题。Burst 对 Job 结构体里的 `NativeArray` 字段有别名信息（NativeContainer 之间不会重叠，手册 Memory aliasing 一章说明了这一点）。但当你把它们拆成独立指针或参数传给其它函数时，编译器可能无法再证明不重叠，退回标量。
2. 浮点归约顺序：`sum += x[i]` 要求按顺序累加。默认 `FloatMode.Strict` 不允许重排浮点加法，所以浮点求和循环通常不会被向量化。整数求和则没有这个限制。
3. 函数调用没有内联：循环体里调用大函数、虚调用、函数指针都会阻止向量化。
4. 复杂控制流：多出口、嵌套分支、`break`。手册给的反例就是在向量化的 `Bar` 里加入 `if (a[i] > b[i]) break;`，结果生成了一次只加一个整数的标量循环。
5. 带 `Strict` 浮点语义的数学函数：需要特殊处理 NaN 或严格舍入的操作可能阻止优化。
6. `OptimizeFor.FastCompilation`：Burst AOT Settings 手册写明该档位下 Burst 不做任何向量化、内联和循环优化。在 Inspector 里发现整段是标量代码时，先检查程序集级或 Job 级是否设了这个选项。

### 让编译器知道"不别名"

- `[NoAlias]`（`Unity.Burst.NoAliasAttribute`）：标在指针参数或结构体字段上，断言它们指向的内存不与其它指针重叠。
- `Aliasing.ExpectNotAliased(a, b)` / `Aliasing.ExpectAliased(a, b)`（`Unity.Burst.CompilerServices.Aliasing`）：在编译期检查你的别名假设，不成立就报编译错误；这些检查只在优化开启时有效。

两者的细节放在 2.10 一章，这里只需记住：向量化失败时先怀疑别名。

### 用编译器断言守住向量化

`Loop.ExpectVectorized()` / `Loop.ExpectNotVectorized()` 是实验性内联函数，需要定义预处理符号 `UNITY_BURST_EXPERIMENTAL_LOOP_INTRINSICS` 才能使用：

```csharp
for (var i = 0; i < count; i++)
{
    Unity.Burst.CompilerServices.Loop.ExpectVectorized();
    a[i] += b[i];
}
```

如果循环没有被向量化，Burst 会在编译时给出错误 `BC1321`（"The loop is not vectorized where it was expected that it is vectorized"）。手册提醒这些函数不能放在 `if` 里（Burst 不会为此报错，所以要自己注意）。

## 手写向量化：`float4` / `int4` + `math`

不依赖编译器猜测，直接用 4 宽类型组织数据。`Unity.Mathematics` 的 `float4` 等被 Burst 映射到 128 位寄存器，运算符逐分量执行。

### 对比示例：统计超过阈值的体素数

标量写法：

```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;
using Unity.Mathematics;   // 下一个向量版 Job 要用 float4 / int4 / math

[BurstCompile]
struct CountScalarJob : IJob
{
    [ReadOnly] public NativeArray<float> Density;
    public float Threshold;
    public NativeArray<int> Result;

    public void Execute()
    {
        int count = 0;
        for (int i = 0; i < Density.Length; i++)
        {
            if (Density[i] > Threshold)
                count++;
        }
        Result[0] = count;
    }
}
```

这个循环不一定被向量化（取决于优化器对分支转换的判断），要用 Burst Inspector 验证，不要假设。

向量友好写法：数据按 `float4` 存放，用比较结果直接累加，不分支：

```csharp
[BurstCompile]
struct CountVectorJob : IJob
{
    [ReadOnly] public NativeArray<float4> Density;   // 每个元素装 4 个体素密度
    public float Threshold;
    public NativeArray<int> Result;

    public void Execute()
    {
        int4 acc = int4.zero;
        float4 t = Threshold;                          // 标量广播
        for (int i = 0; i < Density.Length; i++)
        {
            bool4 hit = Density[i] > t;                // 一次比较 4 个
            acc += math.select(int4.zero, new int4(1), hit);   // 无分支
        }
        Result[0] = math.csum(acc);                    // 最后一次性水平求和
    }
}
```

要点：

- `Density[i] > t` 得到 `bool4`，`math.select` 把它转成 0/1，整个过程无分支。
- 累加用 `int4` 做 4 个独立累加器，循环外再 `csum`。整数加法满足结合律，顺序不影响结果；若是 `float` 累加，这样写等于你手动改变了求和顺序，结果会与顺序求和略有差异。
- 数据布局从 `NativeArray<float>` 变为 `NativeArray<float4>`：这是 SoA/打包布局的改动，需要在数据生产端配合。

## Burst Intrinsics

手册说明：`Unity.Burst.Intrinsics` 暴露了 Intel 从 SSE 到 AVX2 的全部 SIMD 内部函数（嵌套类 `X86.Sse`、`X86.Sse2`、`X86.Sse3`、`X86.Ssse3`、`X86.Sse4_1`、`X86.Sse4_2`、`X86.Popcnt`、`X86.Avx`、`X86.Avx2`、`X86.Fma`、`X86.F16C`、`X86.Bmi1`、`X86.Bmi2`），以及 Arm Neon 的 Armv7/Armv8/Armv8.2（`Arm.Neon`）。大多数场景你用不到它们。

### 向量类型

- `v64`（仅 Arm）、`v128`、`v256` 分别是 64/128/256 位向量。
- Burst 的内部函数使用无类型向量：Intel 的 `__m128`/`__m128i`/`__m128d` 都收敛成 `v128`，`__m256*` 收敛成 `v256`。向量类型里有各种元素类型的字段（联合体式），所以不会做类型检查：用 4 个 float 初始化的向量传给处理整数的函数，编译器不会报错。
- API 命名去掉了 `_mm` 前缀，位域常量换成 C# 枚举。

### 编译期特性检测

```csharp
using static Unity.Burst.Intrinsics.X86;
using static Unity.Burst.Intrinsics.X86.Sse4_2;
using static Unity.Burst.Intrinsics.X86.Avx2;
using static Unity.Burst.Intrinsics.Arm.Neon;

if (IsAvx2Supported)
{
    // AVX2 路径
}
else if (IsSse42Supported)
{
    // SSE4.2 路径
}
else if (IsNeonSupported)
{
    // Arm NEON 路径
}
else
{
    // 通用回退
}
```

手册说明：这些 `IsXXXSupported` 属性由 Burst 在编译期求值，不支持的分支作为死代码被删除，所以不影响性能。后来的级别隐含前面的级别，应从新到旧排列。如果用了当前编译目标不支持的内部函数而没有放进检测分支，会得到编译错误。

在 Burst 关闭（Mono/IL2CPP 托管）时，所有 `IsXXXSupported` 都返回 `false`；大多数 Intel 内部函数有慢速的托管参考实现，便于托管调试，Arm Neon 没有托管实现，对 double 的 FMA 也没有软件回退。

手册给出的"左压缩"片段，展示了加载、比较、取掩码、洗牌、存储的写法（来自 Processor specific SIMD extensions，示意用，依赖 `Input`、`Output`、`Limit`、`Lut` 等上下文）。注意：手册原文这一行写的是 `movemask_ps(a)`，但上一行算出的比较结果 `mask` 没有被用到，按语义应传 `mask`，下面按语义改正：

```csharp
v128 a = Input.ReinterpretLoad<v128>(i);
v128 mask = cmplt_ps(a, Limit);
int m = movemask_ps(mask);
v128 packed = shuffle_epi8(a, Lut[m]);
Output.ReinterpretStore(outputIndex, packed);
outputIndex += popcnt_u32((uint)m);
```

### `Unity.Burst.Intrinsics.Common`：跨平台共享的内部函数

上面的 `X86`、`Arm.Neon` 是针对具体处理器的。除此之外，`Unity.Burst.Intrinsics.Common` 放的是各个硬件目标共享的功能（API 页描述为 "Common intrinsics that are exposed across all Burst targets"），不需要 `IsXXXSupported` 分支保护。手册（Burst Intrinsics Common class）列出四项：

| 内部函数 | 状态 | 作用 |
| --- | --- | --- |
| `Common.Pause()` | 正式 | 提示 CPU 暂停当前线程一下。x86 上映射为 `pause` 指令，ARM 上映射为 `yield` 指令 |
| `Common.umul128(ulong a, ulong b, out ulong high)` | 正式 | 128 位无符号乘法：返回乘积的低 64 位，高 64 位通过 `out` 参数给出 |
| `Common.Prefetch` | 实验性 | 提示 Burst 把某个内存位置预取到缓存里 |
| `Common.InterlockedAnd` / `Common.InterlockedOr` | 实验性 | 对 `int`、`uint`、`long`、`ulong` 做原子与、原子或 |

#### `Pause`

用于自旋锁一类的循环。手册说明：它帮助避免在紧密循环里对原子访问的过度争用（contention），降低这段代码的争用和功耗。API 页补充：这不是操作系统层面的线程让出（yield），只是给 CPU 一个"当前线程可以暂时歇一下"的提示。

```csharp
using System.Threading;
using Unity.Burst.Intrinsics;

// 教学示意，未在 Unity 内编译：自旋等待一个标志位
static unsafe void SpinUntilSet(int* flag)
{
    while (Volatile.Read(ref *flag) == 0)
        Common.Pause();
}
```

多数体素 Job 靠 Job 系统的依赖和 `NativeArray` 分区避免共享写，不需要自旋锁；用到自旋锁的场景请先考虑能否改成每线程各写各的区间再合并。

#### `umul128`

128 位无符号乘法。手册说明这类乘法对哈希函数有用，并且在 x86 和 ARM 目标上与硬件指令一一对应。它可以用来写 64 位混合哈希（例如把两个 64 位值相乘，再把高低两半异或），用于种子派生。这类哈希是纯整数运算，不受 2.6 浮点模式与确定性 里讲的浮点漂移影响。

```csharp
using Unity.Burst.Intrinsics;

// 教学示意，未在 Unity 内编译：高低两半异或，得到 64 位混合值
static ulong MixMul(ulong a, ulong b)
{
    ulong low = Common.umul128(a, b, out ulong high);
    return low ^ high;
}
```

这个混合函数只是示意写法，质量没有评估，真要用来做世界种子，先写 golden test 并检查分布。

#### 实验性：`Prefetch`、`InterlockedAnd`、`InterlockedOr`

手册把这三个标为实验性（experimental），要定义对应的预处理符号才能使用：

- `Common.Prefetch`：需要定义 `UNITY_BURST_EXPERIMENTAL_PREFETCH_INTRINSIC`。它只是提示（hint），Burst 会尝试把该内存位置预取进缓存；手册没有给出签名和性能数据，API 页的方法列表里也没有它，所以签名和收益都待核实，用之前先用 Inspector 和计时验证。
- `Common.InterlockedAnd` / `Common.InterlockedOr`：需要定义 `UNITY_BURST_EXPERIMENTAL_ATOMIC_INTRINSICS`。提供对 `int`、`uint`、`long`、`ulong` 的原子与、原子或，例如多个线程往同一个位掩码里置位或清位。具体签名手册没有写出（待核实）。

实验性接口在后续版本里可能改名、改行为或移除，不要把它们放进需要长期维护的核心代码里。预处理符号怎么定义（Player Settings 的 Scripting Define Symbols，或 asmdef 的 Define Constraints 等）取决于项目，本项目目前没有用到。

建议顺序：先用 `float4`/`int4` + `math` 写；Inspector 里确认没有生成预期指令时，再考虑 intrinsics。

## 对齐与加载存储

- `UnsafeUtility.AlignOf<T>()` 返回类型 `T` 的对齐要求。
- 内部函数的"对齐加载"（如 SSE 的 `load_ps`）要求地址按 16 字节对齐，"非对齐加载"（`loadu_ps`）则无此要求。用 `ReinterpretLoad` 这类封装可以避开这个问题。
- `NativeArray<T>` 分配时的对齐保证具体是多少（是否保证 16 字节）、不同 Allocator 是否一致，我没有在已读资料中核实到（待核实）。在没确认之前，不要假设首地址一定满足 16/32 字节对齐，宁用非对齐加载。
- 让数据 SIMD 友好的结构性办法是：数组元素本身就是 `float4`（16 字节），而不是靠指针强转。

## 在 Burst Inspector 里确认向量化

打开 `Jobs > Burst > Open Inspector`，选中你的 Job：

1. 视图选 `Assembly`，输出模式选 Enhanced 或 Coloured，勾选 `Highlight SIMD Scalar vs Packed`（手册说这用来快速评估向量化代码质量，也就是"SIMD 烟雾测试"）。
2. 看热点循环里的指令：出现 `xmm`/`ymm` 寄存器与 `p` 后缀指令（`addps`、`mulps`、`vpaddd`、`vmovups` 等）说明向量化了；满篇 `ss`/`sd` 说明是标量。
3. 看循环结构：向量化后的循环通常带展开（一次迭代做多组），循环计数器以 4/8/32 为步长增加（手册示例里 `add rax, 32`）。
4. 顶部的 `Architecture` 下拉可以切换目标架构，不同架构生成的指令不同；`Safety Checks` 开关会让汇编里多出检查代码，评估向量化时建议关掉对比。
5. 切到 `LLVM IR Optimization Diagnostics` 视图可以看到优化是否成功的诊断。

## 体素场景的 SoA 化思路

典型的密度判定循环：对一个 16×16×16 区块，每个格点判断"是否实心"。

```
AoS（常见的对象/结构体数组）：      SoA（按字段分开存）：
 [ {d,mat}, {d,mat}, {d,mat}, ...]   density: [ d0 d1 d2 d3 d4 d5 d6 d7 ... ]
 一次加载同时带来用不到的 mat         material: [ m0 m1 m2 m3 ... ]
                                      比较只扫 density，连续、可打包
```

做法：

- 把密度单独放一个 `NativeArray<float>`（或 `NativeArray<float4>`），材质、生物群系等放另一个数组。比较只触碰密度数组，缓存和 SIMD 都更友好。
- 沿 X 轴连续存放（X 变化最快），这样 4 个相邻体素正好在一个 `float4` 里。
- 一次比较 4 个：`bool4 solid = density4 > threshold;`；一次比较 8 个就用两个 `float4`，或在 AVX2 下用 `v256`。
- 用位掩码把 8 个 bool 打包成 1 个字节，生成面片时按位判断邻居是否实心，内存减小到 1/8（相对 `bool` 数组），并可用 `math.countbits` 统计实心数、`math.tzcnt` 找第一个实心位。

位掩码示例（每两个 `float4` 打包成 1 个 `byte`）：

```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;
using Unity.Mathematics;

[BurstCompile]
struct PackSolidMaskJob : IJob
{
    [ReadOnly] public NativeArray<float4> Density;   // 长度必须是偶数
    public float Threshold;
    [WriteOnly] public NativeArray<byte> Mask;       // 长度 = Density.Length / 2

    public void Execute()
    {
        float4 t = Threshold;
        for (int i = 0; i < Mask.Length; i++)
        {
            int lo = math.bitmask(Density[2 * i]     > t);   // 低 4 位
            int hi = math.bitmask(Density[2 * i + 1] > t);   // 高 4 位
            Mask[i] = (byte)(lo | (hi << 4));
        }
    }
}

// 读取：第 k 个体素是否实心
static bool IsSolid(in NativeArray<byte> mask, int k)
    => ((mask[k >> 3] >> (k & 7)) & 1) != 0;
```

`math.bitmask(bool4)` 的位序：`x` 在第 0 位，依次到 `w` 在第 3 位（API 页已核实）。

本项目现状：`IDensityFunction.Sample` 每次取一个点、返回一个 `double`（逐点、对象树、虚调用），这是标量模型，天然不适合 SIMD。向量化的前提是先把采样改成"对一批连续点求值"，这件事放在 3.2 一章之后再谈。

## 常见坑

- 没有验证就假设向量化了：浮点归约、带 `break` 的循环、含大函数调用的循环通常不会。
- 为了向量化在 `float` 求和里用多个累加器，却不知道这改变了求和顺序和结果。
- 把 `NativeArray` 拆成裸指针传入小函数而没加 `[NoAlias]`，失去不别名信息。
- 只在 AVX2 机器上测试，却忽略了目标 CPU 设置与回退路径。
- 手写 intrinsics 而未用 `IsXXXSupported` 分支保护，导致编译错误或在不支持的 CPU 上出现非法指令。
- 用 `Loop.ExpectVectorized()` 却忘了定义 `UNITY_BURST_EXPERIMENTAL_LOOP_INTRINSICS`，或把它放进 `if` 里。
- 在 Inspector 里开着 `Safety Checks` 看汇编，被检查代码干扰判断。

## 小结

- SIMD 让一条指令处理一批数据；x86 是 128/256 位，NEON 是 128 位。
- 先用简单循环、无别名、无提前退出的写法，让 Burst 自动向量化，再用 Inspector 看是否有 `ps`/`ymm` 指令。
- 要确定性的收益，用 `float4`/`int4` 与 `math.select`、`math.bitmask` 做 SoA 布局。
- `Unity.Burst.Intrinsics` 是最后手段，用 `IsXXXSupported` 在编译期分支。
- 本项目的逐点 `Sample` 接口需要改成批量接口后才谈得上向量化。

## 自测题

1. `addss` 与 `addps` 有什么区别？
   答：`addss` 是标量单精度加法，处理 1 个 float；`addps` 是打包单精度加法，一条指令处理一个向量寄存器里的多个 float。
2. 为什么 `for (...) sum += x[i];`（float）通常不能被自动向量化？
   答：默认 `FloatMode.Strict` 不允许重排浮点加法顺序，归约有顺序依赖；整数求和没有这个限制。
3. `[NoAlias]` 和 `Aliasing.ExpectNotAliased` 各自的作用？
   答：前者向编译器断言指针不与其它指针重叠；后者在编译期检查两个指针是否被证明不别名，不成立则报错（需要优化开启）。
4. 在 Inspector 里看到 `vpaddd ymm0, ymm0, ...` 说明什么？
   答：循环使用了 256 位寄存器的打包整数加法，即被 AVX2 向量化了。
5. `math.bitmask(new bool4(true, true, false, true))` 的结果是多少？
   答：`x` 在第 0 位、`y` 在第 1 位、`z` 在第 2 位、`w` 在第 3 位，所以是二进制 1011，即 `0xB`（11），与 API 页的示例一致。

## 参考

- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/optimization-loop-vectorization.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/aliasing.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/optimization-overview.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-burst-intrinsics.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-burst-intrinsics-processors.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-burst-intrinsics-common.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/api/Unity.Burst.Intrinsics.Common.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/editor-burst-inspector.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-type-support.html
- https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/api/Unity.Mathematics.math.bitmask.html
- https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/api/Unity.Mathematics.math.tzcnt.html
- D:\UnityHub\Project\程序化生成\Library\PackageCache\com.unity.burst@626e66ab421b\Runtime\TypeForwarders.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Density\IDensityFunction.cs
