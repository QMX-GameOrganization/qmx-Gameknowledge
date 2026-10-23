---
title: "2.3 Unity.Mathematics"
description: 介绍 Burst 配套的数学库 Unity.Mathematics：向量与矩阵类型、math 函数、noise、Random，以及整数除法、精度和与本项目 ValueNoiseFunction 的移植对照。
sidebar:
  order: 3
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x / Mathematics 1.3.x 为主线；Unity Mathematics 从 Unity 6.5 起成为引擎内置模块，`Unity.Mathematics` 命名空间无需安装包即可使用，API 文档并入核心 Scripting API。本项目 Unity 7000.0.0a8 属于该情形，API 名称不变。

## 要点

- `Unity.Mathematics` 是 Burst 友好的数学库：类型名全小写（`float3`、`int4`、`quaternion`），写法接近 HLSL，Burst 把这些类型当作内建类型，能直接映射到 SIMD 寄存器。
- Unity 手册的建议：Burst 编译的代码里优先用 Unity Mathematics；不走 Burst 的代码里优先用 UnityEngine 的数学 API。
- `math` 静态类提供与 HLSL 对应的函数；`math.select` 是向量化友好的条件选择；`noise` 提供 Perlin/Simplex/Worley；`Random` 是只有 32 位状态的 xorshift 生成器。
- 和 `Mathf` 不同的地方很多（比如 `math.lerp` 不钳制 `t`），迁移时要逐个核对。
- 本项目的 `ValueNoiseFunction` 是整数哈希加三线性插值的值噪声，不等同于 `noise.cnoise`。换用库函数会改变地形，所以建议先原样移植。

## 为什么 Burst 推荐它

- `float2/3/4`、`int2/3/4`、`uint2/3/4`、`bool2/3/4` 有一等公民的 SIMD 优化（Burst 手册 C#/.NET type support），推荐尽量用 4 宽的类型。
- `math` 里的函数是 Burst 的 intrinsic：`math.sqrt`、`math.rcp`、`math.abs` 等会被映射到对应的 CPU 指令；`[BurstCompile(FloatPrecision, FloatMode)]` 也会影响 `sin/cos/exp/log/pow` 等函数的精度实现。
- 纯 struct，无托管对象，适合放进 NativeContainer 和 Job 字段。

## 类型一览

| 类别 | 类型 |
| --- | --- |
| 浮点向量 | `float2` `float3` `float4`、`double2` `double3` `double4` |
| 整数向量 | `int2` `int3` `int4`、`uint2` `uint3` `uint4` |
| 布尔向量 | `bool2` `bool3` `bool4` |
| 半精度 | `half`，以及 `half2` `half3` `half4`（Burst 手册提到字符串插值不支持 half 向量，说明这些类型存在） |
| 矩阵 | `float2x2` `float3x3` `float4x4`（以及 double 版本） |
| 旋转 | `quaternion` |

### 构造与 swizzle

```csharp
using Unity.Mathematics;

float3 a = new float3(1f, 2f, 3f);
float3 b = 5f;                 // 标量隐式广播到全部分量
float4 c = new float4(a, 1f);  // 向量 + 标量拼接
float3 d = a.zyx;              // swizzle：分量重排
float2 e = a.xz;               // 取子集
a.xz = new float2(9f, 8f);     // swizzle 也可以赋值（分量不重复时）
float3 f = a * b + d;          // 运算符都是逐分量的
```

注意：`float4x4` 的 `*` 是逐分量乘法，矩阵乘法要用 `math.mul(m, v)`（手册 Unity Mathematics APIs 里明确写了这一点），详见下一节"矩阵、四元数与变换"。

### 与 UnityEngine 类型互转

`float3` 与 `Vector3`、`float2` 与 `Vector2`、`float4` 与 `Vector4`、`quaternion` 与 `Quaternion`、`float4x4` 与 `Matrix4x4` 之间有隐式转换，用在编辑器、渲染层与 Job 之间交换数据时很方便：

```csharp
Vector3 v = transform.position;
float3 p = v;                   // 隐式转换
transform.position = p + new float3(0, 1, 0);
```

该隐式转换的细节没有在本次读过的页面里逐项核对（待核实）；使用时以编译器提示为准。

## 矩阵、四元数与变换

