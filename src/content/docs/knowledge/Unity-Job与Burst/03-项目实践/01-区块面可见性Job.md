---
title: "3.1 区块面可见性 Job"
description: 解读现有 VoxelFaceVisibilityJob，说明它为什么没进入流式路径，并设计按区块、带邻居边界的面可见性 Job 与等价性验收方法。
sidebar:
  order: 1
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x / Collections 2.x / Mathematics 1.3.x 为主线；本项目的 Unity 7000.0.0a8 中 Burst 2.0.0 与 Collections 6.7.0 是转发到引擎内置模块的壳包。核实不了的标"待核实"。

本章代码是教学骨架，未在 Unity 内编译，复制前核对 API 与项目现状。项目类名、方法名以 `Assets/Scripts/WorldGen/Voxels/` 下的真实代码为准。

## 目标与现状

目标：把 `VoxelMeshBuilder.BuildChunkData` 里"这个体素的这一面要不要生成"的判定，搬进一个按区块调度的 Burst Job，并且结果与现有实现逐面一致。

### 现有 VoxelFaceVisibilityJob 的结构

文件 `VoxelFaceVisibilityJob.cs`，`[BurstCompile] internal struct VoxelFaceVisibilityJob : IJobParallelFor`（见 1.2 Job 类型详解）。

- 工作项：一个体素。`Execute(int index)` 的 `index` 就是体素的线性下标，`Schedule(count, batchSize)` 中 `count = Width * Height * Depth`。
- 字段：`[ReadOnly] NativeArray<byte> Solid`、`[WriteOnly] NativeArray<byte> FaceMask`，以及 `Width`、`Height`、`Depth`。
- 下标换算：`x = index % Width`，`yz = index / Width`，`y = yz % Height`，`z = yz / Height`。这对应线性化公式 `x + Width * (y + Height * z)`，x 变化最快。
- 空体素：`Solid[index] == 0` 时直接写 `FaceMask[index] = 0`。
- 六位掩码：bit 0 到 bit 5 依次是 +X、-X、+Y、-Y、+Z、-Z，与 `VoxelMeshBuilder.Directions` 的顺序（right、left、up、down、forward、back）一致。某一面的邻居不是实心，对应位置 1。
- 边界：私有方法 `IsSolid(x, y, z)` 在任一坐标越出 `[0, Width) / [0, Height) / [0, Depth)` 时返回 false。也就是世界外按空气处理，世界边缘会生成封闭表面。
- 写入模式：每个工作项只写自己的 `FaceMask[index]`，这是 `IJobParallelFor` 安全系统允许的模式（见 1.6 安全系统与竞争条件）。

### 为什么它没进入流式路径

读代码得到的事实如下。

| 事实 | 位置 |
| --- | --- |
| Job 只被 `VoxelMeshBuilder.BuildWithJobs` 与 `BuildChunkMeshesWithJobs` 构造，在 `Assets` 下没有其它调用点 | `VoxelMeshBuilder.cs` |
| 这两个方法的输入是 `VoxelVolume`（一整块 `bool[]`，上限 `MaxVoxelCount = 16000000`），不是 `VoxelChunk` | `VoxelVolume.cs` |
| `VoxelWorldPreview` 不创建 `VoxelVolume`，它只创建 `ChunkGenerationPipeline`；管线里建网格走 `VoxelMeshBuilder.BuildChunkData` | `VoxelWorldPreview.cs`、`ChunkGenerationPipeline.cs` |
| `CopySolidToNative` 在调用线程上逐元素把 `bool[]` 转成 `NativeArray<byte>`，复制的是整个世界 | `VoxelVolume.cs` |
| 两个入口都用 `Allocator.TempJob` 并立刻 `Complete()`，同步等待，主线程没有省下时间 | `VoxelMeshBuilder.cs` |
| Job 的边界判断基于整个体积的 `Width/Height/Depth`；如果拿它直接处理单个区块，区块侧面的邻居会被当成空气，在区块接缝处生成多余的面 | `VoxelFaceVisibilityJob.cs` |
| 面掩码算完之后，顶点、法线、三角形仍由主线程用 `List<Vector3>` / `List<int>` 逐个 `Add` 生成（`BuildChunkMeshesWithJobs` 走 `BuildMeshFromMask`，`BuildWithJobs` 在方法内联同样的循环） | `VoxelMeshBuilder.cs` |

