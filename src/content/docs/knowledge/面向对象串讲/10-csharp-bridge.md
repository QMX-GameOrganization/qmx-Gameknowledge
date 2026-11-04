---
title: "10. 迁移到 C#，再连接 Unity"
description: "对照 C++ 理解 C# 的 class、struct、接口、虚调用、GC 与 Dispose，并给出同规则完整例子。"
sidebar:
  order: 11
---

## 先迁移设计，再核对语言语义

角色维护数值不变量、技能提供可替换行为、流程依赖契约，这些设计思考仍然适用。但 C# 看起来相似的语法，未必保留 C++ 的复制和生命周期语义。

![C++ 值复制、C# 类引用赋值、C# 结构体内引用成员的对照](/qmx-Gameknowledge/assets/oop/csharp.svg)

| 关注点 | C++ | C# |
| --- | --- | --- |
| `class` 与 `struct` | 主要语言差别是默认访问权限 | class 是引用类型，struct 是值类型 |
| 普通对象赋值 | 通常调用复制/移动相关操作 | class 变量赋值复制引用，struct 赋值复制字段 |
| 多态入口 | virtual + 基类指针/引用 | virtual/abstract + override，或接口实现 |
| 继承 | 支持多继承 | 类单继承，可实现多个接口；struct 不继承自定义类 |
| 资源寿命 | 析构与 RAII 管理确定性清理 | GC 处理托管内存，using/Dispose 处理资源释放 |
| 销毁语法 | `~T()` 是析构函数 | `~T()` 是终结器，不能当成作用域析构 |

## 最重要的一处差别：赋值是不是独立对象

```csharp
var a = new Actor("Hero", 100, 8);
var b = a;
b.TakeDamage(20);
Console.WriteLine(a.Hp); // 88：两个变量引用同一个角色。
```

与 C++ 的 `Actor b = a;` 形成对照。普通 C# 类赋值不会自动创建完整独立副本，也不能从 `new` 推导出“所有内部资源都属于这个变量”。

结构体复制也不等于深拷贝：`struct Bag { public List<int> Items; }` 的两个副本包含同一个列表引用；修改列表内容会共享，替换其中一个副本的 `Items` 字段则不会替换另一个字段。结构体放在哪里与其复制语义是两件事，不要背成“struct 永远在栈上”。

## virtual、override 与 new

C# 普通类成员默认不是虚成员；基类要显式使用 `virtual` 或 `abstract`，派生类使用 `override`。`new` 成员隐藏不是动态重写，通过基类变量调用时行为可能不同。`sealed` 类禁止继续继承，`sealed override` 禁止继续重写该成员。

接口实现提供同样的行为契约，下面完整例子用 `ISkill`。接口类型引用普通类对象不会因此自动复制对象；结构体转换为接口通常涉及装箱，泛型约束调用又可能避免装箱，需要结合具体代码分析，不能只看关键字。

## GC 解决的不是全部生命周期

GC 追踪托管对象可达性，并安排回收；它不会保证一个作用域结束时立刻回收，也不会替你正确安排文件、锁、原生缓冲或引擎资源的业务释放时机。

```csharp
// 使用完及时关闭文件；using 依据 Dispose 协议清理。
using (var writer = new System.IO.StreamWriter("battle.txt"))
{
    writer.WriteLine("hp=100");
}
```

`Dispose` 不等于强制 GC；普通托管类没有外部资源时也不需要为了模仿 C++ 额外实现 `IDisposable`。C# 基类构造期间调用虚成员可能进入派生实现，此时派生对象尚未完成构造，这与 C++ 的分派规则不同，但同样应避免依赖未完成对象的可重写行为。

## 同规则的完整 C# 例子

[下载 Battle.cs](/qmx-Gameknowledge/examples/oop/Battle.cs)。在安装 .NET SDK 的终端中，新建一次性控制台项目，将下载文件替换 `Program.cs`：

```bash
dotnet new console -o OopBattle
# 将 Battle.cs 的内容替换到 OopBattle/Program.cs，不要同时保留另一份带 Main 的文件。
dotnet run --project OopBattle
```

它与上一章输出相同的三条施放日志和 `checks: passed`。最后额外检查引用赋值：通过别名治疗目标后，原变量观察到生命值变为 100。这里没有使用释放型资源，因此不需要 `Dispose` 或终结器。

<!-- OOP_CS_SOURCE -->

```csharp
// C#：与 C++ 完整例子保持相同规则，展示引用类型和接口调用。
using System;
using System.Collections.Generic;
using System.IO;

// 普通托管角色；访问权限与规则约束仍由类自己维护。
public sealed class Actor
{
    public string Name { get; }
    public int Hp { get; private set; }
    private readonly int maxHp;
    private readonly int armor;

    public Actor(string name, int maxHp, int armor)
    {
        if (maxHp <= 0 || armor < 0)
            throw new ArgumentOutOfRangeException(nameof(maxHp));
        Name = name;
        this.maxHp = maxHp;
        Hp = maxHp;
        this.armor = armor;
    }

    // 与 C++ 使用相同的比较后减法规则。
    public int TakeDamage(int raw)
    {
        if (raw < 0) throw new ArgumentOutOfRangeException(nameof(raw));
        int damage = raw <= armor ? 0 : raw - armor;
        int applied = Math.Min(Hp, damage);
        Hp -= applied;
        return applied;
    }

    // 先计算可恢复空间；不要依赖整数溢出行为维持业务约束。
    public int Heal(int amount)
    {
        if (amount < 0) throw new ArgumentOutOfRangeException(nameof(amount));
        int applied = Math.Min(maxHp - Hp, amount);
        Hp += applied;
        return applied;
    }
}

// 接口约束行为；本例对象不持有需要确定性释放的外部资源。
public interface ISkill
{
    void Cast(Actor target, TextWriter output);
}

// 相同算法通过数值配置复用。
public sealed class DamageSkill : ISkill
{
    private readonly string name;
    private readonly int power;
    public DamageSkill(string name, int power)
    {
        if (power < 0) throw new ArgumentOutOfRangeException(nameof(power));
        this.name = name;
        this.power = power;
    }
    public void Cast(Actor target, TextWriter output)
    {
        int applied = target.TakeDamage(power);
        output.WriteLine($"{name} -> {target.Name}: damage={applied}, hp={target.Hp}");
    }
}

// 新行为独立实现，不要求改变调度函数。
public sealed class HealSkill : ISkill
{
    private readonly int power;
    public HealSkill(int power)
    {
        if (power < 0) throw new ArgumentOutOfRangeException(nameof(power));
        this.power = power;
    }
    public void Cast(Actor target, TextWriter output)
    {
        int applied = target.Heal(power);
        output.WriteLine($"Heal -> {target.Name}: healing={applied}, hp={target.Hp}");
    }
}

// 组装、调度与示例断言；普通对象赋值复制引用，不复制角色。
public static class Program
{
    private static void RunRound(IEnumerable<ISkill> skills, Actor target, TextWriter output)
    {
        foreach (ISkill skill in skills)
        {
            if (skill == null) throw new ArgumentException("null skill");
            skill.Cast(target, output);
        }
    }

    public static void Main()
    {
        var target = new Actor("Dummy", 100, 8);
        var skills = new List<ISkill>
        {
            new DamageSkill("Slash", 20),
            new DamageSkill("Fireball", 35),
            new HealSkill(25)
        };
        RunRound(skills, target, Console.Out);
        if (target.Hp != 86) throw new Exception("unexpected hp");
        var alias = target;
        alias.Heal(int.MaxValue);
        if (target.Hp != 100) throw new Exception("reference copy check failed");
        Console.WriteLine("checks: passed");
    }
}
```

<!-- END_OOP_CS_SOURCE -->

## 接到 Unity 时多加一层引擎生命周期

普通 C# `Actor`、`ISkill` 可以作为与引擎无关的规则层；`MonoBehaviour` 负责接收输入、生命周期消息和展示。不要用 `new SomeMonoBehaviour()` 当普通规则对象构造，组件通常由场景、预制体或 `AddComponent` 创建。

`Destroy` 处理 Unity 原生对象，与托管包装的 GC 不是同一个过程；Unity 重载的相等比较也使“被销毁对象”的判空与普通引用有所区别。订阅事件后如果忘记取消，订阅者可能被发布者长期引用。对象池则会引入“对象还存在，但已经代表另一次使用”的状态复位问题。

本章的 .NET 控制台示例不等于已经验证 Unity 生命周期。继续阅读：[类型、赋值与参数传递](/qmx-Gameknowledge/knowledge/csharp与unity内存基础/02-types-and-copy/)、[所有权、借用与释放](/qmx-Gameknowledge/knowledge/csharp与unity内存基础/06-ownership-and-disposal/)。

**练习：** 把 C++ 与 C# 的角色复制各画成一张图，再解释：修改生命值、替换变量引用、把对象移出列表，这三种动作分别影响什么？

下一章：[排坑速查、自测与讲授安排](../11-review/)。