本节内容取自 Unity 手册 Unity Mathematics APIs 页，以及 Mathematics 1.3.2 的 API 页（`RigidTransform`、`MinMaxAABB`、`math` 的重载列表）。体素生成里最常见的用途是区块包围盒、实体或相机变换，本项目目前的 `WorldGen/Density` 代码没有用到这些类型，这一节是为之后的网格与实体部分准备。

### 构造 `float4x4`

手册的做法是用 `float4x4` 的构造函数：可以把一个值赋给全部元素，也可以逐个设置 16 个元素；示例里把四个 `float4`（变量名 `c0` 到 `c3`）传进构造函数：

```csharp
using Unity.Mathematics;

// 手册示例：四个 float4 构造单位矩阵
var c0 = new float4(1f, 0f, 0f, 0f);
var c1 = new float4(0f, 1f, 0f, 0f);
var c2 = new float4(0f, 0f, 1f, 0f);
var c3 = new float4(0f, 0f, 0f, 1f);
var m = new float4x4(c0, c1, c2, c3);
```

示例没有逐个说明各构造重载的参数顺序，涉及非对称矩阵时以 API 页和实测为准（待核实）。

### `*` 是逐分量乘，`math.mul` 才是矩阵乘

手册明确写道：`Unity.Mathematics` 与 `UnityEngine` 对 `*` 的定义不同，`float4x4` 的 `*` 实现的是逐分量（componentwise）乘法。手册的例子：全 1 矩阵乘以对角线为 0.5 的矩阵，结果只剩对角线上的 0.5，其余位置与 0 相乘变成 0。

```csharp
float4x4 result = f4x4_Ones * f4x4_HalfIdentity;   // 手册示例，两个变量是手册里预设的矩阵
// result 对角线为 0.5，其余为 0：这是逐分量乘，不是矩阵乘
```

做矩阵乘法必须用 `math.mul`。这是从 `Matrix4x4` 迁移过来时最容易踩的坑：`a * b` 能编译，但结果完全不同。

### `math.mul` 的列向量与行向量约定

手册对 `math.mul` 的描述：

- `math.mul(float4x4, float4)`：把 `float4` 当成 4x1 的列向量，做 4x4 乘 4x1，返回 4x1 的列向量（还是 `float4`）。
- `math.mul(float4, float4x4)`：把 `float4` 当成 1x4 的行向量，做 1x4 乘 4x4，返回 1x4 的行向量。手册说明 Unity Mathematics 把行向量存放在 `float4` 里，没有单独的行向量类型。

```csharp
float4 result1 = math.mul(f4x4, f4);   // 4x4 * 4x1 = 4x1，矩阵在左，列向量
float4 result2 = math.mul(f4, f4x4);   // 1x4 * 4x4 = 1x4，向量在左，行向量
```

所以同一个 `float4` 放在左边还是右边，意义不同，两种写法结果一般不同。参数顺序就是数学上的乘法顺序。

### 四元数：`AxisAngle`、`Euler` 与 `math.mul`

- `quaternion.AxisAngle(float3 axis, float angle)`：先给旋转轴，再给角度，角度单位是弧度而不是度。
- `quaternion.Euler(x, y, z)`：三个角度同样是弧度，手册示例里每个参数都用 `math.radians(...)` 转换。
- 四元数与四元数相乘用 `math.mul`，和矩阵、向量一样，不用 `*`。

```csharp
var axis = new float3(0f, 1f, 0f);
var q = quaternion.AxisAngle(axis, math.radians(45f));
var orientation = quaternion.Euler(
    math.radians(45f),
    math.radians(90f),
    math.radians(180f));
var result = math.mul(q, orientation);   // 手册示例：四元数相乘
```

手册没有在这一页说明 `math.mul(q1, q2)` 表示"先应用哪一个"的组合顺序，也没有说明 `Euler` 三参数重载的默认旋转顺序（待核实）。需要确定顺序时，到 `quaternion` 与 `math` 的 API 页查对应方法的说明，或用已知例子实测。

向量旋转可用 `math.rotate(quaternion, float3)`（API 页描述为"用单位四元数旋转一个向量"）。四元数插值用 `math.slerp` 与 `math.nlerp`，见下面的函数表。

