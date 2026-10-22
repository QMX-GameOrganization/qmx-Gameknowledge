---
title: "3.2 噪声与密度函数的 Burst 化"
description: 盘点密度函数树里阻碍 Burst 的写法，比较参数化 struct、指令解释器、泛型单态化三条改造路线，并给出噪声、样条、二维缓存的移植与逐点验收方法。
sidebar:
  order: 2
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x / Collections 2.x / Mathematics 1.3.x 为主线；本项目的 Unity 7000.0.0a8 中 Burst 2.0.0 与 Collections 6.7.0 是转发到引擎内置模块的壳包。核实不了的标"待核实"。

本章代码是教学骨架，未在 Unity 内编译，复制前核对 API 与项目现状。类名、字段名、数值常量以 `Assets/Scripts/WorldGen/Density/` 下的真实代码为准。

## 目标与现状

目标：让"给定世界坐标 (x, y, z)，求密度 `double`"这件事可以在 Burst Job 里运行，并且在固定种子下与现有托管实现给出同样的地形。

现状：`WorldFields.CreateLearningDefaults(seed, settings).FinalDensity` 返回一棵 `IDensityFunction` 对象树。每个节点是 `class`，通过接口方法 `double Sample(in DensityContext context)` 虚调用子节点；运算用 `Func<>` 委托；列缓存带可变字段。Burst 不能编译托管对象、接口虚调用和委托（见 2.2 支持的 C# 子集），所以整棵树不能原样进 Job。

先看最终公式，它决定了要移植的东西到底有多少。`CreateLearningDefaults` 的结构是（`c`、`e`、`r` 分别是 continents、erosion、ridges 三个二维噪声）：

```
c = Noise2D(seed+1, 0.0025)   e = Noise2D(seed+2, 0.008)   r = Noise2D(seed+3, 0.012)
p = -3 * (abs(abs(r) - 2/3) - 1/3)                      // OriginalTerrainProvider.PeaksAndValleys
offset     = -0.50375 + SplineOffset(c, e, p)
factor     = SplineFactor(c, e, p)
jaggedness = SplineJaggedness(c, e, p)
jaggedTerm = jaggedness * HalfNegative(Noise2D(seed+6, 0.035))

depth   = YClampedGradient(y) + offset
base    = QuarterNegative((depth + jaggedTerm) * factor) * 4
noise3D = Blend(FractalNoise(seed+4), FractalNoise(seed+10004), FractalNoise(seed+20004)) * BaseNoiseStrength
final   = VerticalSlide(base + noise3D, y)
```

其中 `c`、`e`、`r`、`p`、`offset`、`factor`、`jaggedness`、`jaggedNoise` 都只依赖 (x, z)，在代码里被 `Cache2D` 包着；只有 `YClampedGradient`、三个 `FractalNoise` 和 `VerticalSlide` 依赖 y。这个"二维部分 + 三维部分"的分层，是后面所有路线的共同骨架。

## 现状盘点：每种节点的 Burst 障碍

| 文件 | 节点 | Burst 障碍 | 在 FinalDensity 里是否出现 |
| --- | --- | --- | --- |
| `IDensityFunction.cs` | 接口 `Sample(in DensityContext)` | 托管接口虚调用，Job 里无法持有接口引用 | 是（全部） |
| `DensityContext.cs` | `readonly struct`，三个 `int` | 无，已是 blittable | 是 |
| `ConstantFunction.cs` | class，一个 `double` | 仅 class 形式 | 是 |
| `UnaryFunction.cs` | class + `Func<double,double>` | 委托不支持；`HalfNegative`、`QuarterNegative`、`Abs` 都是 lambda 或方法组 | 是 |
| `BinaryFunction.cs` | class + `Func<double,double,double>` | 委托不支持；`Add/Subtract/Multiply/Min/Max` 都靠它 | 是（Add、Subtract、Multiply） |
| `ClampFunction.cs` | class，`Math.Max/Min` | 仅 class 形式 | 否 |
| `RangeChoiceFunction.cs` | class，两个子树分支 | class + 接口 | 否 |
| `YGradientFunction.cs` | class，4 个字段，纯算术 | 仅 class 形式，最易移植 | 是 |
| `ValueNoiseFunction.cs` | class，实例方法 `Lattice` | 仅 class 形式；整数 hash 与 double 插值都是 Burst 友好的 | 是 |
| `OctaveNoiseFunction.cs` | class，`ValueNoiseFunction[] layers`，`foreach` | 托管数组里放引用类型对象 | 是 |
| `BlendedNoiseFunction.cs` | class，三个子节点，`t==0`/`t==1` 分支 | class + 接口；注意惰性求值分支 | 是 |
| `CubicSplineFunction.cs` | class，`CubicSplinePoint[]`，二分查找 | 点数组里带托管引用；嵌套样条递归求值 | 是 |
| `CubicSplinePoint.cs` | `readonly struct`，含 `IDensityFunction ValueFunction` | 含托管引用，不是 blittable | 是 |
| `VerticalSlideFunction.cs` | class，int/double 字段，纯算术 | 仅 class 形式 | 是 |
| `ColumnCacheFunction.cs` | class，可变字段 `hasValue/lastX/lastZ/lastValue` | 可变状态，天然不线程安全；Job 里没有"同一个线程上一次的结果" | 是（所有二维场） |
| `CacheOnceFunction.cs` | class，可变字段，缓存上一个完整坐标 | 同上 | 否 |
| `ProjectedXZFunction.cs` | class，把 Y 置 0 | 仅 class 形式 | 是（`Noise2D`） |
| `OriginalTerrainProvider.cs` | 静态方法，构造样条树 | 构造期托管代码，不进 Job；但它的输出是要被压平的树 | 是 |
| `DensityFunctions.cs`、`WorldFields.cs` | 工厂方法，lambda | 构造期代码，不进 Job | 是 |
| `WorldGenerationSettings.cs` | `[Serializable] sealed class`，全是 `int`/`double` | class；字段本身是 blittable，拷成 struct 即可 | 是（参数来源） |
| `ChunkDensitySampler.cs` | class，`double[] corners` | 托管数组 | 调用方，见 3.3 |

