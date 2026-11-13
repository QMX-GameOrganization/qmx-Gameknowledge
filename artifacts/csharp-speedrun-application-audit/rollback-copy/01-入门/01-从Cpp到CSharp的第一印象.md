---
title: "1.1 从 C++ 到 C#：第一印象与类型对照"
description: "用一张对照表把 C++ 的基础语法映射到 C#：程序结构、基本类型、变量初始化、控制流，以及 Unity 里对应的写法。"
sidebar:
  order: 11
---

> 适用版本：语法以 C# 9.0 为准（Unity 2021 LTS 到 Unity 6000.x 使用的语言版本）。示例用控制台程序写，Unity 里把 `Console.WriteLine` 换成 `Debug.Log` 即可。

## 要点

- C# 的控制流（`if`、`for`、`while`）和 C++ 几乎一样，大部分基础语法你可以直接读懂。
- 真正的差别集中在四处：**没有头文件**、**默认没有指针**、**内存由 GC 回收**、**局部变量必须先赋值才能用**。
- 基本类型的大小在语言里是固定的：`int` 永远是 32 位，`long` 永远是 64 位，不随平台变化。
- `string` 是内置的、不可变的引用类型，`==` 比较的是内容。

## 一个最小程序

```csharp
using System;                       // 类似 using namespace，同时承担 #include 的一部分作用

class Program
{
    static void Main()              // 程序入口，大小写敏感：Main
    {
        int hp = 100;
        float speed = 3.5f;         // float 字面量必须带 f，否则是 double
        string name = "Hero";
        Console.WriteLine($"{name}: hp={hp}, speed={speed}");
    }
}
```

三处和 C++ 不同：没有 `#include` 和头文件，编译器会自己看到整个项目里的所有类型；函数不能脱离类存在，连 `Main` 也要放在类里；`using System;` 只是省去写命名空间前缀，不会把代码"拷贝进来"。

在 Unity 里你不会写 `Main`。引擎启动后，会替你调用挂在物体上的脚本方法（`Start`、`Update`），0.3 篇会讲这个衔接。

## 基本类型对照

| C++ | C# | 说明 |
| --- | --- | --- |
| `int` | `int` | 32 位，固定 |
| `long long` | `long` | 64 位，固定 |
| `unsigned int` | `uint` | 无符号还有 `ulong`、`ushort`、`byte` |
| `char`（8 位） | `byte` 或 `sbyte` | C# 的 `char` 是 16 位 UTF-16 字符，不是字节 |
| `float` / `double` | `float` / `double` | `float` 写 `1.5f`；Unity 的 API 几乎全用 `float` |
| `bool` | `bool` | 只能是 `true`/`false`，`if (hp)` 这类写法不合法 |
| `std::string` | `string` | 引用类型，不可变，见 1.4 |
| `auto` | `var` | 编译期推断类型，局部变量才能用 |
| `const` | `const` / `readonly` | `const` 是编译期常量，`readonly` 是运行时只读字段 |

没有 `bool` 与整数的隐式互转，这能挡住 `if (x = 5)` 这类笔误：C# 里这行直接编译不过。

## 初始值：局部变量与字段规则不同

```csharp
class Player
{
    public int hp;                  // 字段：自动为 0（bool 为 false，引用为 null）
    public string name;             // null

    public void Test()
    {
        int damage;
        // Console.WriteLine(damage);   // 编译错误：使用了未赋值的局部变量
        damage = 10;
        Console.WriteLine(damage + hp);
    }
}
```

C++ 里未初始化的局部变量是随机值；C# 在**编译期**就拒绝读取，所以不会出现随机值。类的字段由运行时清零，这一点比 C++ 省心，但 `string name;` 默认是 `null`，不是空串。

## 控制流：只有 switch 要留意

```csharp
for (int i = 0; i < 3; i++) { /* 和 C++ 一样 */ }
foreach (int x in new int[] { 1, 2, 3 }) { /* 范围 for，见 2.2 */ }

int state = 1;
switch (state)
{
    case 0:
        Console.WriteLine("idle");
        break;                      // 每个分支必须以 break / return / continue / goto 结束
    case 1:
    case 2:                         // 空分支可以直接合并，不算贯穿
        Console.WriteLine("move");
        break;
    default:
        break;
}
```

C# **禁止隐式贯穿**（fall through）：忘写 `break` 是编译错误，而不是运行时 bug。

## 在 Unity 里用到它

基本类型在游戏里各有固定的"岗位"：

| 类型 | Unity 里典型用途 |
| --- | --- |
| `float` | 位置、速度、时间、角度，Unity 的 API 几乎全用它 |
| `int` | 血量、数量、编号、分数 |
| `bool` | 是否在地面、是否死亡、开关 |
| `string` | 物体名、标签、提示文字 |

`.cs` 文件保存在 Assets 目录下，切回 Unity 会自动编译。本栏位的控制台示例怎么搬进 Unity 运行，见 0.4 篇。

## 动手试试

在 `Lab` 脚本的 `Start` 里声明 `int hp`、`float speed`、`bool alive`、`string name`，用 `Debug.Log($"{name} hp={hp} speed={speed}")` 输出。然后故意把 `3.5f` 改成 `3.5`，看 Console 里出现哪个编译错误；再写一行用了未赋值的局部变量，对照 0.4 篇的报错表找到它的错误码。

## 项目应用决策：先按数据含义选类型

类型不是语法装饰，而是给项目数据加约束：`float` 用于速度和冷却，`int` 用于血量和数量，`bool` 用于开关，`string` 用于显示文本和资源键。若把血量写成 `float`，后面就必须明确是否允许小数伤害；若把状态写成 `string`，拼写错误只能运行时发现，应该在 2.1 改为 `enum`。

选择顺序是：先问数据能否出现小数、是否需要名字集合、是否允许为空，再决定类型。这个判断会影响 Inspector 显示、序列化和后续函数签名；不是“看到示例是什么类型就照抄”。

## 常见坑

- `float f = 3.5;` 编译失败，需要 `3.5f`。Unity 里 `Mathf`、`Vector3` 全是 `float`，混入 `double` 字面量最常见。
- 把 `char` 当字节用。需要字节写 `byte`。
- 在 Unity 里用 `Console.WriteLine`：不会报错，但输出不会进 Console 面板，用 `Debug.Log`。
- 误以为局部变量会像字段一样自动清零。

## 小结

读代码时可以先把 C# 当成"去掉头文件、去掉指针、带垃圾回收的 C++"。下一篇进入[类型转换](../02-类型转换/)，这是游戏数值计算中最常踩坑的地方。