### `RigidTransform`

`Unity.Mathematics.RigidTransform` 是"刚体变换"结构体（只含旋转与平移，API 页描述为 a rigid transformation type），标了 `[Serializable]`。

| 成员 | 说明 |
| --- | --- |
| 字段 `rot`、`pos` | 旋转部分（`quaternion`）、平移部分（`float3`） |
| 字段 `identity` | 单位变换 |
| 构造 `RigidTransform(quaternion, float3)` | 单位四元数加平移 |
| 构造 `RigidTransform(float3x3, float3)` | 旋转矩阵加平移 |
| 构造 `RigidTransform(float4x4)` | 从矩阵构造，API 页写明假定矩阵是正交归一的（orthonormal） |
| 静态方法 | `AxisAngle(float3, float)`、`Euler(...)` 与 `EulerXYZ`、`EulerZXY` 等各旋转顺序版本、`RotateX/Y/Z(float)`、`Translate(float3)` |

API 页对 `AxisAngle` 的描述：围绕单位轴旋转，角度是弧度，从旋转轴方向朝原点看为顺时针。`EulerZXY` 的描述里写着"这是 Unity 的默认旋转顺序"。

配套的 `math` 函数：`math.transform(RigidTransform, float3)`（变换一个点）、`math.rotate(RigidTransform, float3)`（只旋转向量）、`math.inverse(RigidTransform)`（求逆）。API 页对 `math.transform` 的描述是"transforming a float3 point by a RigidTransform"。

不含缩放，所以不适合需要非均匀缩放的情形，那时仍用 `float4x4`。

### `MinMaxAABB`

`MinMaxAABB` 在命名空间 `Unity.Mathematics.Geometry` 下，不在 `Unity.Mathematics` 本体里，需要 `using Unity.Mathematics.Geometry;`（也要注意 1.3 的 API 路径是 `Unity.Mathematics.Geometry.MinMaxAABB`，`Unity.Mathematics.MinMaxAABB` 的页面不存在）。API 页描述它是以最小点和最大点存储的轴对齐包围盒（AABB）。

| 成员 | 说明 |
| --- | --- |
| 构造 `MinMaxAABB(float3 min, float3 max)` | 用最小点和最大点构造 |
| 字段 `Min`、`Max` | 包围盒最小点、最大点 |
| 属性 `Center`、`Extents`、`HalfExtents`、`SurfaceArea`、`IsValid` | 中心、全尺寸、半尺寸、表面积、是否有效 |
| `Contains(float3)`、`Contains(MinMaxAABB)` | 点或另一个包围盒是否被完全包含 |
| `Overlaps(MinMaxAABB)` | 是否与另一个包围盒重叠 |
| `Encapsulate(float3)`、`Encapsulate(MinMaxAABB)` | 扩大包围盒以容纳点或包围盒 |
| `Expand(float)` | 按给定的带符号距离扩张 |
| `CreateFromCenterAndExtents`、`CreateFromCenterAndHalfExtents` | 从中心与（半）尺寸创建 |

```csharp
using Unity.Mathematics;
using Unity.Mathematics.Geometry;

// 一个 16x16x16 区块在世界坐标里的包围盒（教学示意，未在 Unity 内编译）
static MinMaxAABB ChunkBounds(int3 chunkCoord)
{
    var min = new float3(chunkCoord.x * 16, chunkCoord.y * 16, chunkCoord.z * 16);
    return new MinMaxAABB(min, min + new float3(16f));
}
```

`Contains` 等方法对"边界上的点算不算在内"的细节，API 页没有展开，做边界判断前先用小测试确认（待核实）。本项目用的 Unity 7000.0.0a8 中 `Unity.Mathematics.Geometry` 是否仍在同一命名空间没有在该版本核对（待核实），1.3.2 文档是依据。

## `math` 函数分类

