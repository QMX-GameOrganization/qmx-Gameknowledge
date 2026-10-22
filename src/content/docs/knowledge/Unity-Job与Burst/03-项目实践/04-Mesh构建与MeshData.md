---
title: "3.4 Mesh 构建与 MeshData"
description: 把区块网格从 List 加 SetVertices 的托管路径，改造为 Mesh.AllocateWritableMeshData 加 Job 直写缓冲、主线程只 Apply 的流程，含顶点格式、索引格式、Bounds 与内存账。
sidebar:
  order: 4
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x / Collections 2.x / Mathematics 1.3.x 为主线；本项目的 Unity 7000.0.0a8 中 Burst 2.0.0 与 Collections 6.7.0 是转发到引擎内置模块的壳包。核实不了的标"待核实"。
>
> 本章代码为教学骨架，未在 Unity 内编译，复制前核对 API 与项目现状。

## 目标与现状

目标：让"顶点和索引的生成"与"写进 Mesh"这两步都离开托管 `List`，由 Burst Job 直接写 `MeshData` 的原生缓冲，主线程只做 `Mesh.ApplyAndDisposeWritableMeshData`。

### 现状流程（以代码为准）

```
后台线程 (Task.Run)                         主线程 (Pump 每帧)
-------------------                         -------------------
ScheduleMesh: 在主线程取好 center/四邻居引用
  |
  v
meshDataPool.TryTake / new ChunkMeshData
  |
  v
VoxelMeshBuilder.BuildChunkData(              meshedQueue.TryDequeue
   center,posX,negX,posZ,negZ,size,data)        |
  - data.Clear()                                v
  - 逐体素逐面: IsSolid(...) 判邻居           uploadMesh(data)
  - Vertices.Add / Normals.Add x4               = AddChunkObject(VoxelMeshBuilder.CreateMesh(data))
  - Triangles.Add x6                              new Mesh{ indexFormat = UInt32 }
  |                                               SetVertices / SetNormals / SetTriangles(.,0)
  v                                               RecalculateBounds()
meshedQueue.Enqueue((index, data))                UploadMeshData(true)
                                                data.Clear(); meshDataPool.Add(data)
```

要点，均来自 `ChunkGenerationPipeline.cs` 与 `VoxelMeshBuilder.cs`：

- `ChunkMeshData` 持有三个 `List`：`Vertices`（`List<Vector3>`）、`Normals`（`List<Vector3>`）、`Triangles`（`List<int>`），外加 `Name`。`Clear()` 只清空计数，容量保留，所以对象池复用后不再重复扩容。
- 对象池是 `ConcurrentBag<ChunkMeshData> meshDataPool`：后台任务 `TryTake`，没有就 `new`；主线程上传完后 `Clear()` 再 `Add` 回池。
- `BuildChunkData` 不调用 Unity API；顶点是世界体素坐标乘 `voxelSize`，即 `(position + Corners[face * 4 + corner]) * voxelSize`，其中 `position = (center.StartX + x, y, center.StartZ + z)`。`AddChunkObject` 创建的子物体本地位置为零，不需要再偏移。
- 每面 4 个顶点，法线取面方向；三角形索引固定 `(start, start+1, start+2)` 与 `(start, start+2, start+3)`。
- `CreateMesh` 固定 `IndexFormat.UInt32`，用 `RecalculateBounds()` 再扫一遍顶点算包围盒，最后 `UploadMeshData(true)`（参数是 `markNoLongerReadable`）。
- 主线程每帧最多上传 `chunksPerFrame` 个（`VoxelWorldPreview` 默认 4）。空网格（`IsEmpty`）不创建 Mesh，也不占上传额度。
- `BuildChunk` 是主线程便捷入口，用 `private static readonly ChunkMeshData MainThreadData` 复用缓冲，非线程安全，后台线程不能用。

代码里还保留了 `Build`、`BuildRegion`、`BuildWithJobs`、`BuildChunkMeshesWithJobs`。其中 `BuildWithJobs` 只把"面可见性"放进 Job（`VoxelFaceVisibilityJob`），顶点生成仍然在主线程循环里 `Add` 到 `List`，这正是本章要改掉的部分。

