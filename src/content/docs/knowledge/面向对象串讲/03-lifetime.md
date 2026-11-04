---
title: "3. 对象生命周期与 RAII"
description: "区分存储和生命周期，理解构造析构顺序、异常清理与资源管理。"
sidebar:
  order: 4
---

## 变量出了作用域，发生了什么

```cpp
#include <iostream>
#include <string>
#include <utility>

// 用日志观察对象的构造和析构，不代表日志应写进所有生产类。
class Trace {
public:
    explicit Trace(std::string name) : name_(std::move(name)) {
        std::cout << "+ " << name_ << '\n';
    }
    ~Trace() { std::cout << "- " << name_ << '\n'; }
private:
    std::string name_;
};

int main() {
    Trace outer{"outer"};
    {
        Trace inner{"inner"};
        std::cout << "work\n";
    }
    std::cout << "after\n";
}
```

预期输出是 `+ outer`、`+ inner`、`work`、`- inner`、`after`、`- outer`，每项一行。可以据此画出作用域时间线：

![构造、工作与逆序析构的时间线，同时展示异常退出仍清理已构造成员](/qmx-Gameknowledge/assets/oop/lifetime.svg)

自动存储期对象通常实现于栈，但“局部变量”和“栈上全部数据”不能直接画等号。局部 `vector` 的控制对象与其动态分配的元素可以位于不同存储区域。C++ 的语义关键是对象何时开始和结束生命周期，而不是背“类一定在堆上”。

## RAII：把资源释放绑到对象寿命

RAII 的全称是 Resource Acquisition Is Initialization。让一个对象在构造过程中取得资源、在析构时释放资源，调用方就能借助作用域安排清理。资源不只是内存，还包括文件、互斥锁、网络句柄等。

```cpp
#include <fstream>
#include <stdexcept>

// 使用标准库资源对象；函数提前返回或抛异常时仍会关闭文件。
void saveBattle() {
    std::ofstream out{"battle.txt"};
    if (!out) throw std::runtime_error("cannot open battle.txt");
    out << "hp=100\n";
    if (!out) throw std::runtime_error("write failed");
} // out 的析构负责资源释放；需要确认持久化成功时还应显式检查关闭结果。
```

没有必要为所有标准库对象再造一个手写析构包装。`string`、`vector`、`unique_ptr` 已经在做资源管理。一个只包含这些成员的类通常可以不写析构函数，这就是后面会说的 Rule of Zero。

## 为什么到处写 new/delete 容易错

```cpp
// 反例：中间的操作可能抛异常，导致最后的 delete 永远执行不到。
// auto* p = new Resource;
// operationThatMayThrow();
// delete p;
```

`new` 通常包括取得存储和构造对象，`delete` 包括析构和释放对应存储。构造本身抛异常时，new 表达式取得的存储会得到相应清理；真正的常见漏洞是“构造成功后、手工 delete 之前”的多条退出路径。优先使用局部对象和拥有资源的标准库类型，不要把裸指针默认当所有者。

## 构造与析构顺序

派生对象的构造顺序是：虚基类（如有）→ 直接基类 → 按声明顺序的成员 → 当前构造函数体。析构反向进行：先执行当前析构函数体，再逆序析构成员和基类。

如果某个成员构造失败，已经完整构造的基类和成员会析构；**当前完整对象的析构函数不会执行**，因为它没有构造完成。这正是资源应由成员 RAII 对象接管的原因，不能只指望最外层析构函数补救。

析构函数一般不应让异常逃逸，尤其在另一异常正在展开栈时。把可能失败的业务提交设计成显式操作，并让析构承担可靠清理。`std::exit`、强制终止、进程崩溃等也不等同于正常作用域退出，不能宣称任何退出都会完整析构局部对象。

## 两个特别容易留下悬空访问的接口

```cpp
// 错误示意：局部对象寿命结束后，返回的引用已悬空。
// const Actor& makeActor() { Actor a{100}; return a; }

// 正确方向：按值返回，由 C++ 的返回值优化/移动机制配合构造。
// Actor makeActor() { return Actor{100}; }
```

返回引用不会自动延长任意局部对象寿命。另一个陷阱是保存 `vector` 元素地址后继续 `push_back`：扩容会让旧地址失效。对象还“在同一个容器”不代表原地址仍然有效。

**练习：** 在上面 `inner` 创建后抛出 `std::runtime_error`，在 `main` 外层的 `try/catch` 中捕获，预测并运行析构日志。区分“已构造对象会清理”和“程序无论如何退出都会清理”。

下一章：[复制、移动与所有权](../04-value-ownership/)。
