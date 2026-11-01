---
title: "3. 托管、非托管与运行后端"
description: "区分托管执行、托管引用、非托管类型和原生内存，说明 Mono、IL2CPP 与 Burst 的边界。"
sidebar:
  order: 3
---

## “托管”需要结合上下文

讨论托管代码，是在说执行依赖运行时服务；讨论托管对象，是在说对象生命周期受 GC 管理；讨论非托管类型，是在说类型内部不包含托管引用。三句话相关，但不等价。

```csharp
struct DensitySample
{
    public float Value;
    public int Material;
}

struct NamedSample
{
    public float Value;
    public string Name;
}
```

`DensitySample` 不含托管引用，是非托管类型；`NamedSample` 含 string 引用，不是非托管类型。二者都是值类型。

## unmanaged 不决定存储位置

```csharp
var samples = new DensitySample[100];
```

数组仍然是托管对象；其中元素类型满足 unmanaged 并不会让数组自动转入原生分配。

`where T : unmanaged` 是编译期类型约束。它比 `where T : struct` 严格：后者并不排除结构体内部含有对象引用。符合 unmanaged 也不保证能直接用于所有原生互操作接口；ABI、字段布局、布尔表示和对齐还需另行核对。

## Unity 的三个执行概念

| 名称 | 主要职责 | 不代表什么 |
| --- | --- | --- |
| Mono | 提供 Unity 某些版本/平台使用的托管运行时 | 不等于所有现代 .NET API 都可用 |
| IL2CPP | 将 IL 转换为 C++ 并进行 AOT 构建 | 不会消除 C# 对象语义和 GC |
| Burst | 将受支持的计算代码编译为优化本机代码 | 不会让任意托管对象图都能进入 Job |

具体支持情况以编辑器、目标平台、后端和包版本为准，不要把 CoreCLR 的分代 GC、对象布局或 JIT 行为直接套到所有 Unity 版本。

Native 容器为 Job 提供可访问的原生数据，但“能创建 NativeArray”和“某段代码符合 Burst 限制”仍需分别确认。Job 内通常使用数值、支持的结构体及 Native 容器，而不是 string、List 或任意 class 对象图。

## unsafe 是另一个维度

`unsafe` 允许使用指针等语言特性，不会关闭 GC，也不会自动取得所有权。固定托管对象、调用原生库、自行分配内存，各有不同的生命周期要求。入门阶段不需要用指针代替容器。

## 自测

**问：IL2CPP 生成了 C++，还会有 GC 吗？** 答：会，转换后仍需保持 C# 托管对象的生命周期语义。

**问：结构体只有 float 字段，把它放进普通数组后谁回收数组？** 答：GC；元素非托管与数组的分配方式不同。

继续：[GC、隐藏分配与测量](/qmx-Gameknowledge/knowledge/csharp与unity内存基础/04-gc-and-allocation/)。深入：[Mono 与 IL2CPP 差异](/qmx-Gameknowledge/knowledge/csharp底层专栏/04-mono与il2cpp/01-mono与il2cpp差异/)、[Burst 学习目录](/qmx-Gameknowledge/knowledge/unity-job与burst/目录/)。