## 顶点数据量估算

以下是估算，不是实测。设某区块暴露面数为 `F`：

| 项 | 公式 | 说明 |
| --- | --- | --- |
| 顶点数 | `V = 4F` | 每面独立 4 个顶点，不共享 |
| 索引数 | `I = 6F` | 每面 2 个三角形 |
| 位置 | `12 * V` 字节 | `Vector3`，3 个 float |
| 法线 | `12 * V` 字节 | 同上 |
| 索引（UInt32） | `4 * I = 24F` 字节 | |
| 合计（现状） | `96F + 24F = 120F` 字节 | 每面约 120 字节 |
| 合计（UInt16 索引） | `96F + 12F = 108F` 字节 | |

CPU 侧现状缓冲的数据部分也是约 `120F` 字节（三个 `List` 的有效元素），另有扩容留下的空闲容量，容量大小取决于历史最大值，需实测。

## 改造目标：MeshData 直写

### 为什么能在 Job 里写

脚本 API 文档对 `Mesh.MeshData` 的描述是：它是为 C# Job System 访问设计的结构体，可写的 `MeshData` 通过 `Mesh.AllocateWritableMeshData` 得到，`MeshDataArray` 与 `MeshData` 可以在任意线程访问。工作流是：

1. 主线程 `Mesh.AllocateWritableMeshData(n)` 得到 `Mesh.MeshDataArray`。
2. 对其中每个 `MeshData` 调 `SetVertexBufferParams` 定义顶点数量与布局，再用 `GetVertexData<T>()` 拿到可写的 `NativeArray<T>`。
3. 调 `SetIndexBufferParams` 定义索引数量与格式，用 `GetIndexData<T>()` 写索引。
4. 设 `subMeshCount`，用 `SetSubMesh` 设子网格。
5. 主线程 `Mesh.ApplyAndDisposeWritableMeshData(dataArray, mesh 或 meshes, flags)`。Apply 之后 `MeshDataArray` 即被释放，不能再用。

官方文档强调：通过这条路径 Unity 只做很少的数据校验，调用者必须保证子网格的索引范围与拓扑正确，且各子网格的 `indexStart`/`indexCount` 不得互相重叠。创建 `MeshDataArray` 本身有内存跟踪开销，所以文档建议一次 `AllocateWritableMeshData` 申请多个，而不是多次各申请一个。

### 两遍法

难点：`SetVertexBufferParams` 要先知道顶点总数，而顶点数取决于暴露面数。所以拆成两遍：

```
Job1 计数        每个区块: 读 solid(中心+四邻居) -> FaceMask(每体素6位) -> FaceCount
                   |
          (主线程 Complete 一次, 读 FaceCount)
                   |
主线程           对每个区块: V=4F, I=6F -> SetVertexBufferParams / SetIndexBufferParams / SetSubMesh
                   |
Job2 写入        每个区块: 按 FaceMask 顺序写 verts / indices
                   |
主线程           ApplyAndDisposeWritableMeshData(dataArray, meshes, flags)
```

偏移怎么得到取决于缓冲的组织方式，有两种：

- 方式 A，每区块一个 `MeshData`（一个 `Mesh`，对应现在每区块一个子 GameObject）。缓冲是区块私有的，Job2 内部用一个运行计数器 `face` 顺序写，顶点偏移 `4*face`、索引偏移 `6*face`。区块之间不需要前缀和。要在区块内部再并行，才需要对"每列的面数"做前缀和（可选，先不做）。
- 方式 B，多个区块合并进同一个 `Mesh`（合并网格，可用多个子网格各占一段）。此时需要对各区块的 `FaceCount` 做前缀和，得到每个区块在共享缓冲里的顶点起点 `vertexStart[c] = 4 * sum(F[0..c-1])` 与索引起点 `indexStart[c] = 6 * sum(F[0..c-1])`，Job2 对各区块并行写自己那一段，因为段不重叠，需要给共享的 `NativeArray` 加 `[NativeDisableParallelForRestriction]`（见 1.6 安全系统与竞争条件）。代价是失去逐区块的视锥剔除粒度，并且合并后的顶点数更容易超过 UInt16 上限。

