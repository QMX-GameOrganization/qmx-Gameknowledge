---
title: "05.1 ECS Job 依赖、Burst 与安全系统"
description: 对照手写 JobHandle，说明 Entities 如何按组件读写自动建立依赖，以及仍需手动管理的边界。
sidebar:
  order: 1
---

## 自动依赖的来源

系统查询和 Job 参数会声明组件读写：

```text
System A：写 Position
System B：读 Position
        ↓
ECS 让 B 等待 A 的 Job
```

这类似本资料 1.3 的 `JobHandle` 链，但依赖依据是组件类型和读写访问。`RefRO`、`RefRW`、Job 参数的 `in/ref` 不是装饰，而是调度信息。

## 自动依赖的边界

ECS 不会自动理解所有外部数据：

- 通过普通 `NativeArray` 传递的自定义依赖。
- 手动覆盖 `Schedule` 依赖参数时的额外句柄。
- 两个不同组件间通过 Entity 引用造成的业务冲突。
- 多个并行 Job 同时写同一个目标 Entity。

这些情况仍要使用 `JobHandle.CombineDependencies`、Proposal/Commit 或串行阶段。

## Burst 的入口

`ISystem` 的生命周期方法可以作为 Burst 入口；`IJobEntity` 也要显式加 `[BurstCompile]`。SystemAPI 的主线程 foreach 适合原型和低频拓扑，密集数据移动再调度 Job。

```csharp
[BurstCompile]
public partial struct MoveItemsJob : IJobEntity
{
    public float DeltaTime;
    private void Execute(ref Item item)
    {
        item.Distance += item.Speed * DeltaTime;
    }
}
```

## Entities 安全检查

安全系统会检查 NativeContainer 生命周期、读写冲突和部分引用失效。结构改变会使旧的 `RefRW<T>`、数组引用和查询结果失效；不能保存它们跨越结构变更。

## 工厂里的并行边界

传送带内部物品移动通常可以按路径并行；多个路径同时写同一个接收器就有冲突。可以先做：

```text
并行生成 TransferProposal
→ 单线程或分区仲裁
→ ECB / Commit 写入接收器
```

不要为了追求 `ScheduleParallel`，让多个线程直接写同一个库存。

## 系统排序、Job 完成与 ECB 回放是三条关系

| 机制 | 回答的问题 | 不负责什么 |
| --- | --- | --- |
| UpdateInGroup / UpdateBefore / UpdateAfter | 哪个系统先执行 OnUpdate、提交工作 | 不保证前一个系统提交的 Job 已经执行完 |
| Dependency / JobHandle | 哪份工作完成后才能访问相关数据 | 不选择生产、运输、消费的业务顺序 |
| ECB Playback | 新实体或组件何时真正提交 | 不让已经执行过的消费者自动再跑一次 |

如果 A 生成位置数据、B 读取位置数据，要先规定 A、B 的业务顺序，再正确连接调度依赖。组件访问声明能帮助 Entities 跟踪冲突，但不会反过来替你决定 A 应排在 B 前面。

典型 SystemBase 调度语句为：

```csharp
Dependency = new MoveJob
{
    DeltaTime = SystemAPI.Time.DeltaTime
}.ScheduleParallel(Dependency);
```

这里接回返回的 JobHandle，使本系统后续使用和其它组件依赖跟踪能看见这份工作。显式取得额外外部数据依赖时，再将它与 Dependency 合并。

主线程 foreach 也要安全访问已有 Job 使用的数据，SystemAPI 会生成所需的访问/同步逻辑；用 EntityManager 随机读写或调用 Complete 可能引入同步点。不要把“有系统更新顺序”当作“工作线程已完成”的证据。

先用 [00.2 完整链路与最小示例](/qmx-Gameknowledge/knowledge/unity-job与burst/05-entities/00-导读/02-从场景到运行时ecs的完整链路/) 的串行示例确认数据链，再将确有性能需求的计算提取成 Job。低频占格索引目前保存托管 Dictionary，使用 SystemBase 主线程处理是明确的选择，不能直接放进 Burst Job。
