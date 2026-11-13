---
title: "4.2 万物之父 object、装箱拆箱与密封类"
description: "所有类型都继承自 object；object 的常用方法；装箱拆箱的含义与代价；sealed 禁止继承。"
sidebar:
  order: 42
---

> 适用版本：C# 9.0。装箱的底层实现（IL 指令、对象头）在「C# 底层专栏」1.2 展开，这里只讲使用层面。

## 要点

- C# 中**所有类型**（包括 `int`、`struct`、数组、你自己的类）最终都继承自 `System.Object`，简写 `object`。C++ 没有这个共同祖先。
- `object` 提供四个人人都有的方法：`ToString()`、`Equals()`、`GetHashCode()`、`GetType()`。
- 把值类型放进 `object`（或接口）变量会发生**装箱**：在堆上新建一个对象保存副本，有分配开销。
- `sealed` 修饰的类不能再被继承。

## object 能装下一切

```csharp
object a = 42;                 // int 装进 object
object b = "text";
object c = new int[] { 1, 2 };
object d = new Player("勇者");   // 假设沿用 4.1 的类

object[] mixed = { 1, "二", 3.0f, new Enemy("史莱姆", 20) };
foreach (object o in mixed)
    Console.WriteLine(o.GetType().Name);     // Int32, String, Single, Enemy
```

这在泛型出现之前是写通用容器的唯一办法（老的 `ArrayList` 就是装 `object` 的）。现在有了泛型（5.1 篇），应该用 `List<T>`，不再需要它。

## object 的四个方法

| 方法 | 作用 | 通常要不要重写 |
| --- | --- | --- |
| `ToString()` | 返回对象的文字描述，默认是类型名 | 常重写，方便 `Debug.Log` 输出 |
| `Equals(object)` | 判断"相等" | 值语义的类型需要重写 |
| `GetHashCode()` | 返回哈希码，用于字典和集合 | 重写 `Equals` 时必须一起重写 |
| `GetType()` | 返回运行时真实类型 | 不能重写 |

```csharp
class Item
{
    public int id;
    public string name;

    public override string ToString() => $"[{id}] {name}";            // override 见 4.3

    public override bool Equals(object obj) => obj is Item other && other.id == id;
    public override int GetHashCode() => id.GetHashCode();
}

Item x = new Item { id = 1, name = "铁剑" };
Item y = new Item { id = 1, name = "铁剑" };
Console.WriteLine(x);                          // [1] 铁剑
Console.WriteLine(x == y);                     // False：== 默认比较引用
Console.WriteLine(x.Equals(y));                // True：我们重写的比较
Console.WriteLine(ReferenceEquals(x, y));      // False
```

要点：对 `class`，`==` 默认比较是否同一个对象；`Equals` 可以按业务含义比较内容。重写 `Equals` 必须同时重写 `GetHashCode`，保证"相等的对象哈希码一定相同"，否则放进 `Dictionary`、`HashSet` 后会查不到。

## 装箱与拆箱

```csharp
int hp = 100;
object boxed = hp;          // 装箱：堆上创建一个盒子，把 100 拷进去
int back = (int)boxed;      // 拆箱：把盒子里的值拷出来，类型必须精确匹配

// long wrong = (long)boxed;   // InvalidCastException：盒子里是 int，不能直接拆成 long
long ok = (int)boxed;          // 先拆成 int 再隐式转 long
```

![int 装箱时在堆上新建盒子保存副本，拆箱时必须按原类型取出](/qmx-Gameknowledge/assets/csharp/boxing.svg)

装箱会**分配堆内存**。偶尔一次无所谓，但在每帧执行的循环里，每次装箱都产生垃圾，累积后引发 GC 卡顿。以下是常见的隐藏装箱位置：

```csharp
string s = string.Format("{0} {1}", hp, 3.5f);   // 参数是 object，值类型被装箱
object key = hp;                                 // 显式装箱
IComparable cmp = hp;                            // 值类型赋给接口变量，也会装箱
```

避免办法：用泛型容器（`List<int>` 不装箱）、用 `int.ToString()` 而不是拼 `object`、避免把 `struct` 放进 `object` 变量。第 2.5 篇提到的"把 struct 当接口用会装箱"就是这里。

## sealed：禁止继承

```csharp
sealed class FinalBoss : Enemy
{
    public FinalBoss() : base("魔王", 9999) { }
}

// class SuperBoss : FinalBoss { }     // 编译错误：FinalBoss 是密封类
```

使用场景：

1. 设计上不希望被扩展（工具类、安全相关类）。
2. `sealed` 类在某些情况下虚调用可以被优化，但对一般游戏逻辑来说差别很小。

`struct` 和静态类天然不能被继承。

## 在 Unity 里用到它

- Unity 自己也有一个"万物之父"：`UnityEngine.Object`，`GameObject`、`Component`、`ScriptableObject` 都继承它。它重载了 `==`，对象被销毁后与 `null` 比较会得到 `true`，所以对 Unity 对象判空用 `!= null`。
- `Debug.Log(obj)` 实际调用的是 `obj.ToString()`，重写 `ToString` 能让日志一眼看懂。
- 装箱产生的垃圾可以在 Profiler（Window → Analysis → Profiler）的 CPU 模块里，按 GC Alloc 列排序找到。

## 动手试试

> **代码归属**：`【实验代码】`。本段只放进 `Assets/Speedrun/Labs/` 临时验证；要进入小游戏主线，请跟随后文或目录中的 `【主线实践】` 文章，在 `Assets/Speedrun/Game/` 重新接入并完成验收。

```csharp
using UnityEngine;

public class Item
{
    public int id;
    public string name;
    public override string ToString() => $"[{id}] {name}";
}

public class BoxDemo : MonoBehaviour
{
    void Start()
    {
        Debug.Log(new Item { id = 1, name = "铁剑" });     // 输出 [1] 铁剑，而不是类型名

        object boxed = 100;                                // 装箱
        Debug.Log((int)boxed);                             // 拆箱：成功
        Debug.Log((long)boxed);                            // 取消注释试试：InvalidCastException
    }
}
```

先把最后一行注释掉运行，再取消注释，看拆箱类型不匹配时的报错，并改成 `(long)(int)boxed` 修复。

## 项目应用决策：object 是边界工具，不是游戏数据模型

日志、编辑器工具或需要接收任意值的基础设施可能使用 `object`；战斗、库存和状态逻辑应保持明确类型，避免装箱、拆箱和运行时类型判断。`UnityEngine.Object` 还带有引擎生命周期语义，不能和普通 C# `object` 混为一谈。

验收时在 Profiler 中观察把结构体放进非泛型集合的分配，再改为泛型集合；比较一个已销毁 Unity 对象和普通 null 的行为，确认判断方式来自对象所属运行时，而不是凭经验套用。

## 常见坑

- 以为 `==` 对 `class` 比较内容，实际比较的是引用。
- 重写了 `Equals` 却没有重写 `GetHashCode`，字典里取不到值。
- 拆箱时类型不精确，抛 `InvalidCastException`。
- 在 `Update` 里用 `string.Format` 或旧式 API 反复装箱。
- 重写 `Equals(object obj)` 时没有先判断 `obj` 的类型，直接强转，传入别的类型就抛异常（上面用 `obj is Item other` 一步完成判断与转换）。

下一篇：[多态、抽象类与接口](../03-多态抽象类接口/)。
