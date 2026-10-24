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
