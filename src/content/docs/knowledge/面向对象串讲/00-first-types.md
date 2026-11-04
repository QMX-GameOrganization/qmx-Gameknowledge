---
title: "0. 语法起步：命名空间、枚举和第一个类"
description: "不假设学过 class、namespace 或 enum，从名字、类型、对象和作用域开始搭桥。"
sidebar:
  order: 1
---

## 这一章不要求你已经学过“类”

你能使用 `std::vector<int>`，不代表你已经学过 `namespace`；你能实现链表，也不代表你已经知道 `class` 的成员访问规则。先把这几个词逐个拆开，后面遇到构造、继承和虚函数时才不会同时卡在多层陌生语法上。

本章只解决“这些写法是什么意思”，不急着背设计原则。每段标注为完整程序的代码都可以单独复制运行。编译使用 C++17；编译器选项见第 9 章。

## 1. 类型与变量：先从熟悉的 int 出发

`int hp = 100;` 中，`int` 是类型，`hp` 是变量名，100 是初始值。类型规定了允许保存什么样的数据，以及能对它执行什么操作。

如果一个角色需要名字、生命值和护甲，分别保存三组数组很容易把索引搞错。我们希望定义一种属于自己程序的类型，让一个变量就能表示“这三个数据属于同一个角色”。

![从内置类型、命名空间到枚举和自定义类的语法地图](/qmx-Gameknowledge/assets/oop/first-types.svg)

## 2. namespace：给名字分一个命名区域

想象战斗代码和音频代码都想把一个函数叫 `play`。名字相同，含义不同，需要让编译器区分。

```cpp
// 完整程序：同名函数可以位于不同命名空间。
#include <iostream>

namespace Battle {
    // 战斗模块的演示入口。
    void play() { std::cout << "battle\n"; }
}

namespace Audio {
    // 音频模块的演示入口。
    void play() { std::cout << "audio\n"; }
}

int main() {
    Battle::play();
    Audio::play();
    std::cout << "done\n";
}
```

输出依次是 `battle`、`audio`、`done`，各一行。`namespace Battle { ... }` 声明一个命名空间；`::` 是作用域解析运算符，`Battle::play` 指定要用哪一个名字。**命名空间不是角色对象，不需要也不能像角色一样创建一个实例。** 同一命名空间可以在多处继续声明，它也不等同于文件夹。

你用过的 `std::vector`、`std::string`、`std::cout`，就是标准库命名空间 `std` 下的名字。`#include <vector>` 引入声明，`std::` 指定名字所属范围，这两件事不同。

`using std::cout;` 可以在当前范围引入这一个名字；`using namespace std;` 则放宽整个命名空间的名字查找。小练习里后者很常见，但公共头文件中尤其容易影响别人的代码。本专题保留 `std::`，让名字来源清晰。不要自己向 `std` 随意添加声明。

## 3. struct：把相关数据放进一种类型

```cpp
// 完整程序：定义自有类型，再创建两个独立对象。
#include <iostream>

struct ActorData {
    int hp = 100;
    int armor = 8;
}; // 注意：类型定义结束后有分号。

int main() {
    ActorData hero;
    ActorData enemy;
    hero.hp = 80;
    std::cout << hero.hp << ' ' << enemy.hp << '\n';
}
```

输出 `80 100`。`ActorData` 是新定义的类型；`hero` 和 `enemy` 是该类型的两个对象。对象是这个类型的一次具体实例。`hp`、`armor` 称为成员变量；`.` 用于通过对象访问成员。`int hp = 100` 是成员默认初值，每个对象都有自己的这份普通成员。

不要把类型定义误读成“已经创建了一个角色”。就像 `int` 本身不是某一个整数，`ActorData` 本身也不是某一个角色。把对象放进 `vector<ActorData>` 时，vector 仍然负责存储，类型负责描述每个元素。

## 4. class：先把它当成可以带操作的自定义类型

