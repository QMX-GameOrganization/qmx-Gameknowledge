---
title: "8. 一份还是每人一份：static 的应用与区别"
description: "从角色编号与累计创建次数出发，细讲静态成员、静态函数、局部静态、文件作用域 static 和常见链接坑。"
sidebar:
  order: 9
---

## 应用：每个角色有编号，所有角色共用编号分配器

生命值应各自独立，编号却要协调生成。若每个角色都有自己的 nextId=0，第一个编号全都相同。我们需要让计数属于类型，而不是每个实例。

![实例成员、静态成员与静态成员函数的关系](/qmx-Gameknowledge/assets/oop/static.svg)

```cpp
#include <iostream>

// 演示类级共享计数；不允许复制/移动以免把“创建次数”与隐式操作混淆。
class Actor {
public:
    Actor() : id_(++created_) {}
    Actor(const Actor&) = delete;
    Actor& operator=(const Actor&) = delete;
    Actor(Actor&&) = delete;
    Actor& operator=(Actor&&) = delete;

    int id() const { return id_; }
    static int totalCreated() { return created_; }
private:
    int id_;                         // 每个对象一份。
    inline static int created_ = 0; // C++17：类型共享的一份定义。
};

int main() {
    Actor a;
    {
        Actor b;
        std::cout << a.id() << ' ' << b.id() << '\n';
        std::cout << Actor::totalCreated() << '\n';
    }
    std::cout << Actor::totalCreated() << '\n';
}
```

输出 `1 2`、`2`、`2`，各一行。b 销毁后累计创建数仍为 2；它**不是当前存活对象数**。这段程序为有限次单线程演示，生产编号分配还需要处理计数溢出、重启和并发等问题。

## 静态数据成员属于类型

非静态 `id_` 每个对象独立；static `created_` 不作为每个对象的独立子对象存储。没有角色对象时，仍可调用允许访问的静态接口。静态成员也受 public/private 控制，static 并不自动公开。

推荐通过 `Actor::totalCreated()` 表达类型级操作。C++ 也允许某些通过对象访问静态成员的写法，如 `a.totalCreated()`，但它没有因为这种语法就获得“当前 a 的统计”。容易误导读者，因此本专题不用这种风格。

## 静态成员函数没有 this

```cpp
// 错误片段：静态函数不知道该取哪一个角色的 id_。
// static int wrong() { return id_; }
// static int wrong() { return this->id_; }

// 合法方向：明确传入对象后，才能针对该对象操作。
// static int readId(const Actor& actor) { return actor.id_; }
```

静态函数可以访问静态成员，也可以通过明确的对象访问它有权限访问的非静态成员。问题不是“静态函数绝对不能碰普通成员”，而是它没有隐含当前对象。静态成员函数不能声明为 const 成员函数，也不能声明为 virtual，因为这两者都依赖实例对象语义。

## inline static 与传统类外定义

```cpp
// 完整形式片段，适用于学习类内声明与类外定义的区别。
class Counter {
public:
    static int value;
};
int Counter::value = 0; // 类外定义时不再重复 static。
```

传统写法在头文件中声明，在**一个**源文件中定义。只声明不定义、又实际需要该对象时，常在链接阶段出现未解析符号。把类外定义直接放进被多个源文件包含的头文件，则可能出现多重定义。

C++17 的 `inline static int value = 0;` 可在类体内给出定义，方便放入头文件；满足 inline 定义规则时，不是每个翻译单元各有一份独立 value。这里 inline 不是“保证速度更快”。

`static constexpr` 常用于编译期常量。C++17 中 constexpr 静态数据成员隐式 inline；更早标准的规则不同。不要把 C++17 写法直接套到旧编译标准后，再用随意补定义修复。

## 函数里的 static：保存跨调用状态

```cpp
// 局部片段：名字只在函数内部可见，但对象不在每次返回时销毁。
int nextTicket() {
    static int ticket = 0;
    return ++ticket;
}
```

普通局部变量每次进入相关作用域重新建立；局部 static 具有静态存储期，需要动态初始化时在首次执行经过声明处完成初始化。C++11 起这类初始化有线程安全保证，**不表示后面的 ++ticket 是线程安全的**。若初始化抛异常，后续进入时可重试，不能把失败当成已经完成初始化。

局部 static 会让函数记住历史，测试顺序可能影响结果；它也可能隐藏共享状态。不必每个生成器都做成 static，很多时候让一个明确对象拥有计数更容易控制寿命和重置。

## 文件作用域 static：又是另一层意思

```cpp
// 放在某个 .cpp 的命名空间作用域。
static int debugCount = 0;
static void traceOnce() { ++debugCount; }
```

此处主要影响名字的链接，通常让名字只在当前翻译单元内部使用。它不是类的共享成员。现代 C++ 也常用匿名命名空间表达内部实现名字。

| 位置 | 主要含义 | 不能混淆的点 |
| --- | --- | --- |
| 类的数据成员 | 各实例共享类型级数据 | 仍受访问控制 |
| 类的成员函数 | 没有隐含 this | 不是 virtual 或 const 成员 |
| 函数内部局部变量 | 跨调用保留，静态存储期 | 初始化安全不等于后续修改安全 |
| 命名空间/文件作用域名字 | 内部链接 | 头文件中的普通 static 变量可能每个翻译单元各一份 |

## 常见坑：统计口径、全局状态和初始化顺序

统计“当前存活数”需要构造增加、析构减少，并认真处理复制和移动，而不只是给普通构造加一行。统计“成功创建数”也不能在随后仍可能失败的构造中随意提前提交。不要让演示计数器被误用为可靠的生产统计。

跨翻译单元依赖其他动态初始化的静态对象，可能遇到初始化顺序问题；退出时又可能有析构依赖问题。局部 static 或显式拥有对象可改善特定情况，但没有消灭所有并发、重入和析构次序约束。

**练习：** 先实现“累计创建次数”，再另写“当前存活数”，禁止复制和移动，比较离开内层作用域后的结果。说明为什么把角色 hp 设为 static 会让所有角色意外共享生命值。

下一章：[复制、移动与所有权](../09-value-ownership/)。
