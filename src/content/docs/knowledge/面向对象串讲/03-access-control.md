---
title: "3. 谁可以改生命值：public、private、protected"
description: "从 UI 误改生命值切入，细讲访问级别、访问位置、同类对象权限与 protected 的边界。"
sidebar:
  order: 4
---

## 应用：UI 只负责展示，不该任意设置生命值

上一章 `hero.hp = -100` 能编译，说明对象只是把数据装在一起，还没有建立修改边界。现在把生命值改为 private，给外部一个查询操作和一个受控修改操作。

![调用方表达意图，角色内部维护状态](/qmx-Gameknowledge/assets/oop/boundary.svg)

```cpp
#include <algorithm>
#include <iostream>

// 限制生命值写入位置；本章约定负伤害视为零，下一章讨论另一种失败策略。
class Actor {
public:
    int hp() const { return hp_; }
    void takeDamage(int amount) {
        const int applied = std::min(hp_, std::max(0, amount));
        hp_ -= applied;
    }
private:
    int hp_ = 100;
};

int main() {
    Actor hero;
    hero.takeDamage(30);
    std::cout << hero.hp() << '\n'; // 70
    // hero.hp_ = -100; // 错误：外部代码不能直接访问私有成员。
}
```

`hp() const` 是只读查询，暂时理解为“不通过这个函数修改当前对象”，第 5 章细讲。函数内部可以使用 `hp_`，因为它是 Actor 的成员函数。变量名末尾 `_` 只是本专题的风格。

## 三种访问级别逐个解释

| 访问者所处的位置 | public | protected | private |
| --- | --- | --- | --- |
| 当前类的成员/友元 | 可以 | 可以 | 可以 |
| 派生类的成员 | 可以 | 可以，但有访问对象限制 | 不能直接访问 |
| 普通外部调用方 | 可以 | 不可以 | 不可以 |

`public` 是外部可依赖的接口；`private` 把实现交给当前类维护；`protected` 为派生类提供受保护的访问。友元会在第 10 章单独说明；继承和 protected 的对象限制在第 11 章配代码展开。现在不需要先会继承，只要不把 protected 误记成“所有相关代码都能访问”。

访问标签持续到下一个标签或类体结束，可写多段 public/private，并不会创建新对象或新作用域。class 默认 private，struct 默认 public，所以忘写 public 后构造或函数可能都无法从外部访问。

## private 是按类授权，不是按单个对象隔离

```cpp
// 局部示例：同一个类的成员可以访问另一个同类对象的私有成员。
class Health {
public:
    bool sameAs(const Health& other) const {
        return value_ == other.value_; // 合法。
    }
private:
    int value_ = 100;
};
```

成员函数属于 Health，因此也可检查 `other.value_`。不是只有 `this->value_` 才能访问。相反，外部函数即使拿到了 `Health&`，也不会因此获得 private 权限。

## 权限不是根据调用者变量名判断

在类外定义的 `Actor::hp()` 仍然是成员函数，仍有权限；一个恰好也叫 `hp` 的普通函数没有权限。把外部函数放进相同命名空间、相同文件或相同文件夹，不会自动变成类的内部成员。

局部变量可以和成员同名，这影响名字查找，但不是访问权限改变。第 5 章用 this 说明如何区分。

## public、private 与继承访问不要混成一件事

`private: int hp_;` 是成员访问标签。`class Enemy : public Actor` 中 public 是继承方式，它会影响从外部看基类接口的可达性。二者相关，但位置和作用不同；不要以为“public 继承”会把基类 private 字段变成 public。

## 访问控制与封装的区别

设为 private 只限制直接访问。如果紧接着提供 `void setHp(int n) { hp_ = n; }`，任何非法数值仍能进入对象。访问控制给出了工具，封装还需要接口维护规则。

同样，返回 `int& hp()` 会把可写引用交给外部，外部又能绕过检查。private 不会自动保护通过接口泄露出去的别名，也不是抵御恶意内存读写的安全机制。

**练习：** 把上一章角色的 hp 和 armor 改为私有，保留只读查询。逐条判断“main 中直接访问”“类外定义的成员函数访问”“另一个同类对象的成员函数访问”是否合法，再用编译器检查有意保留的一条错误。

下一章：[封装、不变量与接口设计](../04-encapsulation/)。