结论：这个 Job 的前提是"整个世界已经采样完并在一块连续内存里"，这与流式区块（采样完一块、等邻居、建网格、释放）的数据生命周期不匹配。要让 Job 进入流式路径，需要的是"按区块、带邻居边界"的新版本，而不是调用参数的调整。

## 设计：按区块的面可见性 Job

### 与 BuildChunkData 的边界逻辑逐条对应

`VoxelMeshBuilder.BuildChunkData(center, posX, negX, posZ, negZ, ...)` 里的私有 `IsSolid(c, posX, negX, posZ, negZ, x, y, z)` 是要复刻的规格。按判断顺序逐条列出：

| 序号 | 条件（局部坐标，查询点为体素加方向偏移） | 结果 | Job 里要保证 |
| --- | --- | --- | --- |
| 1 | `y < 0` 或 `y >= c.SizeY` | 空气 | Y 方向没有邻居区块，顶面和底面一定出面 |
| 2 | `x >= c.SizeX` | `posX != null && posX.Get(0, y, z) != 0` | 读 +X 邻居的 x=0 那一列 |
| 3 | `x < 0` | `negX != null && negX.Get(negX.SizeX - 1, y, z) != 0` | 读 -X 邻居的最后一列，用邻居自己的 `SizeX` |
| 4 | `z >= c.SizeZ` | `posZ != null && posZ.Get(x, y, 0) != 0` | 读 +Z 邻居的 z=0 那一层 |
| 5 | `z < 0` | `negZ != null && negZ.Get(x, y, negZ.SizeZ - 1) != 0` | 读 -Z 邻居的最后一层 |
| 6 | 其它 | `c.Get(x, y, z) != 0` | 区块内部 |

另外三条行为也要保持：

- 邻居为 `null` 表示世界外，按空气处理，世界边缘生成封闭表面。
- `center.SolidCount == 0` 时 `BuildChunkData` 直接返回，没有顶点。Job 版可以同样在调度前跳过。
- 遍历顺序是 z 外层、y 中层、x 内层，面按 0 到 5 的顺序。掩码数组按 `x + SizeX * (y + SizeY * z)` 线性化，升序遍历下标恰好等于这个顺序，所以从掩码展开的顶点顺序与现有实现一致，可以做逐顶点比对。

因为每个查询点只偏移一个轴，不会同时越出 x 和 z，对角邻居（斜向四个区块）用不到，只需要四个邻居。

注意一个隐含前提：`BuildChunkData` 的注释要求邻居与中心同高，Z 方向邻居与中心同宽，X 方向邻居与中心同深。`ChunkGenerationPipeline` 中世界尾部的区块可能小于 16（`Math.Min(ChunkSize, worldX - startX)`），所以邻居的 `SizeX/SizeZ` 要按邻居自己的值取，不能假定都是 16。

### 两种数据组织方案

方案 A：每个 Job 传 5 个只读 `NativeArray<byte>`（center 与四个邻居），Job 内部按上表分支。

方案 B：先把 center 和四个邻居的边界面拼成一个带 1 格 apron（外圈）的 `(SizeX+2) * SizeY * (SizeZ+2)` 数组，Job 只读这一个数组，内部无邻居分支。

```
方案 B 的 padded 数组（俯视，X 向右，Z 向上，Y 方向每格是整列）

        negZ 的最后一层
      +------------------+
 negX |                  | posX
 最后 |   center 内部     | 第 0
 一列 |   SizeX*SizeZ     | 列
      +------------------+
        posZ 的第 0 层

四个角上的格子（x=-1,z=-1 等）不会被读到，保持 0 即可
```

