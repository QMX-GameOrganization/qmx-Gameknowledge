---
title: "5. 查询与修改：成员函数、this、const 和重载"
description: "用只读查看角色、同名参数和链式调用，掌握成员函数语法与声明定义分离。"
sidebar:
  order: 6
---

## 应用：角色既要能修改，也要能只读查看

查询角色信息时不应该意外改动它。参数又常与字段同名。现在把“函数属于哪个对象”和“函数能否修改对象”明确写进代码。

![this 指向当前对象，const 视图限制可调用的修改操作](/qmx-Gameknowledge/assets/oop/members.svg)

```cpp
#include <iostream>

// 维护一个演示等级；用同名参数展示 this，不承载完整角色规则。
class Actor {
public:
    void setLevel(int level) {
        this->level = level; // 左边是当前对象成员，右边是参数。
    }
    int getLevel() const { return level; }
    Actor& levelUp() {
        ++level;
        return *this; // 返回当前对象本身的引用，不是复制它。
    }
private:
    int level = 1;
};

int main() {
    Actor hero;
    hero.setLevel(3);
    hero.levelUp().levelUp();
    const Actor& view = hero;
    std::cout << view.getLevel() << '\n'; // 5
    // view.setLevel(9); // 错误：不能经 const 对象视图调用修改成员。
}
```

这里不做等级范围验证，以集中讲成员语法；实际游戏应像生命值一样限制合法范围，并防止累加溢出。

## this 与 *this 各是什么

非静态成员函数有当前对象，`this` 是指向它的指针。`this->level` 明确选择成员；`*this` 表示当前对象。常见字段命名为 `level_`，就能直接写 `level_ = level`，不必每次显式写 this。

错误片段 `void setLevel(int level) { level = level; }` 只给参数自身赋值，不会改变成员。编译器警告可以帮忙，但理解名字遮蔽更可靠。

返回 `Actor&` 能链式操作同一个对象；返回 `Actor` 通常产生值结果，后续可能修改副本；返回 `Actor*` 则调用方需要用箭头。返回局部对象引用一定不能用于延续其寿命。链式调用只应在含义自然、返回对象仍存活时使用，不是每个接口都应支持。

## const 成员函数的精确作用

后置 `const` 写在参数列表之后：`int getLevel() const`。它限制通过当前对象修改普通成员，使只读对象和只读引用也能调用该函数。声明和类外定义的 const 必须一致。

| 写法 | 返回值 | 当前对象是否只读 |
| --- | --- | --- |
| `int hp() const` | 整数副本 | 是 |
| `const std::string& name() const` | 只读字符串借用 | 是，且返回引用受对象寿命约束 |
| `std::string name() const` | 字符串值结果 | 是，但可能有复制成本 |
| `int& hp()` | 可写整数借用 | 否，而且可能绕过数值规则 |

const 不等于线程安全，也不是深层永久冻结：指针成员指向的外部对象不一定只读。`mutable` 成员允许在 const 成员函数中修改，常用于缓存或同步设施；它不应用来绕过业务只读承诺。

## 重载：同名但参数不同

```cpp
// 局部示例：普通重载，不涉及继承。
class DamageLog {
public:
    void write(int amount);             // 只写数值。
    void write(int amount, bool critical); // 多一个参数。
    // int write(int amount);           // 错误：仅返回类型不同不能重载。
};
```

重载在调用时按参数类型、数量、转换等规则选择候选，不是运行时检查角色类型。默认参数可能让候选变得歧义，例如同时提供 `f(int)` 和 `f(int, int = 0)` 后调用 `f(1)`。不要只看“它们参数列表不同就一定不会冲突”。

const 与非 const 成员函数也能构成重载：

```cpp
class Slot {
public:
    int& value() { return value_; }
    const int& value() const { return value_; }
private:
    int value_ = 0;
};
```

普通 Slot 可选择可写版本，只读 Slot 只能使用只读版本。这个模型适合可写元素容器；若 value_ 是有不变量的生命值，就不应暴露任意可写引用。

## 类内声明，类外定义

```cpp
// 局部示例：放在一个源文件也能观察声明/定义关系。
class Counter {
public:
    void addOne();
    int value() const;
private:
    int value_ = 0;
};

// Counter:: 说明这是类的成员，而不是同名的普通函数。
void Counter::addOne() { ++value_; }
int Counter::value() const { return value_; }
```

拆文件时，把类定义与成员声明放进 `Counter.h`，用 `#pragma once`（广泛支持）或标准 include guard 防止同一翻译单元重复包含；把普通类外定义放进 `Counter.cpp`，再让 main 文件包含头文件。

多个源文件一起编译时，不要把同一个非 inline 函数定义放进公共头文件，造成多重定义。类体内定义的普通成员函数在本专题的常规非模块环境中隐式 inline；inline 首先关联允许满足条件的多处定义，不保证编译器真的展开调用。前置声明也不能代替所有完整定义依赖。

**练习：** 把角色查询函数移到类外，故意漏掉 const 看诊断，再恢复。为日志写两个含义清楚的重载；说明它们为什么与后面的 virtual 多态不同。

下一章：[构造函数与初始化](../06-constructors/)。
