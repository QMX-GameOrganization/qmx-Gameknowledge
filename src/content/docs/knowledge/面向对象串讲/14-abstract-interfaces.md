---
title: "14. 技能必须有行为：抽象类、接口与虚析构"
description: "从禁止创建无意义技能出发，细讲纯虚函数、抽象类型、虚析构、多态所有权与契约。"
sidebar:
  order: 15
---

## 应用：不能创建一个不知道怎样施放的技能

上一章学习 virtual 怎样选择派生实现。现在进一步要求：Skill 只表达共同契约，本身没有可用效果；每个可创建的具体技能必须实现施放行为。

```cpp
#include <iostream>
#include <memory>
#include <vector>

// 纯行为接口：不能直接实例化，可通过基类入口销毁实际技能。
class Skill {
public:
    virtual ~Skill() = default;
    virtual void cast() const = 0;
};

// 完成接口契约后，具体类型才能直接创建。
class Slash final : public Skill {
public:
    void cast() const override { std::cout << "Slash\n"; }
};

// 同一调用形式，不同实现。
class Heal final : public Skill {
public:
    void cast() const override { std::cout << "Heal\n"; }
};

int main() {
    // Skill skill; // 错误：抽象类不能直接实例化。
    std::vector<std::unique_ptr<Skill>> skills;
    skills.push_back(std::make_unique<Slash>());
    skills.push_back(std::make_unique<Heal>());
    for (const auto& skill : skills) skill->cast();
}
```

输出 Slash、Heal，各一行。离开 main 时，vector 销毁智能指针，通过 Skill 的虚析构销毁实际的 Slash 和 Heal 对象。此处只讲调用与所有权，完整战斗例子再加入角色和效果。

## = 0 不是“函数返回零”

`virtual void cast() const = 0;` 声明纯虚函数。类型仍有未实现的纯虚契约时为抽象类型；派生类若不完成对应最终重写，也仍然不能创建完整实例。

抽象类可以有数据、普通函数、构造和析构。它的构造函数负责派生对象中的基类部分，只是不允许直接创建完整抽象基类对象。C++ 没有独立 interface 关键字，常用纯虚抽象类表达接口。接口的重点是协作契约，不是某个命名后缀。

## override 为什么应当写

如果基类声明 `cast() const`，派生写 `cast()`，它们不是同一个重写签名。加 override 会让编译器立即诊断；不加时，你可能只是在隐藏同名函数，派生类依然抽象。参数和成员 const 等规则需要逐项核对，不能只看函数名。

`final` 可用于整个类或某个虚函数，阻止继续扩展相应层次。它表达设计边界，不应无理由地到处添加，也不保证一定更快。

## 虚析构解决的是哪一种删除

当默认删除器持有 `Skill*`，而实际对象是派生类时，需要正确的基类删除契约。对这里的普通删除形式，基类应提供可访问的虚析构。若缺少它，就可能是未定义行为，不能只当成“派生资源可能少释放一点”。

**虚函数并不会自动让析构变虚。** 即使 cast 已经是 virtual，析构仍然需要明确设计。相反，不通过基类销毁的普通非多态值类型通常不需要虚析构。

一种替代设计是 protected 非虚析构，禁止普通外部通过基类删除；但这不适合本例 `unique_ptr<Skill>` 默认删除器。纯虚析构也必须提供定义，因为派生销毁路径仍要经过基类析构；入门接口直接用 `virtual ~Skill() = default` 更清楚。

## 为什么不能用 vector<Skill>

首先 Skill 是抽象类，不能作为可创建元素按值保存；即使换成可实例化基类，按值保存派生对象仍会切片，丢失派生部分。`vector<unique_ptr<Skill>>` 保存独占所有权，不复制完整技能，保留动态类型。

只在当前函数中使用时可接收 `Skill&` 或 `const Skill&` 借用；需要保存所有权时才考虑相应拥有类型。智能指针可能为空，所以容器非空不等于所有元素都可解引用；完整例子会检查空技能。

## 契约不只是一行函数签名

接口还需要说明目标寿命、是否允许空值、失败怎么报告、调用能否有副作用、资源由谁拥有。如果基础契约允许任意合法角色，某派生技能却要求目标必须是某特定子类，否则崩溃，就破坏了可替换性。

如果存在冷却或资源不足，可设计统一失败结果；若不同技能都需要自己的失败分支，调用方应怎样处理？这些业务语义比“能编译为 override”更进一步，但应随着应用需要逐步引入。

**练习：** 新增 Shield 技能，不修改 for 循环；再故意漏掉 const，观察 override 诊断。解释谁拥有技能、为何析构 virtual，以及把参数改为 shared_ptr 是否真的必要。

下一章：[重载、重写、隐藏与其他陷阱](../15-pitfalls/)。