| 类别 | 函数 |
| --- | --- |
| 绝对值 / 范围 | `abs` `clamp` `saturate` `min` `max` `sign` |
| 插值 / 映射 | `lerp` `unlerp` `remap` `smoothstep` `step` |
| 取整 | `floor` `ceil` `round` `frac` `trunc` |
| 条件 | `select` `any` `all` |
| 向量 | `dot` `cross` `length` `lengthsq` `normalize` `distance` |
| 乘加 / 倒数 | `mad` `rcp` `rsqrt` `sqrt` |
| 超越函数 | `sin` `cos` `tan` `exp` `log` `pow` |
| 位运算 | `tzcnt` `lzcnt` `countbits` `bitmask` `reversebits` `rol` `ror` |
| 位模式重解释 | `asuint` `asint` `asfloat` `aslong` `asulong` `asdouble` |
| 正弦余弦 | `sincos` |
| 分量重排 | `shuffle` |
| 四元数插值 | `slerp` `nlerp` |
| 2 的幂与对数 | `ceilpow2` `ceillog2` `floorlog2` |
| 矩阵与变换 | `mul` `transpose` `inverse` `determinant` `transform` `rotate` |
| 归约 | `csum` `cmin` `cmax` |
| 哈希 | `hash` |

#### 本次对照 1.3.2 API 页核实的函数

下面这些已在 `Unity.Mathematics.math` 的 API 页（1.3.2）里确认存在，签名取自页面上的重载列表：

- 位模式重解释（不是数值转换，只是把同样的位当成另一种类型）：`asuint(float)`、`asuint(int)`、`asint(float)`、`asint(uint)`、`asfloat(int)`、`asfloat(uint)`，以及对应的 2/3/4 分量向量重载（如 `asuint(float2)` 返回 `uint2`）；64 位的有 `aslong(double)`、`aslong(ulong)`、`asulong(double)`、`asulong(long)`、`asdouble(long)`、`asdouble(ulong)`。常用于把浮点结果按位取出做哈希或 golden test（见 2.6 浮点模式与确定性）。
- `sincos(float x, out float s, out float c)`：一次得到正弦与余弦；API 页还有 `double2`、`float3` 等向量重载，向量版返回逐分量结果。
- `shuffle(float4 left, float4 right, ShuffleComponent x, ShuffleComponent y, ShuffleComponent z, ShuffleComponent w)`：从两个 `float4` 的分量里按指定顺序挑选，返回 `float4`；另有只给 1、2、3 个 `ShuffleComponent` 的重载（返回标量或对应宽度的向量），以及 `int`、`uint` 等类型的版本。`ShuffleComponent` 是 `math` 里的嵌套枚举，具体成员名没有逐个核对（待核实）。
- `slerp(quaternion q1, quaternion q2, float t)`：球面线性插值；`nlerp(quaternion q1, quaternion q2, float t)`：归一化线性插值。API 页的描述均只说明"使用插值参数 t 在两个四元数之间插值"，没有给出 `t` 是否钳制（待核实）。
- `ceilpow2`：大于等于输入的最小 2 的幂，重载覆盖 `int`、`long`、`uint`、`ulong` 以及 `int2/3/4`、`uint2/3/4`。适合把容量向上取整到 2 的幂。
- `ceillog2`、`floorlog2`：以 2 为底对数的向上、向下取整，重载覆盖 `int`、`uint` 与对应向量。
- `reversebits(uint)`、`rol(uint, int)`、`ror(uint, int)`、`lzcnt(uint)`、`countbits(uint)`：位反转、循环左右移、前导零计数、置位计数。
- 矩阵与变换：`transpose(float4x4)`、`determinant(float4x4)`、`inverse`（有 `float2x2`、`float3x3`、`float4x4`、`double` 版本、`quaternion`、`RigidTransform` 等重载）、`transform(float4x4, float3)`、`rotate(float4x4, float3)`、`rotate(quaternion, float3)`。

其余没有列在这里的函数名是 HLSL 惯例名，或此前核实过但不在本次范围，使用时以 IDE 补全为准。

#### 此前核实过的函数

我核实过存在的函数：`remap`（`remap(srcStart, srcEnd, dstStart, dstEnd, x)`，非钳制线性重映射）、`bitmask(bool4)`（返回 `int`，每分量 1 位、LSB 在前，`x` 在第 0 位）、`tzcnt`（`int/uint/long/ulong` 及向量重载，返回尾部 0 的个数）、`hash`（返回 `uint`，对各种向量、矩阵类型有重载，另有 `hash(void* pBuffer, int numBytes, uint seed = 0)`）、`select(falseValue, trueValue, test)`、`smoothstep(xMin, xMax, x)`、`unlerp(start, end, x)`、`sign`。其余函数名是 HLSL 惯例名，我没有逐个查阅 API 页，使用时以 IDE 补全为准。