两个观察：

1. `ClampFunction`、`RangeChoiceFunction`、`CacheOnceFunction`、`DensityFunctions.Min/Max` 没有出现在当前主世界公式里，第一阶段不用移植。需要时再加。
2. 真正阻碍的是三类东西：对象图（class + 接口）、委托、可变缓存。算术和 hash 本身都是 Burst 友好的。

## 先做的基础件：噪声原样移植

三条路线都要用到同一个噪声实现，所以先移植它。原则：不换算法，只换形式，整数 hash 与 double 插值的每一步都与 `ValueNoiseFunction` 保持一致。**不要改用 `Unity.Mathematics.noise`**（`noise.cnoise`、`noise.snoise` 等）：它们是另一套梯度噪声，值域和形状都不同，换了之后地形会整体改变，也就没有了"托管版是标准答案"这个验收基准。

```csharp
using Unity.Burst;
using Unity.Mathematics;

namespace ProceduralGeneration.WorldGen.Density.Burst   // 命名空间名是建议，不是现有代码
{
    [BurstCompile]
    internal static class ValueNoiseBurst
    {
        // 对应 ValueNoiseFunction.Sample：scale 用于 X/Z，yScale 用于 Y，最后乘 amplitude。
        public static double Sample(int seed, double scale, double yScale, double amplitude,
            int ix, int iy, int iz)
        {
            double x = ix * scale;
            double y = iy * yScale;
            double z = iz * scale;
            int x0 = (int)math.floor(x), y0 = (int)math.floor(y), z0 = (int)math.floor(z);
            double tx = Smooth(x - x0), ty = Smooth(y - y0), tz = Smooth(z - z0);
            double c000 = Lattice(seed, x0, y0, z0),         c100 = Lattice(seed, x0 + 1, y0, z0);
            double c010 = Lattice(seed, x0, y0 + 1, z0),     c110 = Lattice(seed, x0 + 1, y0 + 1, z0);
            double c001 = Lattice(seed, x0, y0, z0 + 1),     c101 = Lattice(seed, x0 + 1, y0, z0 + 1);
            double c011 = Lattice(seed, x0, y0 + 1, z0 + 1), c111 = Lattice(seed, x0 + 1, y0 + 1, z0 + 1);
            double x00 = Lerp(c000, c100, tx), x10 = Lerp(c010, c110, tx);
            double x01 = Lerp(c001, c101, tx), x11 = Lerp(c011, c111, tx);
            return Lerp(Lerp(x00, x10, ty), Lerp(x01, x11, ty), tz) * amplitude;
        }

        static double Lattice(int seed, int x, int y, int z)
        {
            unchecked
            {
                uint h = (uint)seed;
                h ^= (uint)x * 374761393u;
                h ^= (uint)y * 668265263u;
                h ^= (uint)z * 2147483647u;
                h = (h ^ (h >> 13)) * 1274126177u;
                h ^= h >> 16;
                return (h / (double)uint.MaxValue) * 2.0 - 1.0;
            }
        }

        static double Smooth(double v) => v * v * (3.0 - 2.0 * v);
        static double Lerp(double a, double b, double t) => a + (b - a) * t;

        // 对应 OctaveNoiseFunction：层 i 的种子 seed + i*1013，频率 *2^i，权重 *0.5^i，最后除以权重和。
        public static double Octave(int seed, double xzFreq, double yFreq, int octaves,
            int ix, int iy, int iz)
        {
            double sum = 0, weightSum = 0, frequency = 1, weight = 1;
            for (int i = 0; i < octaves; i++)
            {
                sum += Sample(unchecked(seed + i * 1013), xzFreq * frequency, yFreq * frequency, weight, ix, iy, iz);
                weightSum += weight;
                frequency *= 2;
                weight *= 0.5;
            }
            return sum / weightSum;
        }
    }
}
```

逐位一致的检查清单：