本项目现状是方式 A，建议保持。批量 Apply 指的是方式 A 的多区块版本：一次 `AllocateWritableMeshData(n)`，n 个区块各写各的 `MeshData`，最后一次 `ApplyAndDisposeWritableMeshData(dataArray, meshes, flags)`，其中 `meshes` 是长度为 n 的 `Mesh[]` 或 `List<Mesh>`（文档给出的三个重载：单个 `Mesh`、`Mesh[]`、`List<Mesh>`，数组长度必须与 `MeshDataArray` 一致）。

| 方式 | 适用 | 注意 |
| --- | --- | --- |
| 单区块 Apply | 每帧完成一个区块就立刻上传，延迟低 | 每次 Apply 前要有各自的 `MeshDataArray(1)` |
| 多区块批量 Apply | 一批区块一起完成再上传，`MeshDataArray` 开销摊薄 | 一批里最慢的区块决定整批延迟；`Complete` 要等整批 |

## 顶点格式设计

`SetVertexBufferParams(int vertexCount, params VertexAttributeDescriptor[] attributes)` 同时决定顶点数和布局。`VertexAttributeDescriptor` 的构造参数是 `(VertexAttribute attribute, VertexAttributeFormat format, int dimension, int stream)`，除 `attribute` 外都有默认值（官方示例里 `new VertexAttributeDescriptor(VertexAttribute.Position)` 与 `new VertexAttributeDescriptor(VertexAttribute.Normal, stream: 1)` 即用默认的 `Float32`、3 维）。

| 选项 | 每顶点字节 | 布局写法 | 对着色器的影响 | 备注 |
| --- | --- | --- | --- | --- |
| A 朴素：Position float3 + Normal float3 | 24 | `Position, Float32, 3` 与 `Normal, Float32, 3`，同一 stream | 与 URP Lit 兼容，不改材质 | 与现状数据一致，最适合第一步验收 |
| B 去掉法线：Position float3 | 12 | 只有 `Position, Float32, 3` | URP Lit 需要法线，必须自定义着色器，由面方向推导法线 | 顶点数据减半，但要改着色器 |
| C 位置打包进 uint | 4（打包字） | 一个 `UInt32` 单通道属性，语义放哪个通道待核实 | 必须自定义着色器：解包坐标、推导法线、本地到世界变换 | 最省，约束最多 |

### 对材质和着色器的影响

现状材质在 `VoxelWorldPreview.ApplyMaterial` 里：没指定 `material` 时用 `Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard")` 创建。URP Lit 的光照需要顶点法线，所以选项 A 不用动材质；选项 B 与 C 去掉了法线属性，用 Lit 会得到错误光照（具体表现待核实），必须换成自定义着色器：

- 方式一：面方向编码在顶点里（例如 C 方案的打包字含 3 位面索引），在顶点着色器里查表还原法线。
- 方式二：在片元着色器里用位置的屏幕空间导数 `ddx`/`ddy` 算平面法线，不需要任何法线数据，但需要在着色器里自己写；这在体素的平面面上法线精确（实现细节待核实）。
- 自定义着色器需要同时处理 ShadowCaster、DepthOnly（以及启用时的 DepthNormals）等 Pass，否则阴影和深度会缺失或错位（具体 Pass 列表以所用 URP 版本为准，待核实）。

另外，选项 C 的整数顶点属性在部分平台或图形 API 上的支持情况未核实（待核实），不要在目标平台未验证前就作为默认方案。

### 位置打包的容量估算

区块内局部坐标 `x`、`z` 的范围是 `0..16`（含角点偏移，需要 5 位），`y` 的范围是 `0..SizeY`。若 `SizeY` 不超过 511，则 `y` 需要 9 位；`x`、`z`、`y` 共 19 位，再加 3 位面索引共 22 位，一个 32 位字放得下。这要求顶点使用区块局部坐标，因此子 GameObject 必须带上区块的世界位置 `(StartX * voxelSize, 0, StartZ * voxelSize)`，与现状"顶点已是世界坐标、子物体在原点"不同。这是一个需要同步修改 `AddChunkObject` 的地方。

### 骨架里的顶点结构

