---
title: "2. 把角色数据放在一起：类与对象"
description: "从平行数组的问题引入自定义类型，逐项学习 class、struct、成员、对象访问和声明定义。"
sidebar:
  order: 3
---

## 应用：角色增加一个护甲属性

如果名字、生命值和护甲分别放在三个 vector 中，添加、删除、排序时必须同步操作。我们希望“一个角色”成为可以直接放进容器的元素。这一章先把数据组织起来，下一章才收紧访问权限。

## 最小完整程序

![类型、对象、成员与相关语法的关系](/qmx-Gameknowledge/assets/oop/first-types.svg)

```cpp
#include <iostream>
#include <string>
#include <vector>

// 初版公开数据模型：先学习对象语法，后续再保护数值规则。
class Actor {
public:
    std::string name = "Unknown";
    int hp = 100;
    int armor = 8;

    // 成员函数通过当前对象读取对应成员。
    void print() {
        std::cout << name << ": hp=" << hp << ", armor=" << armor << '\n';
    }
};

int main() {
    Actor hero;
    Actor enemy;
    hero.name = "Hero";
    enemy.name = "Enemy";
    hero.hp = 80;
    hero.print();
    enemy.print();

    std::vector<Actor> team;
    team.push_back(hero); // 此处保存一个副本，不是原对象的别名。
    team[0].hp = 70;
    std::cout << hero.hp << ' ' << team[0].hp << '\n';
}
```

输出：

```text
Hero: hp=80, armor=8
Enemy: hp=100, armor=8
80 70
```

## 逐项读懂类定义

`class Actor { ... };` 定义一种类型，结束处的分号不能漏。`Actor hero;` 才创建对象；类名不是某个角色，不能写 `Actor.hp = 80` 来修改“所有角色”。

`name`、`hp`、`armor` 是非静态数据成员，每个对象各有一份。成员的默认初值不是“全体共享的值”。`print()` 是成员函数，通过哪个对象调用，就读取哪个对象的这些成员。

`public:` 表示后面的成员允许外部访问。暂时把数据公开是为了减少新语法，不是最终设计建议。`hero.hp = -100` 目前语法合法，下一章会用访问控制解决入口问题，再用封装解决规则问题。

## 对象、引用与指针怎样访问成员

```cpp
// 接在上述 main 中，都是访问同一个 hero。
Actor& alias = hero;       // 引用：现有对象的别名，不产生新角色。
Actor* pointer = &hero;    // 指针：保存对象地址，可以改指向，也可以为空。
alias.hp = 90;
pointer->hp = 95;
(*pointer).print();        // 等价于 pointer->print()。
```

对象和引用用 `.`；指针用 `->`。解引用空指针再访问成员是未定义行为，不能因为成员函数“看起来没用到数据”就通过空指针调用。引用也可能在原对象销毁后悬空，不是自动延长寿命的工具。

## class 与 struct 到底有什么区别

| 比较项 | class | struct |
| --- | --- | --- |
| 默认成员访问 | private | public |
| 默认继承方式 | private | public |
| 能否写成员函数、构造、析构 | 能 | 能 |
| 能否有 private、虚函数、继承 | 能 | 能 |

在初学阶段，`struct` 常用来表达一组直接公开的数据，`class` 常用来表达需要维护规则的对象。这是习惯，不是功能限制。写 `struct Actor` 再明确使用 `private:`，同样能保护成员。

## 声明与定义先分清

```cpp
class Actor; // 前置声明：告诉编译器存在这个类型，但尚不知道完整成员与大小。
// Actor* p = nullptr; // 可以声明指向未完整类型的指针。
// Actor object;       // 此处不行：尚不能创建需要完整类型的对象。
```

上面是独立语法片段，不要接在同名完整类型之后当成反例运行。写出完整类体才有完整类型定义；成员函数也可以先在类内声明、再在类外定义，第 5 章会拆成头文件和源文件。

## 初学常见坑

- `Actor hero();` 在这种位置可能声明了一个函数，而不是创建对象；入门时优先写 `Actor hero;` 或合适的花括号初始化。
- 未提供初值的普通整数成员可能处于未确定状态；不要读取它。这里显式给出默认值，不能误以为所有对象的所有字段都自动为零。
- `Actor b = a` 通常创建独立对象；内部是否共享资源取决于成员复制语义，第 9 章再深入。别把普通复制误当引用别名。
- 类体里不能随意写一条外部语句 `std::cout << hp;`；执行语句要放进函数等允许的位置。

## 练习与意义

为角色增加 `level`，把两个角色放进 vector，再只修改一个元素。说明类型、对象、成员、容器元素各是什么。此时删一个 vector 元素就能一起删去它的名字、生命值和护甲，这就是本章最直接的收益。

下一章：[public、private、protected 与访问控制](../03-access-control/)。
