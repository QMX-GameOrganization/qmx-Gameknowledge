---
title: "4. 封装、不变量与接口设计"
description: "在已学类与访问控制的基础上，用受伤和治疗维护不变量，解释动作接口和边界输入。"
sidebar:
  order: 5
---

## 把状态和规则放在同一边界里

先认识错误处理语法：`throw std::invalid_argument("...")` 表示输入不符合要求，立即报告失败并离开正常路径。若调用处需要恢复，可以用 `try { ... } catch (const std::invalid_argument& error) { ... }` 捕获并处理；没有匹配处理时，异常继续向外传播。本章正常运行例子不触发异常。第 7 章再解释失败时对象如何清理。

下面是独立可运行程序。所有生命值变化都通过明确操作进行：

```cpp
#include <algorithm>
#include <iostream>
#include <stdexcept>

// 维护角色生命值；每次公开操作结束后都保持生命值范围合法。
class Actor {
public:
    int hp() const noexcept { return hp_; }
    bool alive() const noexcept { return hp_ > 0; }

    // 返回实际扣除量，便于日志和 UI 使用同一结果。
    int takeDamage(int amount) {
        if (amount < 0) throw std::invalid_argument("negative damage");
        const int applied = std::min(hp_, amount);
        hp_ -= applied;
        return applied;
    }

    // 先计算剩余空间，避免先 hp_ + amount 带来的有符号溢出。
    int heal(int amount) {
        if (amount < 0) throw std::invalid_argument("negative healing");
        const int applied = std::min(maxHp_ - hp_, amount);
        hp_ += applied;
        return applied;
    }

private:
    int maxHp_ = 100;
    int hp_ = 100;
};

int main() {
    Actor hero;
    std::cout << hero.takeDamage(130) << ' ' << hero.hp() << '\n';
    std::cout << hero.heal(500) << ' ' << hero.hp() << '\n';
}
```

预期输出：

```text
100 0
100 100
```

这份示例允许从 0 生命值治疗；若游戏禁止治疗死亡角色，应在 `heal` 中增加规则，并同步修改测试。**业务选择应写清楚，语言不会替你决定死亡是否可以逆转。**

## 读懂声明中的每个部分

`Actor hero;` 创建对象；`Actor` 是类型。每个对象拥有自己的非静态成员，普通非静态成员函数不是每个实例各复制一份机器码。`const` 查询和成员调用的细节将在下一章集中展开。

`public` 是外部允许依赖的接口；`private` 限制普通调用方直接访问成员；`protected` 允许派生类访问，但会把内部表示暴露给更多代码。访问控制是编译期规则，不是加密或内存安全沙箱。

`class` 默认成员和默认继承访问为私有，`struct` 默认公开；二者都能有构造、析构、虚函数和访问控制。常见约定是用 `struct` 表达简单公开数据，用 `class` 表达需要维护不变量的对象，这是一种风格选择。

## 规则从创建开始，而不只是修改时检查

本章先给固定初值 100，避免同时引入过多语法。不变量是每个对外可用的状态都应满足的条件，所以创建对象后的初始值也必须合法，不是只在 takeDamage 中检查就够了。

等到需要不同角色拥有不同初始生命值时，第 6 章引入构造函数，使“创建成功就合法”成为创建协议，而不依赖调用方记得先执行 init。

## const 不是“永久不变”的魔法

`Actor&` 是现有角色的引用，可以理解为给同一个对象取别名，传参时不复制角色；`const Actor&` 表示只能通过这个别名进行只读操作。`Actor*` 是保存角色地址的指针，可能为空；通过指针访问成员使用 `->`，通过对象或引用使用 `.`。它们都不自动保证原对象仍然存活。

```cpp
const Actor& view = hero; // 接在上面 main 内使用。
int current = view.hp();  // const 成员函数可被只读视图调用。
// view.heal(1);          // 编译错误：不能通过 const Actor 调用非 const 成员。
```

`hp() const` 的 `const` 限制经由当前对象修改普通成员，不代表线程安全，也不保证它指向的外部对象完全不能变。`mutable` 和指针间接访问还需要独立理解。`noexcept` 表示函数承诺异常不会逃逸；逃逸会终止程序，因此不能给会抛异常的操作随意加它。

## 把接口设计成动作，而不只是数据通道

`setHp(0)` 不说明发生了什么；`takeDamage(20)` 能统一处理护盾、统计、死亡判定。getter 也需要考虑代价和泄露：返回内部 `vector&` 会让外部绕过所有检查；返回值更安全但可能复制；返回只读引用避免复制但受原对象生命周期限制。

本章 hp_ 是每个对象独立的数据；第 8 章需要共享统计时再引入 static，不能把角色生命值误设为全体共享。

## 自测与练习

1. 为什么 `hp_ = std::clamp(hp_ + amount, 0, maxHp_)` 仍有问题？先做的有符号加法可能溢出，clamp 无法事后修复未定义行为。
2. 给角色增加护甲时，把护甲设为公开字段有什么代价？调用方可能制造负护甲，所有公式都需要防御。
3. 独立增加 `maxHp()` 查询与“更改最大生命值”操作，明确当前生命值如何处理，再写出边界例子：0、负数、极大整数、满血和死亡。

下一章：[成员函数、this、const 与重载](../05-member-functions/)。