```csharp
using System.Runtime.InteropServices;
using Unity.Mathematics;

// 选项 A: 与现状等价，24 字节，字段顺序与 VertexAttributeDescriptor 顺序一致
[StructLayout(LayoutKind.Sequential)]
public struct VoxelVertexPN
{
    public float3 Position;
    public float3 Normal;
}
```

对应的布局声明（在主线程调用）：

```csharp
using UnityEngine.Rendering;

static readonly VertexAttributeDescriptor[] LayoutPN =
{
    new VertexAttributeDescriptor(VertexAttribute.Position, VertexAttributeFormat.Float32, 3),
    new VertexAttributeDescriptor(VertexAttribute.Normal,   VertexAttributeFormat.Float32, 3),
};
// data.SetVertexBufferParams(vertexCount, LayoutPN);
```

同一个 stream 内，`VoxelVertexPN` 的字段顺序（Position 在前、Normal 在后）要和描述符数组的顺序一致，并且属性顺序要符合 `VertexAttribute` 枚举顺序（Unity 对声明顺序的具体要求，待核实）。

## 索引格式：UInt16 还是 UInt32

`SetIndexBufferParams(int indexCount, IndexFormat format)`，`IndexFormat` 有 `UInt16` 与 `UInt32`。UInt16 的最大索引值是 65535，所以一个 `Mesh`（不考虑 `baseVertex`）的顶点数不超过 65536 才能用。

用本项目的区块尺寸算上限，设区块体素数 `N = 16 * 16 * SizeY`：

- 最坏情形是三维棋盘：约一半体素为实心且互不相邻，每个实心体素 6 个面都暴露，`F_max = 6 * N / 2 = 3N`，顶点数 `V_max = 12N`。
- 要保证 UInt16 始终够用：`12 * 256 * SizeY <= 65536`，即 `SizeY <= 21`（取整）。
- `SizeY = 128`（`VoxelWorldPreview` 默认世界尺寸 128 的情形）时，最坏顶点数 `12 * 256 * 128 = 393216`，远超 65536。所以不能无条件用 UInt16。

实际地形远没有棋盘那么碎，但"实际够用"必须由运行时判断，不能靠假设。判断条件：Job1 得到 `F` 后，`4 * F <= 65536`（即 `F <= 16384`）则用 `IndexFormat.UInt16`，否则 `UInt32`。这意味着 Job2 要支持两种索引宽度：

- 做两个 Job 结构，或在一个 Job 里按 `bool UseUInt16` 分支，分别调用 `GetIndexData<ushort>()` 与 `GetIndexData<uint>()`。
- 同一批里不同区块可以用不同格式，每个 `Mesh` 独立。
- 节省量：每个索引省 2 字节，每面省 12 字节（约占现状 120 字节的 10%）。收益有限，建议放在 UInt32 版本验收通过之后再做。

## Bounds 与 MeshUpdateFlags

现状 `CreateMesh` 调 `RecalculateBounds()`，会遍历全部顶点。区块的包围盒其实已知，用世界尺寸直接给即可：

```
min  = (StartX * voxelSize, 0,             StartZ * voxelSize)
size = (SizeX * voxelSize,  SizeY * voxelSize, SizeZ * voxelSize)
```

注意 `UnityEngine.Bounds` 用 center 和 size 构造，所以 `chunkBounds = new Bounds(min + size * 0.5f, size)`。

这里 `y` 的范围从 0 起，因为 `BuildChunkData` 里顶点的 `y` 是区块局部的 `y` 乘 `voxelSize`，没有加 `originY`。这个包围盒是上界（可能比实际空气多），对视锥剔除是保守的，代价是空区块部分被多画的概率略增；如需紧包围盒，可在 Job2 里累计 min/max 再写出（可选）。

相关 API 事实，来自脚本 API 文档：

