---
title: "3.6 主线实践：状态边界与 HUD 数据"
description: "把属性、方法、静态规则和序列化配置接成不会被任意脚本破坏的游戏状态。"
sidebar:
  order: 6
---

> 标记：`【主线实践】`。本篇承接 3.1～3.4，重点是状态所有权和调用边界。

> **代码归属**：`【主线代码】`。本篇代码写入 `Assets/Speedrun/Game/`，会被后续章节继续引用；不能只放在 `Labs/`。

## 让状态只能通过合法动作改变

`Health.Hp` 对 HUD 只读，`TakeDamage` 负责校验、扣除、事件和死亡；`GameMath` 只计算无状态规则；Inspector 配置通过 `[SerializeField]` 进入组件，但运行时状态不能直接暴露为公共字段。

```csharp
public sealed class Health : MonoBehaviour
{
    [SerializeField] private int maxHp = 100;
    private int hp;

    public int Hp => hp;
    public bool IsDead => hp <= 0;

    private void Awake() => hp = maxHp;

    public void TakeDamage(int rawDamage, int defense)
    {
        int damage = GameMath.DamageAfterDefense(rawDamage, defense);
        hp = GameMath.ClampInt(hp - damage, 0, maxHp);
    }
}
```

`GameMath` 不保存玩家血量，`Health` 不负责 UI，HUD 只读取公开查询或订阅变化。这样测试伤害规则时不需要创建 Unity 对象，测试血量边界时也不需要依赖 UI。

## 验收

- [ ] 外部脚本不能直接写 `Hp`；
- [ ] 负伤害、超出上限和防御值都得到稳定处理；
- [ ] Inspector 能配置最大血量，但运行时修改走方法；
- [ ] HUD 只读取状态，不拥有状态；
- [ ] 重开时只重置 `Health` 的所有者，不清空整个场景的静态数据。

下一篇：[攻击目标与交互协议](../../../04-继承与多态/05-主线实践攻击目标与交互协议/)。
