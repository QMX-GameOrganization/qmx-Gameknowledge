---
title: "04.1 ItemAcceptor、ItemEjector 与交付协议"
description: 解读输入槽、输出槽、过滤器和 tryAccept 交付协议。
sidebar:
  order: 1
---

## Acceptor 只描述入口条件

`ItemAcceptorComponent` 的职责很窄：

- 定义入口位置和方向。
- 定义可选的物品过滤器。
- 根据槽位和方向找到匹配入口。
- 记录接收后的表现动画。

它本身不决定机器是否完成配方。加工库存由 `ItemProcessor` 或 `Storage` 等组件处理。

## Ejector 持有所有权中的物品

`ItemEjectorComponent` 的每个槽有：

```text
item       还没有交给下游的物品
progress   从器件输出点向外移动的进度
cached...  下游路径或接收槽缓存
```

输出槽里的物品在交付成功前仍属于输出器件。`ItemEjectorSystem` 每 tick 推进进度；进度到达末端后尝试交付。

## 交付协议是局部的布尔事务

源码中关键语义可以概括为：

```text
TryPassOverItem(item, target):
    target 是 BeltPath → target.tryAcceptItem(item)
    target 是 Processor → target.tryTakeItem(item, slot)
    target 是 Storage → target.canAcceptItem(item) 后 takeItem
    失败 → false
```

调用方只有在 `true` 时才清空自己的槽位。这个协议的优点是所有权清晰：一次成功交付只发生一次删除。

## 对 Unity ECS 的迁移

不要在 Burst System 中调用虚方法。可以把交付拆成两阶段：

```text
TransferProposal：源 Entity、目标 Entity、物品类型、数量、端口
TransferCommit：统一确认后写入双方状态
```

但最小原型也可以采用按固定顺序处理的局部提交：先读目标容量，成功后同时扣减源和增加目标。等出现多个输出竞争同一目标，再引入 Proposal/Reservation。

## 过滤器的位置

过滤器属于端口或槽位，而不是传送带。传送带只负责运输；路径末端的目标负责判断：

```text
类型匹配？
槽位可用？
机器当前允许输入？
```

这样分流器、仓库和处理器可以复用相同的交付协议。