| 项目 | 方案 A | 方案 B |
| --- | --- | --- |
| 每个 Job 的输入数组 | 5 个 | 1 个 |
| Execute 内分支 | 每个出界查询都要判断邻居和是否存在 | 只剩 Y 方向的判断 |
| 构造成本（数据来自托管 `byte[]` 时） | 5 次整块拷贝；若按区块缓存 NativeArray，则每个区块只拷一次，所有相关 Job 共用 | 1 次 center 行拷贝 + 4 个边界面拷贝，每个区块每次建网格都要重拼 |
| 内存 | 和区块本体同量级，可复用 | 每个 Job 额外约 `(18*18)/(16*16) - 1`，即约 27% 的临时缓冲 |
| 安全系统 | 同一个 `NativeArray` 会同时出现在最多 5 个 Job 里，必须全部 `[ReadOnly]`，且生产它的采样 Job 的 handle 要作为依赖 | 数组是 Job 私有的，没有跨 Job 共享，依赖关系简单 |
| 缺失邻居 | 需要布尔标志；不要用 center 代替，同一个数组在一个 Job 结构体里出现两次，只要有一个字段没标 `[ReadOnly]` 就会触发冲突检查 | 对应 apron 区域保持 0（`NativeArrayOptions.ClearMemory`） |

边界面拷贝的代价并不对称。`VoxelChunk` 的线性化是 `x + SizeX * (y + SizeY * z)`，所以 ±Z 邻居的边界面是一整块连续内存（z=0 层或最后一层，`SizeX*SizeY` 字节），可以 `memcpy` 式拷贝；±X 邻居的边界面是跨步访问（每个 (y, z) 一个字节，步长 `SizeX`），只能逐字节收集，共 `SizeY * SizeZ` 字节。

数据来源的限制是第一决定因素：`VoxelChunk.solid` 是托管 `byte[]`，Job 读不了托管数组，必须先拷到 `NativeArray`。拷贝本身是单线程内存拷贝，量级是每个区块 `SizeX*SizeY*SizeZ` 字节。如果 3.3 把区块存储改成 `NativeArray<byte>`（由采样 Job 直接写入），方案 A 的拷贝为零，方案 B 剩下的只有拼 apron。选择建议：

- 先实现方案 B。Job 简单，容易验证等价，安全关系清晰。
- 区块存储迁到 `NativeArray` 之后，再评估方案 A，或让 B 的拼装步骤也变成 Job。

## 代码骨架

### Job 结构体（方案 B）

```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;

namespace ProceduralGeneration.WorldGen.Voxels
{
    /// <summary>
    /// 一个工作项一个体素。Padded 的布局：宽 SizeX+2、高 SizeY、深 SizeZ+2，
    /// 区块内部体素 (x,y,z) 位于 (x+1, y, z+1)。输出 FaceMask 与区块线性化一致。
    /// </summary>
    [BurstCompile]
    internal struct ChunkFaceMaskJob : IJobParallelFor
    {
        [ReadOnly] public NativeArray<byte> Padded;
        [WriteOnly] public NativeArray<byte> FaceMask;   // 长度 SizeX*SizeY*SizeZ
        public int SizeX;
        public int SizeY;
        public int SizeZ;

        public void Execute(int index)
        {
            // 与 VoxelFaceVisibilityJob 相同的换算：x 最快，其次 y，最后 z。
            int x = index % SizeX;
            int yz = index / SizeX;
            int y = yz % SizeY;
            int z = yz / SizeY;

            int strideY = SizeX + 2;                 // padded 中 y+1 的步长
            int strideZ = strideY * SizeY;           // padded 中 z+1 的步长
            int p = (x + 1) + strideY * y + strideZ * (z + 1);

            if (Padded[p] == 0) { FaceMask[index] = 0; return; }

            byte mask = 0;
            if (Padded[p + 1] == 0) mask |= 1 << 0;                         // +X
            if (Padded[p - 1] == 0) mask |= 1 << 1;                         // -X
            if (y + 1 >= SizeY || Padded[p + strideY] == 0) mask |= 1 << 2; // +Y，世界顶为空气
            if (y == 0 || Padded[p - strideY] == 0) mask |= 1 << 3;         // -Y，世界底为空气
            if (Padded[p + strideZ] == 0) mask |= 1 << 4;                   // +Z
            if (Padded[p - strideZ] == 0) mask |= 1 << 5;                   // -Z
            FaceMask[index] = mask;
        }
    }
}
```

