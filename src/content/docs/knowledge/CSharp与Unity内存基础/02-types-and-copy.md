---
title: "2. 类型、赋值与参数传递"
description: "区分值复制、引用复制、浅拷贝、装箱与 ref 参数，理解 Native 句柄复制的前置知识。"
sidebar:
  order: 2
---

## 值类型复制值，引用类型复制引用

```csharp
struct Sample
{
    public float Density;
}

var a = new Sample { Density = 1f };
var b = a;
b.Density = 2f;
// a.Density 仍为 1f。

var x = new float[] { 1f };
var y = x;
y[0] = 2f;
// x[0] 为 2f。
```

值类型包括数值、枚举和结构体；引用类型包括类、数组、字符串和委托。字符串不可变，不代表它是值类型。

## 结构体包含引用时，不会递归深拷贝

```csharp
struct Samples
{
    public float[] Values;
}

var a = new Samples { Values = new float[] { 1f } };
var b = a;
b.Values[0] = 3f; // a.Values[0] 也是 3f。
b.Values = new float[] { 9f }; // 只替换 b 的字段。
```

复制的是字段值；数组字段的值是引用。所以“结构体复制后完全独立”只有在内部数据也没有共享关系时才成立。NativeArray 的句柄复制同样需要分析共享关系。

## 按值传参不等于复制整个对象

普通参数默认按值传递：结构体参数取得结构体副本，类或数组参数取得引用副本。

```csharp
// 修改共享数组的元素，但替换局部参数不影响调用者的变量。
static void Edit(float[] values)
{
    values[0] = 5f;
    values = new float[1];
}
```

| 参数形式 | 语义重点 |
| --- | --- |
| 普通参数 | 复制参数值；这个值可能是引用 |
| ref | 允许直接读写调用者的变量位置 |
| out | 被调用方负责赋值后返回 |
| in | 通过只读引用传入；特定结构体成员调用可能触发防御性复制 |

`in` 不是所有结构体的自动性能优化。结构体大小、内联和调用方式都影响成本；需要测量。只读引用也不自动让内部引用的对象不可变。

## 装箱与拆箱

```csharp
int count = 16;
object boxed = count; // 将该值装箱为对象。
int restored = (int)boxed;
```

装箱通常产生托管分配。将结构体转成接口也可能装箱；泛型约束调用则可能避免，取决于具体写法。拆箱必须匹配实际装箱类型，不能把装箱的 int 直接拆成 float。

## 自测

**问：给 class 参数重新赋值，会替换调用者的引用变量吗？** 答：普通按值参数不会；若要替换变量，需要返回新引用或使用 ref 等方式。

**问：复制含 List 字段的 struct，会复制列表元素吗？** 答：不会，只复制列表引用。

继续：[托管、非托管与运行后端](/qmx-Gameknowledge/knowledge/csharp与unity内存基础/03-managed-and-unmanaged/)。深入：[struct 拷贝与防御性复制](/qmx-Gameknowledge/knowledge/csharp底层专栏/01-类型系统/03-struct的拷贝语义与防御性复制/)、[装箱拆箱](/qmx-Gameknowledge/knowledge/csharp底层专栏/01-类型系统/02-装箱拆箱与il实现/)。
