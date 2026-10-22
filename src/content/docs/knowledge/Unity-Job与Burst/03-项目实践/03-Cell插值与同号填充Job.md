---
title: "3.3 Cell 插值与同号填充 Job"
description: 讲解 ChunkDensitySampler 的角点网格、三线性插值与同号填充，设计二维场、角点密度、cell 填充三个 Job 的数据流、写入冲突处理、跨区块一致性与验收方法。
sidebar:
  order: 3
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x / Collections 2.x / Mathematics 1.3.x 为主线；本项目的 Unity 7000.0.0a8 中 Burst 2.0.0 与 Collections 6.7.0 是转发到引擎内置模块的壳包。核实不了的标"待核实"。

本章代码是教学骨架，未在 Unity 内编译，复制前核对 API 与项目现状。类名、方法名、字段名以 `Assets/Scripts/WorldGen/Voxels/ChunkDensitySampler.cs` 等真实代码为准。密度函数本身如何进 Job，见 3.2 噪声与密度函数的 Burst 化；本章假设已有一个可在 Job 里调用的 `DensityEvaluator`。

## 目标与现状

目标：把 `ChunkDensitySampler.Fill(VoxelChunk, originX, originY, originZ)` 的三个步骤（二维场、角点密度、cell 填充）拆成三个 Job，结果与托管版逐字节一致。

### 现有算法

`ChunkDensitySampler` 对应 Minecraft 的 `NoiseChunk` + `NoiseInterpolator`：只在 cell 的角点上计算完整密度，cell 内部做三线性插值。默认 `cellWidth = 4`、`cellHeight = 8`，即 4 × 8 × 4 个体素一个 cell（`VoxelWorldPreview` 里的常量 `CellWidth = 4`、`CellHeight = 8`）。

**1. 角点网格对齐到世界网格。** 令 `baseX = originX + chunk.StartX`，`baseY = originY`，`baseZ = originZ + chunk.StartZ`，则

```
firstX = FloorDiv(baseX, cellWidth)
cellsX = FloorDiv(baseX + sx - 1, cellWidth) - firstX + 1
nx     = cellsX + 1                 // 每个方向角点数 = cell 数 + 1
```

Y、Z 同理（Y 用 `cellHeight`，Z 用 `cellWidth`）。`FloorDiv` 是向负无穷取整的除法，保证坐标为负时 cell 边界仍落在 `cellWidth` 的整数倍上。总角点数 `cornerCount = nx * ny * nz`。

角点 `(ix, iy, iz)` 的世界采样坐标是 `((firstX + ix) * cellWidth, (firstY + iy) * cellHeight, (firstZ + iz) * cellWidth)`，这里已经包含 `origin`。角点按 `((ix * nz + iz) * ny + iy)` 存进 `double[] corners`，Y 变化最快，同一列的角点连续。

角点个数不是固定的 5 × 5：区块宽 16、cell 宽 4、`baseX` 是 4 的倍数时，`cellsX = 4`，每方向 5 个角点列；`baseX` 不是 4 的倍数（例如 `sampleOrigin.x` 为 1）时，区块会跨 5 个 cell，每方向 6 个角点列。

**2. 逐 cell 填充。** 循环顺序是 `cx`、`cz`、`cy`。每个 cell 取 8 个角点值 `c000 … c111`，把 cell 起点换算成区块局部坐标 `cellX/cellY/cellZ`，再裁剪到区块范围 `[x0,x1) × [y0,y1) × [z0,z1)`（区块起点不对齐 cell 时，边缘 cell 只有一部分在本区块内）。

**3. 同号整格填充。** 8 个角点全部 `> 0` 则整块写 1，全部 `<= 0` 则整块写 0，并按体素数累加 `solidCount`。

**4. 混号 cell 的插值。** 先沿 Y，再沿 X，最后沿 Z 做线性插值（对应 MC `doFill` 的 `updateForY → updateForX → updateForZ`）：

```
ty = (y - cellY) * invH;  v00 = Lerp(c000,c010,ty), v10 = Lerp(c100,c110,ty), v01 = Lerp(c001,c011,ty), v11 = Lerp(c101,c111,ty)
tx = (x - cellX) * invW;  vz0 = Lerp(v00,v10,tx), vz1 = Lerp(v01,v11,tx)
tz = (z - cellZ) * invW;  value = Lerp(vz0,vz1,tz) > 0
```

其中 `invW = 1.0 / cellWidth`、`invH = 1.0 / cellHeight`，`Lerp(a,b,t) = a + (b - a) * t`。体素 `(x, y, z)` 对应 cell 内的 `t = (局部偏移) * inv`，取值范围 `[0, (cell 尺寸 - 1) / 尺寸]`，不会取到 1。只有三个方向的偏移都为 0 的体素（恰好落在 cell 起点角 `c000` 上）取值才等于角点值；起点面上的其它体素仍是该面四个角点的插值。

