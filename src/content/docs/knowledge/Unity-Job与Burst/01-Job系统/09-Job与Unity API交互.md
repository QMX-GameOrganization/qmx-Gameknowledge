---
title: "1.9 Job 与 Unity API 交互"
description: Job 里能用什么、不能用什么：数学与随机数、Mesh 数据 API、物理批处理命令、Transform、纹理与 GPU 缓冲，以及主线程与 Job 的分工对照。
sidebar:
  order: 9
---

> 适用版本：以 Unity 6000.x 的 Burst 1.8.x / Collections 2.x / Mathematics 1.3.x 为主线；本项目的 Unity 7000.0.0a8 中 Burst 2.0.0 与 Collections 6.7.0 是转发（shim）壳包，API 仍在 `Unity.Burst` / `Unity.Collections` 命名空间。本章引用的 Scripting API 页面核对自 Unity 6.6（6000.6）文档，7000 上的差异待核实。

## 要点

- Job 运行在工作线程上，Unity 的大部分 API（`GameObject`、`Transform`、`Mesh` 实例方法、`Physics.Raycast` 等）只能在主线程调用，不能在 Job 里用。
- Job 里的数据必须是值类型和 Native 容器。托管对象、`UnityEngine.Object` 派生类的引用不能放进 Job 结构体（Burst 下尤其严格）。
- Unity 为"需要 Job 化的引擎功能"专门提供了线程安全的数据通道：`Mesh.MeshData`、`RaycastCommand` 一类批处理命令、`TransformAccessArray`、`Texture.GetRawTextureData<T>()`、`GraphicsBuffer.LockBufferForWrite`。思路是统一的：主线程拿到可在 Job 里访问的原始数据视图，Job 里只处理数据，主线程再提交。
- 本项目当前的 `ChunkMeshData`（`List<Vector3>` 等托管列表）要在主线程用 `SetVertices` / `SetTriangles` 上传；若要把网格化搬进 Burst Job，`MeshData` 是对应的出口。

## Job 里不能碰什么，能用什么

### 不能碰

- `UnityEngine.Object` 派生类的成员：`Transform.position`、`GameObject.SetActive`、`Mesh.vertices`、`Material.SetFloat` 等。它们依赖主线程上的引擎状态，且在 Burst 里不可编译。
- 托管对象：`class` 实例、`string`（除少量受支持用法）、`List<T>`、委托、`System.Collections.Generic` 的容器。Burst 只支持 HPC# 子集。
- 大多数 Unity 静态 API：`Physics.*`、`Resources.Load`、`Time.deltaTime`（属性读取不能在 Job 内进行，需要在主线程读出后作为字段传入）。

### 能用

- `Unity.Mathematics`：`float3`、`int2`、`math.*`、`quaternion`、`noise.*`。这是 Burst 友好的数学库，也是向量化的首选。
- `UnityEngine.Mathf` 的纯数学静态函数（`Mathf.Sqrt`、`Mathf.Clamp` 等）：它们是静态方法且不依赖引擎状态，多数情况下能在 Burst 中编译。是否逐个函数受支持、行为是否与 `math.*` 完全一致，官方文档没有逐项列出，请以编译结果为准（待核实）。新代码优先用 `Unity.Mathematics`。
- 随机数：用 `Unity.Mathematics.Random`（可变结构体，`Random.CreateFromIndex(uint)` 创建，`NextFloat()`、`NextInt()` 等取值）代替 `UnityEngine.Random`。`UnityEngine.Random` 是全局状态，不能在 Job 里用。每个并行工作项要有各自的种子，常见做法是 `Random.CreateFromIndex((uint)(seed ^ index))`，保证结果与调度顺序无关。
- 值类型的数据：`float`、`int`、`byte`、`Color32`、`Vector3`（作为纯数据结构）等。

### 从主线程传入

`Time.deltaTime`、相机位置、玩家位置、种子等在主线程读出，放进 Job 结构体的字段。

```csharp
[BurstCompile]
struct DriftJob : IJobParallelFor
{
    public NativeArray<float3> Positions;
    public float DeltaTime;        // 主线程传入，Job 内不要再读 Time.deltaTime
    public uint Seed;

    public void Execute(int i)
    {
        var rng = Unity.Mathematics.Random.CreateFromIndex(Seed + (uint)i);
        Positions[i] += rng.NextFloat3Direction() * DeltaTime;
    }
}
// 主线程：new DriftJob { Positions = ..., DeltaTime = Time.deltaTime, Seed = 42 }.Schedule(n, 64);
```

