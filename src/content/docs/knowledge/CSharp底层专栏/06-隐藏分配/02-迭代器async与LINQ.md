---
title: "6.2 迭代器、async 与 LINQ 的隐藏分配"
description: 状态机的生成与装箱时机、Unity 协程的分配点、ValueTask、LINQ 的对象链、foreach 在不同容器上的行为,以及字符串拼接、params、枚举装箱。
sidebar:
  order: 2
---

> 适用版本:编译器行为以 Roslyn 为准;Unity 6000.x 的 C# 版本为 9.0,没有 C# 10 的 interpolated string handler 与 C# 13 的 `params Span<T>`。CoreCLR 的运行时库细节(如 `AsyncStateMachineBox`、`PoolingAsyncValueTaskMethodBuilder`)在 Unity 的 Mono/IL2CPP 类库中不一定存在,标"待核实"处需要在目标 Unity 版本上验证。

## 要点

- `yield return` 方法被编译成一个实现 `IEnumerable<T>`/`IEnumerator<T>` 的**类**;调用它分配一个对象,枚举时通过接口调用,永远不是 struct 枚举器。Unity 协程本质上就是这样的迭代器。
- `async` 方法在 Release 下被编译成 **struct** 状态机,只有在第一次遇到未完成的 `await` 时才装箱到堆;Debug 下状态机是 **class**,一进方法就分配。所以编辑器(默认 Debug 优化)里测到的分配可能比 Player 里多。
- 同步完成的 `async ValueTask<T>` 路径零分配;`async Task<T>` 同步完成时仍需要一个 `Task<T>` 结果对象(少量值有缓存)。
- LINQ 每个操作符几乎都是"一个迭代器对象加一个委托",捕获变量时再加闭包;排序类操作符还要缓冲整个序列。
- `foreach` 是模式匹配:类型上有公共 `GetEnumerator()` 就用它。`List<T>`、`Dictionary<K,V>` 等返回 struct 枚举器,零分配;一旦通过 `IEnumerable<T>` 接口变量访问,struct 枚举器被装箱。
- 字符串拼接、`params object[]`、枚举作字典键或调用 `ToString/HasFlag`,是客户端里最常见的小对象分配来源。

## 迭代器状态机

```csharp
IEnumerable<int> Range(int n)
{
    for (int i = 0; i < n; i++) yield return i;
}
```

编译器生成(示意):

```csharp
sealed class <Range>d__0 : IEnumerable<int>, IEnumerator<int>
{
    int <>1__state;          // 状态机当前位置
    int <>2__current;
    int <>l__initialThreadId;
    int n;                   // 参数
    int <>3__n;              // 参数备份(供 GetEnumerator 复制新实例用)
    int <i>5__1;             // 被提升成字段的局部变量

    bool MoveNext() { switch (<>1__state) { /* 每个 yield 对应一个 case */ } }
    IEnumerator<int> GetEnumerator()
    {
        // 同线程且尚未开始枚举:返回自身,省一次分配
        if (<>1__state == -2 && <>l__initialThreadId == Environment.CurrentManagedThreadId)
        { <>1__state = 0; return this; }
        return new <Range>d__0(0) { n = <>3__n };
    }
}
```

要点:

- 调用 `Range(10)` 就 `new` 一个状态机对象,里面所有局部变量和参数都变成字段。同线程第一次 `foreach` 复用同一个对象当枚举器,因此一次 `foreach` 通常只有一次分配;同一个 `IEnumerable` 被枚举第二次或跨线程枚举时会再分配。
- 每一步都是 `IEnumerator<int>.MoveNext()`/`Current` 的**接口调用**,不能内联。`List<T>` 的 struct 枚举器没有这些开销。
- 迭代器内部不能有 `ref` 局部变量、不能使用 `Span<T>` 等 ref struct 局部(跨 yield 的变量会被提升进类,见 2.4 节)。

### Unity 协程

Unity 的 `StartCoroutine` 接收一个 `IEnumerator`,它由迭代器方法生成,每次调用协程方法就分配一个状态机对象,再加上 Unity 内部的 `Coroutine` 对象。常见的额外分配点:

| 写法 | 分配 |
|---|---|
| `yield return null` | 无(null 不装箱) |
| `yield return 0` / `yield return someStruct` | 装箱成 `object` |
| `yield return new WaitForSeconds(1f)` | 每次 new 一个对象,应缓存复用 |
| `yield return new WaitForEndOfFrame()` | 同上 |
| `StartCoroutine(Foo())` | 状态机对象加 `Coroutine` 对象 |
| `StartCoroutine("Foo")` | 字符串反射查找,更慢,避免 |

缓存 `WaitForSeconds` 对象并复用是社区共识。协程的状态机类字段里会保留被引用的所有局部变量,协程没跑完就一直持有它们,可能是意外的内存保留来源。