**5. 为什么同号填充不改变结果。** 三线性插值是 8 个角点的凸组合（权重非负、和为 1），所以 8 个角点都大于 0 时内部所有点都大于 0；都不大于 0 时同理。这是实数运算下的结论，代码注释也这样说明；在浮点舍入层面，对一般幅度的密度值两者给出相同的符号，极端接近 0 的数值是否可能出现例外（待核实），可以靠后面的逐体素对比测试来确认。

**6. 特例。** `cellWidth == 1 && cellHeight == 1` 时，`Fill` 直接走 `VoxelChunk.Fill`，逐体素精确采样。`VoxelWorldPreview` 的 `cellInterpolation` 开关关闭时就是这条路。

**7. 其它细节。** 每个体素都恰好属于一个 cell，且 cell 覆盖整个区块，所以托管版把区块里每个字节都写了一遍；填完后调用 `chunk.SetSolidCount(solidCount)`。Job 版同样不需要预先清零。

## 数据流设计

```
主线程：算 CellGrid（firstX/Y/Z、cellsX/Y/Z、nx/ny/nz），分配 columns / corners / counts / solid

Job1  ColumnFieldsJob     工作项 = 一个角点列 (ix,iz)    输出 columns[nx*nz]       (ColumnFields: Offset,Factor,JaggedTerm)
  |
Job2  CornerDensityJob    工作项 = 一个角点 (ix,iz,iy)   输出 corners[nx*ny*nz]    (double)
  |
Job3  CellFillJob         工作项 = 一个 cell 列 (cx,cz)  输出 solid[sx*sy*sz]      + counts[cellsX*cellsZ]
  |
主线程/小 Job：sum(counts) -> SolidCount
```

三个 Job 的衔接用 `JobHandle` 依赖（见 1.3 调度与 JobHandle 依赖）：Job2 依赖 Job1，Job3 依赖 Job2。Job1 的输出被 Job2 只读；Job2 的输出被 Job3 只读。

### 为什么这样划分

- Job1 就是 3.2 说的 `Cache2D` 对应物。二维场在每个角点列只算一次，而 Job2 是按角点展开的，每个角点要读自己所在列的 `ColumnFields`。
- Job2 的单个工作项开销最大：每个角点要算三个 3 层 `Octave` 噪声，每层 8 次 hash；所以它是并行收益最大的一步。
- Job3 的开销主要是写内存和同号判断，混号 cell 里还有逐体素的插值。

### Job2 的工作项选择

两种划分：

| 划分 | 写入下标与 index 的关系 | 是否需要 `[NativeDisableParallelForRestriction]` |
| --- | --- | --- |
| 工作项 = 一个角点（`index` 即线性角点下标） | 写 `corners[index]`，下标等于 index | 不需要 |
| 工作项 = 一个角点列（循环 `iy`） | 写 `corners[col*ny .. col*ny+ny)`，下标不等于 index | 需要 |

推荐第一种。线性化是 `((ix * nz + iz) * ny + iy)`，所以 `iy = index % ny`、`col = index / ny`、`ix = col / nz`、`iz = col % nz`。每个工作项写自己的元素，符合 `IJobParallelFor` 安全系统的默认约束（见 1.6 安全系统与竞争条件）。代价是每个角点要自己去 `columns[col]` 取二维结果，这是一次只读的随机访问，开销很小。

## Job3 的写入冲突分析

`solid` 的线性化是 `x + sx * (y + sy * z)`。一个 cell 列 `(cx, cz)` 写入的体素集合是 `{ (x, y, z) | x ∈ [x0,x1), z ∈ [z0,z1), y ∈ [0, sy) }`，其中 `[x0,x1)`、`[z0,z1)` 是该 cell 列裁剪到区块内的范围。

- 不同 cell 列的 `(x, z)` 范围互不重叠（cell 列把区块的 XZ 平面分割成不相交的矩形），所以所有工作项写入的下标集合两两不相交：没有数据竞争。
- 但这个下标集合不是连续的，也和工作项编号 `item = cx * cellsZ + cz` 没有对应关系。`IJobParallelFor` 的安全系统会把可写 `NativeArray` 限制在当前批次对应的下标区间内，越界写会在启用安全检查时抛出 `IndexOutOfRangeException`（具体消息文本待核实）。安全系统无法替你证明"写入集合不相交"。

处理办法有两种：

**办法一（推荐）：工作项 = cell 列，给 `Solid` 加 `[NativeDisableParallelForRestriction]`。**

该属性的含义是"我自己保证多个工作项不会写同一个位置，请关掉按 index 的范围限制"。它只对被标注的这个容器生效，其它容器的检查仍在。（Unity 脚本 API 页对它的描述是：让多个 Job 可以同时访问同一个 NativeContainer，使用者要自己保证访问安全，属性会让安全系统忽略对容器的多次读写。页面没有逐条说明 `IJobParallelFor` 的下标范围限制，这部分语义依据 1.6 安全系统与竞争条件的整理。）使用条件和理由：

1. 理由：写入集合按 cell 列划分，互不重叠（上面已证明）。
2. 条件：每个体素必须只由一个工作项写。`CellGrid` 的 cell 范围计算一旦有偏差（比如区块起点不对齐时的裁剪写错），重叠写不会再被安全系统发现，只会表现为偶发的结果错误。
3. 补偿：在测试里做"写入次数计数"。给每个体素配一个计数，所有工作项写入时把对应计数加一（测试专用的单线程版本），结束时检查每个体素恰好被写一次。