- 种子运算保持整数回绕：`unchecked(seed + i * 1013)`。托管版在构造 `OctaveNoiseFunction` 时就是这么算的。
- 频率与权重的累乘顺序不变：托管版在构造函数里 `frequency *= 2; weight *= 0.5`，每层的 `scale` 是 `xzFrequency * frequency`，采样时再 `context.X * scale`。这里同样先乘频率再乘坐标，不要合并成一次乘法。
- 求和顺序是层 0、1、2 …，最后一次除法 `value / weightSum`，不要换成乘倒数。
- `Math.Floor` 换成 `math.floor` 没有精度差别；`(int)` 转换在输入落在 int 范围内时一致。
- hash 中的 `uint` 乘法依赖回绕，必须放在 `unchecked` 中。
- `Noise2D`（`ProjectedXZFunction` 包 `ValueNoiseFunction`）等于把 y 固定为 0 调 `Sample(seed, scale, scale, amplitude, x, 0, z)`。这时 `ty = Smooth(0) = 0`，理论上可以跳过 y+1 层的四次 hash，结果不变；但第一版请保留完整公式，通过对比测试后再优化。

浮点方面：这里只用了 `+ - * /`、`floor`，都是 IEEE 正确舍入的运算，不涉及 `sin`、`pow` 这类有 ULP 误差的函数。只要不开 `FloatMode.Fast`（那会允许重排与乘加融合），结果应与托管版一致。具体模式见 2.6 浮点模式与确定性；Burst 2.0.0 的默认值是否仍为 `Strict`（待核实）。

## 三条改造路线

三条路线共享同一个前提：把求值拆成两段。

```
第一段（二维）  每个 (x, z) 一次：c, e, p -> offset, factor, jaggedTerm      对应 Cache2D
第二段（三维）  每个 (x, y, z) 一次：gradient, 3D 噪声, blend, slide         依赖 y
```

### 路线 A：参数化 struct，把当前公式写死

做法：写一个 `DensityEvaluator` struct，主世界公式用 C# 代码直接写出来，只把可调参数放进字段，样条控制点放进只读表。没有树，没有解释器，Burst 看到的就是一个普通的数学函数。

参数 struct 来自 `WorldGenerationSettings` 的字段拷贝（blittable）：

```csharp
internal struct DensityParams
{
    public int Seed;
    public int MinY, MaxYExclusive;
    public int GradientFromY, GradientToY;
    public double GradientFromValue, GradientToValue;
    public int BottomSlideSize; public double BottomSlideTarget;
    public int TopSlideSize, TopSlideOffset; public double TopSlideTarget;
    public double BaseNoiseStrength;
    public int NoiseOctaves;
    public double NoiseXZFrequency, NoiseYFrequency, SelectorXZFrequency, SelectorYFrequency;

    public static DensityParams From(int seed, WorldGenerationSettings s)
    {
        s.Validate();   // 与 WorldFields.CreateLearningDefaults 一致，先校验再用
        return new DensityParams { Seed = seed, MinY = s.MinY, MaxYExclusive = s.MaxYExclusive,
            GradientFromY = s.GradientFromY, GradientToY = s.GradientToY,
            GradientFromValue = s.GradientFromValue, GradientToValue = s.GradientToValue,
            BottomSlideSize = s.BottomSlideSize, BottomSlideTarget = s.BottomSlideTarget,
            TopSlideSize = s.TopSlideSize, TopSlideOffset = s.TopSlideOffset, TopSlideTarget = s.TopSlideTarget,
            BaseNoiseStrength = s.BaseNoiseStrength, NoiseOctaves = s.NoiseOctaves,
            NoiseXZFrequency = s.NoiseXZFrequency, NoiseYFrequency = s.NoiseYFrequency,
            SelectorXZFrequency = s.SelectorXZFrequency, SelectorYFrequency = s.SelectorYFrequency };
    }
}

internal struct ColumnFields { public double Offset, Factor, JaggedTerm; }   // 二维段输出
```

求值器（核心部分）：

