---
title: "3.4 GC.Alloc 来源与零 GC 写法"
description: 按编译器与运行时的真实行为整理 Unity 里 GC.Alloc 的常见来源、对应的规避写法，并给出可落地的零 GC 编码规范、Profiler 定位流程和自动化回归断言。
sidebar:
  order: 4
---

> 适用版本：Unity 6（6000.x，C# 9.0 语言版本，Mono / IL2CPP）。涉及编译器行为的条目（委托缓存、foreach 枚举器）依赖 Unity 随附的 Roslyn 版本；旧版 Unity（2017 以前的 mcs 编译器）的"foreach 装箱"之类历史坑不在此展开，标"待核实"的是我没有在当前版本上验证过的条目。

## 要点

- 在 Unity 的 Boehm GC 下，GC 的代价由存活堆决定，频率由分配速率决定（见 3.3）。零 GC 的目标是让**稳态帧**（Update 循环）的分配接近 0，而不是消灭一切分配。
- 托管堆分配只有三类来源：`new` 引用类型、值类型装箱、编译器隐式生成的对象（闭包、迭代器状态机、委托、params 数组、字符串拼接）。隐式的最容易漏。
- 先测后改：Profiler CPU Usage 的 Hierarchy 视图按 GC Alloc 列排序，再用 Call Stacks 或 Deep Profile 定位调用点。
- 用 `ProfilerRecorder` 把"某段代码零分配"写成自动化测试，防止回归。
- 初始化、加载、场景切换允许分配；稳态循环不允许。

## 来源清单与规避写法

| 来源 | 为什么分配 | 规避 |
|---|---|---|
| 值类型装箱 | 值类型赋给 `object` / 接口变量；`string.Format("{0}", intValue)` 的 `object` 参数；非泛型集合 `ArrayList` / `Hashtable` | 用泛型集合；泛型约束 `where T : struct, IFoo` 代替接口形参；插值前先 `ToString()` 并缓存，或用不分配的格式化路径 |
| 默认 `Equals` / `GetHashCode` 的 struct 当字典键 | `ValueType.Equals` 的默认实现通过反射比较字段并装箱参数；`EqualityComparer<T>.Default` 对未实现 `IEquatable<T>` 的 struct 走装箱 | struct 实现 `IEquatable<T>` 并重写 `Equals(object)`、`GetHashCode` |
| 枚举做 `Dictionary` 键 | 在某些运行时版本里，默认比较器对枚举会装箱（待核实当前 Unity 版本） | 传自定义 `IEqualityComparer<TEnum>`，或把枚举转成 int 做键 |
| 捕获变量的 lambda / 局部函数 | 编译器生成闭包类（堆对象）+ 委托对象；每次执行到捕获点都会分配 | 不捕获：把状态作为参数传入（`static` lambda、显式 state 参数）；热路径用预先创建的委托字段 |
| 方法组转委托 | `list.Sort(Compare)`、`button.onClick.AddListener(OnClick)` 这类转换，C# 9 下每次执行都 `new` 一个委托（C# 11 起才缓存静态方法组转换） | 把委托存在字段里复用；订阅一次 |
| 事件 `+=` / `-=` | 委托是不可变的，`Delegate.Combine/Remove` 每次生成新的委托对象（订阅数组） | 订阅发生在初始化阶段，不在每帧 |
| 字符串拼接与格式化 | `string` 不可变；`+`、`Substring`、`Split`、`Replace`、`ToString`、`$"..."` 都产生新对象 | 缓存常用字符串；UI 文本用 `TMP_Text.SetText(string, float)` 一类不拼接的重载，或 `StringBuilder` 复用；比较用 `string.Equals(..., Ordinal)` 而非构造新串 |
| `Object.name`、`GameObject.tag` | 每次访问都从原生层拷贝出一个新的托管字符串 | 比较标签用 `CompareTag`；名字在初始化时读取并缓存 |
| `params` 方法 | 调用方每次隐式 `new T[]` | 提供固定参数个数的重载（`Foo(a)`、`Foo(a, b)`）；或传入复用数组 |
| 协程 | `StartCoroutine` 会分配迭代器状态机 + `Coroutine` 对象；`yield return new WaitForSeconds(x)` 每次 new 一个等待对象；`yield return 1` 装箱 | 缓存 `WaitForSeconds` / `WaitForEndOfFrame` 实例；`yield return null` 不分配；高频逻辑不用协程，改状态机 + Update 计时 |
| 迭代器方法 `IEnumerable<T> Foo() { yield return ... }` | 编译器生成状态机类 | 热路径改用 `List<T>` 参数填充，或手写 struct 枚举器 |
| `foreach` 遍历接口类型 | 遍历 `List<T>` / 数组 / 带 struct 枚举器的类型不分配；通过 `IEnumerable<T>` 接口变量遍历会把 struct 枚举器装箱 | 声明变量时保持具体类型（`List<T>`），不要上转成 `IEnumerable<T>`；当前 Unity 的 Roslyn 编译器对具体类型 foreach 不再装箱 |
| LINQ | 每个操作符分配枚举器对象与委托；`ToList`、`ToArray` 分配集合 | 热路径禁用 LINQ，写 for 循环 |
| Unity API 返回数组 | `GetComponents<T>()`、`GetComponentsInChildren<T>()`、`Physics.RaycastAll`、`Physics.OverlapSphere`、`Input.touches`、`mesh.vertices` / `normals` / `uv` 每次返回新数组（拷贝） | 使用重载 `GetComponents(List<T>)`、`Physics.RaycastNonAlloc`、`OverlapSphereNonAlloc`、`Input.GetTouch(i)`、`mesh.GetVertices(List<Vector3>)` 或 Mesh API 的 `MeshData` |
| `Renderer.material` / `materials` | 第一次访问会实例化材质副本（原生分配）并返回新数组 | 用 `sharedMaterial`，或 `MaterialPropertyBlock` |
| `Debug.Log` | 参数装箱 + 字符串格式化，Release 构建仍会执行 | 用 `[Conditional("UNITY_EDITOR")]` 或自定义日志宏整体剔除调用 |
| 反射 `MethodInfo.Invoke` | 参数打包成 `object[]` 并装箱返回值 | 避免热路径反射；预编译委托（`CreateDelegate`） |
| `Enum.ToString()`、`Enum.HasFlag` | `ToString` 返回新字符串；`HasFlag` 在部分运行时会装箱（待核实） | 缓存名称表；用位运算 `(flags & mask) != 0` |
| `throw` / 异常 | 异常对象与栈信息分配，开销远大于普通分配 | 异常不要用于控制流 |
| `async` / `Task` | 状态机、`Task` 对象、闭包 | 见"语言机制的隐藏分配"章节 |