**办法二：工作项 = 体素，下标等于 index。**

每个工作项通过 `index` 解出 `(x, y, z)`，定位自己所在的 cell，读 8 个角点，同号就直接写，混号就插值。写入下标就是 `index`，不需要关闭限制。缺点是每个体素重复读 8 个角点并做同号判断，混号 cell 内也丢掉了 `v00…v11` 的共享；同时 `solidCount` 不能在 Job 里累加，需要另一个归约步骤（见 1.7 并行写入与归约模式）。每个体素最终的运算序列与办法一相同，所以结果仍然逐位一致。

选择：先用办法一做对，用写入次数测试守住不变量；办法二可以作为对照基线，验证办法一的结果。

### solidCount 的归约

办法一里每个 cell 列把自己的计数写进 `counts[item]`（下标等于 index，不用关闭限制），所有 Job 完成后在主线程对 `counts` 求和，再设置区块的 `SolidCount`。整数求和与顺序无关，结果是确定的。

## 数据布局与局部性

- `solid` 是 `x + sx * (y + sy * z)`，x 变化最快，其次 y，最后 z。内存里连续的是一行 x，然后是一整个 x–y 平面。
- 托管版混号 cell 的循环顺序是 y、x、z，最内层是 z，步长为 `sx * sy` 字节（`sx = 16` 时就是 `16 * sy`）。每写一个体素就跨一整个平面，局部性很差。
- Burst 版可以把循环改成 z、y、x，让 x 在最内层连续写。这不会改变任何体素的值：每个体素的值只取决于它自己的 `ty → (v00,v10,v01,v11) → tx → (vz0,vz1) → tz` 这条运算序列，调整外层循环顺序只是改变计算顺序，不改变每个体素的运算顺序和操作数。唯一的代价是 `vz0`、`vz1` 需要对每个 z 重算一次（或预先对每个 x 缓存）。
- 角点数组 `corners` 的大小很小：高度 128 时 `ny = 17`，5 × 5 个角点列共 425 个 `double`（约 3.4 KB）；高度 384 时 `ny = 49`，约 10 KB。它们完全放得进 L1/L2，所以角点布局不是瓶颈。Y 变化最快的布局对 Job2（同列连续）和 Job3 沿 `cy` 前进（相邻 cell 共享一层角点）都是合适的。
- 角点保持 `double`。改成 `float` 会改变插值结果，破坏与托管版逐位一致的验收。

### 补充：让写入区间"可算术证明"的划分

办法一里，cell 列写入的下标集合是若干段不连续的行，要靠几何论证才能说它们不重叠。还有一种划分让不重叠变得一眼可见：工作项 = 区块的一个 z 层，写入区间是 `[z * sx * sy, (z + 1) * sx * sy)`，这是一段连续内存，不同 z 的区间显然不相交。每个 z 层只属于一个 `cz`，内部循环 `cx`、`cy` 取角点并写入。

- 代价：同一个 cell 会被它覆盖的 `cellWidth` 个 z 层各取一次角点、各做一次同号判断，重复的是廉价的读和比较。
- 仍然需要 `[NativeDisableParallelForRestriction]`：`IJobParallelFor` 的范围限制绑定的是 index 而不是"某段区间"，区间 `z * sx * sy` 与 `index = z` 对不上。这种划分只是让"互不重叠"的证明从几何论证变成算术。
- 另一条路是对每个 z 层用 `NativeArray<T>.GetSubArray(start, length)` 切出子数组，每层单独调度一个 Job，不用关闭限制。多个 Job 同时写同一个数组的不同子数组，安全系统是否放行（待核实），要在 1.6 安全系统与竞争条件讲的规则下实测；而且调度的 Job 数量会按 `sz` 倍增。

本页骨架仍用办法一（工作项 = cell 列）。

## 角点共享边界与跨区块一致性

相邻区块的交界处，两边会各自计算同一批角点，没有共享内存：每个区块的 `corners` 都是自己算出来的。这是托管版就有的设计，注释写明"相邻区块在交界处读到的是同一批角点，不会有接缝"。它成立的前提是下面三条同时成立。

1. 角点坐标只由世界坐标决定。角点 `(ix, iy, iz)` 的采样坐标是 `((firstX + ix) * cellWidth, ...)`，`firstX = FloorDiv(baseX, cellWidth)`。同一个世界位置，不管它是从哪个区块、哪个 `StartX` 或 `sampleOrigin` 算出来的，输入坐标都相同。
2. 体素值只由 8 个角点和"体素到 cell 起点的整数距离"决定。`cellX = (firstX + cx) * cellWidth - baseX`，体素局部坐标 `x` 同样以 `baseX` 为基准，所以 `x - cellX` 里的 `baseX` 抵消，剩下的是体素世界坐标减 cell 起点世界坐标，与区块怎么切无关。
3. 两边的数值路径相同。同一份 `DensityEvaluator`、同一份 `Lerp` 写法、同一个 `FloatMode`。