## async 状态机

```csharp
async Task<int> LoadAsync(int id)
{
    var data = await FetchAsync(id);       // 可能挂起
    return Parse(data);
}
```

Roslyn 在 Release 下生成 `struct` 状态机 `<LoadAsync>d__0 : IAsyncStateMachine`,字段包括状态、`AsyncTaskMethodBuilder<int>`、局部变量与 awaiter。调用时:

1. 方法体入口创建这个 struct(在栈上),调用 `builder.Start(ref stateMachine)` 开始执行 `MoveNext`。
2. 如果每个 `await` 的结果都已经完成(同步完成路径),`MoveNext` 一路跑到 return,直接 `SetResult`;没有状态机装箱,只需要返回的 `Task<int>` 结果对象(对 `Task`(非泛型)是缓存的已完成任务,零分配;对 `Task<T>`,.NET 对 `bool`、小整数等少数值有缓存实例,其余需要 new)。
3. 只要某个 `await` 未完成,builder 把状态机**装箱**到堆(CoreCLR 的实现里,装箱后的盒子 `AsyncStateMachineBox<TStateMachine>` 本身继承自 `Task<TResult>`,与返回的 Task 是同一个对象,一次分配搞定;continuation 的 `Action` 委托也缓存在盒子里)。
4. 完成时通过 `SynchronizationContext` 或线程池回到继续点,调用 `MoveNext` 前进。

Debug 配置下状态机生成为 `class`,每次调用 async 方法都会分配,所以 Unity 编辑器默认的 Debug 代码优化模式下,Profiler 里看到的 async 分配比 Player 里多。以 Player(Release)数据为准。

### 其他成本

- `await` 默认捕获 `SynchronizationContext.Current`,Unity 主线程上这是 `UnitySynchronizationContext`,`await` 之后的代码被投递回主线程执行,每次投递会有队列项的开销。`ConfigureAwait(false)` 让后续在线程池线程运行,此时不能碰 Unity API。
- `ExecutionContext` 也会被捕获与还原,存在 AsyncLocal 时更明显。
- 异常路径:`Task` 内部异常包装成 `AggregateException`;`async void` 方法的异常直接抛到同步上下文,Unity 里表现为 Console 报错而不是被调用方捕获。
- Unity 2023.1 起提供 `Awaitable`(池化、专为 Unity 主循环设计),可替代 `Task` 做 `await Awaitable.NextFrameAsync()` 等;具体版本与功能以所用 Unity 手册为准,待核实。第三方 UniTask 通过自定义 async method builder 实现零分配的 async,同样借助 `[AsyncMethodBuilder]` 特性。

### ValueTask

```csharp
public ValueTask<int> ReadAsync()
{
    if (_buffered > 0) return new ValueTask<int>(_buffered);   // 同步完成:无堆分配
    return new ValueTask<int>(ReadSlowAsync());                // 真异步:包装一个 Task
}
```

`ValueTask<T>` 是个 struct,内部是 `object _obj; T _result; short _token`,`_obj` 可能是 null(结果已就绪)、`Task<T>` 或 `IValueTaskSource<T>`(可池化对象)。约定:

- 只能 `await` 一次,不能并发 `await`,不能多次读 `Result`;需要多次使用时调用 `.AsTask()` 转成 `Task`。
- 返回 `ValueTask` 的 async 方法在慢路径仍会装箱状态机;.NET 6 起可用 `[AsyncMethodBuilder(typeof(PoolingAsyncValueTaskMethodBuilder<>))]` 让状态机盒子池化,Unity 的类库里没有,待核实。

只有在"绝大多数调用同步完成"的热点路径上,`ValueTask` 才值得;普通业务返回 `Task` 更简单,且不易误用。

## LINQ

```csharp
var ids = enemies.Where(e => e.Hp > min)       // 捕获 min:闭包加委托
                 .Select(e => e.Id)             // 委托(缓存)
                 .ToList();                     // 新 List
```

这一行至少产生:捕获 `min` 的闭包与委托、`Where` 的迭代器对象、`Select` 的迭代器对象、一个 `List<int>`(加扩容过程中的数组)、枚举器。优化版的 `Where`/`Select` 对 `List<T>`/数组来源有专用迭代器(如 `WhereListIterator`),以节省一层接口开销,但分配并没有消失。

| 操作 | 额外成本 |
|---|---|
| `OrderBy/ThenBy` | 缓冲整个序列、分配 key 数组与排序映射数组 |
| `GroupBy`、`ToDictionary`、`Distinct` | 构建哈希结构 |
| `ToList/ToArray` | 新集合 |
| `Count()`、`First()`、`Any()` | 对 `ICollection<T>`/`IList<T>` 有快速路径;对一般 `IEnumerable<T>` 需要创建枚举器并遍历 |
| `Sum/Max/Min` | 通常只需要一个枚举器;来源是 `List<T>` 时通过接口访问,struct 枚举器被装箱 |

