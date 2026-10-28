---
title: "4.2 泛型共享与 AOT 限制"
description: CLR 泛型的实例化模型、引用类型共享与值类型特化、IL2CPP 的 generic sharing 与 AOT 无法运行时生成代码带来的限制、link.xml 与裁剪、反射在 IL2CPP 上的坑和规避办法。
sidebar:
  order: 2
---

> 适用版本：CoreCLR 的泛型共享（canonical code）以 .NET 8 为参照；Unity 部分以 Unity 2022 LTS 到 Unity 6 的 IL2CPP 为主，参考官方手册 IL2CPP limitations 与 Unity 博客 IL2CPP Internals: Generic sharing。IL2CPP 的 full generic sharing 等较新特性的引入版本标"待核实"。

## 要点

- C# 泛型是**运行时泛型**，不是擦除：`List<int>` 与 `List<string>` 是不同的运行时类型。区别在于代码如何生成。
- 值类型的每个泛型实例都有独立的机器码（特化），因为大小和布局不同，能内联、无装箱。引用类型的所有实例共享同一份机器码（CoreCLR 中叫 `__Canon` 共享代码），因为引用大小都一样，共享代码通过隐藏的"泛型字典"参数取得实际类型。
- AOT 编译（IL2CPP、Mono AOT、NativeAOT）要求构建时就知道所有会用到的泛型实例。**只有运行时才确定的值类型实例化**（反射 `MakeGenericType`、泛型虚方法的值类型实参等）会失败。
- 规避：让编译器在静态可见的位置出现所需实例（"代码触发"）、避免泛型虚方法与反射构造泛型、把需要的类型用 `link.xml`/`[Preserve]` 保留。
- Unity 里"编辑器正常、真机崩溃"的头号原因之一，就是这类泛型在 Mono JIT 下被运行时即时生成，到了 IL2CPP 缺失。

## 泛型在运行时的实例化模型

以 CoreCLR 为例：

| 泛型实参 | 机器码 | 类型描述 | 特点 |
|---|---|---|---|
| 值类型（`int`、`Vector3`、自定义 struct） | 每个实参各生成一份 | 每个实例独立的 MethodTable | 精确布局、可内联、无装箱 |
| 引用类型（`string`、`object`、任意 class） | 共享一份（`__Canon`） | 每个实例仍有独立 MethodTable | 共享代码需要泛型字典查类型信息 |

引用类型共享的原理：对 `List<string>` 与 `List<Foo>`，字段布局、元素大小、方法的指令序列都完全相同（元素都是 8 字节指针）。只有需要"知道 T 是什么"的操作（`typeof(T)`、`new T[]`、类型转换到 `T`、调用 `T` 的虚方法的某些路径）才需要额外信息，这些通过隐藏参数——泛型字典（generic dictionary）或 MethodTable 里的字典指针——运行时查表取得。因此共享代码比特化代码略慢。

```csharp
static T[] Make<T>(int n) => new T[n];
// 对 T = string：共享代码，需要从字典取 T 的 MethodTable 才能分配数组
// 对 T = int：特化代码，直接用 int[] 的 MethodTable，常量
```

CoreCLR 会在 JIT 时（运行时按需）为值类型实参生成新代码，这在 AOT 里行不通，下面是核心矛盾。

## Mono 的 JIT 与 AOT

- **Mono JIT**（Unity 编辑器、Android/桌面的 Mono 后端）：运行时遇到新的泛型实例，直接 JIT 生成代码；引用类型同样共享代码。基本没有"泛型不可用"的问题。
- **Mono AOT**（早期 iOS 的 Mono 后端）：提前编译，同样遇到值类型泛型实例缺失的问题，Unity 为此长期有"AOT 泛型限制"的文档。现在 iOS 使用 IL2CPP，Mono AOT 在 Unity 里基本退出。

## IL2CPP 的 generic sharing

IL2CPP 在构建时遍历所有程序集，收集泛型实例化（包括由泛型方法调用链推导出的），然后：

1. **引用类型实参**：共享。`List<string>`、`List<GameObject>`、`List<MyClass>` 使用同一份生成的 C++ 方法，类型信息通过 `RGCTX`（Runtime Generic Context）取得。生成的 C++ 方法带 `___` 形式的泛型上下文参数（示意）。
2. **值类型实参**：为每个具体实例生成专用方法。`List<int>`、`List<Vector3>`、`List<MyStruct>` 各有一份。
3. **仍不可知的实例**：若编译期无法枚举（例如运行时用反射构造的值类型实例），IL2CPP 不会生成。较新版本引入了 **full generic sharing**（把值类型实参也走共享的、慢一些的通用路径作为兜底），能让一部分此前会崩溃的场景工作，但性能较差，且覆盖范围有限（具体引入版本与适用场景以官方文档为准，待核实）。