只要这三条成立，两个区块对同一个世界体素给出的 `solid` 值逐位一致，区块切分方式不影响结果；任何一条被破坏，就会在接缝处出现一个 cell 内的形状错位。

### 为什么必须逐位一致

密度值最后只和 0 比较。角点相差 1 ULP 通常不会翻转符号，但会在"密度刚好贴近 0"的体素上翻转。接缝两侧各自算出略有不同的角点，等价于两个区块对同一个 cell 的形状有分歧，后果是面可见性 Job（见 3.1 区块面可见性 Job）看到的邻居体素与自己这边不连贯，边界上出现孔洞或多余的面。所以验收要求位级一致，不是"差不多"。

可能破坏位级一致的来源，细节见 2.6 浮点模式与确定性：

- `FloatMode.Fast` 允许重排与融合，同一段代码在不同批次、不同向量宽度下可能给出不同的末位。三个 Job 都不要开。
- `a + (b - a) * t` 是融合乘加（FMA）的候选，`Strict` 下是否会被融合（待核实，2.6 已标注）。同一个 Job 内的所有体素走同一个编译结果，通常不会因为位置不同而不同，但"托管版"和"Burst 版"之间就可能不同。
- Burst 编译被禁用或回退时，同一个 Job 会跑 Mono 版本。不要让同一个世界的一部分区块走 Burst、另一部分走托管，除非验证过两者逐位一致。

### 跨区块一致性测试

测试分两层：先测角点，再测体素。

```csharp
// 教学骨架：NUnit 风格，名字为示意，未在 Unity 内编译。
// 层 1：同一个世界位置的角点，来自两个区块，位模式必须相同。
// 取区块 A (StartX = 0) 和区块 B (StartX = 16) 的 corners 数组，
// 对共享的世界坐标比较 BitConverter.DoubleToInt64Bits。

// 层 2：同一片世界区域，用不同的切分方式生成，逐字节相同。
// 方式 1：一个 32 宽的大区块。
// 方式 2：两个 16 宽的区块，StartX 分别为 0 和 16。
// 方式 3：同样两块，但 sampleOrigin 偏移 1，StartX 相应调整，使世界坐标相同。
// 三种方式取同一世界范围内的每个体素，必须全部相等。
```

要覆盖的情形：

- 区块起点对齐到 `cellWidth` 与不对齐两种（对齐时交界面上的角点是同一个点，不对齐时同一个 cell 被两个区块各取一部分）。
- 负的世界坐标，用来覆盖 `FloorDiv` 的负数分支。
- 多个种子。

这个测试对托管版 `ChunkDensitySampler` 和 Job 版分别跑一遍，还要跑"托管版 vs Job 版"的交叉比较（见后文验收）。

## innerloopBatchCount 的选择思路

`Schedule(arrayLength, innerloopBatchCount)` 的批大小没有通用最优值。Unity 手册 Parallel jobs 页的建议是：从 1 开始，逐步增大，直到性能收益可以忽略（1.8 调度粒度与性能调优有展开）。这里只给出三个 Job 各自的起点和依据。

| Job | 工作项数量（量级） | 单个工作项的重量 | 起点 | 依据 |
| --- | --- | --- | --- | --- |
| Job1 二维场 | `nx * nz`，一个区块只有几十个 | 几个二维噪声加样条求值，较重 | 1 | 工作项总数少，批大了会让部分核心没活干 |
| Job2 角点密度 | `nx * ny * nz`，几百到上千 | 三个多层噪声，最重 | 从 1 起试，再试 8、16、32 | 工作项多而重，批大一点能省调度开销，但不要大到批数少于核心数 |
| Job3 cell 填充 | `cellsX * cellsZ`，十几个 | 每个工作项写一整列 cell，内存写入量大 | 1 | 工作项数本来就少，一个工作项的工作量已经够大 |

几点说明：

- 工作项总数只有几百时，批大小 64 只会切出几个批次，用不满所有 worker。批数至少要明显大于 worker 数，工作窃取才有空间平衡负载。
- 如果同时有很多区块的三段链在飞（见 3.5 调度管线与 Profiling），外层并行已经让 worker 饱和，单个 Job 内的批大小影响会变小。这时先用 1.8 的方法在整条管线上测，不要孤立地调某一个 Job。
- 以上都是起点，不是结论。具体数值要在自己机器上测，结果记入文末的性能记录表。

## 骨架代码

以下骨架假设 3.2 已经给出 `DensityEvaluator` 和 `ColumnFields`（`Offset`、`Factor`、`JaggedTerm`），并且 `EvalColumn(int x, int z)`、`EvalVoxel(int x, int y, int z, in ColumnFields col)` 这两个方法可以在 Job 里调用。`CellGrid` 是本页为了传参约定的名字，项目里没有这个类型。

### 网格参数

