---
title: "11. 特定角色增加能力：继承语法与访问规则"
description: "从精英角色扩展普通角色出发，细讲 public/protected/private 继承、访问权限和基类转换。"
sidebar:
  order: 12
---

## 应用：精英角色增加怒气，仍然能使用基础角色操作

先学习继承本身的语法，不立刻与虚函数混在一起。下例精英角色拥有基础生命值规则，并增加怒气；“继承”和“动态多态”不是同一个概念。

```cpp
#include <algorithm>
#include <iostream>

// 基类维护生命值；派生类通过受控操作使用，不开放字段写入。
class Actor {
public:
    int hp() const { return hp_; }
    void takeDamage(int amount) {
        hp_ -= std::min(hp_, std::max(0, amount));
    }
protected:
    bool wounded() const { return hp_ < 100; }
private:
    int hp_ = 100;
};

// 公共继承让外部可以把精英角色当作基础角色借用。
class Elite : public Actor {
public:
    void charge() {
        if (wounded()) rage_ = 10;
    }
    int rage() const { return rage_; }
private:
    int rage_ = 0;
};

int main() {
    Elite elite;
    elite.takeDamage(30); // 继承而来的公开操作。
    elite.charge();
    Actor& baseView = elite;
    std::cout << baseView.hp() << ' ' << elite.rage() << '\n'; // 70 10
    // elite.wounded(); // 错误：外部不能调用 protected 成员。
    // elite.hp_ = 1;  // 错误：private 字段不对外部或派生类直接开放。
}
```

本例没有通过基类指针删除派生对象，因此暂未需要虚析构；第 14 章会明确讨论这种删除方式的要求。不能把这段特定使用条件推广成“基类析构永远不必 virtual”。

## 冒号后的 public 是继承方式

`class Elite : public Actor` 中 Elite 是派生类，Actor 是直接基类。Elite 对象中包含 Actor 基类子对象，也拥有自己的 rage_。并不是简单地把基类源代码文本复制过来。

`class Elite : Actor` 默认 private 继承；`struct Elite : Actor` 默认 public 继承。为了让含义明确，业务代码中通常显式写出继承方式。

## 三种继承方式如何影响基类接口

下表只讨论派生类对原基类 public/protected 成员的访问表现，不会把基类 private 成员变成可直接访问。

| 原本的基类成员 | public 继承后 | protected 继承后 | private 继承后 |
| --- | --- | --- | --- |
| public | 保持 public | 作为 protected | 作为 private |
| protected | 保持 protected | 保持 protected | 作为 private |
| private | 派生类不能直接访问 | 派生类不能直接访问 | 派生类不能直接访问 |

基类 private 字段仍属于基类子对象，并未从派生对象中消失；它由基类操作维护。派生类可调用允许访问的基类函数，间接使用规则。把 private 改成 protected 只为“省一个函数”，会让派生类依赖内部表示，基类以后更难改变。

## 公共继承支持常见的向上转换

`Actor& baseView = elite` 不复制对象，引用的是原对象中的基类部分。`Actor* p = &elite` 类似；它们只暴露基类接口，不能通过 baseView 直接调用 Elite 独有的 rage()。

而 `Actor sliced = elite` 会创建新的基类对象，不再保留精英角色的完整派生状态，这叫切片。若改成 private/protected 继承，普通外部代码不能照搬这种隐式向上转换。转换也需要基类关系无歧义，多继承时更要注意。

## protected 还有访问对象的限制

```cpp
// 局部语法示例；同一组 Base/Derived 放到单独练习文件。
class Base {
protected:
    int value_ = 0;
};

class Derived : public Base {
public:
    void inspect(Derived& peer, Base& plain) {
        value_ = 1;       // 可以：当前派生对象。
        peer.value_ = 2;  // 可以：通过派生类型对象访问。
        // plain.value_ = 3; // 错误：不能借此任意访问一个 Base 对象的受保护字段。
        (void)plain;
    }
};
```

“派生类能访问 protected”是简化说法，不能推导出“它可以修改任意 Base& 的 protected 字段”。权限还与访问表达式涉及的对象类型有关。实际设计优先通过基类受控操作表达需求，减少依赖这些细节。

## 继承不是为了少写几行字段

Elite 能否真的当作 Actor 使用，除了语法，还要满足行为契约。若派生类偷偷规定“普通受伤调用不能用”，那公共可替换关系就值得怀疑。后面会用技能例子继续验证；当前阶段先把语法和访问规则写正确。

**练习：** 将 Elite 的继承方式分别改为 public、protected、private，判断 main 中的 `takeDamage` 和向上引用哪一行失败。每次只改一个地方，让编译诊断与访问表对应。

下一章：[派生构造、析构顺序与名字查找](../12-inheritance-lifetime/)。
