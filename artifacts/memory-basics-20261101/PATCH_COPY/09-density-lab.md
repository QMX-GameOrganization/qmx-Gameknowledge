---
title: "9. 密度采样实践与排错"
description: "用一个完整的双 Job 示例练习分配、依赖、读取与释放，并给出观测、自测和进阶路线。"
sidebar:
  order: 9
---

## 练习目标

用同一个简单密度公式先写托管版本，再写 Job 版本。比较结果是否一致，再观察分配和执行时间。公式刻意简单，教学重点是生命周期，不代表真实地形质量。

## 可以放进脚本的完整示例

将下列内容保存为 `DensityMemoryLesson.cs`。项目需要已启用 Job、Collections 和 Burst 支持。在组件菜单执行“运行内存练习”，预期打印 `solid=127`。此处是待自行运行的练习预期，本专题没有实际 Unity 运行记录。

```csharp
using Unity.Burst;
using Unity.Collections;
using Unity.Jobs;
using UnityEngine;

/// <summary>演示采样、消费与原生工作区的同步释放，不承担世界生成调度。</summary>
public sealed class DensityMemoryLesson : MonoBehaviour
{
    [BurstCompile]
    private struct SampleJob : IJobParallelFor
    {
        public NativeArray<float> Density;

        /// <summary>每次迭代只写当前索引，避免迭代之间争用输出。</summary>
        public void Execute(int index)
        {
            Density[index] = index - 128f;
        }
    }

    [BurstCompile]
    private struct CountJob : IJob
    {
        [ReadOnly] public NativeArray<float> Density;
        public NativeArray<int> SolidCount;

        /// <summary>在完整采样结果上计数；零密度按本练习约定不计入实体。</summary>
        public void Execute()
        {
            int count = 0;
            for (int i = 0; i < Density.Length; i++)
            {
                if (Density[i] > 0f)
                    count++;
            }
            SolidCount[0] = count;
        }
    }

    /// <summary>在同次同步调用内完成全部 Job，finally 负责回收已创建资源。</summary>
    [ContextMenu("运行内存练习")]
    private void RunLesson()
    {
        NativeArray<float> density = default;
        NativeArray<int> count = default;
        JobHandle lastUse = default;

        try
        {
            density = new NativeArray<float>(256, Allocator.TempJob);
            count = new NativeArray<int>(1, Allocator.TempJob);

            // 每次成功调度后立即保存句柄；后续调度失败仍能等待已启动的工作。
            lastUse = new SampleJob { Density = density }.Schedule(256, 32);
            lastUse = new CountJob
            {
                Density = density,
                SolidCount = count
            }.Schedule(lastUse);

            lastUse.Complete();
            Debug.Log($"solid={count[0]}");
        }
        finally
        {
            // 正常与调度异常路径都先等待，再释放；这些句柄仅由本函数持有。
            lastUse.Complete();
            if (count.IsCreated)
                count.Dispose();
            if (density.IsCreated)
                density.Dispose();
        }
    }
}
```

这个例子在同次调用中同步等待，因此采用 TempJob。真实跨帧流水线不能直接照搬：需要操作对象保存句柄、拥有资源、处理取消，并选择合适分配器。Job 执行本身发生致命错误的恢复也不能仅靠教学示例保证。

日志会有托管分配，不能用这段带日志的演示宣称“零 GC”。两个 Job 很小，调度开销可能超过并行收益，也不能据此宣称性能提升。

## 生命周期图

```text
主线程分配 density、count
          ↓
SampleJob 写 density
          ↓ 依赖
CountJob 读 density、写 count
          ↓ Complete
主线程读取 count[0]
          ↓
Dispose count、density
```

## 逐步实验与验收

| 实验 | 操作 | 应验证的现象 |
| --- | --- | --- |
| 托管基线 | float[256] 按相同公式填充并计数 | 实体数量为 127 |
| Job 对照 | 运行上面的组件 | 同输入实体数量仍为 127 |
| 句柄共享 | 独立小例中复制 NativeArray 并通过副本写一个元素 | 原句柄读取到相同写入；只释放一次 |
| 调度依赖 | 在安全检查开启的独立实验中移除消费者依赖 | 通常在调度或访问时报告冲突；具体报错随版本变化 |
| 异常清理 | 在成功调度采样后、调度计数前主动抛出托管异常 | finally 等待采样后释放资源 |
| 性能观察 | 去掉日志，增大输入，预热并重复测量 | 分开记录 GC.Alloc、Job 耗时、等待与总耗时 |

错误实验只在隔离的教学场景和开启安全检查的环境中进行；关闭检查时没有报错不代表代码正确。

## 排错顺序

1. 写资源表：每项分配的所有者、全部读者/写者和最后使用句柄。
2. 查别名：是否复制过 NativeArray，保存过 AsArray 或 Slice。
3. 查时序：结果读取、释放、扩容是否发生在使用者结束之前。
4. 查期限：TempJob 是否跨越四帧，取消后是否仍保留未释放资源。
5. 查发布：任务失败时是否错误地把部分结果交给展示层。
6. 最后测性能，区分分配成本、数据复制、计算与同步等待。

## 自测与下一步

**问：为何 count 是 NativeArray<int>，不直接把 int 放进 Job？** 答：Job 结构体按值复制，普通 int 字段不会自动回写调用方；容器提供共享输出。

**问：为什么最后要等 CountJob 才能释放 density？** 答：它是 density 的消费者，采样结束只说明写入完成。

完成后进入 [Job/Burst 学习路线](/qmx-Gameknowledge/knowledge/unity-job与burst/00-导读/01-学习路线与版本说明/)。指针、Marshal、SafeHandle、池化、自定义分配器和原子操作按项目需要学习，不必作为理解 NativeArray 的前置门槛。

## 官方资料

- [C# 类型系统](https://learn.microsoft.com/zh-cn/dotnet/csharp/fundamentals/types/)
- [C# 非托管类型](https://learn.microsoft.com/zh-cn/dotnet/csharp/language-reference/builtin-types/unmanaged-types)
- [GC 基础](https://learn.microsoft.com/zh-cn/dotnet/standard/garbage-collection/fundamentals)（涉及具体回收器时区分 .NET 与 Unity）
- [Unity Job System 的 NativeContainer](https://docs.unity3d.com/6000.0/Documentation/Manual/JobSystemNativeContainer.html)
- [Collections 2.5 分配器概览](https://docs.unity3d.com/Packages/com.unity.collections@2.5/manual/allocator-overview.html)
- [Burst 1.8 手册](https://docs.unity3d.com/Packages/com.unity.burst@1.8/manual/index.html)