> 编译器相关条目的结论受 Unity 随附的 C# 编译器版本影响。想确认一条规则在你的版本上是否成立，最可靠的办法是写最小例子，在 Profiler 里看 GC Alloc 列，而不是背结论。

### 最容易被误判的几项

1. `yield return null` 不分配：`null` 是引用，不需要装箱。分配的是 `yield return 0`（装箱 int）和 `new WaitForSeconds`。
2. `Vector3`、`Quaternion` 等 struct 不会分配。分配的是你把它们塞进 `object`、接口、`Dictionary<object, ...>`、`params object[]`。
3. 非捕获 lambda 不是每次分配。Roslyn 会把它缓存在静态字段里（编译器生成的 `<>c` 类），只有捕获 `this` 或局部变量时才每次生成闭包。
4. 字符串字面量是驻留的，不分配；运行期拼出来的字符串才分配。

## 定位流程

1. 在目标设备的开发版 Player 上连接 Profiler，录制稳态场景几百帧。
2. CPU Usage 模块切到 Hierarchy，按 **GC Alloc** 列降序，筛出分配最多的帧与方法。
3. 打开 Call Stacks（Profiler 工具栏的 Call Stacks 选项）捕获 GC.Alloc 的调用栈；或临时启用 Deep Profile 看逐函数分配（Deep Profile 本身开销大，数值只作定性判断）。
4. 修复后重新录制，对比同一场景的 GC Alloc 总量。
5. 需要看趋势时，Memory 模块的 "GC Allocated In Frame"、"GC Used Memory"、"GC Reserved Memory" 计数器能画出每帧分配量曲线。

## 零 GC 的编码规范

下面是可直接放进团队规范的一组规则，适用于**每帧都会执行**的代码路径：

1. 稳态循环里不出现 `new` 引用类型（`new List<>()`、`new WaitForSeconds()`、`new int[n]`、`new Foo()`）。需要容器时，字段持有并 `Clear()`。
2. 不装箱：不把值类型赋给 `object` / 非泛型接口；泛型约束代替接口形参。
3. 不用 LINQ、不用 `params`、不在热路径拼接字符串。
4. Unity API 一律用 `NonAlloc` / `List<T>` 重载；`GetComponent` 结果在 `Awake` 缓存。
5. 回调与委托：订阅一次，不在帧循环里 `+=`/`-=`；lambda 不捕获变量，或在初始化阶段创建一次后复用。
6. 字典键与集合元素的 struct 必须实现 `IEquatable<T>`；枚举键传自定义比较器（待核实当前版本是否必要）。
7. 临时缓冲：小的用 `stackalloc`（`Span<T>`），大的用对象池或 `NativeArray`（`Allocator.Temp`/`TempJob`），不要每帧 new 数组。
8. 把分配集中到边界：加载、切场景、关卡开始；在这些点之后主动 `GC.Collect()`。

示意代码（每帧收集范围内的碰撞体，零分配）：

```csharp
using System.Collections.Generic;
using UnityEngine;

public sealed class ProximityScan : MonoBehaviour
{
    const int MaxHits = 64;

    readonly Collider[] _hits = new Collider[MaxHits];      // 预分配，长期复用
    readonly List<Enemy> _enemies = new List<Enemy>(MaxHits);

    [SerializeField] float radius = 8f;
    [SerializeField] LayerMask mask;

    void Update()
    {
        int n = Physics.OverlapSphereNonAlloc(transform.position, radius, _hits, mask);
        _enemies.Clear();                                    // Clear 不释放底层数组
        for (int i = 0; i < n; i++)
        {
            if (_hits[i].TryGetComponent(out Enemy e))       // TryGetComponent 不分配（失败时也不会像 GetComponent 一样产生编辑器内的字符串垃圾）
                _enemies.Add(e);
        }
    }
}

public sealed class Enemy : MonoBehaviour { }
```