### Debug.Log

Burst 编译的 Job 里可以调用 `Debug.Log`，但参数有严格限制（字符串字面量、`FixedString` 等；不能传托管对象），格式化能力有限。详情见 Burst 章节，此处不展开（具体支持范围待核实）。生产代码里不要在 Job 的热路径上打日志。

## Mesh：MeshData 一族 API

`Mesh.MeshData` 是"供 C# Job System 访问网格数据的结构体"（Scripting API 描述）。分两种：

| 类型 | 获取 | 用途 |
|---|---|---|
| 只读 `MeshData` | `Mesh.AcquireReadOnlyMeshData(mesh)` 返回 `Mesh.MeshDataArray` | 在 Job 里读已有网格 |
| 可写 `MeshData` | `Mesh.AllocateWritableMeshData(n)` 返回 `Mesh.MeshDataArray` | 在 Job 里生成新网格 |

要点（均来自 `MeshData` 与 `ApplyAndDisposeWritableMeshData` 的文档）：

- `MeshDataArray` 和其中的 `MeshData` 可以在任意线程访问；创建 `MeshDataArray` 有内存追踪的固定开销，所以一次请求多个比多次请求一个高效。
- 只读数据用完必须 `Dispose`（或用 `using`）。如果在 `MeshDataArray` 存活期间修改了 Mesh，Unity 会复制一份数据，你的修改也不会反映到已取得的 `MeshData` 上。
- 可写流程：`SetVertexBufferParams` 设顶点数量和布局，`GetVertexData<T>()` 拿到 `NativeArray<T>` 写顶点；`SetIndexBufferParams` 设索引数量与格式，`GetIndexData<T>()` 写索引；`subMeshCount` 属性设子网格数，`SetSubMesh(int index, SubMeshDescriptor desc, MeshUpdateFlags flags = ...)` 设每个子网格的范围（`flags` 参数可省略，用默认值）；最后 `Mesh.ApplyAndDisposeWritableMeshData(dataArray, mesh)`（还有 `Mesh[]`、`List<Mesh>` 重载，以及带 `MeshUpdateFlags` 的版本）把数据交给 `Mesh` 并释放 `MeshDataArray`。
- `ApplyAndDisposeWritableMeshData` 做的数据校验很少：子网格的 `indexStart` / `indexCount` 范围和拓扑必须你自己保证正确，且子网格索引范围不能互相重叠。
- 应用之后 `MeshDataArray` 已被释放，不能再用。
- 包围盒：`SetSubMesh` 默认会自动计算 `SubMeshDescriptor` 的 `bounds`、`firstVertex`、`vertexCount`（传 `MeshUpdateFlags.DontRecalculateBounds` 可关闭）。但这只作用于子网格的包围盒，`Mesh` 自身的包围盒仍要在应用后调用 `mesh.RecalculateBounds()`（官方示例和 `Mesh.SetSubMesh` 文档都是这么做的）。本章示例是"先写完顶点和索引，再调 `SetSubMesh`"；如果要在写入之前就确定子网格范围（两遍法的做法），要带 `MeshUpdateFlags.DontRecalculateBounds` 并手动填 `firstVertex` 等字段，见 3.4 Mesh 构建与 MeshData。

另有直接把 `NativeArray` 写进已有 `Mesh` 的路径：`Mesh.SetVertexBufferData` / `Mesh.SetIndexBufferData`，同样接受 `NativeArray<T>` 重载，通常要配合 `SetVertexBufferParams` / `SetIndexBufferParams` 使用。具体的参数列表（`dataStart`、`meshBufferStart`、`count`、`stream`、`flags`）本章未逐个核对，使用时以 IDE 提示为准（待核实）。

### 最小示例：在 Job 里写一个四边形

顶点格式：位置 `float3` + 法线 `float3`，同一个顶点流（stream 0）里交错存放。Unity 要求同一个流内属性按固定顺序排列（位置在前，法线在后），与结构体字段顺序一致。

