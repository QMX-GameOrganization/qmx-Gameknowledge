---
title: "0.4 在 Unity 里学 C#：练习方法、读报错与查文档"
description: "搭一个练习场景，把本栏位所有控制台示例搬到 Unity 里跑；认识 Console、常见编译错误，以及怎样查官方 API 文档。"
sidebar:
  order: 4
---

> 适用版本：Unity 2021 LTS 到 Unity 6000.x，C# 9.0。代码编辑器的选择与配置步骤以各自官方文档为准。

## 要点

- 本栏位的**所有控制台示例**都可以放进 Unity 里运行：把 `Main` 里的代码搬到 `Start()`，`Console.WriteLine` 换成 `Debug.Log`。
- 建一个固定的"练习场景"，之后每学一个知识点就在里面试一下。
- 看懂 Console 里的红色报错，是学 C# 最快的方式：错误信息通常直接告诉你**哪个文件、哪一行、什么问题**。
- 不会的 API，查官方的 Scripting API 文档，比搜博客更准确。

## 搭一个练习环境

1. 用 Unity Hub 安装一个 Unity 版本（Unity 2021 LTS 或 Unity 6 均可），新建一个 3D 项目。
2. 选一个代码编辑器（Visual Studio、Rider 或 VS Code），在 Edit → Preferences → External Tools 里指定。配置好后，输入时有补全和报错提示，学语法非常有用。
3. 新建场景 `Lab`，在 Hierarchy 里创建一个空物体，命名 `LabRunner`。
4. 新建脚本 `Lab`，挂到 `LabRunner` 上。

这个 `Lab` 脚本就是你的"草稿纸"：

```csharp
using System;                          // 书上示例常用，如 Math、Convert
using System.Collections.Generic;      // List、Dictionary
using UnityEngine;

public class Lab : MonoBehaviour
{
    void Start()
    {
        // 把书里 Main 方法中的代码粘贴到这里
    }
}
```

## 把控制台示例搬进来

| 书上的写法 | 在 Unity 里 |
| --- | --- |
| `static void Main() { ... }` | 放进 `void Start() { ... }` |
| `Console.WriteLine(x);` | `Debug.Log(x);` |
| 示例里定义的 `class Player { }` | 写在 `Lab` 类**外面**，同一个文件里即可 |
| `static` 辅助方法 | 写在 `Lab` 类里面，与 `Start` 并列 |
| `Console.ReadLine()` | 不可用，改用 `[SerializeField]` 字段或按键输入 |

例如把 2.3 篇的数组示例搬进来：

```csharp
using UnityEngine;

public class Lab : MonoBehaviour
{
    void Start()
    {
        int[] a = { 1, 2, 3 };
        int[] b = a;
        b[0] = 99;
        Debug.Log(a[0]);                 // 输出 99
    }
}
```

如果示例里要定义自己的普通类，放在文件末尾：

```csharp
public class Lab : MonoBehaviour
{
    void Start()
    {
        Enemy e = new Enemy { name = "史莱姆", hp = 30 };
        Debug.Log($"{e.name} {e.hp}");
    }
}

public class Enemy                         // 普通类，不继承 MonoBehaviour，可以 new
{
    public string name;
    public int hp;
}
```

只有继承 `MonoBehaviour` 的类需要"文件名等于类名"；普通类没有这个限制。

## 读 Console

保存脚本后切回 Unity，右下角会出现"正在编译"的转圈。编译通过才能点 Play。

| 颜色 | 含义 |
| --- | --- |
| 白色 | `Debug.Log` 的普通信息 |
| 黄色 | 警告，能运行但可能有问题 |
| 红色 | 编译错误（不能运行）或运行时异常 |

红色信息形如 `Assets/Lab.cs(12,9): error CS0103: The name 'hp' does not exist in the current context`：文件 `Lab.cs` 第 12 行第 9 列，错误码 `CS0103`，意思是"当前上下文里没有叫 hp 的名字"。**双击这条信息，编辑器会跳到出错那一行。**

## 常见报错对照

| 报错 | 通常原因 |
| --- | --- |
| `CS0103` 名称不存在 | 变量拼错、变量在别的作用域、忘了声明 |
| `CS0246` 找不到类型 | 忘了 `using`，或类型名拼错 |
| `CS1002` 应输入 ; | 上一行少了分号 |
| `CS0029` 无法隐式转换 | 类型不匹配，如 `int x = 3.5f;`（1.2 篇） |
| `CS0165` 使用了未赋值的变量 | 局部变量没有先赋值（1.1 篇） |
| `NullReferenceException`（运行时） | 引用为空，常见于 Inspector 里忘了拖物体（1.3 篇） |
| `The script class can't be found` | 脚本文件名和类名不一致 |
| `MissingReferenceException` | 使用了已被销毁的物体 |

## 查官方文档

在 Unity 官网的 Scripting API 里搜类名，例如 `Transform`、`Physics.Raycast`。页面通常分成：

- **Properties**（属性）：如 `Transform.position`，注意它是属性，返回副本（3.3 篇）。
- **Public Methods**（方法）：如 `Transform.Rotate`。
- **Static Methods**（静态方法）：如 `Physics.Raycast`、`Mathf.Lerp`（3.4 篇）。
- 每页底部有可复制的小示例。

遇到不认识的语法，可以回到本栏位对应的那篇再看一遍。

## 本栏位每篇怎么用

从第 1 章开始，每篇都有两个小节：

- **在 Unity 里用到它**：这个语法在引擎里出现在哪里，能解决什么问题。
- **动手试试**：一个 5 到 15 分钟的小练习，放进 `Lab` 脚本里做。

推荐的节奏是：先读正文，再把示例敲一遍（不要复制粘贴，敲的过程会让你发现细节），然后**故意改坏**——删一个分号、改一个类型、把 `ref` 去掉——看 Console 报什么错。这比单纯阅读记得牢得多。

## 项目应用决策：练习脚本和主线代码分开

`Lab` 适合验证一个孤立语法，主线 `Assets/Speedrun/Game/` 适合保存会被后续章节继续使用的类型。两者混在一起会产生重复的 `Health`、`Enemy` 和 `GameManager`，编译器报错只是表象，真正的问题是代码没有明确所有者。

每次练习都要写清楚：这是一次性实验，还是要进入方块地牢。若进入主线，就改已有脚本并补运行验收；若只是实验，就放进带篇号的 `Labs` 子目录，并在完成后删除或移出场景。

## 常见坑

- Play 模式下在 Inspector 里改的值，退出 Play 后会恢复。想保留，退出后重新改。
- 改了脚本没保存就切回 Unity，没有触发编译。
- 同一个场景里把 `Lab` 挂了好几个物体，日志重复输出。
- 不同篇的练习里有同名类（如 `Health`、`Enemy`、`HpLogger`）。同一个工程里重复定义会报 `CS0101`。每做完一篇，把练习脚本放进以篇号命名的文件夹（如 `Assets/Practice/3.3`），要做下一个同名练习时删除或移走旧的。
- 脚本报了编译错误，Unity 会继续运行**上一次编译成功的版本**，容易误以为改动不起作用。先看 Console。

下一章开始系统学语法：[从 C++ 到 C#：第一印象与类型对照](../../01-入门/01-从Cpp到CSharp的第一印象/)。
