---
title: "18. 完整实践：可扩展战斗技能"
description: "编译完整 C++17 战斗例子，跟踪数值与对象寿命，以实际变更验证面向对象的意义。"
sidebar:
  order: 19
---

## 先看运行目标

目标角色有 100 生命值和 8 点固定护甲。按顺序施放原始伤害 20 的斩击、伤害 35 的火球、治疗量 25 的治疗：实际扣血依次为 12 和 27，再恢复 25，最终生命值为 86。

这里火球也受护甲影响，这是为了保持单一、可验证的减伤规则，并不表示所有游戏都应如此。没有施法者、阵营、魔法值、冷却、暴击或异步效果；先把这一小条业务链做清楚。

![完整回合数值轨迹：100 到 88 到 61，再治疗到 86](/qmx-Gameknowledge/assets/oop/battle-flow.svg)

## 下载和编译

[下载完整 battle.cpp](/qmx-Gameknowledge/examples/oop/battle.cpp)。文件包括所有头文件、类型、`main` 和边界断言，无须拼接其他章节。

GCC / Clang：

```bash
g++ -std=c++17 -Wall -Wextra -Wpedantic battle.cpp -o battle
./battle
# 或使用 clang++ 替换 g++。
```

Windows 的 Visual Studio x64 开发者命令提示符：

```bat
cl /nologo /std:c++17 /EHsc /W4 /utf-8 battle.cpp /Fe:battle.exe
battle.exe
```

预期输出如下；示例日志采用英文，便于在不同终端编码下比较：

```text
Slash -> Dummy: damage=12, hp=88
Fireball -> Dummy: damage=27, hp=61
Heal -> Dummy: healing=25, hp=86
checks: passed
```

断言覆盖零伤害、护甲完全挡住攻击、极大伤害、极大治疗、满血治疗、负治疗输入以及整个回合的日志。请勿定义 `NDEBUG` 后误以为仍运行了 `assert` 检查；生产测试通常应使用独立测试框架。

## 完整代码

<!-- OOP_CPP_SOURCE -->

```cpp
// C++17：用角色规则、技能接口与独占所有权演示面向对象协作。
#include <algorithm>
#include <cassert>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

// 维护角色的不变量：最大生命值为正，生命值与护甲始终处于合法范围。
class Actor {
public:
    Actor(std::string name, int maxHp, int armor)
        : name_(std::move(name)), maxHp_(maxHp), hp_(maxHp), armor_(armor) {
        if (maxHp <= 0 || armor < 0) {
            throw std::invalid_argument("invalid actor stats");
        }
    }

    const std::string& name() const noexcept { return name_; }
    int hp() const noexcept { return hp_; }

    // 防御只处理受伤，不修改技能本身；减法前先比较以避免整数溢出。
    int takeDamage(int raw) {
        if (raw < 0) throw std::invalid_argument("negative damage");
        const int damage = raw <= armor_ ? 0 : raw - armor_;
        const int applied = std::min(hp_, damage);
        hp_ -= applied;
        return applied;
    }

    // 本例允许从零生命值治疗；先算可恢复空间，避免 hp_ + amount 溢出。
    int heal(int amount) {
        if (amount < 0) throw std::invalid_argument("negative healing");
        const int applied = std::min(maxHp_ - hp_, amount);
        hp_ += applied;
        return applied;
    }

private:
    std::string name_;
    int maxHp_;
    int hp_;
    int armor_;
};

// 技能只借用目标和输出流，不拥有它们；允许通过接口销毁具体技能。
class Skill {
public:
    virtual ~Skill() = default;
    virtual void cast(Actor& target, std::ostream& out) const = 0;
};

// 数值不同但算法相同的攻击共用一种实现，无需每个伤害值建立子类。
class DamageSkill final : public Skill {
public:
    DamageSkill(std::string name, int power) : name_(std::move(name)), power_(power) {
        if (power < 0) throw std::invalid_argument("negative power");
    }
    void cast(Actor& target, std::ostream& out) const override {
        const int applied = target.takeDamage(power_);
        out << name_ << " -> " << target.name() << ": damage=" << applied
            << ", hp=" << target.hp() << '\n';
    }
private:
    std::string name_;
    int power_;
};

// 治疗拥有独立行为，通过同一契约参与战斗流程。
class HealSkill final : public Skill {
public:
    explicit HealSkill(int power) : power_(power) {
        if (power < 0) throw std::invalid_argument("negative power");
    }
    void cast(Actor& target, std::ostream& out) const override {
        const int applied = target.heal(power_);
        out << "Heal -> " << target.name() << ": healing=" << applied
            << ", hp=" << target.hp() << '\n';
    }
private:
    int power_;
};

// 流程只负责顺序调度；技能由调用方持有，目标在本次调用期间必须存活。
void runRound(const std::vector<std::unique_ptr<Skill>>& skills,
              Actor& target, std::ostream& out) {
    for (const auto& skill : skills) {
        if (!skill) throw std::invalid_argument("null skill");
        skill->cast(target, out);
    }
}

// 同时检查规则边界与统一调度；不依赖执行未定义行为来观察错误。
void verifyRules() {
    Actor edge{"Edge", 100, 8};
    assert(edge.takeDamage(0) == 0);
    assert(edge.takeDamage(8) == 0);
    assert(edge.takeDamage(std::numeric_limits<int>::max()) == 100);
    assert(edge.hp() == 0);
    assert(edge.heal(std::numeric_limits<int>::max()) == 100);
    assert(edge.heal(1) == 0);
    bool rejected = false;
    try { edge.heal(-1); }
    catch (const std::invalid_argument&) { rejected = true; }
    assert(rejected && edge.hp() == 100);

    Actor dummy{"Dummy", 100, 8};
    std::vector<std::unique_ptr<Skill>> skills;
    skills.push_back(std::make_unique<DamageSkill>("Slash", 20));
    skills.push_back(std::make_unique<DamageSkill>("Fireball", 35));
    skills.push_back(std::make_unique<HealSkill>(25));
    std::ostringstream captured;
    runRound(skills, dummy, captured);
    assert(dummy.hp() == 86);
    assert(captured.str() ==
        "Slash -> Dummy: damage=12, hp=88\n"
        "Fireball -> Dummy: damage=27, hp=61\n"
        "Heal -> Dummy: healing=25, hp=86\n");
}

// 组装处知道具体技能；扩展技能时修改这里，而不修改 runRound。
int main() {
    verifyRules();
    Actor dummy{"Dummy", 100, 8};
    std::vector<std::unique_ptr<Skill>> skills;
    skills.push_back(std::make_unique<DamageSkill>("Slash", 20));
    skills.push_back(std::make_unique<DamageSkill>("Fireball", 35));
    skills.push_back(std::make_unique<HealSkill>(25));
    runRound(skills, dummy, std::cout);
    std::cout << "checks: passed\n";
}
```

