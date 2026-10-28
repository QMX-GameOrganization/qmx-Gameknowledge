---
title: "1.1 Data0 脚本体系"
description: 从 Data0 里的 .scr、.def、.phx、.xml 看这个引擎怎样把玩法写成数据：物品、动画事件、物理、AI 参数、技能与任务。
sidebar:
  order: 1
---

> 适用版本：Dying Light 1.55.0.0。示例摘自 `DL1/DL1Source/Data0/data/`，行号为所读文件当前拷贝的行号。

## 要点

- 游戏玩法的大部分“可调内容”不在 C++ 里，而在 Data0 的文本声明里。物品、动画事件、物理参数、AI 参数、技能、任务都是这样。
- 这些文本分成两种风格：带 `Item(...) { ... }` 块的脚本式声明（`.scr`、`.phx`），和带属性的 XML（技能、buff、任务）。
- 枚举和 ID 由 `.def` 文件定义，并明文要求与 C++ 枚举保持同步。这是数据层与代码层的契约。

## 声明形态一览

| 文件类型 | 位置示例 | 声明内容 | 形态 |
| --- | --- | --- | --- |
| `.scr` 物品 | `scripts/inventory/inventory.scr` | 物品属性、堆叠上限、配方 | `Item("id", Category) { Price(20); MaxStackCount(999999); ... }` |
| `.scr` 动画 | `characters/animations/animscripts/*.scr` | 动画片段与事件 | `SeqTrack(名, anm2, 起帧, 止帧, fps, ...) { Event(帧, 事件, 参数) }` |
| `.scr` AI 参数 | `ai/zombie/zombie_data*.scr` | 视距、听觉、伤害倍率 | `ParamFloat("sight_range", 10.0) //[m]` |
| `.phx` 物理 | `odephysics/walkfly/walk_player.phx` | 物理体与行走参数 | `PhysicsWalkParams() { StairHeight(0.51) }` |
| `.def` 枚举 | `ai/ai_main_goal_rules.def` | 规则 ID、模块类型 | `$ShouldDie (i, 3)` |
| `.xml` | `skills/*.xml`、`quests/**/*.xml` | 技能、buff、任务阶段 | 属性化 XML 节点 |

## 三个典型例子

### 物品与配方

医疗包蓝图把配方直接写成声明：

```text
Item("Craftplan_MedKit_Large_Healing", CategoryType_Collectable)
{
    ItemType(ItemType_CraftPlan);
    RequiredItem("Craft_Alcohol", 1);
    RequiredItem("Craft_Gauze", 1);
    CraftedItem("Medkit_HealthPackLarge", 1, 2);
}
```

注意 `CraftedItem` 后面两个整数。教材没有证实它们与产量的对应关系，于是把它们原样保留，让调用方通过显式的“产量策略”选择。声明里读得到的东西，不一定知道意思。

### 动画片段与事件

```text
SeqTrack("FPP_Unarmed_FinishWins_FinisherBackFast",
         "M_FPP_Unarmed_FinisherBack_Fast.anm2", 5, 45, 30, 1, 0.0)
{
    Event(0,  0, 1) { PlaySound23D(..., "player_grab_finish_back_fast_begin.wav", ...) }
    Event(15, 0, 1) { PlaySound23D(..., "..._hit.wav", ...) }
    Event(20, GIVE_GRAB_DAMAGE, 1)
    Event(21, 0, 1) { PlaySound23D(..., "..._end.wav", ...) }
    Event(36, GRAB_RELEASE, 1)
    Event(36, CAN_WALK, 1)
}
```

一个片段由“引用哪个 `.anm2`、取第几帧到第几帧、按多少 fps 播放”加“局部帧上的事件”组成。事件把动画、声音、伤害、输入窗口连起来，细节见 3.1。

### 物理参数的继承覆盖

玩家物理脚本先 `!include` 通用 Walk/Fly 配置，再覆盖几项。通用配置默认值与玩家覆盖值对比：

| 参数 | 通用默认 | 玩家覆盖 |
| --- | --- | --- |
| `WalkAcceleration` / `WalkDeceleration` | 40 / 20 | -1 / -1 |
| `StairHeight` | 0.35 | 0.51 |
| `MaxGroundDEGToWalk` / `Jump` | 40 / 35 | 50 / 45 |
| `AirControlFactor` | 0.0 | 1.0 |
| `MaxClimbSpeed` | 2 | 4 |

玩家的 -1 并不表示“没有加速度”，而是触发 4.2 要讲的分支：任一加减速参数不大于零时，物理层直接采用目标速度。声明值的语义要结合消费者代码才能读对。

## 编译产物与源格式

两处线索说明这些文本不是运行时直接解析的最终形态：

- `zombie_data.scr` 旁边有同名 `.dat`，例如 `zombie_data.dat`、`zombie_data_custom_preset_anim_set_a.dat`。
- 任务 XML 里每个节点都带 `pxsl_line="18"` 这样的属性。教材明确说这是“源生成信息”，不是当前 XML 文件的行号，因此验证工具改用 XML 解析器的真实行号。

`.dat` 文件是二进制，开头能直接看到动画名字符串（如 `mz_upset_stand_attack_lefthand_v01`），可以判断它是 `.scr` 的预编译形态；具体格式本专栏没有逆向，待核实。`pxsl_line` 则暗示任务 XML 由另一种更简洁的源格式（名字里的 PXSL）生成。这是工具链设计的参考：作者写紧凑 DSL，引擎吃展开后的产物。

## 值得学的点

- 参数文件用 `!include` 做继承，子预设只写与父级不同的行。`zombie_data_custom_preset_biter_policeman.scr` 开头 `!include(anim_set_c)`，随后只写 `damage_mul`、`health_mul` 等几行覆盖。这种“基础表加差量覆盖”的数据组织比复制整表更容易维护。
- 参数注释直接带单位，例如 `ParamFloat("sight_range", 10.0) //[m]`。单位写在数据里，减少调用方出错。
- 事件名用符号（`GIVE_GRAB_DAMAGE`、`CAN_WALK`）而不是数字，数字 ID 另在 `animscripts/events.def` 中定义：`CLIMBING_LENGTH` 是 539，`ENABLE_DUCK` 是 561，`CAN_WALK` 是 610，`GIVE_GRAB_DAMAGE` 是 611，`GRAB_RELEASE` 是 613。这与教材里原生函数 `FUN_180c2aaa0` 通过事件 ID `0x21b`/`0x231` 查询 `CLIMBING_LENGTH`/`ENABLE_DUCK` 对得上（0x21b = 539，0x231 = 561），说明脚本符号名到二进制 ID 的映射可以靠 `.def` 打通。

## 常见坑

- 看到 `natural_movement.scr` 就以为它是“可攀爬表面白名单”。教材专门指出它只是编辑器资源集合，没有证明运行时只靠它判断攀爬。
- 把同名物品的多条声明合并成一条。`Melee_ShortKnifeCGen` 有三条声明，Condition 分别为 40、32、12，教材保留三条，没有猜变体选择规则。

## 参考资料

- `DL1/DL1Source/Data0/data/scripts/inventory/collectables.scr`、`inventory.scr`
- `DL1/DL1Source/Data0/data/characters/animations/animscripts/m_fpp_grab.scr`
- `DL1/DL1Source/Data0/data/odephysics/walkfly/walk_player.phx`、`odephysics/generic/odephysicswalkfly.phx`
- `DL1/DL1Source/Data0/data/quests/slums/slums_sq_voltage_quest.xml`