```csharp
internal struct DensityEvaluator
{
    public DensityParams P;
    [ReadOnly] public NativeArray<SplineHeader> Splines;   // 见下文"样条扁平化"
    [ReadOnly] public NativeArray<SplineNode> Nodes;

    // 第一段：对应 WorldFields 里被 Cache2D 包裹的所有二维场。
    public ColumnFields EvalColumn(int x, int z)
    {
        double c = ValueNoiseBurst.Sample(P.Seed + 1, 0.0025, 0.0025, 1.0, x, 0, z);
        double e = ValueNoiseBurst.Sample(P.Seed + 2, 0.008,  0.008,  1.0, x, 0, z);
        double r = ValueNoiseBurst.Sample(P.Seed + 3, 0.012,  0.012,  1.0, x, 0, z);
        double p = -3 * (math.abs(math.abs(r) - 2.0 / 3.0) - 1.0 / 3.0);
        double jn = ValueNoiseBurst.Sample(P.Seed + 6, 0.035, 0.035, 1.0, x, 0, z);
        EvalSplines(c, e, p, out double offsetSpline, out double factor, out double jagged);
        return new ColumnFields
        {
            Offset = -0.50375 + offsetSpline,
            Factor = factor,
            JaggedTerm = jagged * (jn > 0 ? jn : jn * 0.5),     // HalfNegative
        };
    }

    // 第二段：对应 YClampedGradient、NoiseGradientDensity、BlendNoise、VerticalSlide。
    public double EvalVoxel(int x, int y, int z, in ColumnFields col)
    {
        double vertical = YGradient(y);
        double depth = vertical + col.Offset;
        double inner = (depth + col.JaggedTerm) * col.Factor;
        double baseTerrain = (inner > 0 ? inner : inner * 0.25) * 4.0;          // QuarterNegative, 再乘 4

        double a = ValueNoiseBurst.Octave(unchecked(P.Seed + 4),     P.NoiseXZFrequency,    P.NoiseYFrequency,    P.NoiseOctaves, x, y, z);
        double b = ValueNoiseBurst.Octave(unchecked(P.Seed + 10004), P.NoiseXZFrequency,    P.NoiseYFrequency,    P.NoiseOctaves, x, y, z);
        double s = ValueNoiseBurst.Octave(unchecked(P.Seed + 20004), P.SelectorXZFrequency, P.SelectorYFrequency, P.NoiseOctaves, x, y, z);
        double t = math.max(0, math.min(1, (s + 1) * 0.5));
        double blended = t == 0 ? a : (t == 1 ? b : a + (b - a) * t);          // 保留 t==0 / t==1 分支，见下
        double raw = baseTerrain + blended * P.BaseNoiseStrength;
        return Slide(raw, y);
    }

    double YGradient(int y)
    {
        double t = (y - P.GradientFromY) / (double)(P.GradientToY - P.GradientFromY);
        t = math.max(0.0, math.min(1.0, t));
        return P.GradientFromValue + (P.GradientToValue - P.GradientFromValue) * t;
    }

    double Slide(double value, int y)
    {
        int topEnd = P.MaxYExclusive - P.TopSlideOffset;
        if (P.BottomSlideSize > 0 && y < P.MinY + P.BottomSlideSize)
        {
            double t = math.clamp((y - P.MinY) / (double)P.BottomSlideSize, 0.0, 1.0);
            value = P.BottomSlideTarget + (value - P.BottomSlideTarget) * t;
        }
        if (P.TopSlideSize > 0 && y > topEnd - P.TopSlideSize)
        {
            double t = math.clamp((topEnd - y) / (double)P.TopSlideSize, 0.0, 1.0);
            value = P.TopSlideTarget + (value - P.TopSlideTarget) * t;
        }
        return value;
    }
    // EvalSplines 见"样条扁平化"一节
}
```

对照托管源码需要注意的点：

- `BlendedNoiseFunction` 在 `t == 1` 时直接返回 `b`，而 `a + (b - a) * 1` 在浮点下不保证等于 `b`。移植时必须保留 `t == 0` 与 `t == 1` 两个分支，否则会产生末位差异。
- 乘法顺序按托管树里 `left * right` 的顺序写：`jaggedness * HalfNegative(...)`、`(depth + jaggedTerm) * factor`、`QuarterNegative(...) * 4.0`。IEEE 乘法可交换，但保持顺序更容易对照。
- `math.max/min` 与 `Math.Max/Min` 在 NaN 输入上的行为是否一致（待核实）。正常数据没有 NaN，验收时检查输出里没有 NaN 即可。
- `math.clamp(x, 0.0, 1.0)` 是否与 `Math.Max(0, Math.Min(1, x))` 逐位一致（待核实）；对非 NaN 输入两者等价，对应 `VerticalSlideFunction.Clamp01`。

### 样条扁平化

`OriginalTerrainProvider` 生成三棵嵌套样条树。数一下节点：

- `Offset`：最外层 `c` 样条；它的 9 个点里有 5 个常量值和 4 个 `ErosionOffset`（`e` 样条，其 7 个点共用同一个 `p` 样条 `r`）。共 1 + 4 + 4 = 9 个样条。
- `Factor`：最外层 `c` 样条；4 个 `ErosionFactor`，每个有 `broad`（`e` 样条）、`r`（`p` 样条）、外层 `e` 样条。共 1 + 4 × 3 = 13 个样条。
- `Jaggedness`：`ridge`（`p` 样条）、`er`（`e` 样条）、最外层 `c` 样条，其中一个点的值是 `Multiply(ridge, er)`，也就是两个样条的乘积。共 3 个样条。

合计 25 个样条，每个样条的坐标输入都是三个二维场 `c`、`e`、`p` 之一。这给了一个很有利的做法：**不做递归，按拓扑序自底向上，把每个样条求值一次，结果存进一个小数组**。

```csharp
internal enum ValueKind : byte { Constant, Spline, Product }
internal enum CoordInput : byte { Continents, Erosion, Ridges }

internal struct SplineHeader
{
    public int FirstNode, NodeCount;   // 在 Nodes 里的区间，Location 严格递增
    public CoordInput Coordinate;
}

internal struct SplineNode             // 对应 CubicSplinePoint
{
    public double Location, Derivative;
    public ValueKind Kind;
    public double Value;               // Kind == Constant 时使用
    public int ChildA, ChildB;         // Kind == Spline 用 ChildA；Product 用 ChildA * ChildB（样条下标）
}
```

约定：样条在 `Splines` 数组里按"被引用者在前"排序（子样条下标小于父样条），这样顺序遍历一遍就保证子样条的结果已经算好。托管侧的压平器遍历 `CubicSplineFunction`，用"对象引用 -> 下标"的字典去重，这样 `r` 这类被 7 个点共享的样条只存一份。