```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Collections.LowLevel.Unsafe;
using Unity.Jobs;
using Unity.Mathematics;

// 主线程算好，按值拷进各个 Job。字段与 ChunkDensitySampler.Fill 里的局部变量一一对应。
internal struct CellGrid
{
    public int BaseX, BaseY, BaseZ;          // originX + StartX, originY, originZ + StartZ
    public int FirstX, FirstY, FirstZ;       // FloorDiv(base, cell)
    public int CellsX, CellsY, CellsZ;
    public int Nx, Ny, Nz;                   // cells + 1
    public int SizeX, SizeY, SizeZ;          // 区块尺寸
    public int CellWidth, CellHeight;

    public static int FloorDiv(int a, int b)
    {
        int q = a / b;
        return (a % b != 0 && (a < 0) != (b < 0)) ? q - 1 : q;
    }

    public static CellGrid Create(int baseX, int baseY, int baseZ,
        int sx, int sy, int sz, int cellWidth, int cellHeight)
    {
        var g = new CellGrid
        {
            BaseX = baseX, BaseY = baseY, BaseZ = baseZ,
            SizeX = sx, SizeY = sy, SizeZ = sz,
            CellWidth = cellWidth, CellHeight = cellHeight,
        };
        g.FirstX = FloorDiv(baseX, cellWidth);
        g.CellsX = FloorDiv(baseX + sx - 1, cellWidth) - g.FirstX + 1;
        g.FirstY = FloorDiv(baseY, cellHeight);
        g.CellsY = FloorDiv(baseY + sy - 1, cellHeight) - g.FirstY + 1;
        g.FirstZ = FloorDiv(baseZ, cellWidth);
        g.CellsZ = FloorDiv(baseZ + sz - 1, cellWidth) - g.FirstZ + 1;
        g.Nx = g.CellsX + 1; g.Ny = g.CellsY + 1; g.Nz = g.CellsZ + 1;
        return g;
    }
}
```

### Job1：二维场

```csharp
[BurstCompile]   // FloatMode 保持默认 Strict，不要改成 Fast，见 2.6
internal struct ColumnFieldsJob : IJobParallelFor
{
    public DensityEvaluator Eval;                 // 内部的只读表已在 3.2 标 [ReadOnly]
    public CellGrid Grid;
    [WriteOnly] public NativeArray<ColumnFields> Columns;   // 长度 Nx * Nz

    public void Execute(int col)                  // col = ix * Nz + iz，与托管版 columnBase 的列号一致
    {
        int ix = col / Grid.Nz;
        int iz = col % Grid.Nz;
        int wx = (Grid.FirstX + ix) * Grid.CellWidth;
        int wz = (Grid.FirstZ + iz) * Grid.CellWidth;
        Columns[col] = Eval.EvalColumn(wx, wz);
    }
}
```

### Job2：角点密度

工作项 = 一个角点。`index` 就是 `((ix * Nz + iz) * Ny + iy)`，所以写入下标等于 index，不需要关闭限制。

```csharp
[BurstCompile]
internal struct CornerDensityJob : IJobParallelFor
{
    public DensityEvaluator Eval;
    public CellGrid Grid;
    [ReadOnly] public NativeArray<ColumnFields> Columns;
    [WriteOnly] public NativeArray<double> Corners;          // 长度 Nx * Ny * Nz

    public void Execute(int index)
    {
        int iy  = index % Grid.Ny;
        int col = index / Grid.Ny;                           // 与 Job1 的列号相同
        int ix  = col / Grid.Nz;
        int iz  = col % Grid.Nz;
        int wx = (Grid.FirstX + ix) * Grid.CellWidth;
        int wy = (Grid.FirstY + iy) * Grid.CellHeight;
        int wz = (Grid.FirstZ + iz) * Grid.CellWidth;
        Corners[index] = Eval.EvalVoxel(wx, wy, wz, Columns[col]);
    }
}
```

这里的 `Eval.EvalVoxel(wx, wy, wz, Columns[col])` 对应托管版的 `density.Sample(new DensityContext(wx, (firstY + iy) * cellHeight, wz))`。要求 `EvalColumn` 与 `EvalVoxel` 的组合与托管 `FinalDensity` 逐位一致，这由 3.2 的验收保证。

### Job3：cell 填充

工作项 = 一个 cell 列 `(cx, cz)`，`item = cx * CellsZ + cz`，循环 `cy` 在 Job 内部。`Solid` 加 `[NativeDisableParallelForRestriction]`，原因和守护措施见前文。