```csharp
using System.Runtime.InteropServices;
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;
using Unity.Mathematics;
using UnityEngine;
using UnityEngine.Rendering;

[StructLayout(LayoutKind.Sequential)]
struct QuadVertex
{
    public float3 Position;
    public float3 Normal;
}

[BurstCompile]
struct WriteQuadJob : IJob
{
    public Mesh.MeshData Data;      // 可写 MeshData
    public float Size;

    public void Execute()
    {
        NativeArray<QuadVertex> v = Data.GetVertexData<QuadVertex>();
        var n = new float3(0, 0, -1);
        v[0] = new QuadVertex { Position = new float3(0,    0,    0), Normal = n };
        v[1] = new QuadVertex { Position = new float3(Size, 0,    0), Normal = n };
        v[2] = new QuadVertex { Position = new float3(Size, Size, 0), Normal = n };
        v[3] = new QuadVertex { Position = new float3(0,    Size, 0), Normal = n };

        NativeArray<ushort> idx = Data.GetIndexData<ushort>();
        idx[0] = 0; idx[1] = 2; idx[2] = 1;     // 顺时针为正面（面朝 -Z 的相机）
        idx[3] = 0; idx[4] = 3; idx[5] = 2;

        Data.subMeshCount = 1;
        Data.SetSubMesh(0, new SubMeshDescriptor(0, 6));
    }
}

static Mesh BuildQuad(float size)
{
    // 1. 主线程：分配并声明布局（顶点数、属性、索引数、索引格式）
    Mesh.MeshDataArray array = Mesh.AllocateWritableMeshData(1);
    Mesh.MeshData data = array[0];
    data.SetVertexBufferParams(4,
        new VertexAttributeDescriptor(VertexAttribute.Position, VertexAttributeFormat.Float32, 3),
        new VertexAttributeDescriptor(VertexAttribute.Normal,   VertexAttributeFormat.Float32, 3));
    data.SetIndexBufferParams(6, IndexFormat.UInt16);

    // 2. Job：填充数据（可换成 Schedule 异步，之后再 Complete）
    new WriteQuadJob { Data = data, Size = size }.Schedule().Complete();

    // 3. 主线程：应用并释放 MeshDataArray，然后补包围盒
    var mesh = new Mesh { name = "Quad" };
    Mesh.ApplyAndDisposeWritableMeshData(array, mesh);
    mesh.RecalculateBounds();
    return mesh;
}
```

本示例的顶点布局在官方文档示例中还有"位置与法线分流（stream 1）"的写法；两种都合法，交错布局对 GPU 读取更友好。示例按官方 `MeshData` 页的写法手写：API 名、参数形态、顶点流内属性顺序、缠绕方向（顺时针为正面，法线 -Z 朝向 -Z 处的相机）都已逐行核对，但没有在 7000.0.0a8 里编译运行（待核实）。`SetSubMesh` 在 Job 里会自动算子网格包围盒，`Mesh` 自身的包围盒由最后的 `RecalculateBounds()` 补上。

对照本项目：`VoxelMeshBuilder.CreateMesh` 目前是 `mesh.SetVertices(List<Vector3>)`、`SetNormals`、`SetTriangles(List<int>, 0)`、`RecalculateBounds`、`UploadMeshData(true)`，并且设置了 `indexFormat = IndexFormat.UInt32`。迁移到 `MeshData` 时对应 `SetIndexBufferParams(count, IndexFormat.UInt32)` 和 `GetIndexData<int>()`，省去 List 到原生缓冲的一次拷贝。

## Physics 批处理命令

物理查询本身只能在主线程调用，但 Unity 提供了"命令结构体 + 批量调度"的方式，把成百上千次查询交给作业系统并行执行：

- `RaycastCommand`（已对照 Scripting API 页与官方示例核对）：用 `new RaycastCommand(origin, direction, QueryParameters.Default)` 构造（结构体的属性有 `from`、`direction`、`distance`、`physicsScene`、`queryParameters`），`RaycastCommand.ScheduleBatch(commands, results, minCommandsPerJob, dependsOn)` 返回 `JobHandle`；结果写入 `NativeArray<RaycastHit>`。命令 N 的结果在 `results[N * maxHits]`，`maxHits` 大于实际命中数时，第一个无效结果的 `collider` 为 null，遍历时遇到即可停止。层掩码、是否命中触发器和背面等用 `QueryParameters` 控制（当前版本把这些参数收进了 `QueryParameters`，旧文章里的 `layerMask` 构造参数写法可能已过时）。
- 同族命令：`SpherecastCommand`、`CapsulecastCommand`、`BoxcastCommand`、`OverlapSphereCommand`、`OverlapBoxCommand`、`OverlapCapsuleCommand`、`ClosestPointCommand` 等。本章只核对了 `RaycastCommand` 的页面，其它命令的名称与 `ScheduleBatch` 参数形态以 IDE 提示和对应 Scripting API 页为准（待核实）。