几个值得记住的点：

- `math.lerp(a, b, t)` 不钳制 `t`；要钳制先 `saturate(t)`。
- `math.unlerp(a, b, x)` 是 `lerp` 的反函数，同样不钳制。
- `math.smoothstep(min, max, x)` 的参数是边界和输入值，与 `Mathf.SmoothStep(from, to, t)` 的含义不同（后者是在 `from`→`to` 之间平滑插值）。
- `math.mad(a, b, c)` 是 `a * b + c`，可映射到 FMA 指令（取决于 CPU 目标和 `FloatMode`）。

### `math.select` 与三元运算符

```csharp
float s = flag ? a : b;                         // 标量：编译器可能生成分支或条件移动
float4 v = math.select(falseV, trueV, mask4);   // 向量：逐分量选择，无分支
```

- 参数顺序是 `select(falseValue, trueValue, condition)`，容易和三元运算符顺序（条件在前、真值在先）搞反。
- `condition` 可以是 `bool` 或与向量同宽的 `bool2/3/4`，因此一条指令完成逐分量选择，不产生分支；这正是向量化友好的写法（见 2.4 一章）。
- 代价：`select` 的两个分支都会被求值，不会短路。分支里有开销大的计算或可能出错的运算（除以零、越界读）时，要先保护再 select。

## `Unity.Mathematics.noise`

`noise` 是静态类（API 页描述为 "A static class containing noise functions"）。API 页列出的方法：

| 方法 | 说明 |
| --- | --- |
| `cnoise(float2/float3/float4)` | 经典 Perlin 噪声 |
| `pnoise(x, period)` | 经典 Perlin 噪声的周期（可平铺）版本 |
| `snoise(float2/float3/float4)` | Simplex 噪声；另有 `snoise(float3, out float3 gradient)` 重载 |
| `srnoise(float2)`、`srnoise(float2, float rot)` | 2D 非平铺 simplex，可带旋转梯度，无解析导数 |
| `srdnoise(float2)`、`srdnoise(float2, float rot)` | 同上，带解析导数 |
| `psrnoise` `psrdnoise` | 2D 平铺版本（periodic） |
| `cellular(float2/float3)`、`cellular2x2`、`cellular2x2x2` | Worley 噪声，不同搜索窗口大小 |

`cellular` 系列的返回类型是 `float2`，API 页描述为特征点距离：F1（最近）在 `x`，F2（次近）在 `y`。各噪声函数的返回值区间，API 页没有给出，不要凭记忆假设，使用前用小测试打印范围（待核实）。

```csharp
using Unity.Mathematics;

float h = noise.snoise(new float2(x, z) * 0.01f);   // 每次调用都是纯函数，无状态
```

`noise` 没有"种子"参数。要得到不同的种子，需要给坐标加偏移（如 `p + seedOffset`）。

## `Unity.Mathematics.Random`

`Random` 是一个只有 32 位状态的 xorshift 生成器（API 页描述），核心逻辑不含整数乘法以利于 SIMD 化。

- 构造：`new Random(uint seed)`，种子必须非零；`Random.CreateFromIndex(uint index)` 先把 index 哈希再作种子，index 不能是 `uint.MaxValue`；`InitState(uint)` 重置状态，同样要求非零。
- 取值：`NextFloat()` 在 `[0, 1)`，`NextFloat(max)`、`NextFloat(min, max)`，以及 `NextInt(min, max)`、`NextUInt`、`NextBool`、`NextFloat2/3/4`、`NextFloat3Direction`、`NextQuaternionRotation` 等，带范围参数的重载区间都是含下界、不含上界（`[min, max)`）；无参的 `NextInt()` 范围是 `[-2147483647, 2147483647]`。
- 字段 `state` 不应为零，为零则生成器永远输出零。

### 每个工作项独立的 Random

```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;
using Unity.Mathematics;

[BurstCompile]
struct FillRandomJob : IJobParallelFor
{
    public uint BaseSeed;
    [WriteOnly] public NativeArray<float> Output;

    public void Execute(int index)
    {
        // 每个 index 一个独立的、经过哈希的种子，且不会得到 state = 0
        var rng = Random.CreateFromIndex(BaseSeed + (uint)index);
        Output[index] = rng.NextFloat();
    }
}
```