求值（不递归）：

```csharp
// results[i] 是第 i 个样条在当前列的值。
static double EvalSpline(in SplineHeader h, NativeArray<SplineNode> nodes, NativeArray<double> results, double input)
{
    int first = h.FirstNode, last = h.FirstNode + h.NodeCount - 1;
    if (input < nodes[first].Location) return LinearExtend(nodes[first], results, input);
    if (input >= nodes[last].Location) return LinearExtend(nodes[last], results, input);

    int low = first, high = last;                   // 与 CubicSplineFunction.FindSegment 相同的二分
    while (low + 1 < high)
    {
        int mid = (low + high) / 2;
        if (input < nodes[mid].Location) high = mid; else low = mid;
    }
    SplineNode left = nodes[low], right = nodes[low + 1];
    double length = right.Location - left.Location;
    double t = (input - left.Location) / length;
    double lv = NodeValue(left, results), rv = NodeValue(right, results);
    double delta = rv - lv;
    double p = left.Derivative * length - delta;
    double q = delta - right.Derivative * length;
    return (lv + (rv - lv) * t) + t * (1.0 - t) * (p + (q - p) * t);
}

static double NodeValue(in SplineNode n, NativeArray<double> results) =>
    n.Kind == ValueKind.Constant ? n.Value
    : n.Kind == ValueKind.Spline ? results[n.ChildA]
    : results[n.ChildA] * results[n.ChildB];          // Product：ridge * er，左右顺序与托管树一致

static double LinearExtend(in SplineNode n, NativeArray<double> results, double input) =>
    NodeValue(n, results) + n.Derivative * (input - n.Location);
```

`EvalSplines` 的外层：在 `Allocator.Temp` 上分配 25 个 double 的 `results`，按下标顺序算每个样条（坐标取 `c/e/p` 之一），最后三个根样条的下标分别是 Offset、Factor、Jaggedness 的最外层样条。每列一次，25 个样条的开销远小于体素级的三个 `Octave` 噪声。

和托管版的对应点：

- 托管版是惰性求值，只算当前所在区间两端的子样条；扁平版把 25 个样条全算一遍。各样条的值只取决于自己的坐标输入和子样条的值，所以多算几个不会改变任何一个样条的结果。
- 本项目所有 `CubicSplinePoint` 都没有传 `derivative`（取默认 0），但表里保留了 `Derivative` 字段，以后改公式不用改格式。
- 压平器要读 `CubicSplineFunction` 的私有字段 `coordinate` 与 `points`。要么给这个类加 `internal` 访问器（对现有代码的改动，由你决定），要么另写一份镜像 `OriginalTerrainProvider` 的表构建代码，再用逐点测试保证两边一致。

### 路线 A 小结

| 项目 | 评价 |
| --- | --- |
| 改公式的成本 | 改 C# 代码并重新编译；改参数（频率、八度、slide）只改 `DensityParams`，不用重编 |
| 运行性能 | 没有解释开销，最容易被 Burst 优化 |
| 编译时间 | 一个中等大小的函数，最短 |
| 调试难度 | 最低：普通代码，可对着托管版逐段对照 |
| 缺点 | 公式写死；新增一种节点要改求值器；与"节点树"的数据驱动思路脱节 |

### 路线 B：压平成指令数组 + Job 内解释器

做法：在托管侧把对象树编译成线性指令序列（寄存器式），Job 里用一个 `switch` 循环执行。公式变化只需要重新编译指令数组，不用改 Job 代码。

指令集设计（按 FinalDensity 实际用到的节点）：

| Op | 含义 | 操作数 |
| --- | --- | --- |
| `Const` | `reg[dst] = K` | K |
| `Noise2D` | 二维 `ValueNoise`（y 固定为 0） | 种子下标、scale、amplitude |
| `Octave3D` | 分形噪声 | seed、xz 频率、y 频率、八度数 |
| `Add` `Sub` `Mul` | 二元算术 | A、B |
| `Abs` `HalfNeg` `QuarterNeg` | 一元函数 | A |
| `YGradient` | 与 y 有关的渐变 | 四个参数在 K/表中 |
| `Spline` | 查样条表 | 样条下标，坐标寄存器 A |
| `Blend` | `t` 混合，含 `t==0`/`t==1` 分支 | A、B、selector |
| `Slide` | 垂直渐变 | 参数表下标 |
| `Out` | 最终输出 | A |

```csharp
internal enum Op : byte { Const, Noise2D, Octave3D, Add, Sub, Mul, Abs, HalfNeg, QuarterNeg,
                          YGradient, Spline, Blend, Slide, Out }

internal struct Instr
{
    public Op Op;
    public int Dst, A, B, C;     // 寄存器下标或表下标
    public double K;             // 只有一个立即数；Noise2D、Octave3D、YGradient、Slide 等多参数指令
                                 // 要把参数放进旁表，A/B/C 存表下标
}

// regs 是长度 >= 指令数的 double 缓冲（Job 内用 Allocator.Temp 分配或每线程一份）。
static double Run(NativeArray<Instr> prog, int count, NativeArray<double> regs, int x, int y, int z)
{
    for (int i = 0; i < count; i++)
    {
        Instr ins = prog[i];
        switch (ins.Op)
        {
            case Op.Const:  regs[ins.Dst] = ins.K; break;
            case Op.Add:    regs[ins.Dst] = regs[ins.A] + regs[ins.B]; break;
            case Op.Mul:    regs[ins.Dst] = regs[ins.A] * regs[ins.B]; break;
            // ... 其余 Op
            case Op.Out:    return regs[ins.A];
        }
    }
    return 0;
}
```