在 Unity 里:

- 帧循环里的 LINQ 是 GC 的常客;初始化阶段、编辑器工具、一次性的数据处理可以放心用。
- IL2CPP 下 LINQ 使用大量泛型,值类型的泛型实例若在编译时找不到,会落入慢速的通用路径(见 4.2 节)。涉及自定义 struct 的 `OrderBy<TSource, TKey>` 等调用最需要实测。
- 热路径换成手写 `for` 加预分配的 `List<T>`/数组,配合不捕获的 `static` 比较函数,是最稳妥的写法。

## foreach 在不同容器上的行为

C# 的 `foreach` 不要求实现 `IEnumerable`,编译器按**模式**查找:

1. 类型上有公共可访问的 `GetEnumerator()`,返回的类型有 `MoveNext()` 与 `Current`,就直接用它。
2. 数组被降级成带索引的 `for` 循环。
3. 否则才退到 `IEnumerable<T>`/`IEnumerable` 接口。

```csharp
List<int> list = ...;
foreach (var x in list) { }                   // List<int>.Enumerator(struct),零分配

IEnumerable<int> seq = list;
foreach (var x in seq) { }                    // 调用 IEnumerable<int>.GetEnumerator():struct 枚举器被装箱

Dictionary<int,string> d = ...;
foreach (var kv in d) { }                     // Dictionary.Enumerator(struct),零分配

foreach (Transform child in transform) { }    // Transform 只实现非泛型 IEnumerable,GetEnumerator 返回对象:有分配
```

其他注意:

- 历史上 Unity 旧版 Mono 编译器(Unity 5.5 之前)在 `foreach` 上对 `List<T>` 也会装箱枚举器,造成"每个 foreach 24 字节"的民间说法。Unity 5.5 随编译器升级修复(据发行说明记忆,待核实)。Unity 6 用 Roslyn,不再有这个问题,但通过接口访问仍会装箱。
- 在 `foreach` 里修改集合会让 struct 枚举器的版本号检查失败,抛 `InvalidOperationException`。
- 泛型方法 `void Process<T>(T collection) where T : IEnumerable<int>` 对 struct 类型的 `T` 不会装箱(约束调用),但对 `IEnumerable<int>` 参数会。

## 字符串、params 与枚举

### 字符串

```csharp
string s = a + b + c;                         // 编译为 String.Concat(a, b, c):一次分配结果
string t = "";
for (int i = 0; i < n; i++) t += i;           // 每轮新字符串,总拷贝 O(n^2),且 i 装箱或 ToString
string u = $"HP: {hp} / {max}";               // C# 9:string.Format(format, object, object),hp 与 max 装箱
```

- 插值字符串在 C# 9 下转成 `string.Format`(或在全部为字符串时转成 `String.Concat`);值类型参数装箱成 `object`,还有格式化解析成本。C# 10 的 `DefaultInterpolatedStringHandler` 在 Unity 中不可用,待核实。
- 较新的 Roslyn 对 `string + 值类型` 会生成直接对值类型的 `ToString()` 调用,避免装箱(这一优化的版本归属待核实);无论如何,`ToString()` 本身产出新字符串。
- 解决办法:复用 `StringBuilder`(用 `Append(int)` 等重载不装箱);缓存少量数值字符串;UI 文本用 TextMeshPro 的 `SetText("{0}", value)` 这类不产生托管字符串的重载;日志用条件编译包裹,避免在发布构建里拼接。
- `string.Split`、`Substring`、`Trim` 都产生新字符串;解析场景改用 `ReadOnlySpan<char>`(见 2.4 节)。

### params

```csharp
void Log(string fmt, params object[] args);
Log("x={0} y={1}", x, y);                     // 每次调用:new object[2],x 和 y 各装箱
```

`params T[]` 每次调用新建数组;`params object[]` 再加每个值类型参数装箱。BCL 的做法是为 1~3 个参数提供**固定参数个数的重载**(如 `String.Concat(a, b, c)`),自己的热路径函数也应如此。`Debug.LogFormat` 是典型例子。C# 13 的 `params ReadOnlySpan<T>` 在 Unity 中不可用。

### 枚举