要点：

- Y 方向在 padded 数组里没有 apron，所以 `+Y/-Y` 两个面用显式比较，对应上表第 1 条。
- `[WriteOnly]` 的 `FaceMask` 每个工作项只写 `FaceMask[index]`，下标等于 `Execute` 的参数，不需要 `[NativeDisableParallelForRestriction]`。如果以后改成"一个工作项一行"，就要按 3.3 里的做法处理。
- 分支都依赖 `Padded` 中的数据，不依赖其它工作项，没有跨工作项的写。

### 拼装 padded 数组（托管侧）

```csharp
// 假设 center、各邻居均与 center 同高；邻居按各自的 SizeX/SizeZ 取边界。
static NativeArray<byte> BuildPadded(VoxelChunk c, VoxelChunk posX, VoxelChunk negX,
    VoxelChunk posZ, VoxelChunk negZ, Allocator allocator)
{
    int sx = c.SizeX, sy = c.SizeY, sz = c.SizeZ;
    int strideY = sx + 2, strideZ = strideY * sy;
    var padded = new NativeArray<byte>(strideZ * (sz + 2), allocator, NativeArrayOptions.ClearMemory);

    byte[] src = c.RawSolid;                          // internal，同程序集可用
    for (int z = 0; z < sz; z++)
    for (int y = 0; y < sy; y++)
    {
        // 一行 x 连续：从区块拷到 padded 的 (1, y, z+1)。
        NativeArray<byte>.Copy(src, sx * (y + sy * z), padded, 1 + strideY * y + strideZ * (z + 1), sx);
        if (posX != null) padded[(sx + 1) + strideY * y + strideZ * (z + 1)] = posX.Get(0, y, z);
        if (negX != null) padded[0 + strideY * y + strideZ * (z + 1)] = negX.Get(negX.SizeX - 1, y, z);
    }
    for (int y = 0; y < sy; y++)
    for (int x = 0; x < sx; x++)
    {
        if (posZ != null) padded[(x + 1) + strideY * y + strideZ * (sz + 1)] = posZ.Get(x, y, 0);
        if (negZ != null) padded[(x + 1) + strideY * y + 0] = negZ.Get(x, y, negZ.SizeZ - 1);
    }
    return padded;
}
```

`NativeArray<T>.Copy(T[] src, int srcIndex, NativeArray<T> dst, int dstIndex, int length)` 是 Collections 提供的静态重载（待核实 7000.0.0a8 下签名是否保持不变）。±Z 的边界面其实是连续的，可以整块 `Copy`，这里为了对称性用了逐字节循环，性能优化时再改。

### 调度

```csharp
NativeArray<byte> padded = BuildPadded(center, posX, negX, posZ, negZ, Allocator.Persistent);
var mask = new NativeArray<byte>(center.SizeX * center.SizeY * center.SizeZ,
    Allocator.Persistent, NativeArrayOptions.UninitializedMemory);
var job = new ChunkFaceMaskJob
{
    Padded = padded, FaceMask = mask,
    SizeX = center.SizeX, SizeY = center.SizeY, SizeZ = center.SizeZ
};
JobHandle handle = job.Schedule(mask.Length, 256);   // 批大小 256 只是起点，见 1.8
// ... 之后在 handle 完成时读取 mask，再释放：
// padded.Dispose(handle); mask.Dispose(handle2);
```