```cpp
// 完整程序：一个最小的类，还没有构造函数或继承。
#include <iostream>

// 仅用于初识成员访问；完整生命值约束将在第 2 章加入。
class Counter {
public:
    // 这是成员函数，通过某个对象调用。
    void addOne() { value_ += 1; }
    int value() { return value_; }

private:
    int value_ = 0;
};

int main() {
    Counter a;
    Counter b;
    a.addOne();
    a.addOne();
    std::cout << a.value() << ' ' << b.value() << '\n';
    // a.value_ = 99; // 如果取消注释，编译失败：外部不能访问私有成员。
}
```

输出 `2 0`。`public:` 后的成员可被外部使用，`private:` 后的成员只允许类自身成员及获授权的友元等访问；这里先只记住外部 `main` 不能直接读写它。访问标签持续到下一个访问标签或类定义结束。

`addOne()` 和 `value()` 是成员函数，与普通函数一样可以有参数和返回值，但通过具体对象调用，因此知道自己要操作哪一份成员数据。`a.addOne()` 改的是 a，不会改 b。`value_` 末尾的下划线只是本专题的命名习惯，不是语言要求。

`struct` 也能写成员函数和 private，`class` 也能写公开字段。两者最先需要记住的差别是默认访问：struct 默认 public，class 默认 private。不要先记成“struct 只能放数据，class 才能写函数”。

## 5. enum：给有限几种选项起类型安全的名字

如果技能类型用整数 0、1、2 表示，读到 `if (kind == 2)` 时就要去查 2 是什么。枚举给这些有限选项明确名字。

```cpp
// 完整程序：本专题优先使用作用域枚举 enum class。
#include <iostream>

enum class SkillKind {
    Slash,
    Fireball,
    Heal
};

int main() {
    SkillKind kind = SkillKind::Heal;
    switch (kind) {
    case SkillKind::Slash:    std::cout << "slash\n"; break;
    case SkillKind::Fireball: std::cout << "fireball\n"; break;
    case SkillKind::Heal:     std::cout << "heal\n"; break;
    }
}
```

输出 `heal`。`SkillKind` 是类型，`SkillKind::Heal` 是一个有名字的枚举值，`kind` 是保存该值的变量。这里的 `enum class` 是**作用域枚举的组合语法**，不是在枚举里又创建普通类，也没有继承关系。

传统 `enum` 会把枚举项名字带入外围作用域，且存在到整数的隐式转换；`enum class` 把名字放在枚举作用域里，不会随意隐式变成整数。它仍有底层整数表示，但不应把随便读到的整数强转后就当有效业务值。解析文件或网络输入时要验证是否属于允许集合。

枚举只表达“是哪一种”，不会自动实现这类技能的行为。下一章先展示分支代码为什么会变多，之后才讨论何时需要多态。不要为了使用面向对象而消灭合理的小枚举。

## 6. 后续陌生语法按需学习

| 会遇到的写法 | 现在只需知道 | 正式解释位置 |
| --- | --- | --- |
| `Actor(int hp)` | 创建对象时执行的构造函数 | 第 2 章 |
| `: hp_(hp)` | 构造函数的成员初始化列表 | 第 2 章 |
| `const Actor&` | 通过只读引用借用现有对象，不复制对象 | 第 2、4 章 |
| `throw`、`try`、`catch` | 报告失败并在另一个位置处理 | 第 2、3 章 |
| `~Actor()` | 对象生命周期结束时执行的析构函数 | 第 3 章 |
| `unique_ptr`、`std::move` | 独占所有权及其转移 | 第 4 章 |
| `: public Skill` | 公共继承 | 第 5 章 |
| `virtual`、`override` | 可替换行为与编译器检查 | 第 6 章 |

遇到看不懂的符号，先定位这一层语法，而不是怀疑整段业务规则都不懂。后面的章节会在首次重要使用时解释它。

## 课前验收

自己写一个 `Score` 类，初值 0，提供公开的 `addOne()` 和 `value()`，把分数设为私有。创建两个对象，只修改其中一个，预测输出后运行。再把它放进 `namespace Game`，使用 `Game::Score` 创建对象。最后定义 `enum class RoundState { Ready, Running, Finished };`，保存一个当前回合状态。

能说清“命名空间、类型、对象、成员、枚举值”各指什么，就可以进入主线；不需要在这一章就懂虚函数或设计模式。

下一章：[从过程代码到对象边界](../01-why-oop/)。