```csharp
[BurstCompile]
internal struct CellFillJob : IJobParallelFor
{
    public CellGrid Grid;
    [ReadOnly] public NativeArray<double> Corners;
    [NativeDisableParallelForRestriction] [WriteOnly] public NativeArray<byte> Solid;  // 长度 SizeX*SizeY*SizeZ
    [WriteOnly] public NativeArray<int> Counts;                                         // 长度 CellsX * CellsZ

    double Corner(int ix, int iy, int iz) => Corners[(ix * Grid.Nz + iz) * Grid.Ny + iy];
    static double Lerp(double a, double b, double t) => a + (b - a) * t;   // 与托管版写法一致

    public void Execute(int item)
    {
        int cx = item / Grid.CellsZ, cz = item % Grid.CellsZ;
        int sx = Grid.SizeX, sy = Grid.SizeY, sz = Grid.SizeZ;
        double invW = 1.0 / Grid.CellWidth, invH = 1.0 / Grid.CellHeight;

        int cellX = (Grid.FirstX + cx) * Grid.CellWidth - Grid.BaseX;
        int cellZ = (Grid.FirstZ + cz) * Grid.CellWidth - Grid.BaseZ;
        int x0 = math.max(0, cellX), x1 = math.min(sx, cellX + Grid.CellWidth);
        int z0 = math.max(0, cellZ), z1 = math.min(sz, cellZ + Grid.CellWidth);

        int count = 0;
        for (int cy = 0; cy < Grid.CellsY; cy++)
        {
            double c000 = Corner(cx, cy, cz),         c100 = Corner(cx + 1, cy, cz);
            double c010 = Corner(cx, cy + 1, cz),     c110 = Corner(cx + 1, cy + 1, cz);
            double c001 = Corner(cx, cy, cz + 1),     c101 = Corner(cx + 1, cy, cz + 1);
            double c011 = Corner(cx, cy + 1, cz + 1), c111 = Corner(cx + 1, cy + 1, cz + 1);

            int cellY = (Grid.FirstY + cy) * Grid.CellHeight - Grid.BaseY;
            int y0 = math.max(0, cellY), y1 = math.min(sy, cellY + Grid.CellHeight);

            bool allSolid = c000 > 0 && c100 > 0 && c010 > 0 && c110 > 0
                         && c001 > 0 && c101 > 0 && c011 > 0 && c111 > 0;
            bool allAir   = c000 <= 0 && c100 <= 0 && c010 <= 0 && c110 <= 0
                         && c001 <= 0 && c101 <= 0 && c011 <= 0 && c111 <= 0;
            if (allSolid || allAir)
            {
                byte v = allSolid ? (byte)1 : (byte)0;
                for (int z = z0; z < z1; z++)
                for (int y = y0; y < y1; y++)
                {
                    int row = sx * (y + sy * z);
                    for (int x = x0; x < x1; x++) Solid[row + x] = v;
                }
                if (allSolid) count += (x1 - x0) * (y1 - y0) * (z1 - z0);
                continue;
            }

            // 混号 cell：循环改成 z、y、x，x 最内层连续写。每个体素的运算序列与托管版相同。
            for (int z = z0; z < z1; z++)
            {
                double tz = (z - cellZ) * invW;
                for (int y = y0; y < y1; y++)
                {
                    double ty = (y - cellY) * invH;
                    double v00 = Lerp(c000, c010, ty), v10 = Lerp(c100, c110, ty);
                    double v01 = Lerp(c001, c011, ty), v11 = Lerp(c101, c111, ty);
                    int row = sx * (y + sy * z);
                    for (int x = x0; x < x1; x++)
                    {
                        double tx = (x - cellX) * invW;
                        double vz0 = Lerp(v00, v10, tx), vz1 = Lerp(v01, v11, tx);
                        bool isSolid = Lerp(vz0, vz1, tz) > 0;
                        Solid[row + x] = isSolid ? (byte)1 : (byte)0;
                        if (isSolid) count++;
                    }
                }
            }
        }
        Counts[item] = count;
    }
}
```

`Solid` 同时标 `[WriteOnly]` 是为了让意图更明确，是否与 `[NativeDisableParallelForRestriction]` 同时使用没有冲突（待核实）。

## 调度顺序与 JobHandle 依赖链

```csharp
// 主线程。Persistent 的理由同 3.1：管线跨帧运行，TempJob 有 4 帧上限（见 1.5）。
var grid = CellGrid.Create(baseX, baseY, baseZ, sx, sy, sz, cellWidth, cellHeight);
int cornerCount = grid.Nx * grid.Ny * grid.Nz;

var columns = new NativeArray<ColumnFields>(grid.Nx * grid.Nz, Allocator.Persistent,
    NativeArrayOptions.UninitializedMemory);
var corners = new NativeArray<double>(cornerCount, Allocator.Persistent,
    NativeArrayOptions.UninitializedMemory);
var solid   = new NativeArray<byte>(sx * sy * sz, Allocator.Persistent,
    NativeArrayOptions.UninitializedMemory);      // 前提：Job3 覆盖每个体素，由测试守护
var counts  = new NativeArray<int>(grid.CellsX * grid.CellsZ, Allocator.Persistent,
    NativeArrayOptions.UninitializedMemory);

JobHandle h1 = new ColumnFieldsJob  { Eval = eval, Grid = grid, Columns = columns }
    .Schedule(columns.Length, 1);
JobHandle h2 = new CornerDensityJob { Eval = eval, Grid = grid, Columns = columns, Corners = corners }
    .Schedule(cornerCount, 16, h1);
JobHandle h3 = new CellFillJob      { Grid = grid, Corners = corners, Solid = solid, Counts = counts }
    .Schedule(counts.Length, 1, h2);

// 中间数组在读它的最后一个 Job 完成后释放，挂在依赖链上，不必回到主线程等。
JobHandle freeColumns = columns.Dispose(h2);
JobHandle freeCorners = corners.Dispose(h3);
// solid 与 counts 要读，所以 h3 完成之后在主线程取用，然后手动 Dispose。
```