要点：

- `Random` 是 struct。把它按值复制，副本和原件会各自产生**相同的**序列；跨方法传递时用 `ref`。
- 所有线程用同一个 seed 创建，会得到相同的随机序列；用 `CreateFromIndex(index)`（以工作项索引或区块坐标哈希为输入）能让结果与调度顺序、线程数无关，利于可复现的世界生成。
- 同一文件里同时 `using UnityEngine;` 和 `using Unity.Mathematics;` 时，`Random` 有歧义（编译错误），要写全名 `Unity.Mathematics.Random`。
- 体素世界里更推荐"位置→哈希→值"的无状态风格（见下面的整数哈希），而不是依赖随机数流的消耗顺序。

## `Mathf` ↔ `math` 对照

| `Mathf` | `math` | 注意 |
| --- | --- | --- |
| `Mathf.Abs` | `math.abs` | 相同 |
| `Mathf.Min/Max` | `math.min/max` | 向量版本逐分量 |
| `Mathf.Clamp` | `math.clamp` | 相同 |
| `Mathf.Clamp01` | `math.saturate` | 相同 |
| `Mathf.Lerp` | `math.lerp` | `Mathf.Lerp` 钳制 `t`，`math.lerp` 不钳制 |
| `Mathf.InverseLerp` | `math.unlerp` | 同上：Mathf 钳制，math 不钳制 |
| `Mathf.SmoothStep(from, to, t)` | `math.smoothstep(min, max, x)` | 参数含义不同 |
| `Mathf.FloorToInt(x)` | `(int)math.floor(x)` | 先 floor 再转 |
| `Mathf.CeilToInt(x)` | `(int)math.ceil(x)` | |
| `Mathf.Sqrt/Pow/Sin/Cos` | `math.sqrt/pow/sin/cos` | 精度受 `FloatPrecision` 影响 |
| `Mathf.Deg2Rad` | `math.radians(x)` | 函数而非常量 |
| `Mathf.PerlinNoise` | `noise.cnoise` | 值域与算法不同，不可互换 |
| `Mathf.Sign` | `math.sign` | 对 0 的返回值不同：`Mathf.Sign(0)` 返回 1，`math.sign(0)` 返回 0（两边文档都有明确描述） |

## 整数除法与取模

- C# 的 `/` 对整数向零截断，`%` 的结果符号跟随被除数：`-1 / 4 == 0`，`-1 % 4 == -1`。
- 体素网格需要的是"向下取整除法"：`-1` 号体素应该属于区块 `-1`，而不是区块 `0`。直接用 `/` 会在原点附近出现一格错位。
- 整数除法指令本身较慢，且除数非常量时 Burst 无法把它改成乘法；除数是 2 的幂时，优先用位运算。

```csharp
using Unity.Mathematics;

// 任意正除数 b 的 floor 除法与对应取模
static int FloorDiv(int a, int b)
{
    int q = a / b;
    // 有余数且 a、b 异号时，截断比 floor 大 1，需要减回去
    return (a % b != 0 && ((a ^ b) < 0)) ? q - 1 : q;
}

static int FloorMod(int a, int b) => a - FloorDiv(a, b) * b;

// 除数为 2 的幂（如区块边长 16）：算术右移就是 floor，按位与就是非负取模
const int ChunkShift = 4;          // 2^4 = 16
const int ChunkMask = 15;
static int ChunkCoord(int worldX) => worldX >> ChunkShift;   // -1 >> 4 == -1
static int LocalCoord(int worldX) => worldX & ChunkMask;     // -1 & 15 == 15
```

向量化版本：`int4` 的 `>>` 与 `&` 都是逐分量运算，可以一次算四个坐标。浮点情况下，对应写法是 `(int)math.floor(x / 16f)`。

## 浮点精度提醒

