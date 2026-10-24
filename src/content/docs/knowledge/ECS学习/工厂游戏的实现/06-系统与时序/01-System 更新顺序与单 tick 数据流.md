---
title: "06.1 System 更新顺序与单 tick 数据流"
description: 用固定时序解释生产、传送和交付如何避免顺序依赖。
sidebar:
  order: 1
---

## shapez.io 的系统职责

核心系统可以按职责归纳：

```text
BeltSystem          建筑变化时维护 BeltPath
ItemEjectorSystem   推进输出槽并向下游交付
BeltPath.update     推进路径中的物品并处理末端
ItemProcessorSystem 推进加工、接收输入、生成待输出物品
ItemAcceptorSystem  主要处理接收后的动画表现
```

拓扑系统和动态模拟系统不是同一频率：拓扑变化时重算连接，正常 tick 不重复查地图。

## 推荐的 Unity ECS 时序

```text
FixedStepSimulationSystemGroup
  ├─ TopologyRebuildSystem       只处理 Dirty
  ├─ ProductionInputSystem       接收/锁定输入
  ├─ ProcessingSystem            推进生产进度
  ├─ OutputInsertSystem          把待输出放入端口槽
  ├─ BeltMovementSystem          移动路径内物品
  ├─ BeltTransferSystem          处理路径末端交付
  └─ StatisticsSystem            统计吞吐和阻塞
```

如果输出先于传送带移动，物品可能本 tick 进入路径；如果你希望一 tick 延迟，可以用两个队列明确规定边界。关键不是哪一种，而是全局固定且可测试。

## 读写边界

同一阶段不要让多个系统同时修改同一库存。可以选择：

```text
系统顺序串行提交
或
Proposal → Commit 的两阶段事务
```

当多个输出竞争一个接收口时，Proposal/Commit 更容易做公平策略；最小单链原型可以先用固定查询顺序，再记录后续升级点。

## 固定时间步

生产时间、传送速度和加工进度都应使用固定模拟步长：

```text
accumulator += frameDelta
while accumulator >= fixedDelta:
    RunSimulationTick(fixedDelta)
    accumulator -= fixedDelta
```

渲染只读取当前状态，不决定物品实际移动多少。