- `SubMeshDescriptor` 的字段有 `indexStart`、`indexCount`、`topology`、`baseVertex`、`bounds`、`firstVertex`、`vertexCount`。构造函数 `new SubMeshDescriptor(indexStart, indexCount)`（`topology` 默认三角形，也可显式传 `MeshTopology.Triangles`）。
- 按 `SubMeshDescriptor` 页的说明，`bounds`、`firstVertex`、`vertexCount` 由 `Mesh.SetSubMesh` 自动计算，除非传入 `MeshUpdateFlags.DontRecalculateBounds`。官方 `AllocateWritableMeshData` 示例是先写完顶点和索引，再调 `SetSubMesh`；本章骨架在写入之前就要定缓冲大小，所以先带该 flag 并手动填这三项（`MeshData.SetSubMesh` 对这几项的具体计算时机，文档没有细说，待核实）。
- `MeshUpdateFlags` 的成员：`Default`、`DontValidateIndices`、`DontResetBoneBounds`、`DontNotifyMeshUsers`、`DontRecalculateBounds`、`DontValidateLodRanges`。可以用 `|` 组合。
- `ApplyAndDisposeWritableMeshData` 的 `flags` 参数是 `MeshUpdateFlags`。文档说明它很少校验数据，并说 `DontValidateLodRanges` 可关闭 LOD 范围校验。`DontValidateIndices` 在 Apply 路径上是否生效，文档没有明说（待核实）。
- `MeshData.SetSubMesh(int index, SubMeshDescriptor desc, MeshUpdateFlags flags)` 带 `flags` 参数（来自脚本 API 页的声明；官方示例省略该参数，说明它有默认值）。骨架同时在 Apply 之后显式设 `mesh.bounds`，不单靠这个参数。
- Apply 带 `DontRecalculateBounds` 后，`Mesh.bounds` 是否保持 `SubMeshDescriptor.bounds`/你设置的值，需要在 Unity 里验证（待核实）。稳妥做法：Apply 之后立刻 `mesh.bounds = chunkBounds;`，并在 Scene 视图或 Frame Debugger 里确认剔除正常。

建议的 flags 组合：先用 `MeshUpdateFlags.DontRecalculateBounds`，其余保持默认校验；等验收通过、需要进一步省时间再加 `DontValidateIndices`。

## 骨架代码

假设已经有 3.1 的单区块版面可见性 Job 产出的 `FaceMask`（每体素 6 位，位序与 `VoxelFaceVisibilityJob` 相同：0 为 +X，1 为 -X，2 为 +Y，3 为 -Y，4 为 +Z，5 为 -Z）。

```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;
using Unity.Mathematics;
using UnityEngine;
using UnityEngine.Rendering;

// Job1 的计数部分: 对一个区块的 FaceMask 数 1 的个数。
[BurstCompile]
public struct CountFacesJob : IJob
{
    [ReadOnly] public NativeArray<byte> FaceMask;
    [WriteOnly] public NativeArray<int> FaceCount; // 长度 1

    public void Execute()
    {
        int n = 0;
        for (int i = 0; i < FaceMask.Length; i++)
            n += math.countbits((uint)FaceMask[i]);
        FaceCount[0] = n;
    }
}

// Job2: 一个区块一个 Job，写自己的 MeshData。
[BurstCompile]
public struct WriteChunkMeshJob : IJob
{
    [ReadOnly] public NativeArray<byte> FaceMask;
    [ReadOnly] public NativeArray<float3> Corners;   // 24 个，同 VoxelMeshBuilder.Corners
    [ReadOnly] public NativeArray<float3> Directions; // 6 个，同 VoxelMeshBuilder.Directions
    public int SizeX, SizeY, SizeZ;
    public int StartX, StartZ;
    public float VoxelSize;
    public Mesh.MeshData Output;   // 主线程已调用 SetVertexBufferParams / SetIndexBufferParams

    public void Execute()
    {
        var verts = Output.GetVertexData<VoxelVertexPN>();
        var indices = Output.GetIndexData<uint>();   // 选 UInt32 时
        int face = 0;
        for (int z = 0; z < SizeZ; z++)
        for (int y = 0; y < SizeY; y++)
        for (int x = 0; x < SizeX; x++)
        {
            byte mask = FaceMask[x + SizeX * (y + SizeY * z)];
            if (mask == 0) continue;
            float3 pos = new float3(StartX + x, y, StartZ + z);
            for (int f = 0; f < 6; f++)
            {
                if ((mask & (1 << f)) == 0) continue;
                int v0 = face * 4;
                for (int c = 0; c < 4; c++)
                    verts[v0 + c] = new VoxelVertexPN
                    {
                        Position = (pos + Corners[f * 4 + c]) * VoxelSize,
                        Normal = Directions[f],
                    };
                int i0 = face * 6;
                indices[i0 + 0] = (uint)v0; indices[i0 + 1] = (uint)(v0 + 1); indices[i0 + 2] = (uint)(v0 + 2);
                indices[i0 + 3] = (uint)v0; indices[i0 + 4] = (uint)(v0 + 2); indices[i0 + 5] = (uint)(v0 + 3);
                face++;
            }
        }
    }
}
```