使用模式：主线程填 `commands` 数组，`ScheduleBatch` 得到句柄，可以与其它 Job 串联依赖，`Complete` 后读 `results`。命令和结果数组都要自己 `Dispose`。物理世界在批处理执行期间不应被修改。

```csharp
var commands = new NativeArray<RaycastCommand>(n, Allocator.TempJob);
var results  = new NativeArray<RaycastHit>(n, Allocator.TempJob);
for (int i = 0; i < n; i++)
    commands[i] = new RaycastCommand(origins[i], Vector3.down, QueryParameters.Default);

JobHandle h = RaycastCommand.ScheduleBatch(commands, results, 32, default);
h.Complete();
// 读 results[i].collider != null ...
commands.Dispose(); results.Dispose();
```

体素场景里，如果地形碰撞用 `MeshCollider`，射线对着它的查询用这套命令；纯体素数据上的查询（"这个点是不是实心"）直接读体素数组，不要经过物理系统。

## Transform：TransformAccessArray

场景里有大量对象要每帧改位置（例如飘落物、粒子化的方块），可以用 `TransformAccessArray`（装载一批 `Transform`）配合 `IJobParallelForTransform`。后者的 `Execute(int index, TransformAccess transform)` 里通过 `TransformAccess` 读写位置、旋转、缩放。手册（Parallel jobs 页）将它称为 ParallelForTransform Job，专为 Transform 操作设计。`TransformAccessArray` 本身要在主线程构造和增删。本章未核对 `TransformAccessArray` 的构造参数和 `Schedule` 扩展方法的精确签名（待核实）。

## Texture：GetRawTextureData

`Texture2D.GetRawTextureData<T>()` 返回指向纹理内存的 `NativeArray<T>`，可以直接传进 Job 里写像素，写完后主线程调用 `texture.Apply()` 上传。适用于程序化生成噪声贴图、体素地图小地图等。返回的数组直接引用纹理内存，不要在 Job 运行期间对同一纹理调用会改变其内存的 API。

## GPU 缓冲：ComputeBuffer / GraphicsBuffer

- `GraphicsBuffer.LockBufferForWrite<T>(int bufferStartIndex, int count)` 返回大小为 `count` 的可写 `NativeArray<T>`，写完后调用 `UnlockBufferAfterWrite<T>` 提交（该页面确认了方法名，参数细节待核实），能比先写 CPU 数组再 `SetData` 少拷贝。注意三点（均来自脚本 API 页面）：缓冲必须用 `GraphicsBuffer.UsageFlags.LockBufferForWrite` 创建，否则抛异常；返回的数组内容未定义，只能写不能读；推荐线性写入，因为它可能指向 write-combined 内存。
- `ComputeBuffer.SetData(NativeArray<T>)` / `GraphicsBuffer.SetData(NativeArray<T>)` 接受 `NativeArray` 重载，上传 Job 产出的数据（本章未逐页核对）。

## 回读：AsyncGPUReadback

GPU 数据读回 CPU 用 `AsyncGPUReadback.Request(...)` 或 `AsyncGPUReadback.RequestIntoNativeArray(ref NativeArray<T> output, GraphicsBuffer src, Action<AsyncGPUReadbackRequest> callback)`（`src` 还可以是 `ComputeBuffer` 或 `Texture`，有带 `size` / `offset` 的重载，已按脚本 API 页核对）。请求完成后在回调里取数据交给 Job 处理。它不阻塞主线程，但结果要等若干帧。`RequestIntoNativeArray` 的 `output` 在请求完成前不能 `Dispose`，也不能释放其底层内存。

## 只点名的相关设施

- Animation Jobs / Playables：`IAnimationJob` 让你在动画图里用 Job 处理骨骼。
- `BatchRendererGroup`：自己管理实例数据并提交绘制，常与 Burst Job 配合生成实例缓冲。
- 这两项与本项目的体素生成关系不大，本章只列名称。

## 主线程与 Job 可做什么