<!-- END_OOP_CPP_SOURCE -->

## 沿调用链解释每一步

1. `main` 是组装处：创建一个目标和三个技能对象。斩击与火球共享伤害算法，仅配置不同，因此用同一个 `DamageSkill` 类。
2. `vector<unique_ptr<Skill>>` 负责保存并独占技能；容器不负责技能如何施放。不能复制独占指针，所以用 `make_unique` 创建并转移所有权。
3. `runRound` 通过基类接口发起调用，不做 `if (name == "Fireball")`。它只借用目标、技能集合和输出流。
4. `DamageSkill::cast` 请求 `Actor::takeDamage`。角色统一应用护甲和扣血上限，技能拿到实际扣除值后记录日志。
5. `HealSkill::cast` 调用不同操作，但仍符合统一的施放契约。最大生命值不变量继续由角色维护。
6. `main` 离开作用域时，技能容器先析构，独占指针通过虚析构销毁实际技能；目标随后析构。技能没有长期保存目标引用。

本例把规则变化集中在角色、把行为变化放进技能、把调度次序留给流程。理解的是这些边界，而不是记住类名。

## 用新需求证明设计是否有用

**任务 A：加一种重击，伤害 50。** 在组装处再加一个 `DamageSkill("Heavy", 50)`。算法相同，无须创建新子类，也无须修改 `runRound`。在现有三个技能后追加时，角色从 86 扣 42，变成 44。

**任务 B：加一个完全恢复生命值的技能。** 新建 `FullHealSkill`，在 `cast` 中调用 `target.heal(std::numeric_limits<int>::max())` 并写日志，然后在组装处注册。角色既有的溢出防护和上限规则仍然适用；不用开放 `hp_`，不用改战斗循环。

**任务 C：生命值为零时禁止普通治疗。** 修改角色规则并更新对应断言，明确满血和死亡治疗的返回值。它是领域规则变化，应该影响使用该规则的所有技能；不要在每个治疗子类偷偷复制一份检查。

## 当前模型的边界

这是教学模型，没有保证整个回合的原子性：若后面的技能为空，前面已经生效的技能不会回滚；若日志流在状态改变后抛异常，数值也已经改变。真实项目需要明确是“每次施放独立提交”、允许部分成功，还是先验证整批并使用事务协议。

不持有目标引用简化了寿命；异步投射物若要跨帧命中，必须重新设计目标标识和有效性校验。接口增长、存档协议、网络同步和线程安全也都需要真实需求驱动，不能由这一份示例推导出已经解决。

下一章：[分阶段验收与排坑速查](../19-review/)。