分配器选 `Persistent` 的原因：管线是跨帧运行的，而 `Allocator.TempJob` 的生命周期上限是 4 帧，超时会报泄漏警告（见 1.5 内存分配器与生命周期）。长期复用时建议池化这些数组，避免每个区块都分配。

方案 A 的 Job 字段形态如下，供对照：

```csharp
[BurstCompile]
internal struct ChunkFaceMaskJobA : IJobParallelFor
{
    [ReadOnly] public NativeArray<byte> Center, PosX, NegX, PosZ, NegZ;
    public bool HasPosX, HasNegX, HasPosZ, HasNegZ;   // 不存在的邻居不要用别的区块数据顶替；
                                                      // 数组字段本身也要传已构造的数组（如长度 0 的 NativeArray），
                                                      // 默认值（未构造）的 NativeArray 在调度时通常会被安全系统拒绝（待核实）
    public int SizeX, SizeY, SizeZ;                   // center 尺寸
    public int PosXSizeX, NegXSizeX, PosZSizeZ, NegZSizeZ; // 邻居自己的尺寸，用于取"最后一列/层"
    [WriteOnly] public NativeArray<byte> FaceMask;

    bool IsSolid(int x, int y, int z)
    {
        if (y < 0 || y >= SizeY) return false;                                   // 表第 1 条
        if (x >= SizeX) return HasPosX && PosX[0 + PosXSizeX * (y + SizeY * z)] != 0;           // 第 2 条
        if (x < 0)      return HasNegX && NegX[(NegXSizeX - 1) + NegXSizeX * (y + SizeY * z)] != 0; // 第 3 条
        if (z >= SizeZ) return HasPosZ && PosZ[x + SizeX * (y + SizeY * 0)] != 0;               // 第 4 条
        if (z < 0)      return HasNegZ && NegZ[x + SizeX * (y + SizeY * (NegZSizeZ - 1))] != 0; // 第 5 条
        return Center[x + SizeX * (y + SizeY * z)] != 0;                          // 第 6 条
    }
    public void Execute(int index) { /* 与方案 B 相同的换算，六次 IsSolid 查询 */ }
}
```

注意第 2、3 条里 `z` 取的是中心的 z，依赖邻居的 `SizeZ` 等于中心；第 4、5 条里 `x` 取的是中心的 x，依赖邻居的 `SizeX` 等于中心。

## 调度与依赖：邻居没就绪怎么办

现有管线的规则在 `ChunkGenerationPipeline.TryScheduleMesh`：区块自身已在 `loaded` 里，并且 `IsReady` 对 x-1、x+1、z-1、z+1 四个邻居都成立（越界视为就绪）才派发建网格任务；超出 `maxMeshingInFlight` 的进 `pendingMesh` 队列。所有调度状态只在主线程修改。

换成 Job 后，这条规则有两种落地方式：

1. 保持现状：采样仍是 `Task.Run`，主线程在"五块都采样完"时才拼 padded 数组并 `Schedule`。邻居未就绪就不调度，不需要 `JobHandle` 依赖。改动最小，推荐作为第一步。
2. 采样也变成 Job（见 3.3 与 3.5）：此时"就绪"可以放宽为"邻居的采样 Job 已调度"，面可见性 Job 用 `JobHandle.CombineDependencies` 合并五个采样 handle 作为 `dependsOn`（见 1.3 调度与 JobHandle 依赖）。主线程不必等采样完成，但要保证被依赖的 `NativeArray` 在这些 Job 完成之前不被释放。

无论哪种方式，释放规则不变：`TryRelease` 只有在自身和四邻居的网格都完成（`meshDone`）后才移除区块。迁到 NativeArray 之后，"移除"要变成"在最后一个读它的 Job 完成后 `Dispose`"，可以用 `NativeArray<T>.Dispose(JobHandle)` 把释放也挂到依赖链上。