编译器（托管侧）要做的事：

1. 遍历 `IDensityFunction` 树（同样需要读私有字段，见上文），按对象引用做公共子表达式合并。托管树里的 `Cache2D` 节点在这里变成"这个子表达式只依赖 (x, z)"的标记。
2. 给每条指令算"是否依赖 y"：只依赖 (x, z) 的指令归入二维段，其余归入三维段。二维段每列执行一次，结果写进列数组，三维段按体素或角点执行。这就是 `Cache2D` 的对应物。
3. `Blend` 不能因为寄存器已经都算好就省掉 `t==0`/`t==1` 分支，原因同路线 A。

| 项目 | 评价 |
| --- | --- |
| 改公式的成本 | 最低：只改托管侧的树，重新编译成指令；Job 代码不变 |
| 运行性能 | 每条指令一次分发加寄存器读写，Burst 难以跨指令优化；相对路线 A 的差距要实测，不预设倍数 |
| 编译时间 | Job 本身小，编译快 |
| 调试难度 | 较高：需要同时验证树编译器、指令解释器、Burst 三层；指令序列要有反汇编打印工具 |
| 缺点 | 要自己写和维护小型 VM；新节点要同时改编译器和解释器 |

### 路线 C：泛型结构体组合（单态化）

做法：每种节点写成实现同一接口的 `struct`，父节点用泛型参数持有子节点类型。接口只作为泛型约束使用，不会产生虚调用；Burst 对每个具体类型组合生成专用代码，能跨节点内联（见 2.9 泛型与接口）。

```csharp
internal interface IDensity { double Sample(int x, int y, int z); }

internal struct Const : IDensity
{
    public double V;
    public double Sample(int x, int y, int z) => V;
}

internal struct Add<A, B> : IDensity where A : unmanaged, IDensity where B : unmanaged, IDensity
{
    public A Left; public B Right;
    public double Sample(int x, int y, int z) => Left.Sample(x, y, z) + Right.Sample(x, y, z);
}

internal struct Octave : IDensity
{
    public int Seed, Octaves; public double XZ, Y;
    public double Sample(int x, int y, int z) => ValueNoiseBurst.Octave(Seed, XZ, Y, Octaves, x, y, z);
}

// Cache2D 的对应物：节点不自己算，而是读调用方预先填好的列数据。
internal struct ColumnOffset : IDensity
{
    public ColumnFields Col;    // 由二维段 Job 的结果装入
    public double Sample(int x, int y, int z) => Col.Offset;
}

[BurstCompile]
internal struct DensityJob<TDensity> : IJobParallelFor where TDensity : unmanaged, IDensity
{
    public TDensity Density;
    [WriteOnly] public NativeArray<double> Output;
    public void Execute(int index) { /* 把 index 换算成 x,y,z 后调用 Density.Sample */ }
}

// 泛型 Job 要让 Burst 提前知道具体类型：
// [assembly: RegisterGenericJobType(typeof(DensityJob<MyFinalDensity>))]
```

要点与限制：

- 泛型 Job 的具体实例需要被 Burst 发现。直接在 C# 里写出 `new DensityJob<Concrete>()` 并调度通常可以被发现；不要通过泛型辅助方法间接调度（手册明确说 Burst 不支持这种写法，Editor 里能跑、Player 构建里可能发现不了实例）。程序集级属性 `RegisterGenericJobType` 登记的是 Job 反射数据，不能当作 Burst 发现实例的保证，详见 2.9 泛型与接口。
- 完整公式会形成很长的嵌套类型，例如 `Add<Mul<..., Const>, Octave>` 一层层套下去。可以用 `using Alias = ...` 起别名，或者用一个 `Build()` 工厂方法配合 `var`。
- 样条仍然适合用路线 A 的扁平表来表示，而不是把每个点变成一个类型；否则 25 个样条的类型组合会让编译时间和类型数量失控。
- 变更任何一处结构（增加节点、换节点类型）都会产生新的类型实例，Burst 要重新编译这一个实例。

| 项目 | 评价 |
| --- | --- |
| 改公式的成本 | 改泛型组合并重新编译；参数可以运行时改 |
| 运行性能 | 理论上与路线 A 相当，因为都是编译期展开的直线代码 |
| 编译时间 | 随类型组合增大而增长，三条路线里最不可控 |
| 调试难度 | 编译错误信息长、Burst Inspector 里函数名极长（见 2.5 Burst Inspector 与调试） |
| 适合场景 | 公式经常变、又要求零解释开销的场合；当前项目的公式固定，收益不明显 |

### 三条路线对比

