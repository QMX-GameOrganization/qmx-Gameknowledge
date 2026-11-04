---
title: "9. 复制、移动与所有权"
description: "把 C++ 的对象语义与 STL 容器连接起来，理解 Rule of Zero、智能指针和悬空引用。"
sidebar:
  order: 10
---

## 赋值到底复制了什么

```cpp
struct Inventory {
    std::vector<std::string> items;
};
// 片段需要 <vector>、<string>。
Inventory a{{"sword"}};
Inventory b = a;
b.items[0] = "staff"; // 不会修改 a 的字符串。
```

编译器生成的复制操作逐个复制成员；`vector<string>` 的复制创建独立的元素。并不能由此推出“类默认都是深拷贝”：若成员是裸指针，默认复制只复制地址；若是 `shared_ptr`，复制的是共享所有权；若是 `unique_ptr`，复制被禁止。

![值复制、独占所有权移动与非拥有借用的关系图](/qmx-Gameknowledge/assets/oop/ownership.svg)

## 创建副本和给已有对象赋值不是同一个操作

| 写法（以类型 T 为例） | 何时使用 | 常见声明形式 |
| --- | --- | --- |
| `T b = a;` | 新对象从已有对象初始化 | `T(const T& other)`，复制构造 |
| `b = a;` | b 已存在，替换它的状态 | `T& operator=(const T& other)`，复制赋值 |
| `T b = std::move(a);` | 新对象从可移动来源初始化 | `T(T&& other)`，移动构造 |
| `b = std::move(a);` | b 已存在，接收可移动来源 | `T& operator=(T&& other)`，移动赋值 |

`T&&` 是这里用于移动操作的右值引用写法，不能当成两个普通引用。具名变量即使类型为右值引用，作为表达式时也通常是左值，所以移动构造内部转移其成员时仍常需要 std::move。模板转发引用另有推导规则，这一阶段不展开。

赋值时接收方已有资源，需要处理旧资源、自赋值和失败路径；构造时还没有一个已存在的完整接收对象。标准库成员通常已经处理相应细节，优先组合它们，而不是先手写裸指针版本。

下面是独立程序，用背包快照验证默认成员复制与独占转移：

```cpp
#include <iostream>
#include <memory>
#include <string>
#include <utility>
#include <vector>

// 值快照：vector<string> 的复制保留独立元素，无需手写特殊成员。
struct InventorySnapshot {
    std::vector<std::string> items;
};

int main() {
    InventorySnapshot first{{"sword"}};
    InventorySnapshot second = first; // 复制构造。
    second.items[0] = "staff";
    InventorySnapshot third;
    third = second;                   // 复制赋值。
    std::cout << first.items[0] << ' ' << third.items[0] << '\n';
    auto owner = std::make_unique<std::string>("shield");
    auto moved = std::move(owner);
    std::cout << static_cast<bool>(owner) << ' ' << *moved << '\n';
}
```

输出 `sword staff`、`0 shield`，各一行。`static_cast<bool>` 是显式转换，用来观察源独占指针是否仍拥有对象；`*moved` 解引用字符串。不要把 unique_ptr 移动后的空状态推广成所有类型移动后都为空。

## 先确定对象能否被复制，再写语法

背包快照通常有独立复制的意义；一个代表已打开文件的独占句柄通常不应被默认复制；引用某个世界中角色的句柄又可能只是身份，不代表复制角色本体。复制语义由领域含义决定。

| 形式 | 含义 | 释放责任 |
| --- | --- | --- |
| `T` | 直接拥有一个值 | 值的析构负责其成员 |
| `T&` / `const T&` | 必须绑定一个对象，常用于借用 | 不负责释放，要保证被借用者仍活着 |
| `T*` | 可以为空，常表达可选借用 | 裸指针本身不表达所有权 |
| `unique_ptr<T>` | 独占动态对象 | 唯一所有者负责销毁 |
| `shared_ptr<T>` | 共享动态对象的所有权 | 最后一个共享所有者离开时销毁对象 |
| `weak_ptr<T>` | 观察共享对象，不延长对象寿命 | 使用前 `lock()` 获取临时所有权 |

裸指针并非一律错误；错误是让调用方猜“这个指针应该 delete 吗”。引用也不是自动安全：不为空不代表不会悬空。

## std::move 不是移动发动机

```cpp
auto first = std::make_unique<std::string>("sword");
// auto copied = first;        // 编译错误：独占所有者不可复制。
auto second = std::move(first); // 转移所有权；此后 first 为空。
// 片段需要 <memory>、<utility>、<string>，不依赖自定义类。
```

`std::move` 本身只是把表达式转换为可供移动操作选择的值类别。真正的资源转移由被调用的移动构造或移动赋值执行，也可能最终发生复制（例如某些 const 对象）。对 `unique_ptr`，移动后源为空；对很多标准库类型，只能一般地依赖“有效但状态未指定”，不能把字符串或 vector 移动后一定为空当普遍规则。自定义类型还要看它自己的移动后契约。

同样不要把移动当性能保证。小值复制可能更简单；移动不总是 O(1)；是否选到移动操作还受类型、异常保证和容器实现约束。

## Rule of Zero、Three、Five

优先采用 Rule of Zero：资源放进 `vector`、`string`、`unique_ptr` 等成员，自己的业务类不手写析构、复制和移动。

历史上的 Rule of Three 提醒你：若手写析构、复制构造、复制赋值之一来管理资源，另外两项通常也要审视。C++11 后加入移动构造和移动赋值，形成 Rule of Five。它们是设计提示，不是“每个类必须写五个函数”。

```cpp
// 示意：只表达移动的资源集合，使用默认操作保持成员自身的语义。
class Backpack {
public:
    Backpack() = default;
    Backpack(const Backpack&) = delete;
    Backpack& operator=(const Backpack&) = delete;
    Backpack(Backpack&&) noexcept = default;
    Backpack& operator=(Backpack&&) noexcept = default;
private:
    std::vector<std::unique_ptr<std::string>> items_;
};
```

手写或声明析构函数会影响隐式移动操作的生成，不能以为“我只加了一个打印析构，其他都不变”。给移动加 `noexcept` 也要建立在成员操作确实不会抛出的前提上。

## 容器、智能指针与地址稳定性

`vector<Actor>` 扩容会移动或复制元素，元素地址可能失效。`vector<unique_ptr<Actor>>` 扩容移动的是智能指针，所拥有的 `Actor` 通常仍留在原处；但删除、reset 或销毁该所有者之后，角色地址仍然失效。智能指针不会修复所有外部裸指针。

长期引用游戏实体时，可以考虑 ID 加代际计数，由注册表验证是否仍有效；这是另一种生命周期协议，并非“换成整数就没有悬空问题”。

共享所有权也有成本：引用计数和复杂的释放时机。两个对象互持 `shared_ptr` 会形成环，外部所有者全放手仍可能无法释放；应把某个观察方向改成 `weak_ptr`，或重新划分唯一所有者。引用计数安全也不意味着对象内容可被多线程无同步修改。

**自测：** 为什么查看背包内容时通常接收 `const Backpack&`，而不是按值接收 `shared_ptr<Backpack>`？因为它通常只需要借用，不需要参与拥有；接口应表达实际责任。

下一章：[运算符重载与 friend](../10-operators-friends/)。
