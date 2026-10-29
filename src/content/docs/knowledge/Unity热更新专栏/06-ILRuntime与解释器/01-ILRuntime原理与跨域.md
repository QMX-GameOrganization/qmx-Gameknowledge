---
title: "6.1 ILRuntime 原理与跨域"
description: ILRuntime 的 IL 解释执行原理、热更域与主域的类型隔离、跨域继承与委托适配、CLR 绑定与性能、接入与使用限制。
sidebar:
  order: 1
---

> 适用版本：ILRuntime 的各版本。该项目近年的维护活跃度、对新 Unity 与 C# 版本的支持范围**需要查看仓库当前状态（待核实）**。本页内容用于理解"独立解释器"这一类方案的设计，并为与 HybridCLR 对比提供依据。

## 要点

- ILRuntime 是用纯 C# 写的 **IL 解释器**，运行在 Mono 或 IL2CPP 的托管层内。热更 dll 通过 `AppDomain.LoadAssembly` 加载到 ILRuntime 自己的域，由它解释执行。
- 因为是独立实现，**热更类型不是 CLR 的真实类型**。它们对 CLR 来说只是 ILRuntime 内部的数据结构，这带来三个后果：跨域继承需要**适配器**、反射和某些 CLR 机制不能直接作用于热更类型、热更类型与主域类型之间的转换需要处理。
- 调用主工程（AOT）方法靠**反射**，默认较慢且产生 GC；可通过 **CLR 绑定（CLR Binding）** 生成直接调用的代码来优化。
- 不需要修改引擎或 IL2CPP，接入门槛低，是 HybridCLR 之前的主流 C# 热更方案之一。

## 架构

```
主域 (CLR, 真实类型, AOT 或 Mono)
   │  AppDomain (ILRuntime)
   ▼
 热更域: 解释执行 IL
   ├─ ILTypeInstance: 热更类型的实例,ILRuntime 自己的对象表示
   ├─ 栈/寄存器模拟: 栈帧、局部变量
   └─ 对主域的调用: 反射 / CLR 绑定 / 委托适配
```

解释执行流程：

1. 读取 dll 元数据，把方法的 IL 翻译成内部指令格式（预处理）。
2. 逐条指令在自带的虚拟栈上执行，使用自己的内存表示（值类型、引用类型的内部存储）。
3. 遇到调用主域方法，则通过反射（或绑定）调用；返回值转换回自己的表示。

## 跨域继承与适配器

热更类想继承主工程里的类或实现接口（常见的：继承 `MonoBehaviour`、实现 `IDisposable`、继承某个 AOT 基类）。因为热更类型不是真实 CLR 类型，ILRuntime 需要一个**适配器类**：

```csharp
// 主工程中: 一个继承自 AOT 基类的适配器
public class MyBaseAdapter : CrossBindingAdaptor
{
    public override Type BaseCLRType => typeof(MyBase);
    public override Type AdaptorType  => typeof(Adaptor);
    public override object CreateCLRInstance(ILRuntime.Runtime.Enviorment.AppDomain appdomain, ILTypeInstance instance)
        => new Adaptor(appdomain, instance);

    class Adaptor : MyBase, CrossBindingAdaptorType
    {
        // 重写 MyBase 的虚方法, 内部转调热更域里的实现
    }
}
// 注册
appdomain.RegisterCrossBindingAdaptor(new MyBaseAdapter());
```

要点：

- 每个被热更类继承的 AOT 类型都需要一个适配器，需要为其中被重写的方法编写转发代码。
- 对 `MonoBehaviour`：热更类型不能直接被 Unity 当作组件挂载，一般通过一个主工程里的"代理 MonoBehaviour"，由它转发生命周期给热更域的对象。这是 ILRuntime 项目的常见做法，也是主要的复杂度来源。

## 委托与回调

把热更域的方法传给主域的委托类型（例如 `Action`、`UnityAction`、`Comparison<T>`）需要**委托转换**：

