---
title: "3.1 SeqTrack 与事件时钟"
description: 动画事件如何把动画、声音、伤害、输入窗口连起来，以及一个“不会漏事件、不会重复触发”的时钟该怎么写。
sidebar:
  order: 1
---

> 适用版本：Dying Light 1.55.0.0。依据 `DL1/Teach/Logic/教学.md` 第 1、2 节与 `EventClock.cs`。原引擎对事件参数 `RawParameter` 的派发语义未查证，本章只讲教学时钟。

## 要点

- 动画脚本里每个 `SeqTrack` 附带一串 `Event(帧, 事件, 参数)`。事件到了对应帧就发出：播声音、造成伤害、开关输入窗口、允许移动。
- 帧率是每个 `SeqTrack` 自己的，不能全局写死 30。示例表里有 24、28、30、31、33、35、40、60。
- 游戏帧率抖动时，一次更新可能跨过多个事件。派发条件必须是区间 `(上一时间, 当前时间]`，而不是“当前帧 == 事件帧”。
- 事件列表在脚本里的书写顺序不是严格按帧递增，需要排序。

![事件时钟](/qmx-Gameknowledge/assets/dl1/dl1-event-clock.svg)

## 原脚本的事实

背后快速处决的片段是源帧 5 到 45、30 FPS。事件在该片段的局部帧上：

| 局部帧 | 事件 |
| --- | --- |
| 0 | 播放 `player_grab_finish_back_fast_begin` |
| 15 | 播放 `..._hit` |
| 20 | `GIVE_GRAB_DAMAGE` |
| 21 | 播放 `..._end` |
| 36 | `GRAB_RELEASE`、`CAN_WALK` |

攀爬片段允许**半帧事件**：`Event(18.5, ENABLE_DUCK, -1)`、`Event(19, CLIMBING_LENGTH, -1)`，帧率 40 FPS。抓取输入窗口则用 `GRAB_INPUT_START/STOP` 在局部帧 0 到 11 开合。

## 教学内核：EventClock

```csharp
public sealed class EventClock
{
    private readonly AnimationTrack Track;
    private readonly AnimationEvent[] EventList;
    private int NextEvent;
    private double PreviousFrame = -1;
    private bool Canceled;

    public EventClock(AnimationTrack Track)
    {
        this.Track = Track;
        EventList = Track.EventList.OrderBy(i => i.Frame).ThenBy(i => i.Line).ToArray();
    }

    public AnimationEvent[] Advance(double LocalSeconds)
    {
        double Frame = LocalSeconds * Track.FramesPerSecond;
        if (!double.IsFinite(Frame) || Frame < 0 || Frame < PreviousFrame)
            throw new ArgumentOutOfRangeException(nameof(LocalSeconds), "时钟必须有限 非负 单调递增");
        PreviousFrame = Frame;
        if (Canceled) return [];
        var Fired = new List<AnimationEvent>();
        while (NextEvent < EventList.Length && EventList[NextEvent].Frame <= Frame)
            Fired.Add(EventList[NextEvent++]);
        return Fired.ToArray();
    }
    // SampleSourceFrame / Cancel 略
}
```

逐处设计意图：

| 位置 | 目的 |
| --- | --- |
| 每个实例自己的游标 `NextEvent` | 两个角色不共用静态状态，处决双方各持一个时钟 |
| 构造时按帧排序，同帧按源行号 | 事件顺序确定，不依赖脚本书写顺序 |
| `LocalSeconds × FramesPerSecond` | 用该 SeqTrack 自己的帧率换算 |
| 拒绝倒退和 NaN | 重播应创建新实例，不能偷偷重置已造成伤害的游标 |
| `while` 而不是 `if` | 低帧率下一次更新要消费所有已跨越的事件 |
| 游标只前进 | 同一时刻重复调用不会再次扣血 |
| 返回事件，不在时钟内调用声音/伤害 | 时钟是纯逻辑，副作用交业务层 |
| `SampleSourceFrame` 才加 `StartFrame` | 事件在局部帧，采样源动画才需要加起始帧 |

## 容易漏掉的边界

- 零帧事件在第一次 `Advance` 才被消费，初始 `PreviousFrame = -1` 保证了这一点。
- 取消是实例级的：`Cancel` 只终止这个动作实例，原始数据不变。取消后输入窗口应一并关闭，否则动作被打断后会残留交互权限。
- 半帧事件靠 `double` 比较：18.49 帧不触发蹲伏，18.5 帧触发，19 帧触发攀爬长度。
- `RawParameter`（`1` 或 `-1`）被完整保留，但教学内核不把它当开关值，因为原引擎的语义没有查证。

## 与伤害的衔接：事件交付不是事务

战斗课程特意指出一个边界：`EventClock.Advance` 先推进游标，接收器随后失败不会恢复游标。教学宿主应在异常时立即终止动作并取消对应伤害，保留首个错误，不能用再次 `Advance` 同一时刻重试已交付的事件。这个例子说明“消息已交付”与“业务已完成”是两件事。

## 值得学的点

- **区间派发是通用规则**。动画事件、粒子触发、脚本时间线、音频事件都能套用。
- **让时钟只返回“发生了什么”**，不直接执行。这样可以对时钟做纯单元测试，也便于与 ECS 的“事件缓冲 + 系统消费”对接。
- **把帧率放进数据**，不要在代码里假设 30 FPS。

## 常见坑

- 用 `==` 比较帧号。低帧率或暂停恢复时会漏事件。
- 用浮点秒直接比较事件时间而不换算成帧，半帧事件会丢。
- 把事件重复派发当成“幂等无害”。伤害事件一旦重复就是双倍扣血。

## 自测

1. 把整个处决一次推进到 2 秒，与分六次推进比较，事件序列应相同（见教材自测）。
2. 把 `while` 改成 `if`，跨帧测试应当失败。预测失败原因再运行。
3. 重复推进同一时刻，不应再次触发声音或伤害。

## 参考资料

- `DL1/Teach/Logic/EventClock.cs`、`Evidence.cs`
- `DL1/Teach/Logic/教学.md`（第 1、2 节）
- `DL1/DL1Source/Data0/data/characters/animations/animscripts/m_fpp_grab.scr`、`m_fpp_nm_climb.scr`