依赖关系：

```
h1 (Job1) --> h2 (Job2) --> h3 (Job3) --> 主线程读取 solid / counts
               |              |
        columns.Dispose(h2)  corners.Dispose(h3)
```

- Job2 依赖 h1 是因为它读 `Columns`，Job3 依赖 h2 是因为它读 `Corners`。依赖链上每一步的输入都是上一步的输出，没有可以并行的相邻阶段；并行性来自每个阶段内部，以及多个区块的链同时在飞。
- 同一个区块的 `columns`、`corners`、`counts` 每个区块各一份。不同区块的链互不依赖，可以直接调度，不要把区块 A 的 h3 作为区块 B 的 `dependsOn`，那会把本可并行的链串成一条。
- 若调度的是很多区块，需要限制在飞的数量，沿用现有管线里 `maxSamplingInFlight` 与 `maxLoadedChunks`（背压）一类的思路（见 3.5 调度管线与 Profiling）。
- 若后面接面可见性 Job（见 3.1），可以把 `h3` 作为它的 `dependsOn`，用 `JobHandle.CombineDependencies` 合并五个区块的 handle，`solid` 保持 `NativeArray`，不必拷回托管数组。

### 取回结果

现有 `VoxelChunk` 的 `RawSolid` 和 `SetSolidCount` 都是 `internal`，Job 版结果要写回它只有两条路：

1. 在同一个程序集里，`h3.Complete()` 后 `solid.CopyTo(chunk.RawSolid)`，再 `chunk.SetSolidCount(sum)`，`sum` 是 `counts` 各项之和。多一次 `sx*sy*sz` 字节的拷贝，适合先对照验证。
2. 让后续阶段直接读 `NativeArray<byte>`，绕过 `VoxelChunk`，这属于重构区块数据结构，留到 3.5。

本页不修改项目代码，上面两种写法只是教学示意。

## 验收

验收分三组对比，结论的性质不同，不要混在一起。

### 对比 A：Job 版 vs 托管版 `ChunkDensitySampler`（cell 开）

要求逐字节一致，`SolidCount` 相等。没有"预期差异"，任何不同都是 bug。先用 3.2 的验收保证 `DensityEvaluator` 与 `FinalDensity` 的密度一致，这一步才有意义。这一组还应包含：

- 角点数组逐位比较：托管版的 `corners` 是私有字段，要比较就只能在测试里复制一份同样的角点公式，或者对同一世界坐标分别调用 `density.Sample` 与 `EvalVoxel`。
- 区块起点对齐与不对齐、负坐标、多个种子、多种区块高度。
- 写入覆盖测试：把 `solid` 先填成 `0xFF`，跑完后不应残留 `0xFF`。这只能发现漏写，发现不了重复写。重复写要靠测试专用的单线程版本，给每个体素计数，所有体素的计数必须恰好为 1。

### 对比 B：cell 开 vs cell 关（逐点采样）

`cellInterpolation` 关闭时，`VoxelWorldPreview` 传入 `cellW = 1`、`cellH = 1`，`ChunkDensitySampler` 走 `VoxelChunk.Fill`，每个体素精确采样一次。cell 插值本身会改变细节，这是已知的，不是 bug。判断"预期差异"还是"bug"可以用下面的检查：

| 检查 | 预期 | 违反时的含义 |
| --- | --- | --- |
| 差异体素是否都落在混号 cell 内 | 是 | 同号 cell 内有差异，说明同号填充或角点有误 |
| 恰好落在角点上的体素（x、y、z 三个方向相对 cell 起点的偏移都为 0）符号是否与逐点采样一致 | 一致，三个方向的插值权重都为 0，值就是角点值 | 角点坐标或 `FloorDiv` 有误 |
| 差异是否集中在地表附近 | 是，插值只影响密度接近 0 的位置 | 大片或随机分布的差异，多半是索引错位 |
| 同一设置下换区块切分方式，差异图是否变化 | 不变 | 区块边界处理有误，见前文一致性测试 |
| 差异比例与 `GetCellAliasingWarning` 的结论是否相符 | 返回 `null` 时差异较少，返回警告时可以更多 | 差异突然变大而设置没变，查最近改动 |

关于 `GetCellAliasingWarning(cellWidth, cellHeight)`：它用最高倍频的频率（`max(NoiseXZFrequency, SelectorXZFrequency) * 2^(NoiseOctaves - 1)`）与 `0.5 / cellWidth` 比较，Y 方向用 `0.5 / cellHeight`，超过就返回警告字符串，否则返回 `null`。直觉是：cell 角点相当于对密度场按 `cellWidth` 间距采样，高于 `0.5 / cellWidth` 的细节无法被角点表示。这只是一个预警阈值，不是误差上界。差异比例没有现成的通过标准，先在稳定版本上记录基线，后续改动对照基线判断（具体数值待实测）。