```csharp
appdomain.DelegateManager.RegisterMethodDelegate<int>();               // Action<int>
appdomain.DelegateManager.RegisterFunctionDelegate<int, string>();     // Func<int,string>
appdomain.DelegateManager.RegisterDelegateConvertor<UnityAction>(
    act => new UnityAction(() => ((Action)act)()));
```

没有注册对应的委托签名，会在运行时报错。生成这些注册代码有辅助工具，但仍需要维护。

## CLR 绑定

默认调用主域方法走反射，产生 GC 且慢。ILRuntime 提供生成工具（"Generate CLR Binding"）：

- 对指定类型生成"绑定"代码，调用时不经反射，直接用强类型代码。
- 只对热更代码里实际调用到的主域方法生成。
- 需要随主包发布，且热更代码新增了对尚未绑定方法的调用时，性能会回退到反射（功能仍可用）。

## 值类型与泛型

- 值类型在主域和热更域之间传递，需要处理装箱与拷贝；对 Unity 常用结构体（`Vector3`、`Quaternion`）有专门的 `ValueTypeBinder` 优化机制（待核实），否则每次传递产生分配。
- 热更域的泛型实例化：热更类型作为泛型实参传给主域泛型（如 `List<HotClass>`），实际存的是 `ILTypeInstance`，类型信息特殊，某些场景（反射、序列化）需要小心。
- 在 IL2CPP 上，主域泛型的值类型实例仍有 AOT 缺失问题，需要代码中引用保留，或者借助 ILRuntime 的 `RegisterValueTypeBinder`/泛型实例注册（待核实）。

## 使用限制

- 热更类型没有真实的 CLR 类型，**不能**用 `typeof(HotClass)` 在主域进行 CLR 级别操作（需要通过 ILRuntime 的类型接口）。
- 不能在主域用 `Activator.CreateInstance` 直接创建热更类型。
- 不能把热更类型作为主域泛型约束（如 `where T : HotBase`）。
- 某些高级 C# 特性（如部分 `unsafe` 用法、复杂泛型）支持有限。
- 调试支持：官方提供了断点调试工具，但体验与原生调试有差距（待核实）。

## 与 HybridCLR 的取舍

- ILRuntime 的优势：不改引擎，接入简单，纯托管，兼容性取决于自身实现。
- 劣势：跨域适配代码多，类型系统不统一，反射与序列化需额外处理；性能受自带解释器与跨域调用影响。
- HybridCLR 通过在运行时层集成，消除了绝大多数适配成本（见 4.1）。

## 常见坑

1. **忘记注册委托转换/适配器**：运行时才报错，不是编译期，需要覆盖测试。
2. **未生成 CLR 绑定**：热更代码里频繁调用主域 API 产生大量 GC 与耗时。
3. **IL2CPP 下主域泛型实例缺失**：与前述 AOT 限制同源。
4. **热更类型传入主域的序列化器/反射代码**：JSON 库等对热更类型不识别。
5. **版本兼容**：Unity、C# 编译器版本更新后，新语法或新 IL 模式可能导致解释器不支持，升级前先验证。

## 面试追问

**Q：ILRuntime 为什么需要适配器？**
热更类型不是 CLR 的真实类型，主域代码无法继承或把它当作基类实例使用；适配器是在主域里的真实类，内部转发给热更域的实现。

**Q：CLR 绑定解决什么问题？**
热更代码调用主域方法默认走反射，慢且分配；绑定生成直接调用的代码，避免反射开销。

**Q：独立解释器相比运行时集成的解释器，主要缺点是？**
类型系统被隔离，需要大量跨域适配与转换，并且调用主域代码时缺少原生桥接，性能与易用性受限。

## 参考资料

- [ILRuntime GitHub](https://github.com/Ourpalm/ILRuntime)
- [ILRuntime 官方文档](https://ourpalm.github.io/ILRuntime/public/v1/guide/index.html)
- [HybridCLR 官方文档（对比）](https://hybridclr.doc.code-philosophy.com/)