主线程调用（单批 n 个区块，批量 Apply）：

```csharp
void BuildBatch(ChunkJobInput[] inputs, Mesh[] meshes, Material material)
{
    int n = inputs.Length;
    // 1. Job1: FaceMask 已由 3.1 的 Job 产出; 这里排 CountFacesJob 并 Complete。
    var counts = new NativeArray<int>(n, Allocator.TempJob);
    var handles = new NativeArray<JobHandle>(n, Allocator.Temp);
    for (int i = 0; i < n; i++)
    {
        var countJob = new CountFacesJob
        {
            FaceMask = inputs[i].FaceMask,
            FaceCount = counts.GetSubArray(i, 1),
        };
        handles[i] = countJob.Schedule();
    }
    JobHandle.CombineDependencies(handles).Complete();   // 同步点: 要用计数调用 SetVertexBufferParams

    // 2. 分配 MeshData 并定义缓冲大小
    var dataArray = Mesh.AllocateWritableMeshData(n);
    for (int i = 0; i < n; i++)
    {
        int faces = counts[i];
        var data = dataArray[i];
        data.SetVertexBufferParams(faces * 4, LayoutPN);
        data.SetIndexBufferParams(faces * 6, IndexFormat.UInt32);
        data.subMeshCount = 1;
        // 此时顶点和索引还没写入。SetSubMesh 默认会按缓冲内容计算 bounds / firstVertex / vertexCount，
        // 所以带 DontRecalculateBounds，并在描述符里手动给出这三项。
        var desc = new SubMeshDescriptor(0, faces * 6, MeshTopology.Triangles)
        {
            firstVertex = 0,
            vertexCount = faces * 4,
            bounds = inputs[i].Bounds,
        };
        data.SetSubMesh(0, desc, MeshUpdateFlags.DontRecalculateBounds);
    }

    // 3. Job2: 并行写入
    for (int i = 0; i < n; i++)
    {
        var writeJob = new WriteChunkMeshJob
        {
            FaceMask = inputs[i].FaceMask,
            Corners = CornersNative, Directions = DirectionsNative,
            SizeX = inputs[i].SizeX, SizeY = inputs[i].SizeY, SizeZ = inputs[i].SizeZ,
            StartX = inputs[i].StartX, StartZ = inputs[i].StartZ,
            VoxelSize = voxelSize,
            Output = dataArray[i],
        };
        handles[i] = writeJob.Schedule();
    }
    JobHandle.CombineDependencies(handles).Complete();

    // 4. 主线程唯一的 Unity 对象操作: 批量 Apply
    for (int i = 0; i < n; i++) meshes[i] = new Mesh { name = inputs[i].Name };
    Mesh.ApplyAndDisposeWritableMeshData(dataArray, meshes, MeshUpdateFlags.DontRecalculateBounds);
    for (int i = 0; i < n; i++) meshes[i].bounds = inputs[i].Bounds;

    counts.Dispose();
    handles.Dispose();
}
```

骨架说明：

- `GetSubArray` 配合多个并发 Job 写同一个 `NativeArray<int>` 的不同片段，安全系统是否放行取决于版本，若报冲突就改成每个区块独立的长度 1 数组（待核实）。
- `Corners` 与 `Directions` 是 24 与 6 个 `float3` 的 `NativeArray`，在初始化时 `Allocator.Persistent` 分配一次，销毁时释放；不要直接在 Job 里用静态数组（原因见 2.8 静态数据与 SharedStatic）。
- 如果 Job2 出现 `SubMesh` 与顶点数不匹配之类的问题，优先检查 `faces` 是否与 `FaceMask` 的 1 的个数一致，因为 Apply 路径几乎没有校验。
- 面的写入顺序与 `BuildChunkData` 一致（z、y、x 三重循环，每个体素按 face 0..5），所以顶点序列应当逐位一致，便于逐元素对比。

