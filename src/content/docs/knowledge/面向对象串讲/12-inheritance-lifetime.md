---
title: "12. 派生对象的构造、析构与名字查找"
description: "追踪基类和成员的建立顺序，解释名字隐藏、using、限定调用与多继承中的歧义。"
sidebar:
  order: 13
---

## 应用：精英角色需要给基类传名字

基类没有无参数构造时，派生构造不能假装基类会自行完成初始化。必须明确给基类参数，并理解它与派生成员的先后关系。

```cpp
#include <iostream>
#include <string>

// 用日志展示基类部分何时建立与结束。
class Actor {
public:
    explicit Actor(const std::string& name) {
        std::cout << "Actor+ " << name << '\n';
    }
    ~Actor() { std::cout << "Actor-\n"; }
};

// 成员资源日志，帮助观察成员先于派生构造函数体完成。
class Equipment {
public:
    Equipment() { std::cout << "Equipment+\n"; }
    ~Equipment() { std::cout << "Equipment-\n"; }
};

// 派生初始化列表明确构造基类；析构反向经过派生体、成员与基类。
class Elite : public Actor {
public:
    Elite() : Actor("Elite"), equipment_() { std::cout << "Elite+\n"; }
    ~Elite() { std::cout << "Elite-\n"; }
private:
    Equipment equipment_;
};

int main() {
    Elite elite; // 直接销毁完整派生对象，不经基类指针 delete。
}
```

预期逐行输出：

```text
Actor+ Elite
Equipment+
Elite+
Elite-
Equipment-
Actor-
```

![基类、成员与派生函数体的构造析构顺序](/qmx-Gameknowledge/assets/oop/inheritance.svg)

## 把顺序和原因一起记

先构造直接基类，再按声明顺序构造成员，最后执行派生构造函数体。派生逻辑可能要使用基类与成员，因此它们先准备好。析构先执行派生析构体，再逆序销毁成员，最后销毁基类。

多直接基类时按基类列表顺序，不按初始化列表书写顺序。存在虚基类时，虚基类有更早的构造规则，并由最派生类负责相应初始化。这个例子没有虚继承，不要为了背完整顺序先把所有复杂层次堆进同一程序。

派生类不能在自己的初始化列表直接初始化基类 private 字段；应调用基类构造。`using Base::Base` 可以在合适场景继承构造函数，但不会替你解决派生新增字段的不变量，也不能当成“所有构造都完全一样”。

## 派生类同名函数会隐藏基类名字

```cpp
// 局部片段：没有 virtual，先只观察名字查找与重载。
struct Base {
    void print(int) const {}
};
struct Derived : Base {
    void print(const char*) const {}
};
// Derived d;
// d.print(3); // 错误：找到派生 print 后，不自动把基类同名函数都加入候选。
// d.Base::print(3); // 可以：明确限定基类名字。
```

如果想把两组候选都暴露出来，在 Derived 中增加 `using Base::print;`。这里 using 与 `using namespace` 都与名字有关，但写法和场景不同。重载决议发生在名字查找得到候选之后，因此不能把隐藏简单理解为“参数不合适时总能回到基类”。

基类和派生类也可拥有同名字段，那会造成更复杂的理解成本，并非自动共享同一份数据。一般避免拿同名字段表达“重写状态”。

## 限定名字不等于动态多态

`d.Base::print(3)` 明确选择基类成员。等到下一章加入虚函数，显式限定调用还可以抑制相应虚分派。遇到意外输出时，需要分开分析“名字查找到谁”和“是否进行虚分派”，不能只看对象确实是派生类型。

## 多继承与菱形先认识风险

```cpp
// 局部示意：B 和 C 各拥有一份 A 基类子对象，D 中产生歧义。
struct A { int id = 0; };
struct B : A {};
struct C : A {};
struct D : B, C {};
// D d; d.id = 1; // 错误：不清楚是 B 分支还是 C 分支的 id。
```

限定 `d.B::id` 可以选择一个分支，却不会把两份数据合并。若 B 与 C 虚继承 A，最派生对象可共享相应虚基类部分，但构造责任和对象布局会更复杂。**虚继承用于基类子对象共享，虚函数用于行为分派，不是一件事。**

业务初学阶段优先使用清楚的单继承接口和组合，遇到明确的多基类约束再深入。这里认识语法与风险，不要求把菱形当作默认设计。

**练习：** 增加第二个成员资源，交换初始化列表顺序但保持成员声明顺序，预测并运行日志。另写一个同名函数隐藏例子，用 using 恢复重载集合。

下一章：[虚函数与动态多态](../13-polymorphism/)。
