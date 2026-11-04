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