## Mesh 变成不可读之后的限制

现状 `UploadMeshData(true)` 的参数 `markNoLongerReadable` 为 true，上传到 GPU 后 CPU 侧的网格副本被释放，Mesh 变成不可读。这能省下一份 CPU 内存，但意味着：

- 不能再用 `mesh.vertices`、`mesh.triangles` 之类属性回读，也不能再 `Mesh.AcquireReadOnlyMeshData` 做后处理（对不可读网格的行为待核实）。
- 运行时用它创建 `MeshCollider` 通常需要可读网格（待核实）；项目目前没有碰撞需求，如果以后要加，要么保留可读、要么单独另建碰撞网格。
- 不能 `CombineMeshes`，也不能再编辑顶点。想改网格就重新生成，这与"区块数据可重算"的设计吻合。

走 `ApplyAndDisposeWritableMeshData` 之后，是否还需要 `UploadMeshData(true)` 来释放 CPU 副本、以及 Apply 出来的 Mesh 默认是否可读，文档没有写明（待核实）。做法：Apply 后加一次 `mesh.UploadMeshData(true)`，再用 Memory Profiler 或 Profiler 的 Mesh 内存统计对比前后，以实测为准。

## 显存与 CPU 内存的账

设一个区块暴露面数为 `F_c`，顶点步长 `S`（字节），索引宽度 `W`（2 或 4 字节）：

```
GPU 网格内存 (每区块)  = 4 * F_c * S + 6 * F_c * W
整个世界 GPU 内存      = sum_c ( 4 * F_c * S + 6 * F_c * W )

CPU 瞬时内存 (现状, 每个在途区块) ≈ 4 * F_c * 24 + 6 * F_c * 4 + List 容量余量
CPU 瞬时内存 (MeshData, 每个在途区块) ≈ 4 * F_c * S + 6 * F_c * W   (原生缓冲, Apply 后释放)
```

对比时要注意：

- 现状有两份 CPU 数据：`ChunkMeshData` 的 `List`（可复用，容量按历史峰值长期占用）和 `Mesh` 内部副本（`SetVertices` 等会拷贝，`UploadMeshData(true)` 后释放）。`MeshData` 方案没有 `List` 这一份，但 Job 运行期间的 `MeshDataArray` 是原生内存，随 Apply 释放，需要在 Profiler 里确认峰值。
- 现状的 `meshDataPool` 在后台线程和主线程之间流转，池里保留的容量不随世界缩小而释放；`MeshData` 方案按 `F_c` 精确分配，无此长期占用。
- 所有具体字节数都取决于 `F_c`，要用 `SolidCount` 与实际的 `mesh.vertexCount` 实测后代入公式，这里不给固定数值。

## 验收

1. 数量一致：对同一个区块、同一份 `VoxelChunk` 数据，分别走旧路径 `BuildChunkData` 与新路径，比较 `ChunkMeshData.Vertices.Count` 与 `mesh.vertexCount`，`ChunkMeshData.Triangles.Count / 3` 与 `mesh.GetIndexCount(0) / 3`。四邻居缺失（世界边缘）的区块也要测。
2. 内容一致：新旧顶点顺序按设计应逐位相同，可对前 N 个顶点的位置与法线逐个比对；若不要求顺序一致，则对"面的集合"（体素坐标加面索引）做排序后比较。
3. 渲染一致：同一 `seed` 与 `sampleOrigin` 下，新旧路径的画面截图对比，光照一致（选项 A 下材质不变）；边界区块之间没有缝或多余的面。
4. 包围盒：Scene 视图开 Gizmos 或检查 `mesh.bounds`，应等于上文的 `min`/`size`；移动相机到区块边缘附近，确认没有被错误剔除。
5. 空区块：`SolidCount == 0` 或 `F == 0` 时不应创建 Mesh（现状行为是 `IsEmpty` 就不上传），新路径要保持一致。批量 Apply 时 `MeshDataArray` 里的每一项都会写进对应的 `Mesh`，没法单独跳过某一项，所以空区块的做法是 Apply 之后 `Destroy` 这个空 `Mesh`、不创建子物体（或者在分配前就把 `F == 0` 的区块排除在这一批之外）。
6. 泄漏与安全检查：开启 Jobs 的泄漏检测，反复"生成、清除"若干次，不应出现泄漏报告（见 1.5 内存分配器与生命周期）。