| 写法 | 问题 |
|---|---|
| `e.ToString()` | 每次生成字符串(内部有名称缓存,但返回新字符串或需要查表),不要在热路径使用 |
| `e.HasFlag(F.X)` | 参数类型是 `Enum`,值类型实参装箱;CoreCLR 的 JIT 把它当内联函数处理,Mono 与 IL2CPP 没有这个优化。用 `(e & F.X) != 0` 替代 |
| `Dictionary<MyEnum, V>` | 默认比较器对枚举在旧 Mono 上会走 `object` 比较并装箱,是 Unity 里广为人知的问题;Unity 6 是否仍存在待核实,稳妥做法是以 `int` 为键,或传入自定义 `IEqualityComparer<MyEnum>` |
| `Enum.GetValues(typeof(E))` | 每次返回新数组;缓存起来 |
| 把枚举传给 `object` 参数 | 装箱 |

### 其他常见的 Unity 引擎侧分配(非语言层)

- `gameObject.tag == "Enemy"` 每次返回新字符串,用 `CompareTag`。
- `GetComponents<T>()` 返回新数组或 List,用传入 `List<T>` 的重载。
- `Transform` 的 `foreach` 如上所述,改用 `for` 加 `GetChild`。

## 常见坑

- 以为 `foreach` 总会分配,或总不分配:取决于静态类型是具体集合还是接口。
- 在 Unity 编辑器里看到 async 方法分配很多,就推断 Player 也一样。先切 Code Optimization 到 Release 再测,或直接在 Player 里测。
- 迭代器协程里 `yield return new WaitForSeconds` 在循环中每帧 new。
- 滥用 `ValueTask`,多次 await 或并发 await 同一个实例导致未定义行为。
- 在 `Update` 里写 LINQ 或字符串拼接显示 HUD。
- 热路径调用 `params object[]` 日志函数,即使日志级别被关闭,参数数组与装箱已经发生。

## 面试追问

1. **`yield return` 的方法被编译成什么?为什么说 `foreach` 一个迭代器至少有一次分配?** 要点:一个同时实现 `IEnumerable<T>` 与 `IEnumerator<T>` 的类,局部变量与参数变成字段,`MoveNext` 里是 switch 状态跳转;调用迭代器方法即分配;首次同线程 `GetEnumerator` 复用自身。
2. **async 方法什么时候发生堆分配?** 要点:Release 下状态机是 struct,只有遇到未完成的 await 才装箱(CoreCLR 里盒子本身就是 Task);同步完成路径下对 `Task` 无分配、对 `Task<T>` 看结果缓存;Debug 下状态机是 class,总分配。
3. **ValueTask 比 Task 好在哪?有什么使用约束?** 要点:同步完成路径不分配;内部用 `object _obj` 区分结果就绪、Task 或可池化的 `IValueTaskSource`;只能 await 一次,不能并发,多次使用需 `AsTask`。
4. **`foreach` 遍历 `List<T>` 和遍历 `IEnumerable<T>` 有什么区别?** 要点:模式匹配到 struct 枚举器与走接口装箱的差别;数组被降级为 for;不是所有 foreach 都分配。
5. **LINQ 在游戏帧循环里的问题是什么?怎么替代?** 要点:每个操作符一个迭代器加委托,捕获再加闭包,排序要缓冲;替换为手写 for、预分配集合和不捕获的 static 函数;初始化期可以使用。
6. **`$"HP: {hp}"` 在 Unity 里产生多少分配?** 要点:C# 9 下转为 `string.Format` 或 `Concat`,值类型参数装箱,加结果字符串;可用 StringBuilder、预缓存、TMP 的 `SetText` 重载避免。
7. **`HasFlag` 和 `Dictionary<Enum,...>` 在 Unity 上有什么坑?** 要点:`HasFlag` 参数装箱,CoreCLR 的 JIT 优化在 Mono/IL2CPP 上没有;枚举键的默认比较器在旧版 Mono 上装箱,Unity 6 是否仍然存在需实测;替代方案是位运算与整数键或自定义比较器。

## 参考资料

- Microsoft Learn,Iterators(yield):https://learn.microsoft.com/en-us/dotnet/csharp/iterators
- Microsoft Learn,Asynchronous programming 与 Task-based async pattern:https://learn.microsoft.com/en-us/dotnet/csharp/asynchronous-programming/
- Microsoft Learn,ValueTask 与 IValueTaskSource:https://learn.microsoft.com/en-us/dotnet/api/system.threading.tasks.valuetask-1
- Microsoft Learn,foreach 语句(模式匹配枚举):https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/statements/iteration-statements
- Unity 手册,C# compiler and language version reference:https://docs.unity3d.com/6000.2/Documentation/Manual/csharp-compiler.html
- Unity 手册,IL2CPP limitations(泛型代码共享):https://docs.unity3d.com/6000.0/Documentation/Manual/scripting-restrictions.html
- Unity 手册,Garbage collection best practices:https://docs.unity3d.com/6000.0/Documentation/Manual/performance-garbage-collection-best-practices.html