Unity 博客 IL2CPP Internals: Generic sharing implementation 详细解释了 `RGCTX`、共享方法的生成和如何从 `Il2CppClass` 取类型信息。关于"代码触发"的描述，看官方 IL2CPP limitations 页面。

这解释了两个常见现象：

- **包体变大**：每个值类型泛型实例是一份代码。`Dictionary<K,V>` 若 K、V 有大量不同的 struct 组合，膨胀明显。
- **泛型共享的性能代价**：引用类型的共享代码比特化慢一点，通常可忽略；热点上用值类型实例得到特化代码更快。

## AOT 限制：哪些写法会在 IL2CPP 失败

官方 IL2CPP limitations 手册的主要内容归纳（以手册为准）：

1. **没有 JIT**：不能 `System.Reflection.Emit`，不能运行时生成程序集。表达式树的 `Compile()` 退化成解释执行。
2. **泛型虚方法（Generic Virtual Methods）**：虚方法本身带泛型参数，且用值类型实参，且在构建期不能确定调用目标的情形，可能没有生成对应实例。
3. **反射构造泛型**：`typeof(List<>).MakeGenericType(typeof(MyStruct))`，`MethodInfo.MakeGenericMethod(typeof(MyStruct))`，如果代码里没有其他位置直接使用 `List<MyStruct>` 或该泛型方法的 `MyStruct` 版本，实例不存在。
4. **序列化库内部大量使用反射 + 泛型**：JSON/protobuf/MessagePack 等库在 IL2CPP 上需要额外配置（link.xml、AOT 代码生成器）。
5. **`Marshal.GetDelegateForFunctionPointer`/`GetFunctionPointerForDelegate`** 对委托类型的限制，需要静态方法与 `MonoPInvokeCallback`（见 4.1 节）。
6. **被裁剪的代码**：反射或字符串名引用的类型/成员若被 linker 移除，运行时找不到。

典型错误信息：

```
ExecutionEngineException: Attempting to call method 'System.Collections.Generic.List`1[[MyStruct]]::.ctor' for which no ahead of time (AOT) code was generated.
```

具体措辞随版本不同，但都含有 "no ahead of time (AOT) code was generated"（待核实各版本措辞）。

### 复现示例

```csharp
struct Item { public int Id; }

static class Repro
{
    // 没有任何地方直接写 List<Item>，仅通过反射构造
    public static object MakeList()
    {
        var t = typeof(List<>).MakeGenericType(typeof(Item));
        return Activator.CreateInstance(t);   // Mono JIT 正常，IL2CPP 可能失败
    }
}
```

## 规避方法

### 1. 让实例在静态可见处出现

在某个会被编译的位置显式使用该实例，哪怕永远不执行：

```csharp
using UnityEngine.Scripting;

[Preserve]
static class AotHints
{
    [Preserve]
    static void Hints()
    {
        // 构建时 IL2CPP 看到这些实例，就会生成对应代码
        new List<Item>();
        new Dictionary<int, Item>();
        Helper.Process<Item>(default);
    }
}
```

`[Preserve]` 防止 linker 把这个"从未被调用"的类和方法裁掉。注意：代码被裁剪之前 IL2CPP 的泛型收集依赖的是裁剪后的 IL，所以 `Hints` 必须被保留。

### 2. 用 `link.xml` 保留反射使用的类型

```xml
<linker>
  <assembly fullname="MyGame.Data" preserve="all"/>
  <assembly fullname="mscorlib">
    <type fullname="System.Collections.Generic.List`1" preserve="all"/>
  </assembly>