| 维度 | A 参数化 struct | B 指令解释器 | C 泛型组合 |
| --- | --- | --- | --- |
| 实现量 | 小 | 大（编译器 + VM） | 中 |
| 改公式 | 改代码 | 改托管树，Job 不变 | 改类型组合 |
| 改参数 | 不重编 | 不重编 | 不重编 |
| 运行开销 | 最低 | 分发开销，需实测 | 与 A 相近 |
| 编译时间 | 短 | 短 | 可能很长 |
| 调试 | 简单 | 三层验证 | 类型名与报错冗长 |
| 对现有树的依赖 | 只需读参数与样条点 | 需要完整遍历树 | 需要手工同步 |

本项目建议先做 A。理由是公式固定且体量不大，A 的验证链最短；B 和 C 只在"公式要频繁变或要做成数据驱动"时才值得。

## Cache2D 在 Job 世界里的对应物

`ColumnCacheFunction` 记的是"上一次的 (X, Z) 与结果"：只对"同一列连续采样"的访问顺序有效，所以 `VoxelChunk.Fill` 和 `ChunkDensitySampler.Fill` 都把 Y 放在最内层循环。它有可变状态，也就是为什么每个线程都得用自己的 `WorldFields`。

Job 里的替代方案是把"缓存"变成显式的数据阶段：

```
Job 1 二维场预计算   工作项 = 一个角点列 (ix, iz)      输出 NativeArray<ColumnFields>，长度 nx*nz
Job 2 三维采样       工作项 = 一个角点列或一个角点       只读 ColumnFields，输出角点密度
```

这样没有可变缓存，也不再依赖遍历顺序；每个二维场在每列只算一次，是严格的"一列一次"，而不是"碰巧连续才命中"。`ChunkDensitySampler.Fill` 里角点列数是 `nx * nz`，其中 `nx = cellsX + 1`、`nz = cellsZ + 1`；区块 16 格宽、cell 宽 4 且区块起点对齐到 4 的倍数时是 5 × 5，起点不对齐（`originX + StartX` 不是 4 的倍数）时 `cellsX` 可达 5，列数最多到 6 × 6。两个 Job 的接线细节见 3.3。

## WorldGenerationSettings 如何传入 Job

- `WorldGenerationSettings` 是 `[Serializable] sealed class`，所有字段都是 `int`/`double`，但它是引用类型，不能放进 Job。
- 在主线程用 `DensityParams.From(seed, settings)` 一次性拷成 blittable struct，再放进 Job 字段。`VoxelWorldPreview.CreatePipeline` 已经用 `generationSettings.Clone()` 做快照，原理相同，只是 `Clone` 之后还是 class。
- 样条表（`Splines`、`Nodes`）与参数 struct 是两类数据：参数每次生成可能变，样条表在公式不变时可以跨区块、跨帧复用，用 `Allocator.Persistent` 创建一次并在世界销毁时 `Dispose`（见 1.5 内存分配器与生命周期）。
- `GetCellAliasingWarning` 只读设置值，依旧在托管侧调用，不需要进 Job。

## 确定性

- 同一次运行内，相邻区块在边界处各自重算角点，只要它们走的是同一份 Burst 代码、同一份 `DensityParams`，结果就逐位一致（见 2.6 浮点模式与确定性）。这一点比"与托管版一致"更重要，因为不一致会在区块接缝处产生裂缝。
- 编辑器里 Burst 的 JIT 编译和 Player 里的 AOT 编译、不同 CPU 架构，是否对这条代码路径给出逐位相同的结果，取决于编译器的浮点设置。避免依赖 `sin/cos/pow` 这类函数，不开 `FloatMode.Fast`。同一二进制、同一机器上 `Strict`（默认）即可满足"相邻区块逐位一致"；若要求跨平台、跨架构逐位一致，按 2.6 的结论设置 `FloatMode.Deterministic`（更新日志写明 1.8.25 起正式支持，见 2.6）。
- 不要把同一个世界的一部分区块用托管版算、另一部分用 Burst 版算，除非已验证两者逐位一致。

## 验收

托管版是标准答案，不要删除，也不要改动它的公式。

### 逐点对比

在固定种子（例如 1、12345、777）下，用同一批坐标分别求托管值和 Burst 值：

```csharp
// 托管侧：每次比较用新建的 WorldFields，因为其中的列缓存带可变状态。
var managed = WorldFields.CreateLearningDefaults(seed, settings).FinalDensity;
double expected = managed.Sample(new DensityContext(x, y, z));
// Burst 侧：用路线 A 的 EvalColumn + EvalVoxel（Run 单线程即可）。
double actual = evaluator.EvalVoxel(x, y, z, evaluator.EvalColumn(x, z));
```

坐标取样要覆盖：

- 随机点，x/z 范围包含负数（hash 里 `(uint)x` 与 `floor` 在负数上最容易出错）。
- 世界底部和顶部的 slide 带（`y` 靠近 `MinY` 与 `MaxYExclusive - TopSlideOffset`）。
- 样条的外推区（`c`、`e`、`p` 落在第一个控制点之前和最后一个控制点之后）。
- `BlendNoise` 的 `t == 0` 与 `t == 1` 两种情况（可以用参数让 selector 恒定来构造）。
- 单个噪声层、单个样条、二维段输出、最终值，分层各比一遍，出错时才能定位。

