---
title: "9.2 迁移到 Unity ECS 项目"
description: 把前几章的设计逐项映射为 Unity Entities 的组件、缓冲区与系统草案，并指出哪些要改写、哪些可以直接用。
sidebar:
  order: 2
---

> 适用版本：思路与具体包版本无关。下面的 C# 是**未编译的草案**，API 名称按 Entities 1.x 的常见写法给出，使用前需对照你工程里的实际版本核实（待核实）。映射思路沿用 ECS 学习专栏“08 Unity ECS 映射”和“06 系统与时序”的约定：Burst 里不调用托管对象方法，竞争写入用“提案缓冲 → 仲裁 → 提交”。

## 要点

- 原素材的教学内核是面向对象写的（类、字典、`List`），不能原样放进 Burst Job。迁移时保留**算法与规则**，把**数据结构**换成组件、`DynamicBuffer` 和 Blob。
- 字符串 ID 要换成整数 ID（原作本来就是整数 ID 加名称表）。
- 凡是“先检查后提交”的地方，都对应 ECS 里一个明确的系统阶段边界。

## 映射总表

| 素材里的设计 | ECS 里的形态 | 要改什么 |
| --- | --- | --- |
| 属性四槽（5.1） | 每个实体一个 `DynamicBuffer<AttrSlot>`（基值、加值、倍率增量、当前值），属性用整数 ID 作下标 | 字典 → 数组/缓冲区；字符串 → int |
| Buff 列表与到期（5.2） | `DynamicBuffer<ActiveBuff>`（buff ID、栈数、剩余时间） | 稳定压缩可在 Burst Job 里原样写 |
| 事件时钟（3.1） | `AnimEventCursor { NextEvent, PreviousFrame }` + 事件表放 `BlobAsset`；输出到 `DynamicBuffer<FiredEvent>` | 每帧先清空输出缓冲，再填写 |
| 音频调度（3.2） | 同上，播放由主线程系统消费 `FiredEvent` | 音频 API 非 Burst，放在托管系统 |
| 运动请求（4.1） | `MotionRequest` 组件，由输入/AI 系统写，运动系统读 | 一次性跳跃请求需明确“谁清除” |
| 局部轴限速与驱动力（4.2） | `MotionSolveSystem`（Burst），读 `MotionRequest` 与 `Velocity`，写 `Velocity` | 纯数学，可直接移植 |
| 随机核（5.3） | `RandomState48 { ulong State }` 组件 | 每实体一份，天然可存档 |
| 伤害链（5.3） | 命中系统写 `DamageProposal` 缓冲；`DamageCommitSystem` 去重并写生命 | 去重集合 → 按 `(发射ID, 目标)` 排序后去重 |
| 制作事务（7.3） | `CraftRequest` 缓冲 + 一个校验提交系统 | “候选副本”用临时 `NativeArray` |
| 技能 DAG（5.5） | 技能表放 `BlobAsset`，已学集合是 `DynamicBuffer<LearnedSkill>` | 成环检测放烘焙（baking）阶段 |
| AI 规则表（6.1） | 有序 `BlobArray<GoalRule { GoalId, RuleId }>`，实体持有模块掩码 | 谓词用静态函数 + `switch(RuleId)` |
| 感知快照（6.3） | `Observation` 在一个 Job 中批量构造，决策 Job 只读 | 物理视线用 `RaycastCommand`/物理查询批处理 |
| 任务图（7.1） | 节点表放 Blob，运行状态放 `DynamicBuffer<NodeState>` | 树递归 → 显式栈或扁平数组 |

## 例一：属性刷新（草案）

```csharp
public struct AttrSlot : IBufferElementData
{
    public float Base, Add, MulDelta, Value;
}

public struct ModifierRef : IBufferElementData
{
    public int AttrId;        // 整数 ID，对应属性名表
    public float ValueAdd;
    public float ValueMul;
    public short Stack;
    public bool Timed;
}

[BurstCompile]
partial struct AttributeRefreshJob : IJobEntity
{
    void Execute(ref DynamicBuffer<AttrSlot> slots, in DynamicBuffer<ModifierRef> mods)
    {
        // 1. 清零
        for (int i = 0; i < slots.Length; i++) { var s = slots[i]; s.Add = 0; s.MulDelta = 0; s.Value = s.Base; slots[i] = s; }
        // 2. 先应用无期限条目，再应用限时条目
        for (int pass = 0; pass < 2; pass++)
            for (int i = 0; i < mods.Length; i++)
            {
                var m = mods[i];
                if ((m.Timed ? 1 : 0) != pass) continue;
                var s = slots[m.AttrId];
                s.Add += m.Stack * m.ValueAdd;
                s.MulDelta += m.Stack * m.ValueMul;
                s.Value = (s.MulDelta + 1f) * s.Base + s.Add;       // 3. 重算当前值
                slots[m.AttrId] = s;
            }
    }
}
```