同一个 `NativeArray` 被多个 Job 读取时，只要所有 Job 都标 `[ReadOnly]`，它们可以并发运行；只要有一个 Job 以可写方式持有（例如还没完成的采样 Job），读它的 Job 就必须依赖那个 handle（见 1.6 安全系统与竞争条件）。

从掩码到顶点的下一步（`List` 逐个 `Add` 还是 Job 里写 `MeshData`）是 3.4 的内容。本章先让它保持 `BuildMeshFromMask` 那样的主线程或后台线程托管循环，把变量控制在"面判定"这一处。

## 验收：与 BuildChunkData 等价

验收标准分三层，越往下越严格。

1. 统计量一致：同一组 `VoxelChunk` 输入下，参考实现 `ChunkMeshData.Vertices.Count`、`Triangles.Count` 与 Job 掩码推出的值相等。掩码里每个置位对应一个面，一个面是 4 个顶点、6 个索引，所以 `Vertices.Count == 4 * 置位总数`，`Triangles.Count == 6 * 置位总数`。
2. 逐面集合一致：把两边都变成 `(x, y, z, face)` 集合，比较集合相等。参考实现一侧用法线判断 `face`（法线等于 `Directions[face]`），再用 4 个顶点各轴的最小值减去 `(StartX, 0, StartZ)` 得到体素坐标（测试时取 `voxelSize = 1`）。
3. 逐顶点顺序一致：把掩码按"下标升序、面 0 到 5"展开成顶点，与参考实现的 `Vertices` 序列逐个比较。因为两边遍历顺序相同（见上文），这一层应当成立；如果不成立，说明掩码线性化或遍历顺序有偏差。

### 一个简单的测试思路

项目目前没有 asmdef，脚本在默认的 Assembly-CSharp 里；Unity 的测试程序集不能直接引用它，所以需要先给 `WorldGen` 加一个 asmdef（待核实具体接入步骤），再建 EditMode 测试。

```csharp
// 测试骨架：3x3 区块网格，只验证中心区块，每个用例换种子或邻居缺失模式。
[Test]
public void ChunkFaceMaskMatchesBuildChunkData([Values(1, 12345, 777)] int seed)
{
    var density = WorldFields.CreateLearningDefaults(seed).FinalDensity;
    var sampler = new ChunkDensitySampler(density);               // 默认 4x8x4 cell
    VoxelChunk Make(int cx, int cz)
    {
        var chunk = new VoxelChunk(cx * 16, cz * 16, 16, 128, 16);
        sampler.Fill(chunk, 0, -64, 0);                           // originY=-64 即 WorldGenerationSettings.MinY；预览组件默认 sampleOrigin 是 (0,0,0)
        return chunk;
    }
    var c = Make(1, 1);
    var data = new ChunkMeshData();
    VoxelMeshBuilder.BuildChunkData(c, Make(2, 1), Make(0, 1), Make(1, 2), Make(1, 0), 1f, data);
    // 1. 用 BuildPadded + ChunkFaceMaskJob 算掩码（job.Run 即可，便于测试）
    // 2. 比较置位总数与 data.Vertices.Count / 4
    // 3. 把 data 解码成 (x,y,z,face) 集合，与掩码集合比较
}
```

补充这几类用例，它们对应 `IsSolid` 的每一条分支：

- 四个邻居分别为 `null`（世界边缘）。
- 全实心 center，邻居全空或全实心，检查接缝处的面数。
- `SolidCount == 0` 的 center。
- 尾部窄区块：center 宽度小于 16 时，邻居的"最后一列"取自邻居自己的 `SizeX`。
- 人工构造的单体素：在 center 角落放一个实心体素，邻居在对应位置放另一个，确认被剔除的面恰好是接缝那一面。

另一个有用的检查是接缝：把相邻两个区块各自算出的面合起来，接缝两侧都是实心的体素之间不应出现任何面，只有一侧实心一侧空气时才恰好出一个面。