## 与现有管线的衔接提醒

- 现有 `ChunkGenerationPipeline` 的 `uploadMesh` 回调签名是 `Action<ChunkMeshData>`，改造后上传单元不再是 `ChunkMeshData`，而是"已完成的 Job 句柄加 `MeshDataArray`"，调度部分见 3.5 调度管线与 Profiling。
- `VoxelChunk` 的 `solid` 是托管 `byte[]`，`RawSolid` 是 `internal`。项目里没有找到 `.asmdef`，所以同一程序集内可直接访问；Job 要吃的是 `NativeArray<byte>`，需要一次拷贝，或让采样阶段直接写原生数组（见 3.3 Cell 插值与同号填充 Job）。
- 四邻居以只读数据传入，邻居必须在 Job 运行期间保持存活，这与 3.5 的生命周期规则一致。

## 小结

- 现状每面约 120 字节（位置 12x4 加法线 12x4 加 6 个 UInt32 索引 24），属估算。
- `MeshData` 路径：主线程 `AllocateWritableMeshData` 和 `SetVertexBufferParams`/`SetIndexBufferParams`，Job 直写 `GetVertexData<T>()` 与 `GetIndexData<T>()`，主线程 `ApplyAndDisposeWritableMeshData`。
- 先计数后写入的两遍法是必须的，因为缓冲大小要在写入前定好；区块私有缓冲只需区块内计数器，合并网格才需要跨区块前缀和。
- 去掉法线或打包位置会省内存，但要自定义着色器，应放在朴素格式验收之后。
- 区块高 128 时不能无条件用 UInt16，要按 `4F <= 65536` 在运行时判断。
- Bounds 用世界尺寸直接设，Apply 后显式赋值，避免 `RecalculateBounds` 的遍历。

## 自测题

1. 为什么 `SetVertexBufferParams` 必须在 Job2 之前调用，因此需要两遍？
   答：缓冲大小要由暴露面数决定，而暴露面数只有算完可见性才知道；`GetVertexData`/`GetIndexData` 返回的数组长度在 Params 调用时就固定了。
2. `SizeY = 128` 的区块最坏情形顶点数是多少，能否保证用 UInt16？
   答：最坏棋盘 `V_max = 12 * 256 * 128 = 393216`，超过 65536，不能保证；要按实际 `F` 在运行时判断。
3. 区块私有缓冲与合并网格，哪个需要跨区块前缀和？
   答：合并网格；各区块要写进共享缓冲的不同区间，起点由 `FaceCount` 的前缀和给出。
4. 选项 B 去掉法线后，为什么不能继续用 URP Lit？
   答：Lit 的光照依赖顶点法线，没有法线属性就得不到正确光照，需要自定义着色器推导法线（并补齐阴影/深度 Pass）。
5. 把 `UploadMeshData(true)` 之后的 Mesh 用来建 `MeshCollider` 可能有什么问题？
   答：Mesh 不可读，运行时建碰撞体通常需要可读数据（待核实），要保留可读副本或另建碰撞网格。

## 参考

- https://docs.unity3d.com/ScriptReference/Mesh.MeshData.html
- https://docs.unity3d.com/ScriptReference/Mesh.ApplyAndDisposeWritableMeshData.html
- https://docs.unity3d.com/ScriptReference/Rendering.MeshUpdateFlags.html
- https://docs.unity3d.com/ScriptReference/Rendering.SubMeshDescriptor.html
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelMeshBuilder.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkMeshData.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkGenerationPipeline.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelWorldPreview.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelFaceVisibilityJob.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelChunk.cs

