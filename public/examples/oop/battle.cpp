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