同号 cell 的差异为 0 在实数运算里由凸组合保证。浮点下是否在极端接近 0 时出现例外，前文已标待核实，B 组的第一行检查就是用来确认它的：若同号 cell 内出现差异，先排除 bug，再考虑是否是浮点例外。

### 对比 C：Job 版 cell 关 vs 托管版 cell 关

此时角点阶段不需要，三个 Job 退化成"每个体素直接 `EvalVoxel`"。通常没有必要为它单独写 Job，但可以作为 3.2 的整体回归：它和对比 A 的区别是不经过插值，能把密度函数的问题和插值的问题分开。

## 性能记录表（模板）

由读者在自己的机器上填写。记录硬件、Unity 版本、是否在编辑器、Burst 是否启用、区块尺寸、worker 数。表中没有预填任何数据。

| 场景 | 区块数 | 区块尺寸 | cell | 路径 | Job1 batch | Job2 batch | Job3 batch | worker 数 | 耗时 (ms) | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 单区块 | | | 开 | 托管 | 不适用 | 不适用 | 不适用 | 1 | | |
| 单区块 | | | 开 | Job + Burst | | | | | | |
| 单区块 | | | 关 | 托管 | 不适用 | 不适用 | 不适用 | 1 | | |
| 整个世界 | | | 开 | 托管 | 不适用 | 不适用 | 不适用 | | | |
| 整个世界 | | | 开 | Job + Burst | | | | | | |
| 首次调用（含 JIT） | | | 开 | Job + Burst | | | | | | 编辑器第一次运行 |

测量时分开记录 JIT 编译时间与稳态时间，并用 Profiler 看三个 Job 各自的耗时占比（见 3.5 调度管线与 Profiling）。

## 小结

- `ChunkDensitySampler` 的角点网格对齐世界网格，靠 `FloorDiv` 处理负坐标，每方向角点数是 cell 数加 1，且随区块起点是否对齐而变化。
- 同号 cell 整格填充来自三线性插值是角点凸组合的性质，实数上不改变结果。
- Job 化拆成二维场、角点密度、cell 填充三步，用 `JobHandle` 串成一条链，不同区块的链之间不互相依赖。
- Job3 的写入集合按 cell 列互不重叠，但与 index 对不上，需要 `[NativeDisableParallelForRestriction]`，并用覆盖与计数测试守住不变量。
- 相邻区块各自重算边界角点，结果必须逐位一致，所以不能开 `FloatMode.Fast`，也不能混用托管与 Burst 路径。
- 验收分 A、B、C 三组：A 要求逐字节一致，B 的差异分为预期与 bug，要靠检查表区分。

## 自测题

1. 角点个数为什么不是固定的 5 × 5？
   答：每方向角点数是 `cellsX + 1`，`cellsX = FloorDiv(baseX + sx - 1, cellWidth) - FloorDiv(baseX, cellWidth) + 1`。区块起点不对齐 `cellWidth` 时会跨更多个 cell，角点列数随之增加。
2. Job3 的写入下标集合互不重叠，为什么仍然要加 `[NativeDisableParallelForRestriction]`？
   答：`IJobParallelFor` 的安全系统按 index 限制可写范围，而 cell 列写入的下标与 `item` 编号没有对应关系，安全系统无法证明不重叠。关闭限制后"不重叠"由开发者保证，所以要有覆盖和计数测试。
3. 相邻区块各自重算边界角点，结果为什么必须逐位一致？
   答：密度只与 0 比较，末位差异会让贴近 0 的体素符号翻转，两个区块对同一个 cell 的形状就会不一致，接缝处出现孔洞或多余的面。
4. cell 开与 cell 关的结果不同时，怎么判断是预期差异还是 bug？
   答：看差异是否只出现在混号 cell 内、是否集中在地表附近、格点上的体素是否一致、换区块切分方式后差异是否不变。同号 cell 内出现差异或格点体素不一致，就是 bug。
5. 把混号 cell 的循环顺序从 y、x、z 改成 z、y、x，为什么不改变结果？
   答：每个体素的值只取决于自己的 `ty`、`tx`、`tz` 和 8 个角点，运算序列没变，只是计算顺序变了，每个体素的操作数与操作顺序保持不变。

## 参考

- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkDensitySampler.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelChunk.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelWorldPreview.cs（`cellInterpolation`、`CellWidth`、`CellHeight`、`GetCellAliasingWarning` 调用处）
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Density\WorldGenerationSettings.cs（`GetCellAliasingWarning`）
- Unity 手册：Parallel jobs（`innerloopBatchCount` 的建议、工作窃取）https://docs.unity3d.com/Manual/job-system-parallel-for-jobs.html
- Unity 手册：Write multithreaded code with the job system、Thread safe types（仅确认页面结构，未含 `[NativeDisableParallelForRestriction]` 的说明）
- Burst 手册 1.8 首页（仅确认入口页，未读到具体章节）https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/index.html
- 本系列：3.1 区块面可见性 Job、3.2 噪声与密度函数的 Burst 化、2.6 浮点模式与确定性、1.8 调度粒度与性能调优
