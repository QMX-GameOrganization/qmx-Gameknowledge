---
title: "6. 角色出生就合法：构造函数与初始化"
description: "从自定义生命值出发，细讲构造函数、初始化列表、explicit、委托构造与默认操作。"
sidebar:
  order: 7
---

## 应用：不同角色有不同的初始生命值

此前给所有角色固定的默认值。现在玩家有 100 生命值，Boss 有 500。若先创建对象再调用 `init`，可能忘记初始化，或在 init 前被其他函数使用。我们希望创建成功时就得到合法角色。

## 最小完整程序

![构造参数、成员初始化和构造函数体的先后关系](/qmx-Gameknowledge/assets/oop/construction.svg)

```cpp
#include <iostream>
#include <stdexcept>
#include <string>

// 在创建时完成名称和生命值校验，避免半初始化状态流向外部。
class Actor {
public:
    Actor() : Actor("Unknown", 100) {} // 委托给另一个构造函数。
    Actor(const std::string& name, int maxHp)
        : name_(name), maxHp_(maxHp), hp_(maxHp) {
        if (maxHp <= 0) throw std::invalid_argument("maxHp must be positive");
    }
    int hp() const { return hp_; }
    const std::string& name() const { return name_; }
private:
    std::string name_;
    const int maxHp_;
    int hp_;
};

int main() {
    Actor hero{"Hero", 100};
    Actor boss("Boss", 500);
    Actor unknown;
    std::cout << hero.name() << ' ' << hero.hp() << '\n';
    std::cout << boss.name() << ' ' << boss.hp() << '\n';
    std::cout << unknown.name() << ' ' << unknown.hp() << '\n';
}
```

输出 `Hero 100`、`Boss 500`、`Unknown 100`，各一行。这里不需要理解继承或虚函数，就能完整使用构造函数。

## 构造函数怎么写

函数名与类名相同，**没有返回类型，连 void 都不写**。可以有多个重载。创建对象时由初始化语法选择构造函数；它不是创建后再随意调用的普通成员函数。`Actor()` 在类内是无参数构造函数，而 `Actor hero();` 在某些声明上下文会成为函数声明，应注意位置。

冒号后是成员初始化列表：`name_(name)` 初始化成员 name_，参数 name 只是这次输入；`hp_(maxHp)` 初始化当前生命值。大括号内是构造函数体，此时基类和成员已完成相应初始化。

## 初始化列表与函数体赋值有何区别

```cpp
// 对比片段，不要同时给同一构造函数放两份定义。
// 推荐：直接初始化。
// Actor(...) : name_(name), maxHp_(maxHp), hp_(maxHp) { ... }

// 另一种写法会先按各自规则初始化，再执行赋值。
// Actor(...) { name_ = name; hp_ = maxHp; }
```

对类类型成员，先默认构造再赋值可能做额外工作；对引用成员和 const 成员，必须在初始化阶段绑定/初始化，不能指望函数体再补赋值。没有默认构造函数的成员也必须获得合适构造参数。不是所有成员都可以“先随便放着，进入函数体再设置”。

成员实际初始化顺序按**类中声明顺序**，不是列表书写顺序。假设先声明 `hp_`、后声明 `maxHp_`，再写 `hp_(maxHp_)`，就可能在 maxHp_ 初始化前读取它。把声明顺序、初始化列表顺序和依赖顺序保持一致。

## 默认构造、默认初值、default 与 delete

类完全没声明构造函数时，编译器可在符合条件时生成默认构造函数。一旦声明了一个带参数构造函数，就不能想当然地继续写 `Actor a;`；你可能需要显式提供无参数构造。

`Actor() = default;` 请求生成默认实现，但成员必须允许相应构造，否则它仍可能被定义为删除。`Actor() = delete;` 明确禁止无参数创建，适合必须提供某项依赖的类型。成员默认初值会用于未被该构造函数显式初始化的成员，初始化列表中的显式选择优先。

委托构造 `Actor() : Actor("Unknown", 100) {}` 复用另一构造的初始化逻辑，避免多个构造各维护一份校验。委托构造的列表不能同时再初始化其他成员，且不能形成委托循环。

## explicit：不要让一个数字悄悄变成角色

```cpp
// 局部示例：只演示转换入口；参数合法性应按业务补充。
class Health {
public:
    explicit Health(int value) : value_(value) {}
private:
    int value_;
};
// Health a{100};      // 可以：直接初始化。
// Health b = 100;     // 错误：explicit 阻止这种隐式转换。
```

容易误解的地方是 `Health b = 100` 并不是普通“给已有对象赋值”，它在声明一个新对象。explicit 主要控制相关隐式转换和复制初始化，不等于禁止所有使用等号的表达式，也不会自动禁止对象复制。

## 花括号和圆括号不是永远等价

花括号常能拒绝窄化转换，但如果类型同时提供 `initializer_list` 构造，列表初始化可能优先选择它。熟悉的例子：`vector<int> a(3, 7)` 是三个 7，`vector<int> b{3, 7}` 是两个元素 3 和 7。不要机械地把所有括号替换成花括号。

## 失败与边界

构造校验失败时抛异常，外部得不到正常完成构造的对象。已完整构造的成员会按规则清理，而完整对象的析构不会执行；下一章追踪这个顺序。构造函数不应把尚未完成的 this 发布给回调或外部全局表。

**练习：** 给角色增加必须在创建时指定的阵营枚举。决定是否允许无参数创建，分别用 default、delete 或委托表达决定；测试 0、负数和正常最大生命值。

下一章：[析构、生命周期与 RAII](../07-lifetime/)。
