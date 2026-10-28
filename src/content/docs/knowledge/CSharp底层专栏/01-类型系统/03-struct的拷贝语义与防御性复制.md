---
title: "1.3 struct 的拷贝语义与防御性复制"
description: 可变 struct 的陷阱、readonly struct 与 in 参数、防御性复制的触发条件，foreach 与属性/索引器里的隐式拷贝，以及 ref 局部与 ref 返回如何消除拷贝。
sidebar:
  order: 3
---

> 适用版本：C# 7.2 引入 `readonly struct`、`in`、`ref readonly`；C# 8 引入 `readonly` 成员；Unity 6 的 C# 9.0 全部支持。防御性复制由编译器在 IL 层面插入，三种运行时一致；JIT 能否把多余拷贝优化掉则因运行时而异。

## 要点

- struct 的每次"读取到一个新位置"都是拷贝：赋值、传参、返回、属性 getter、索引器、`foreach` 迭代变量、捕获。
- 对 `readonly` 字段、`in` 参数、`ref readonly` 局部变量调用**非 readonly** struct 的方法时，编译器为了保证不被修改，会先拷贝一份再在副本上调用，这叫防御性复制。
- 把 struct 声明为 `readonly struct`（或给不修改状态的成员加 `readonly`），编译器就确认调用不会修改自身，不再复制。
- 可变 struct 容易产生"修改没生效"的 bug。除非是 `Enumerator` 这类刻意设计，游戏数据 struct 建议优先写成不可变，或只通过 `ref` 修改。
- `ref` 局部、`ref` 返回、`Span<T>`、`CollectionsMarshal.AsSpan` 可以拿到元素地址，是在托管侧"原地修改"数据的手段。

## 哪些操作会拷贝

```csharp
struct Stats { public int Hp, Atk, Def; }

class Unit
{
    public Stats S;                        // 字段
    public Stats Prop { get; set; }        // 属性
    public Stats this[int i] => S;         // 索引器返回拷贝
}

var u = new Unit();
u.S.Hp = 10;           // OK：字段是变量，原地修改
u.Prop.Hp = 10;        // 编译错误 CS1612：属性返回的是临时拷贝
var list = new List<Stats> { default };
list[0].Hp = 10;       // 编译错误 CS1612：List 索引器返回拷贝
var arr = new Stats[1];
arr[0].Hp = 10;        // OK：数组索引是 ldelema，取的是元素地址
```

编译错误 CS1612 实际上是编译器在保护你：既然修改的是临时副本，不如直接报错。真正危险的是**没有报错**但语义也不符合直觉的场景，下面三种最常见。

### 场景一：通过接口或方法修改，对象被复制

```csharp
struct Timer { public float T; public void Tick(float dt) => T += dt; }

class Holder { public readonly Timer Timer; }   // readonly 字段

var h = new Holder();
h.Timer.Tick(1f);   // 编译通过，但 Tick 作用在防御性副本上，h.Timer.T 仍为 0
```

`Tick` 不是 `readonly` 方法，编译器无法确定它不修改 `this`，而字段是 `readonly`，所以先 `ldfld` 把值复制到临时变量，再对临时变量调用 `Tick`。IL 示意：

```
ldarg.0
ldfld  valuetype Timer Holder::Timer     // 拷贝出整个值
stloc.0
ldloca.s 0                                // 取副本地址
ldc.r4 1
call instance void Timer::Tick(float32)   // 修改的是副本
```

### 场景二：foreach 的迭代变量是只读副本

```csharp
var arr = new Stats[3];
foreach (var s in arr)
{
    s.Hp = 1;        // 编译错误 CS1654：迭代变量是只读的
}
```

编译器禁止修改。想原地改，要用 `for` 加索引，或 `foreach (ref var s in span)`（`Span<T>` 与数组的 `ref` 迭代，C# 7.3 起对 `Span<T>` 可用；对数组可写成 `foreach (ref var s in arr.AsSpan())`）。

遍历 `List<Stats>` 时迭代变量也是拷贝，若 `Stats` 很大，`foreach` 每个元素拷贝一次。在热路径用 `CollectionsMarshal.AsSpan(list)`（.NET 5+；Unity 的 .NET Standard 2.1 API 是否包含需验证，待核实），或换成数组/`NativeArray`。