</linker>
```

`link.xml` 放在 `Assets` 目录的任何位置。它只保留类型/成员本身，**不会凭空创建值类型泛型实例**；对泛型实例仍需要上面的"静态可见"。

### 3. 避免需要运行时才确定的泛型

- 把"根据类型字符串创建泛型容器"改为预先注册的工厂表：`Dictionary<string, Func<object>>`，每个条目用 lambda `() => new List<Item>()` 创建，lambda 内的泛型实例静态可见。
- 避免泛型虚方法；改为接口加泛型约束，或先装箱成 `object`（成本换取可用性）。
- 序列化库选择支持 AOT 的方案（带源生成或预生成的格式化器）。

### 4. 值类型换成引用类型实参

对只要工作、不追求最高性能的场景，用引用类型做泛型实参走共享代码，不受值类型实例缺失的限制。

### 5. 上线前在 IL2CPP 真机（或同后端的桌面构建）跑覆盖测试

用 Windows/macOS 的 IL2CPP Player 做自动化冒烟，比等到 iOS 真机才发现快得多。

## 泛型与裁剪的交互

裁剪发生在 IL2CPP 转 C++ 之前，不被引用的泛型实例同样不生成。反射获取 `List<Item>` 的 `Add` 方法时，该方法是否被保留，取决于是否在代码中静态用到过。`preserve="all"` 对整个程序集有效，但会使包体增大；折中是只保留有反射访问的命名空间。

## 与 C++ 对照

C++ 模板是纯编译期的"特化一切"：每个模板实参组合都实例化一份代码（等价于 IL2CPP 对值类型的处理），没有"共享引用类型代码"的概念，也没有"运行时才确定的实例化"，所以不存在 AOT 缺实例的问题；代价是代码膨胀和更长的编译时间（C++ 链接器可以合并相同的实例化，叫 COMDAT folding/ICF，类似引用类型共享）。C# 的运行时泛型要处理"模板元编程做不到的动态场景"，AOT 平台因此要承担限制。C++ 的 `if constexpr`/特化在 C# 里对应泛型的 `typeof(T) == typeof(int)` 判断：JIT 对值类型实例会把这类分支在特化代码中折叠成常量。

## 常见坑

1. **只在编辑器测试**：Mono 下的泛型反射在 IL2CPP 真机失败。
2. **link.xml 不能创建泛型实例**：它只防裁剪。
3. **强制实例的辅助类被裁剪**：忘记 `[Preserve]`。
4. **泛型虚方法 + struct**：最难排查的类型，改成非虚的泛型方法加接口约束。
5. **包体因值类型泛型膨胀**：减少不同值类型的 `Dictionary` 组合，或统一用 `int` id。
6. **假设 IL2CPP 的 full generic sharing 能解决所有问题**：它有性能代价，覆盖范围有限。

## 面试追问

**Q：C# 泛型和 Java 泛型的根本区别？**
Java 是类型擦除，运行时只剩 `Object`，原始类型要装箱。C# 保留运行时类型信息，值类型实例各自特化，不装箱，`typeof(T)`、`new T[]` 都可用。代价是运行时/AOT 需要处理实例化。

**Q：CLR 为什么让引用类型泛型共享代码，而值类型不共享？**
引用类型都是等宽指针，布局和指令相同，共享节省代码和 JIT 时间；值类型的大小、对齐、复制指令、是否含引用都不同，必须特化，也因此能内联且不装箱。

**Q：IL2CPP 下泛型相关的崩溃怎么排查？**
看日志里的 "no ahead of time (AOT) code was generated" 和类型名，定位是哪个值类型实例缺失；然后在一个被 `[Preserve]` 的辅助方法里显式使用该实例，或者改掉反射构造泛型的写法；必要时用 IL2CPP 的 C++ 输出确认实例是否生成。

**Q：`link.xml` 和 `[Preserve]` 的区别与限制？**
两者都是防裁剪，`link.xml` 按程序集/类型声明，`[Preserve]` 标在代码成员上。它们都不能创建泛型实例，只保留已存在的代码。

**Q：泛型共享对性能有什么影响？**
共享的引用类型版本需要通过泛型字典查类型信息，略慢于特化；值类型特化代码更快、可内联，但会增大包体与构建时间。

## 参考资料

- [Unity Manual: IL2CPP limitations](https://docs.unity3d.com/6000.3/Documentation/Manual/scripting-restrictions.html)
- [Unity blog: IL2CPP Internals: Generic sharing implementation](https://unity.com/blog/engine-platform/il2cpp-internals-generic-sharing-implementation)
- [Unity Manual: Managed code stripping 与 link.xml](https://docs.unity3d.com/Manual/managed-code-stripping.html)
- [Book of the Runtime: Generics（共享泛型与泛型字典）](https://github.com/dotnet/runtime/blob/main/docs/design/coreclr/botr/shared-generics.md)
- [Generics in the runtime - .NET](https://learn.microsoft.com/dotnet/standard/generics/)