- `float` 只有 24 位有效数字：坐标到 `1e6` 量级时，相邻可表示数的间距约 0.06，噪声采样会出现抖动和块状瑕疵。大世界应在区块局部坐标里做噪声采样（用整数区块坐标 + 局部浮点偏移），或使用 `double`。
- `Unity.Mathematics` 同样提供 `double2/3/4`，但 SIMD 宽度减半（SSE 一次 2 个 double）。
- `[BurstCompile(FloatMode.Fast)]` 可能重排运算并放宽 NaN 处理，换来速度，但会让结果和托管版本不同；需要可复现的世界生成时用默认 `Strict`，跨平台一致要求更高时才考虑 `Deterministic`（仅 64 位）。

## 本项目对照：`ValueNoiseFunction` 与库噪声

先读 `Assets/Scripts/WorldGen/Density/ValueNoiseFunction.cs`。它的算法是：

1. 把 `context.X/Y/Z` 乘以 `scale`、`yScale`（`double`）。
2. 用 `Math.Floor` 得到整数格点 `x0,y0,z0`；`tx = Smooth(x - x0)`，`Smooth(v) = v*v*(3 - 2*v)`。
3. 对八个格点调用 `Lattice(x, y, z)`：`uint h = (uint)seed; h ^= (uint)x * 374761393u; h ^= (uint)y * 668265263u; h ^= (uint)z * 2147483647u; h = (h ^ (h >> 13)) * 1274126177u; h ^= h >> 16;`，再映射到 `[-1, 1]`。
4. 三线性插值后乘 `amplitude`。

这是整数哈希值噪声（value noise）。`noise.cnoise` 是梯度噪声（Perlin），`snoise` 是 simplex，二者的格点处取值方式、插值曲线和值域都不同，所以换用库函数不是"优化"，而是**换了另一种地形**。建议做法：

- 第一步原样移植：算法、常量、`double` 精度都保持不变，只把 `Math.Floor` 换成 `math.floor`（或保留 `Math.Floor`，Burst 支持 `System.Math`），把 `seed`、`scale` 等放进 struct 字段。`uint` 乘法在 Burst 下同样按 `unchecked` 回绕（移植版里显式写了 `unchecked`，不依赖项目的溢出检查设置）。
- 为移植前后的输出做对拍测试（固定种子、网格采样、逐点比较）。Burst 默认 `FloatMode.Strict`，理论上应与托管结果一致，但这一点以测试为准，不要假设。
- 地形稳定后，再决定是否引入 `noise.snoise` 作为新特性；它会改变世界形状，应作为单独的变更。

移植骨架（只示意结构，不改动算法）：

```csharp
using Unity.Mathematics;

// 普通 struct，不需要 [BurstCompile]；它被某个 [BurstCompile] 的 Job 调用时，会随 Job 一起被编译
public struct ValueNoiseBurst
{
    public int Seed;
    public double Scale;
    public double YScale;
    public double Amplitude;

    public double Sample(double px, double py, double pz)
    {
        double x = px * Scale, y = py * YScale, z = pz * Scale;
        int x0 = (int)math.floor(x), y0 = (int)math.floor(y), z0 = (int)math.floor(z);
        double tx = Smooth(x - x0), ty = Smooth(y - y0), tz = Smooth(z - z0);
        double c000 = Lattice(x0, y0, z0),         c100 = Lattice(x0 + 1, y0, z0);
        double c010 = Lattice(x0, y0 + 1, z0),     c110 = Lattice(x0 + 1, y0 + 1, z0);
        double c001 = Lattice(x0, y0, z0 + 1),     c101 = Lattice(x0 + 1, y0, z0 + 1);
        double c011 = Lattice(x0, y0 + 1, z0 + 1), c111 = Lattice(x0 + 1, y0 + 1, z0 + 1);
        double x00 = Lerp(c000, c100, tx), x10 = Lerp(c010, c110, tx);
        double x01 = Lerp(c001, c101, tx), x11 = Lerp(c011, c111, tx);
        return Lerp(Lerp(x00, x10, ty), Lerp(x01, x11, ty), tz) * Amplitude;
    }

    private static double Lerp(double a, double b, double t) => a + (b - a) * t;

    private double Lattice(int x, int y, int z)
    {
        unchecked
        {
            uint h = (uint)Seed;
            h ^= (uint)x * 374761393u;
            h ^= (uint)y * 668265263u;
            h ^= (uint)z * 2147483647u;
            h = (h ^ (h >> 13)) * 1274126177u;
            h ^= h >> 16;
            return (h / (double)uint.MaxValue) * 2.0 - 1.0;
        }
    }

    private static double Smooth(double v) => v * v * (3.0 - 2.0 * v);
}
```