判据分两级：

1. 首选逐位一致：`BitConverter.DoubleToInt64Bits(expected) == BitConverter.DoubleToInt64Bits(actual)`。纯 `+ - * /`、`floor` 的算法在严格浮点模式下应当可以做到。
2. 若逐位不一致，退而求其次：`|expected - actual| <= 1e-12 * max(1, |expected|)`（容差数值是起点，不是依据，待用实测的最大偏差调整），并且统计"符号翻转"次数，即 `expected > 0` 与 `actual > 0` 不同的点数。符号翻转必须为 0，否则体素会变化。

同时检查输出里没有 `NaN` 和 `Infinity`。

### 体素级对比

用 `ChunkDensitySampler.Fill` 的托管结果作为基准区块，用 Burst 版生成同一区块，逐字节比较 `VoxelChunk` 的内容和 `SolidCount`。这一步同时验证了 3.3 的 cell 插值，所以放在 3.3 完成之后做一次整体回归。

### 性能对比表模板

由读者在自己的机器上填写，记录硬件、Unity 版本、是否在编辑器、Burst 是否启用（`Jobs > Burst > Enable Compilation`，待核实菜单名称）、区块高度、worker 数。

| 场景 | 区块数 | 区块高度 | cell 插值 | 托管版耗时 (ms) | Burst 版耗时 (ms) | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| 只算二维段 | | | 不适用 | | | |
| 一列 y 方向全高密度 | | | 关 | | | |
| 一个区块 | | | 开 | | | |
| 一个区块 | | | 关 | | | |
| 整个世界 | | | 开 | | | |
| 首次调用（含 JIT 编译） | | | 开 | | | 编辑器内第一次运行 |

测量时分开记录 JIT 编译时间与稳态时间，并用 Profiler 看是否有 Job 之外的瓶颈（见 3.5 调度管线与 Profiling）。

## 推荐实施顺序

1. 保留托管树，当作测试基准。
2. 写 `ValueNoiseBurst`，先通过单点逐位对比测试（只测 `Sample` 与 `Octave`）。
3. 移植 `YGradient`、`Blend`、`Slide` 和 `HalfNegative`/`QuarterNegative`，同样单点对比。
4. 写样条压平器与扁平求值，对比 `Offset`、`Factor`、`Jaggedness` 三个二维输出。
5. 合成 `DensityEvaluator`，对比最终密度，达标后接入 3.3 的 Job 链。
6. 在 Profiler 里确认瓶颈。只有当公式需要频繁变化，或者 A 的代码维护已成负担时，再评估 B 或 C。

## 小结

- 阻碍 Burst 的是 class 对象图、接口虚调用、`Func` 委托、可变缓存；算术与 hash 都能直接搬。
- 当前 `FinalDensity` 只用到少数几种节点，且结构清晰地分成"二维段"与"三维段"。
- 噪声原样移植，保持整数 hash、频率累乘、权重累加的顺序，不用 `Unity.Mathematics.noise`。
- 样条用"节点表 + 子样条下标 + 拓扑序自底向上求值"，不需要递归。
- `Cache2D` 的 Job 对应物是显式的二维场预计算阶段。
- 先做路线 A；验收以托管版为基准，逐点比对并要求符号翻转为 0。

## 自测题

1. 为什么不能用 `Unity.Mathematics.noise.cnoise` 代替 `ValueNoiseFunction`？
   答：它们是不同的噪声算法，值域与形状不同，地形会整体改变，也失去了托管版作为验收基准的意义。
2. 当前 `FinalDensity` 里哪些节点没有被用到，因此第一版可以不移植？
   答：`ClampFunction`、`RangeChoiceFunction`、`CacheOnceFunction` 以及 `DensityFunctions.Min/Max`。
3. 扁平化样条为什么选择拓扑序自底向上求值，而不是递归？
   答：嵌套深度只有三层、总共 25 个样条，且所有样条的输入都是二维场。按"子样条在前"排序后顺序遍历一遍就能避免递归，不依赖 Burst 对递归的支持（待核实）。
4. `BlendedNoiseFunction` 的 `t == 1` 分支为什么必须保留？
   答：`a + (b - a) * 1` 在浮点下不保证等于 `b`，去掉分支会产生末位差异，破坏逐位一致。
5. `ColumnCacheFunction` 在 Job 世界里怎么替代？
   答：用一个显式的二维场预计算 Job，输出每个角点列的 `ColumnFields`，三维采样 Job 只读它。

## 参考

- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Density\（IDensityFunction、DensityContext、UnaryFunction、BinaryFunction、ClampFunction、RangeChoiceFunction、YGradientFunction、ValueNoiseFunction、OctaveNoiseFunction、BlendedNoiseFunction、CubicSplineFunction、CubicSplinePoint、VerticalSlideFunction、ColumnCacheFunction、CacheOnceFunction、ProjectedXZFunction、OriginalTerrainProvider、DensityFunctions、WorldFields、WorldGenerationSettings）
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkDensitySampler.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelChunk.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelWorldPreview.cs
- D:\UnityHub\Project\程序化生成\Library\PackageCache\com.unity.burst@626e66ab421b\Runtime\TypeForwarders.cs