### 场景三：可变 struct 的枚举器

`List<T>.Enumerator` 是 struct，`MoveNext` 会修改自身状态。下面写法会死循环：

```csharp
var e = list.GetEnumerator();       // e 是局部变量，OK
while (e.MoveNext()) { ... }        // 作用在 e 本身

class Bag { public List<int>.Enumerator E; }
// 如果 E 是 readonly 字段，E.MoveNext() 会在副本上执行，永远停在起点
```

这就是经典的"不要把可变 struct 存在 readonly 字段里"。

## 防御性复制的触发条件

编译器在以下情况为 struct `S` 的实例成员调用插入拷贝：

| 调用对象 | 是否可能复制 |
|---|---|
| `in S p` 参数上调用成员 | 若 `S` 不是 `readonly struct` 且成员未标 `readonly`：复制 |
| `readonly` 字段上调用成员 | 同上 |
| `ref readonly` 局部或返回值上调用成员 | 同上 |
| 属性 getter 返回值上调用成员 | 本来就是临时副本，不叫防御性复制，但同样是拷贝 |
| 普通局部变量、非 readonly 字段、数组元素 | 不复制 |

`in` 参数本想避免拷贝，如果 `S` 不是 `readonly struct`，每个成员调用都可能复制一次，比按值传参还慢。这是最常见的 `in` 误用。

解决办法：

```csharp
readonly struct Stats2
{
    public readonly int Hp, Atk, Def;
    public Stats2(int hp, int atk, int def) { Hp = hp; Atk = atk; Def = def; }
    public int Power => Atk * 2 + Def;             // 不修改状态，无需复制
    public Stats2 WithHp(int hp) => new(hp, Atk, Def);  // C# 9 目标类型 new
}

static int Calc(in Stats2 s) => s.Power;   // 不复制，传的是地址
```

对于不能整体改成 `readonly struct` 的类型（比如 Unity 的 `Vector3` 是可变 struct，字段公开可写），可以对不修改状态的方法/属性加 `readonly` 修饰（C# 8）：

```csharp
struct Acc
{
    public float Sum;
    public readonly float Average(int n) => Sum / n;   // 编译器保证不修改 this
    public void Add(float v) => Sum += v;
}
```

C# 8 起，在 `readonly` 成员内对 `this` 的写入会产生编译错误，所以编译器才可以放心地省掉复制。

## ref 局部与 ref 返回

```csharp
ref Stats Find(Stats[] arr, int id)
{
    for (int i = 0; i < arr.Length; i++)
        if (arr[i].Hp == id) return ref arr[i];      // 返回元素地址
    throw new KeyNotFoundException();
}

ref var s = ref Find(arr, 3);   // s 是元素的别名
s.Hp += 5;                      // 直接修改数组里的元素
```

`ref` 返回的目标必须在方法返回后仍然有效（编译器做逃逸检查，叫 ref safety）：数组元素、字段可以，局部变量不行。

要点：

- `ref` 局部变量初始化后默认绑定在同一位置，C# 7.3 起可以用 `s = ref other` 重新绑定。
- 数组在 GC 压缩移动对象时，托管指针（`ref`）会被 GC 追踪并更新，所以 `ref` 是安全的；原始指针 `T*` 则需要 `fixed`。见第 2 章。
- 在 Unity 里与 `NativeArray<T>` 配合，用 `ref` 索引器的变体或 `UnsafeUtility.ArrayElementAsRef<T>` 原地修改元素，避免读-改-写的两次拷贝。

## 大小、拷贝成本与选择

经验阈值：16 字节以内按值，超过考虑 `in`/`ref`。实测要用基准而不是凭经验，因为 JIT 的 struct promotion 和内联会改变结果。这里给的是方法而不是数字：

1. 用 BenchmarkDotNet（CoreCLR）或 Unity Profiler 的 Deep Profile/自写计时（Unity）。
2. 同时测"按值""`in`""`ref`"三种签名。
3. 检查 `in` 版本是否因为非 readonly 而变慢，对照 IL 里有没有 `ldobj`/`stloc` 的复制序列。