| 事情 | 主线程 | Job（含 Burst） | 备注 |
|---|---|---|---|
| 创建、销毁 `GameObject` / `Mesh` / `Texture` | 可以 | 不可以 | Job 里只准备数据 |
| 读写 `Transform` | 可以 | 仅通过 `TransformAccessArray` + `IJobParallelForTransform` | |
| `Mesh` 实例方法（`SetVertices` 等） | 可以 | 不可以 | Job 里用 `MeshData` |
| 读取、生成网格数据 | 可以 | 可以，用 `Mesh.MeshData` | 应用阶段 `ApplyAndDisposeWritableMeshData` 在主线程 |
| `Physics.Raycast` 等查询 | 可以 | 不可以 | 用 `RaycastCommand` 等批处理命令 |
| `Time.deltaTime`、相机、输入 | 可以 | 不可以 | 主线程读出后传入字段 |
| 随机数 | `UnityEngine.Random` | `Unity.Mathematics.Random` | 每工作项独立种子 |
| 数学 | `Mathf`、`Unity.Mathematics` | `Unity.Mathematics`，`Mathf` 纯函数多数可用（待核实） | |
| 纹理像素 | `SetPixels` 等 | `GetRawTextureData<T>()` 返回的 `NativeArray` | 之后主线程 `Apply()` |
| GPU 缓冲上传 | `SetData` | `LockBufferForWrite` 返回的数组 | 缓冲需带 `LockBufferForWrite` 用法标志，只写不读 |
| `Debug.Log` | 可以 | 受限（字面量 / `FixedString`） | 热路径别打 |
| 托管对象、`List<T>`、`class` | 可以 | 不可以 | 改用 `NativeArray`、`NativeList`、结构体 |

## 常见坑

- 在 Job 结构体里放了 `Transform` / `Material` / `string` 字段：编译期或调度期报错，改成传值类型数据。
- 在 Job 里读 `Time.deltaTime`：不可用，必须主线程读出再传。
- 用 `UnityEngine.Random`：全局状态且线程不安全；换成 `Unity.Mathematics.Random`，并保证每个工作项种子不同且非零状态。
- `MeshDataArray` 忘了释放：要么 `ApplyAndDisposeWritableMeshData`，要么手动 `Dispose`。只读的也要 `Dispose`。
- 应用 `MeshData` 前忘了 `Complete()` Job：数据未写完就应用。
- `SetSubMesh` 的 `indexCount` 与实际写入量不符：引擎几乎不校验，结果是渲染错乱或崩溃。
- `RaycastCommand` 结果下标当成 `results[i]`：当 `maxHits > 1` 时第 N 个命令的结果从 `N * maxHits` 开始。

## 小结

- Job 只处理数据，引擎对象的创建、修改、物理查询留给主线程。
- Unity 为网格、物理、Transform、纹理、GPU 缓冲都提供了面向 Job 的数据接口，用它们而不是绕道托管容器。
- 随机数和时间等"全局状态"一律改为显式传入的参数。

## 自测题

1. 为什么不能在 Burst Job 里读 `Time.deltaTime`，应该怎么办？
   答：它依赖引擎主线程状态；在主线程读出，作为字段传入 Job。
2. `Mesh.AllocateWritableMeshData` 到网格出现在场景里，需要哪几步，各在哪个线程？
   答：主线程分配并 `SetVertexBufferParams` / `SetIndexBufferParams`，Job 里写 `GetVertexData` / `GetIndexData` 和 `SetSubMesh`，主线程 `Complete` 后 `ApplyAndDisposeWritableMeshData` 并 `RecalculateBounds`。
3. `RaycastCommand` 与直接调 `Physics.Raycast` 的区别？
   答：前者批量异步并行执行并写入结果数组，需要 `Complete` 后读取；后者同步且只能在主线程。
4. 在 Job 里怎么保证不同工作项的随机数互不相同又可复现？
   答：用 `Random.CreateFromIndex` 或 seed 与 index 混合生成各自的 `Random`，不依赖线程调度。
5. `ApplyAndDisposeWritableMeshData` 调用之后，原来的 `MeshDataArray` 还能用吗？
   答：不能，它已被释放。

## 参考

- https://docs.unity3d.com/ScriptReference/Mesh.MeshData.html
- https://docs.unity3d.com/ScriptReference/Mesh.ApplyAndDisposeWritableMeshData.html
- https://docs.unity3d.com/ScriptReference/RaycastCommand.html
- https://docs.unity3d.com/Manual/job-system-parallel-for-jobs.html
- https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/csharp-system-support.html
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\VoxelMeshBuilder.cs
- D:\UnityHub\Project\程序化生成\Assets\Scripts\WorldGen\Voxels\ChunkMeshData.cs