这与 5.1 的 `Refresh` 顺序一致。注意：原函数每次 `Apply` 里先加值刷新一次、再加倍率刷新一次，最终值相同，这里合并为一次刷新。如果你需要与原函数的中间状态完全一致，可以拆成两步。

## 例二：事件游标（草案）

```csharp
public struct AnimEventCursor : IComponentData { public int NextEvent; public float PreviousFrame; }
public struct FiredEvent : IBufferElementData { public int EventId; public float Frame; }

// 系统内：
buffer.Clear();
float frame = seconds * clip.FramesPerSecond;
while (cursor.NextEvent < events.Length && events[cursor.NextEvent].Frame <= frame)
{
    var e = events[cursor.NextEvent];
    buffer.Add(new FiredEvent { EventId = e.Id, Frame = e.Frame });
    cursor.NextEvent++;
}
cursor.PreviousFrame = frame;   // 同 3.1：时间不得倒退，倒退时应报错或重建游标
```

事件表预先按“帧、源行号”排序后烘焙进 Blob，运行时系统里只剩游标推进。下游的伤害系统消费 `FiredEvent`，并按 5.3 的做法用 `(发射ID, 目标)` 去重。

## 系统顺序建议

沿用工厂游戏专栏的固定时序思想：

```text
InputSystem            写 MotionRequest、一次性请求
PerceptionSystem       构造 Observation 快照
AIDecisionSystem       按规则表选目标
AnimEventSystem        推进游标，输出 FiredEvent
MotionSolveSystem      解算速度、驱动力
DamageProposalSystem   命中产生提案
DamageCommitSystem     去重、写生命、产生死亡边沿事件
AttributeRefreshSystem 清零重算
BuffExpirySystem       稳定压缩到期项
```

顺序的原则和 3.1、5.3 一致：**事件先产生、再消费**；**同一阶段不要让两个系统写同一份数据**。到期与重算放在伤害之后还是之前，是一个需要你显式决定并测试的选择。

## 哪些可以直接搬

- 公式：局部轴限速、驱动力、属性四槽、LCG、有符号半径、`started guard` 真值表。
- 算法：三色 DFS、读写双指针压缩、区间事件派发。
- 测试向量：教材里的算例（80 / 0.1 / 160 / 120，220 / 145 / 265 / 170，种子 12345 的前八个随机数）可以直接做单元测试。

## 哪些不要照搬

- `Dictionary<string, …>`、`List<…>.ToArray()`、LINQ（`OrderBy`、`GroupBy`）：这些是教学写法，在 Burst/热路径里要换成数组和排序好的 Blob。
- 抛异常的失败策略：Burst 里用错误码、事件或 `Assert`。
- 单线程假设：并行 Job 里的去重、累加需要用 `ParallelWriter` 或分块归约，见 Job 与 Burst 专栏的并行写入一章。

## 常见坑

- 把属性名字符串直接带进 `IComponentData`（托管类型无法 Burst）。
- 在 `ForEach` 里边遍历边向同一缓冲区增删元素。
- 忘记在帧初清空 `FiredEvent`，导致事件重复消费。
- 以为“教学内核能跑”就等于“原作行为”，不检查各章末尾的边界声明。

## 一条最小实践路线

1. 先做属性内核（例一）和单元测试（用 5.1 的 4 个算例）；
2. 再做事件游标和 `FiredEvent`，接一个“动画事件 → 日志”；
3. 接运动请求和速度解算；
4. 最后接伤害提案与去重。

每一步都先写“恰好违反规则的测试”，参考 8.2。

## 参考资料

- 本专栏第 3、4、5、7 章与 9.1
- ECS 学习专栏：工厂游戏的实现（06 系统与时序、08 Unity ECS 映射）
- Unity Job 与 Burst 专栏：并行写入与归约模式