注意 `ValueNoiseFunction` 现在是 class 且实现 `IDensityFunction`，如何把它挂入可 Burst 的结构见 3.2 一章。

## 常见坑

- 把 `Mathf.Lerp` 直接替换成 `math.lerp`，丢了钳制，边缘处出现越界值。
- `new Random(0)`：状态为 0，永远输出 0。种子用 `CreateFromIndex` 或保证非零。
- 复制 `Random` 变量后各自抽数，得到重复序列。
- 用 `/` 和 `%` 处理负坐标，区块边界错位一格。
- 以为 `math.select` 会短路：两个分支都会算。
- 在大坐标上直接用 `float` 采样噪声，远处出现块状抖动。
- 把 `noise.cnoise` 当作 `ValueNoiseFunction` 的"更快版本"，实际上换了地形。
- 用 `*` 乘两个 `float4x4`：得到的是逐分量乘，不是矩阵乘；要用 `math.mul`。
- `quaternion.AxisAngle` 与 `quaternion.Euler` 直接传角度值：参数是弧度，要先 `math.radians`。
- `math.mul(m, v)` 与 `math.mul(v, m)` 随手互换：前者把 `v` 当列向量，后者当行向量，结果不同。

## 小结

- Burst 代码里用 `Unity.Mathematics`：类型内建、函数是 intrinsic、能映射到 SIMD。
- `math.select`、`saturate`、`mad`、位运算是向量化友好写法的常用工具。
- `Random` 要非零种子、按 `ref` 传递、每工作项独立；无状态哈希更适合世界生成。
- 整数除法要自己写 floor 版本，2 的幂用移位和按位与。
- 本项目的值噪声先原样移植、再对拍，之后再讨论换算法。

## 自测题

1. `math.lerp` 和 `Mathf.Lerp` 最大的行为差异是什么？
   答：`Mathf.Lerp` 钳制 `t` 到 `[0,1]`，`math.lerp` 不钳制。
2. `math.select(a, b, c)` 在 `c` 为 true 时返回哪个？
   答：返回 `b`（第二个参数，真值）；顺序是 `select(falseValue, trueValue, condition)`。
3. 为什么 `new Random(0)` 是错误用法？
   答：种子必须非零，状态为 0 会使生成器永远输出同一个值；应使用非零种子或 `CreateFromIndex`。
4. `-1 / 16` 与 `-1 >> 4` 分别是多少？体素分区块时该用哪个？
   答：`-1 / 16 == 0`（向零截断），`-1 >> 4 == -1`（算术右移即 floor）。该用 `>> 4`。
5. 为什么不能直接把 `ValueNoiseFunction` 换成 `noise.cnoise`？
   答：前者是整数哈希值噪声，后者是梯度噪声，算法和值域都不同，换了会改变地形。
6. `float4x4 c = a * b;` 和 `float4x4 c = math.mul(a, b);` 有什么区别？`math.mul(m, v)` 与 `math.mul(v, m)` 呢？
   答：前者是逐分量乘，后者才是矩阵乘；`math.mul(m, v)` 把 `float4` 当列向量（4x4 乘 4x1），`math.mul(v, m)` 把它当行向量（1x4 乘 4x4）。

## 参考

- https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/manual/index.html
- https://docs.unity3d.com/Manual/unity-mathematics.html
- https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/api/Unity.Mathematics.math.html
- https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/api/Unity.Mathematics.RigidTransform.html
- https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/api/Unity.Mathematics.Geometry.MinMaxAABB.html
- https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/api/Unity.Mathematics.noise.html
- https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/api/Unity.Mathematics.Random.html
- https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/api/Unity.Mathematics.math.remap.html
- https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/api/Unity.Mathematics.math.bitmask.html
- https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/api/Unity.Mathematics.math.tzcnt.html
- https://docs.unity3d.com/Packages/com.unity.mathematics@1.3/api/Unity.Mathematics.math.hash.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-type-support.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/compilation-burstcompile.html
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Density\ValueNoiseFunction.cs
