---
title: "5.2 Buff 定义与到期的稳定压缩"
description: 如何只解析确实读懂的部分、把没读懂的原样保留；以及到期清理为什么用读写双指针做稳定压缩，而不是逐项删除。
sidebar:
  order: 2
---

> 适用版本：Dying Light 1.55.0.0。依据 `DL1/Teach/Logic/Attributes/属性消费与重算教学.md` 第 4、5 节与 `DL1/DL1Source/Data0/data/skills/buffs.xml`。原 `OnGain`、`OnLose`、`OnMaxStack` 的动作执行器没有接入。

## 要点

- Buff 在 XML 里除了数值贡献，还带时间线、获得时动作、叠层上限、叠层行为等。教学解析器**只解析读懂的部分**，其余原样保存成“未应用内容”，让调用方能看到“还有东西没处理”。
- 到期清理用读写双指针一趟完成，保持剩余条目的原有顺序，避免逐项 `Remove` 造成的二次复杂度。
- 数值贡献与 buff 生命周期分开：属性内核（5.1）不知道什么叫到期。

## Buff 的声明形态

```xml
<buff id="Painkillers" duration="25">
    <property name="MaxHealth" value_add="120"/>
    <!--property name="HealthRegeneration" value_add="5"/-->
    <varlist_timeline var="f_game_player_injection_1">
        <key t="0" val="0"/>
        <key t="0.5" val="0.7"/>
        ...
    </varlist_timeline>
</buff>
```

教材确认：Painkillers 的数值贡献只有 `duration = 25` 和 `MaxHealth value_add = 120`；`varlist_timeline`（注射画面时间线）不属于属性内核。Strength 有两个数值属性 `MeeleDamageMul value_add = 1` 和 `MeeleForceMul value_add = 1`。被注释掉的 `HealthRegeneration` 不会被当成有效 property，教材有测试覆盖这一点。

## 只解析读懂的，保留没读懂的

`BuffDefinition.Parse` 接收已取出的单个 `<buff>` 元素：

| 范围 | 处理 |
| --- | --- |
| `id`、`duration`、`property` 的数值或布尔贡献 | 解析 |
| 其余属性 | 放进不可变的 `UnappliedAttributeDict` |
| 其余子元素 | 按原顺序序列化进 `UnappliedChildList` |
| 混合 `set` 与数值字段 | 不在教学子集内，明确报错 |
| `change` 字段 | 不接受（`skills.xml` 的 `change="x..."` 消费桥未证实） |
| 数字解析 | 使用 invariant culture，不受系统地区设置影响 |

`HasUnappliedContent` 为 true 时，调用方一眼能看出“这个定义不完整”。具体保留的东西包括：Painkillers 的 `varlist_timeline`、MedKitNormal 的 `OnGain`、MultikillTimer 的 `max_stacks`、`apply_behaviour` 和 `OnMaxStack`。本节不播放 timeline、不加医疗生命、不追加经验、不派发这些动作。

边界声明很细：保留的是 XML 树的名称、属性值、后代和顺序，不承诺源文件字节、实体写法、引号或空白的原始往返。

**这是处理“半懂的数据”的好模板**：不要为了让测试全绿而丢弃未知字段，也不要假装已经实现；让数据带着“未应用”标记走完整个流水线。

## 到期：稳定压缩

`BuffExpiry` 每次推进：所有限时条目的剩余时间减去宿主时间步，收集剩余 ≤ 0 的条目名，再整体重算。关键是怎样把到期条目从列表里去掉：

```csharp
// 示意：读写双指针，稳定压缩
int Write = 0;
for (int Read = 0; Read < TimedList.Count; Read++)
{
    var Entry = TimedList[Read];
    Entry.Remaining -= DeltaSeconds;
    if (Entry.Remaining <= 0) { ExpiredList.Add(Entry.Name); continue; }   // 到期：只记名字
    TimedList[Write++] = Entry;                                            // 存活：按原顺序写回
}
TimedList.RemoveRange(Write, TimedList.Count - Write);                      // 一次清尾部
```

特点：

- **稳定**：存活条目的相对顺序不变，到期名称的顺序也不变。这对属性重算（顺序影响布尔覆盖）和日志排查都有用。
- **线性**：每条记录只读一次、最多写一次，总共 O(n)。
- **一次性清尾**：`RemoveRange` 只发生一次。

原函数是逐项 `memmove`，复杂度二次。教材说明这是**教学实现的性能改善**，保证到期名称和剩余贡献顺序与原版相同，但没有执行原 `OnLose` 动作，因此不声称覆盖原事件重入时序。原过期路径还有一个“特殊状态暂停”分支，也没有实现。

## 两种调用方式

```csharp
string[] Advance(float DeltaSeconds);                          // 低频：内部分配临时列表，返回数组
void Advance(float DeltaSeconds, List<string> ExpiredList);    // 高频：调用方复用列表，方法先 Clear 再写入
```

后者的合同：方法会先 `Clear`，再写入本帧到期名称；若要跨帧保留，需要宿主另存快照。容量足以容纳本帧到期数时，`Add` 不需要扩容；教材没有设置来历不明的“最大到期数”。同样的理由，条目遍历用索引而不是 `IReadOnlyList` 枚举器（避免接口枚举器的装箱分配），字典的 `Values` 采用结构体枚举。

## 时间步约束

时间步须为宿主有效的非负秒数。负时间的恢复策略没有证据，所以没有加入。

## 值得学的点

- **未知字段不丢，也不假装执行**，并给出“有未应用内容”的标志。
- **稳定压缩**：任何“遍历中删除”的列表都可以用读写指针替代 `RemoveAt`。
- **低频 API 与高频 API 并存**：易用的版本分配，热路径的版本零分配，二者行为一致。
- **数字解析用固定文化**，避免在使用逗号作小数点的系统上读错。

## 与 C# 底层专栏的对应

“索引遍历避免枚举器装箱”和“输出列表由调用方复用”都属于隐藏分配问题，参考 C# 底层专栏的“隐藏分配”一章。

## 常见坑

- 在遍历的同时 `RemoveAt`，会跳过下一个元素或造成二次复杂度。
- 在属性内核里记录“还剩几秒”。生命周期归 buff 条目，属性内核只管数值。
- 解析器遇到不认识的字段静默忽略，导致数据错误很久才暴露。

## 参考资料

- `DL1/Teach/Logic/Attributes/BuffDefinition.cs`、`AttributeBank.cs`
- `DL1/DL1Source/Data0/data/skills/buffs.xml`
- `DL1/Unpack/_logic_research/Attributes/verification.json`