> `TryGetComponent` 与 `GetComponent` 的区别：按 Unity 手册，组件不存在时 `GetComponent` 在 Editor 里会为错误信息分配内存，`TryGetComponent` 不会。该差异只在 Editor 内出现。

## 用自动化测试防回归

用 `ProfilerRecorder` 读取每帧 GC 分配量，写成 PlayMode 测试。计数器名称为 Memory 类别下的 `GC Allocated In Frame`：

```csharp
using System.Collections;
using NUnit.Framework;
using Unity.Profiling;
using UnityEngine.TestTools;

public class ZeroGcTests
{
    [UnityTest]
    public IEnumerator SteadyState_AllocatesNothing()
    {
        // 预热：让对象池、缓存、JIT/IL2CPP 的一次性分配先发生
        for (int i = 0; i < 30; i++) yield return null;

        using var rec = ProfilerRecorder.StartNew(ProfilerCategory.Memory, "GC Allocated In Frame");
        long worst = 0;
        for (int i = 0; i < 120; i++)
        {
            yield return null;
            if (rec.Valid && rec.LastValue > worst) worst = rec.LastValue;
        }
        Assert.AreEqual(0, worst, "稳态帧出现了托管分配，请在 Profiler 中用 Call Stacks 定位。");
    }
}
```

要点：测试需要在稳态（预热后）进行；在 Editor 里测量会混入编辑器自身分配，更可靠的是在 Development Player 里跑；断言用"最坏帧"而不是平均值，因为一次分配就足以触发 GC。

## 不要走极端

- 零 GC 的成本是可读性与开发速度：LINQ、闭包、字符串插值在非热路径（UI 打开时、设置界面）完全可以用。
- 每个池子都是一份需要维护的状态机（见 3.5）。先用 Profiler 找最大的几个来源，处理掉 80% 的分配再停手。
- 分配很多但存活堆很小，GC 的单次暂停本来就短；真正致命的是存活堆大 + 频繁触发的组合。

## 常见坑

- 只在 Editor 里测。Editor 的 Mono 与 Player 的 IL2CPP 在泛型、委托缓存上行为可能不同。
- 把"托管 GC.Alloc 为 0"当作"没有内存问题"：`Texture2D`、`Mesh`、`Material` 等的原生内存分配不计入托管 GC.Alloc，要在 Memory Profiler 里单独看。
- 修复一处又在别处引入同类分配：没有自动化断言。
- 预分配过大的缓冲，把托管堆撑大，反而拉长每次 GC 的标记时间。

## 面试追问

1. Unity 里最常见的 GC.Alloc 来源有哪些，你怎么定位？ 要点：装箱、闭包/委托、字符串、params、协程 `new WaitForSeconds`、返回数组的 Unity API、LINQ；用 Profiler Hierarchy 的 GC Alloc 列 + Call Stacks；ProfilerRecorder 做回归。
2. 什么情况下 lambda 会分配？ 要点：只有捕获了局部变量或 `this` 时才生成闭包对象；非捕获 lambda 被编译器缓存成静态委托；方法组转换在 C# 9 下每次都新建委托。
3. `foreach` 一定会分配吗？ 要点：遍历数组或具体类型的 `List<T>` 用 struct 枚举器，不分配；通过 `IEnumerable<T>` 接口遍历会装箱枚举器；`yield` 迭代器方法有状态机分配。
4. 为什么 struct 做字典键要实现 `IEquatable<T>`？ 要点：默认 `ValueType.Equals` 用反射并装箱，慢且分配；实现 `IEquatable<T>` 后泛型比较器走强类型路径，无装箱。
5. 协程和 `Update` 状态机，在 GC 上有什么差别？ 要点：协程有迭代器状态机和 `Coroutine` 对象，等待对象每次 new；`Update` + 计时字段零分配，但可读性差；折中是缓存等待对象并控制协程数量。
6. 零 GC 是不是越彻底越好？ 要点：不是。目标是稳态路径；加载与 UI 允许分配；每个池和缓存都带来维护与状态残留风险。

## 参考资料

- Unity Manual：Optimizing your code for managed memory，https://docs.unity3d.com/6000.0/Documentation/Manual/performance-optimizing-code-managed-memory.html
- Unity Manual：Tracking garbage collection allocations，https://docs.unity3d.com/6000.0/Documentation/Manual/performance-track-garbage-collection.html
- Unity Scripting API：Unity.Profiling.ProfilerRecorder，https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Unity.Profiling.ProfilerRecorder.html
- Microsoft Learn：Boxing and unboxing，https://learn.microsoft.com/en-us/dotnet/csharp/programming-guide/types/boxing-and-unboxing
