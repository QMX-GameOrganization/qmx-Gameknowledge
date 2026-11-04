---
title: "1. 给名字分区域：namespace、enum 与作用域"
description: "从模块重名和回合状态出发，补齐 std::、namespace、using 与枚举的基础，不预设类知识。"
sidebar:
  order: 2
---

## 应用一：战斗和音频都想叫 play

在大程序里，同一个词可以在不同模块表达不同含义。我们希望保留自然名字，又能明确告诉编译器用哪一个。

```cpp
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

输出 battle、audio、done，各一行。`namespace Battle { ... }` 声明命名空间；`::` 是作用域解析运算符，`Battle::play` 指定名字来源。命名空间不代表一个具体游戏对象，不需要也不能像角色一样创建实例。

`std::vector`、`std::string`、`std::cout` 中的 std 是标准库命名空间。`#include <vector>` 引入相关声明，`std::` 指定名字来源，二者不同；只写 std:: 不能替代 include。

## using 的三种相关写法先分清

```cpp
// 局部片段。
using std::cout;             // 引入一个名字，可在适当范围直接写 cout。
// using namespace std;     // using 指令，影响名字查找，不是复制整个标准库。
using Score = int;          // 类型别名：Score 是 int 的另一个名字，不是新的独立类型。
```

公共头文件里使用 `using namespace std;` 会影响包含它的其他代码，容易重名。本专题保留 std::，让来源清楚。类型别名不会阻止 Score 与 int 混用；若需要独立的类型规则，后面可以定义类。

同一个命名空间可以在不同位置继续声明，也可嵌套，例如 C++17 的 `namespace Game::Battle { ... }`。命名空间与文件夹不是强制一一对应；不要自己向 std 随意添加声明。

## 作用域：名字在哪个范围可见

花括号经常创建局部作用域，局部变量可能遮蔽外部同名变量。命名空间限定可以明确选择更外层名字；函数内部的局部名字不因此成为命名空间成员。

```cpp
// 独立程序：观察局部名字遮蔽。
#include <iostream>
namespace Game { int score = 10; }
int main() {
    int score = 3;
    std::cout << score << ' ' << Game::score << '\n'; // 3 10
}
```

名字可见范围与对象存活时间是不同维度；后面的 static 会展示“名字只在函数中可见，但对象跨调用存活”。

## 应用二：回合状态不再用神秘数字

用整数 0、1、2 表示回合状态，读 `state == 2` 时很难直接知道含义。枚举为有限选项命名。

```cpp
#include <iostream>

enum class RoundState {
    Ready,
    Running,
    Finished
};

int main() {
    RoundState state = RoundState::Running;
    switch (state) {
    case RoundState::Ready:    std::cout << "ready\n"; break;
    case RoundState::Running:  std::cout << "running\n"; break;
    case RoundState::Finished: std::cout << "finished\n"; break;
    }
}
```

输出 running。RoundState 是新类型，RoundState::Running 是枚举值，state 是保存该值的变量。`enum class` 是作用域枚举的组合语法，**不是先要求你已经会普通 class**；它与后面定义角色类是两种不同语法。

`switch` 按枚举值选择分支；break 离开 switch。新增选项时应检查所有相关分支，开启编译器警告有帮助，但不要假设每种编译设置都会强制你处理所有枚举值。

## enum 与 enum class 的区别

| 写法 | 枚举项名字 | 与整数的关系 |
| --- | --- | --- |
| `enum State { Ready, Running };` | 枚举项进入外围作用域，可能重名 | 可隐式转换为整数 |
| `enum class State { Ready, Running };` | 常写 State::Ready，名字集中在枚举作用域 | 不随意隐式转换为整数 |

可以显式指定底层类型，例如 `enum class State : unsigned char { Ready, Running };`。本专题不用整数底层表示承担业务意义；解析配置或网络输入时，强制转换不等于验证某个数字是合法状态。不要把枚举值默认当连续数组下标，也不要假定所有枚举都从 0 连续增长。

## 本章的边界与练习

命名空间只组织名字，枚举只表达有限分类，它们不会自动封装角色，也不会自动执行技能行为。我们先补齐这些常见写法，是为了后面能读懂对象代码中的名字。

练习：建立 Game 和 Audio 两个命名空间，各写一个 status 函数；再用 RoundState 表示游戏回合。解释 std::、Game:: 与 RoundState:: 各在限定什么。下一章再正式创建第一个自定义角色类型。

下一章：[类与对象](../02-class-basics/)。