IL2CPP 上，C++ 编译器（clang）常能消除多余拷贝，Mono JIT 做得较少。因此结论在 IL2CPP 与 Mono 上可能不同，要分别测。

## 与 C++ 对照

- `readonly struct` + `in` 相当于 `const T&` 参数；但 C++ 的 `const` 是**类型系统里的传递属性**，`const` 对象只能调用 `const` 成员函数，编译器对违反直接报错；C# 的 `in` 参数调用非 `readonly` 成员则选择"悄悄复制"，语义安全但性能不透明。
- C++ 的 `const T&` 可能绑定临时对象并延长其生命周期，C# 的 `ref` 局部不能指向临时对象，因此没有悬空问题（由 ref safety 保证）。
- C# 没有移动语义；"把大 struct 的所有权转给别人而不拷贝"只能通过 `ref`/指针。
- `Span<T>` 和 `ref struct` 相当于带编译器生命周期检查的 `std::span` / 受限的引用包装。

## 常见坑

1. **`readonly` 字段加可变 struct = 隐形复制**。要么字段去掉 `readonly`，要么类型改成 `readonly struct`。
2. **`in` 参数配合普通 struct**。给 struct 加 `readonly` 或让成员标 `readonly`。
3. **属性里返回大 struct**。每次读属性拷贝一次；热路径提供 `ref readonly` 返回的方法。
4. **在 `List<T>` 中放可变 struct 并"就地修改"**：必须 `var v = list[i]; v.X = 1; list[i] = v;`，三次拷贝，或改用数组/`Span`。
5. **字典里的 struct 值**：`dict[key].X = 1` 编译错误；`TryGetValue` 取出的也是拷贝；.NET 6+ 的 `CollectionsMarshal.GetValueRefOrNullRef` 能拿到引用，Unity 的 BCL 可能没有，待核实。
6. **Unity 的 `Vector3` 等公开可变字段**：`transform.position.x = 1` 编译错误（属性返回拷贝），是 Unity 最经典的 CS1612 场景。

## 面试追问

**Q：什么是防御性复制？什么时候发生？**
编译器为了保证 `readonly` 字段、`in` 参数、`ref readonly` 变量不被修改，在对其调用非 readonly 的 struct 成员前，先把值复制到临时变量，再对副本调用。避免方法：struct 声明为 `readonly struct`，或把不修改状态的成员标 `readonly`。

**Q：`in` 参数一定比按值传递快吗？**
不一定。小 struct（≤16 字节）按值传递可能走寄存器，`in` 反而多了一次间接访问；非 readonly 的大 struct 用 `in` 还会因为防御性复制变得更慢。

**Q：为什么 `list[0].X = 1` 编译错误，而 `arr[0].X = 1` 可以？**
`List<T>` 索引器是方法调用，返回 `T` 的拷贝，改拷贝没意义；数组元素访问编译成 `ldelema`，得到元素的地址，直接修改。

**Q：`ref return` 的安全性怎么保证？**
编译器的 ref safety 分析要求返回的引用所指向的存储在调用方仍有效，如堆上对象的字段、数组元素、`ref` 参数；返回局部变量的引用会编译失败。GC 压缩时托管引用会被更新，不会悬空。

**Q：为什么说可变 struct 是"邪恶的"？**
因为拷贝语义让修改可能作用于副本，行为依赖于存储位置（局部变量、字段、`readonly` 字段、属性返回值），难以推理。游戏里为了性能使用可变 struct 时，应限定在数组原地修改或 `ref` 传递的范围内。

## 参考资料

- [Write safe and efficient C# code（in、ref readonly、readonly struct）](https://learn.microsoft.com/dotnet/csharp/write-safe-efficient-code)
- [readonly struct - C# 8 readonly members](https://learn.microsoft.com/dotnet/csharp/language-reference/builtin-types/struct#readonly-instance-members)
- [Compiler Error CS1612](https://learn.microsoft.com/dotnet/csharp/misc/cs1612)
- [Ref safety（ref 返回与逃逸规则）](https://learn.microsoft.com/dotnet/csharp/language-reference/statements/declarations#ref-locals)