## 预期收益来自哪里

不给倍数，因为取决于硬件、区块高度和实心比例，要用 Profiler 测。收益的来源和抵消项如下：

- 来源一：面判定循环从"托管循环加六次带邻居与空值判断的方法调用"变成 Burst 编译的扁平循环，内存访问是连续数组（见 2.4 SIMD 与自动向量化中关于向量化条件的说明）。
- 来源二：`IJobParallelFor` 把单个区块的体素范围分给多个工作线程，单区块延迟下降。但现有管线已经用 `Task.Run` 在多个区块之间并行，如果线程已被占满，单区块内再并行的额外收益有限。
- 抵消项一：构造 padded 数组的拷贝，以及 `NativeArray` 的分配与释放。
- 抵消项二：掩码之后的顶点生成（`Vertices`、`Normals`、`Triangles` 三个 `List` 的 `Add`）仍然是托管代码，很可能占据 `BuildChunkData` 耗时的大头。没有测量之前不能假定面判定是瓶颈；先在 `ChunkGenerationPipeline.MeshMilliseconds` 的基础上，用 Profiler Marker 把"面判定"和"顶点生成"的耗时分开量。
- 不变的部分：主线程上传 `CreateMesh` 的成本不受本章影响。

## 小结

- 现有 `VoxelFaceVisibilityJob` 是整个世界范围的 `IJobParallelFor`，输入来自 `VoxelVolume.CopySolidToNative`，在流式路径里没有调用点。
- 单区块版本必须复刻 `BuildChunkData` 里 `IsSolid` 的六条规则，尤其是邻居用各自的 `SizeX/SizeZ` 取边界、Y 越界为空气、缺失邻居为空气。
- 方案 B（padded 数组）实现简单、安全关系清晰；方案 A 在区块存储迁到 `NativeArray` 后更省拷贝。
- 验收用统计量、逐面集合、逐顶点顺序三层比对，并覆盖接缝与缺失邻居用例。
- 收益要分项测量，别假定面判定就是瓶颈。

## 自测题

1. `VoxelFaceVisibilityJob` 为什么不能直接逐区块调用而不改？
   答：它的边界判断基于整个体积的 `Width/Height/Depth`，区块侧面的邻居会被当成空气，接缝处会多出面。
2. 方案 B 里 ±Z 邻居的边界面和 ±X 邻居的边界面，拷贝代价有何不同？
   答：线性化为 `x + SizeX * (y + SizeY * z)`，±Z 的边界面是连续内存，可整块拷贝；±X 是跨步访问，只能逐字节收集。
3. 为什么缺失的邻居不能用 center 数组顶替？
   答：同一个 `NativeArray` 在一个 Job 结构体里出现两次时，只要有一个字段缺 `[ReadOnly]`，安全系统就会报冲突；而且语义上缺失邻居应为空气，不是 center 的数据。
4. 掩码按下标升序展开，为什么能和 `BuildChunkData` 的顶点顺序逐个对应？
   答：两者遍历顺序都是 z 外、y 中、x 内、面 0 到 5，线性化 `x + SizeX*(y + SizeY*z)` 的升序就是这个顺序。
5. 管线跨多帧运行，数组该用什么分配器，为什么？
   答：`Allocator.Persistent`（配合池化）。`TempJob` 的生命周期上限为 4 帧，跨帧持有会产生泄漏警告。

## 参考

- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelFaceVisibilityJob.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelMeshBuilder.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelChunk.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelVolume.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkMeshData.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkGenerationPipeline.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelWorldPreview.cs
- https://docs.unity3d.com/ScriptReference/Unity.Jobs.IJobParallelForExtensions.Schedule.html
- https://docs.unity3d.com/ScriptReference/Unity.Collections.NativeDisableParallelForRestrictionAttribute.html
- D:\UnityHub\Project\程序化生成\Library\PackageCache\com.unity.burst@626e66ab421b\Runtime\TypeForwarders.cs

