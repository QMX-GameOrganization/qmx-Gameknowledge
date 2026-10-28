---
title: "4.1 Mono 与 IL2CPP 的差异"
description: Unity 两种脚本后端的编译与运行模型、内存与 GC、运行时检查、代码生成、调试与性能差异，以及对 CoreCLR 迁移的现状说明。
sidebar:
  order: 1
---

> 适用版本：以 Unity 2022 LTS 到 Unity 6（6000.x）为主。Unity 官方论坛《Path to CoreCLR, 2026: Upgrade Guide》写明 Unity 6.8 起以 CoreCLR 取代 Mono，发布时间与行为细节请以官方后续文档为准。Mono 与 IL2CPP 的具体实现细节会随小版本变动。

## 要点

- **Mono 后端**：C# 编译成 IL（程序集），运行时由 Mono 运行时加载，用 JIT（或在不允许 JIT 的平台用 AOT）把 IL 翻译成机器码。编辑器里一律使用 Mono。
- **IL2CPP 后端**：构建时把 IL 先转成 C++ 源码，再用平台的 C++ 编译器（clang/MSVC/Xcode 等）编译成原生代码，随包携带轻量的运行时库（libil2cpp）。没有 JIT，没有 `Reflection.Emit`。iOS、主机、WebGL 只能用 IL2CPP，Android 与桌面可选。
- 两者都用 **Boehm-Demers-Weiser GC**：保守式、非分代、非移动（可选增量模式）。这点和 CoreCLR 的分代压缩 GC 完全不同，见第 3 章。
- IL2CPP 的运行时代码质量通常比 Mono JIT 好，但会插入空指针、数组边界、除零检查，可通过 `Il2CppSetOption` 关闭；构建时间和包体更大。
- 差异最大的是：泛型的实例化时机（AOT 需要编译期可见）、反射与裁剪、native 回调的写法、调试与崩溃堆栈。
- Unity 官方的 Path to CoreCLR 计划会改变上述一部分结论，评估时要区分"今天用的版本"和"路线图"。

## 编译与执行模型

| 阶段 | Mono | IL2CPP |
|---|---|---|
| C# → IL | Roslyn，两者相同 | 相同 |
| IL → 机器码时机 | 运行时 JIT（首次调用方法时编译），部分平台 AOT | 构建时：IL → C++ → 原生 |
| 运行时是否有 JIT | 有（iOS 等禁止 JIT 的平台例外，用 Mono AOT） | 无 |
| 动态代码生成 | `System.Reflection.Emit`、`Expression.Compile` 可用 | `Reflection.Emit` 不可用；`Expression.Compile` 退化为解释执行 |
| 泛型实例化 | 运行时按需 JIT | 构建时静态确定，缺失则运行时报错 |
| 启动 | 有 JIT 预热开销 | 无 JIT 预热，但加载元数据 |
| 增量构建速度 | 快 | 慢，全平台 C++ 编译 |
| 包体 | 小 | 大（C++ 展开代码、泛型实例、元数据文件） |

IL2CPP 构建的产物包含两部分：生成的 C++ 代码（以及编译好的原生库），和 `global-metadata.dat`（类型、方法、字符串字面量等元数据，供反射、`GetType`、泛型字典等运行时功能使用）。

IL2CPP 把每个 C# 类翻译成一个 C++ `struct`，第一个成员是对象头，方法翻译成 C 风格的函数，虚调用通过类的 vtable 间接调用。Unity 的 IL2CPP 生成的方法在 C++ 里的形态（示意）：

```cpp
// 示意：C# 方法 int Add(int a, int b) { return a + b; }
IL2CPP_EXTERN_C int32_t Foo_Add_m123456 (Foo_t* __this, int32_t ___a0, int32_t ___b1, const RuntimeMethod* method) {
    // 方法入口的 StackTraceSentry、静态构造初始化检查
    return il2cpp_codegen_add(___a0, ___b1);
}
```

生成函数名、辅助宏名称随 Unity 版本变化，上例只表示结构。

## 内存与 GC

Mono 与 IL2CPP 在 Unity 里都使用 Boehm GC（Unity 对其做过定制，加入了增量模式）：

| 特性 | Boehm（Unity） | CoreCLR GC |
|---|---|---|
| 扫描 | 保守式：栈和寄存器里的任何"像指针"的值都当引用 | 精确式：JIT 提供栈映射 |
| 分代 | 无 | 有（Gen0/1/2） |
| 压缩 | 无，非移动 | 有（可选） |
| 碎片 | 会产生外部碎片，堆只增不减的倾向 | 压缩后较少 |
| 增量 | 支持增量标记（可开关） | 后台 GC（并发） |
| 分配 | 按大小类的空闲链表 | 线程本地分配上下文，bump pointer |

后果：

- 因为是保守式且不移动，**对象不会被搬动**，所以不需要为"传给 native"而固定对象（虽然仍要遵守语言层的 `fixed`/`GCHandle` 规则，因为代码要在 CoreCLR 迁移后仍然正确）。
- 保守扫描可能把整数误认为指针，导致某些对象无法回收（"假保留"），这是堆只增不减的原因之一。
- 非分代意味着每次回收都要标记整个存活堆，存活对象越多，GC 越慢。增量 GC 把标记分散到多帧，但总工作量不变。
- 堆会向系统申请新的块，回收后的空闲块不一定归还操作系统。

详细机制见 3.3 节。

## 运行时检查与代码生成

IL2CPP 在生成的 C++ 里默认插入：

- 空引用检查（访问成员前判空，抛 `NullReferenceException`）
- 数组边界检查
- 除零检查（整数除法）
- 类型转换检查、静态构造函数的触发检查、栈溢出相关的托管栈追踪辅助

这些检查可以用 `Il2CppSetOptionAttribute` 对类型或方法关闭，该属性定义在 Unity 安装目录下 IL2CPP 的附带源文件里，需要把它拷进项目使用（具体路径随版本变化，待核实）：

```csharp
using Unity.IL2CPP.CompilerServices;

[Il2CppSetOption(Option.NullChecks, false)]
[Il2CppSetOption(Option.ArrayBoundsChecks, false)]
[Il2CppSetOption(Option.DivideByZeroChecks, false)]
static class Hot
{
    public static int Sum(int[] a)
    {
        int s = 0;
        for (int i = 0; i < a.Length; i++) s += a[i];
        return s;
    }
}
```

关闭检查后，错误会变成未定义行为（段错误、内存越界读写）而不是托管异常，只在热点、经过充分测试的代码里使用。

构建设置里的 **IL2CPP Code Generation**（Unity 2022.x 以后的 Player 设置，"Faster runtime" 与 "Faster (smaller) builds"）控制泛型实例化的生成策略：前者为每个泛型实例生成专用代码，后者尽可能共享，体积更小但运行更慢（选项名称与版本对应关系待核实）。**C++ Compiler Configuration**（Debug/Release/Master）控制 C++ 编译器的优化级别。

Mono 的 JIT 优化相对保守（没有分层编译和 PGO 这类 CoreCLR 的特性），IL2CPP 把优化交给 clang/MSVC 等成熟的 C++ 编译器，内联、常量传播、循环优化更激进。因此纯计算密集的 C# 代码在 IL2CPP 上通常更快，而 Burst 编译的代码不受后端影响（Burst 直接从 IL 生成机器码，见 Job 与 Burst 专栏）。

## 差异清单

| 主题 | Mono | IL2CPP |
|---|---|---|
| 反射 | 完整 | 可用，但依赖元数据与未被裁剪的代码；`MakeGenericType`/`MakeGenericMethod` 有值类型限制 |
| `Reflection.Emit` / 动态程序集 | 支持 | 不支持 |
| `Expression.Compile` | 编译成 IL（JIT） | 解释执行，慢 |
| 向 native 传托管回调 | 实例或静态方法 | 必须是静态方法，且标注 `[MonoPInvokeCallback(typeof(Delegate类型))]` |
| 泛型虚方法、值类型泛型 | 运行时生成 | 需要编译期实例化，缺失则运行时报 `ExecutionEngineException` 类错误 |
| 栈溢出 | 通常直接终止进程，无法捕获 | 同样直接崩溃（C++ 栈溢出），深度递归要避免 |
| 异常处理开销 | 较高 | 使用 C++ 异常，开销大，不要用异常做控制流 |
| 调试 | 编辑器与 Development Build 支持托管调试器 | Development Build 也支持托管调试，崩溃堆栈可能是 C++ 符号，需要符号文件 |
| 属性 `Preserve` 与裁剪 | 受托管代码裁剪影响 | 受裁剪影响，且泛型、反射更敏感 |

关于 native 回调的写法：

```csharp
using AOT;      // MonoPInvokeCallbackAttribute 所在命名空间

delegate void NativeLogCb(int level, IntPtr msg);

[MonoPInvokeCallback(typeof(NativeLogCb))]
static void OnNativeLog(int level, IntPtr msg) { /* 必须是 static */ }

// 传给 native
Native_SetLogCallback(Marshal.GetFunctionPointerForDelegate<NativeLogCb>(OnNativeLog));
```

需要持有委托引用，防止被 GC 回收后 native 回调悬空（Boehm 不移动对象，但回收仍会发生）。互操作更多细节见 2.2 节。

## 托管代码裁剪（Managed Stripping）

构建时 Unity 的 linker 会裁掉未被引用的类型和成员以减小包体，级别有 Disabled、Minimal、Low、Medium、High（不同版本的选项集合略有差异，待核实）。IL2CPP 的 C++ 代码量与裁剪强相关。

裁剪的盲区是**只通过反射、字符串名或序列化使用的类型**，linker 无法静态看到引用，需要显式保留：

```xml
<!-- Assets/link.xml -->
<linker>
  <assembly fullname="MyGame.Runtime" preserve="all"/>
  <assembly fullname="Newtonsoft.Json">
    <type fullname="Newtonsoft.Json.Converters.*" preserve="all"/>
  </assembly>
</linker>
```

或在代码上标注 `UnityEngine.Scripting.PreserveAttribute`（`[Preserve]`），告诉 linker 保留该成员。

## 对 Unity 里常见问题的影响

1. **性能 Benchmark 要在目标后端上跑**。编辑器里的 Mono 结果不能代表 IL2CPP 真机表现。
2. **GC 行为一致但装箱、闭包的 C++ 实现不同**，分配量用 Profiler 在真机验证。
3. **异常**：IL2CPP 的 `try/catch` 比 Mono 更重，热路径不要抛异常。
4. **泛型**：Mono 下运行正常的反射泛型代码，到 IL2CPP 真机崩溃，是最常见的"编辑器正常、真机崩溃"的原因之一（见 4.2 节）。
5. **崩溃堆栈**：IL2CPP 崩溃日志里是生成的 C++ 函数名，如 `Foo_Bar_m123456`，需要 `il2cpp` 产出的符号映射（Android 的 `symbols.zip`、iOS 的 dSYM）才能还原。

## Path to CoreCLR

Unity 官方论坛的《Path to CoreCLR, 2026: Upgrade Guide》（2026-03-26 发布）写明：Unity 计划在 2026 年内完成一系列改动，在 Unity 6.8 中替换脚本运行时，CoreCLR 成为 C# 层的基础，Unity 6.8 将不再提供 Mono 选项。官方对 6.8 的目标是整体性能持平（有的场景更快，有的更慢），源码层面大体兼容，同时列出了若干破坏性变更。Unity 6.7 LTS 的 alpha 版本里提供了实验性的 CoreCLR 桌面 Player（自 alpha 2 起），以及实验性的 IL2CPP iOS Player（自 alpha 5 起），用来提前验证项目。

对本专栏的影响：

- CoreCLR 路径下，GC 是 .NET 的分代压缩 GC，LOH 阈值为 85 KB（官方帖中的回复）。关于分代、压缩、精确扫描、`GCHandle`/固定的结论会随之变化，写通用代码时遵守规范，不依赖 Boehm 的非移动性质。
- IL2CPP 继续保留，官方回复明确说"IL2CPP 使用的 Boehm GC 行为没有变化"，所以本节的 AOT 限制与 Boehm 结论对 IL2CPP 目标仍然适用。同一个项目可能出现"编辑器是 CoreCLR GC，Player 是 IL2CPP + Boehm"的差异，性能测试要在目标后端上做。
- 浮点语义：官方帖指出 CoreCLR 下浮点计算在某些情况下可能与旧行为有细微差别；IL2CPP 与 Burst 不受影响。
- 具体发布日期、各平台覆盖范围、增量 GC 在 CoreCLR 下是否有等价物，以官方后续发布为准（待核实）。
- CoreCLR 带来的语言特性（C# 12+ 的集合表达式、`ref struct` 泛型等）和 API（`Span` 相关 API、`CollectionsMarshal`）会逐步可用，写面试题时说明"当前主流 Unity 为 Mono/IL2CPP + Boehm"，同时了解 CoreCLR 的行为。

## 与 C++ 对照

IL2CPP 本质上是"C# 到 C++ 的转译器 + 小型运行时库"，运行时库负责 GC、类型元数据、反射、线程、异常。理解 IL2CPP 的输出对想弄懂"C# 是怎么翻成 C++"很有帮助：

| C# 概念 | 在 IL2CPP 生成的 C++ 中 |
|---|---|
| class | C++ `struct`，首成员为对象头 |
| struct | C++ `struct`，值语义 |
| 虚方法 | 通过 `Il2CppClass` 的 vtable 数组间接调用 |
| 接口方法 | 通过接口偏移表查找 |
| 泛型实例 | 每个（值类型）实例生成一份代码；引用类型共享 |
| 字符串字面量 | 元数据里的表，首次访问时创建并驻留 |
| 异常 | C++ 异常或带 setjmp 的机制（随平台和设置变化，待核实） |
| `lock` | 运行时库的监视器实现 |

## 常见坑

1. **把编辑器里的性能数据当结论**：编辑器用 Mono + 额外检查 + 调试符号，和 IL2CPP Release 差别很大。
2. **IL2CPP 关闭检查后不测试边界**：错误变成静默内存破坏。
3. **native 回调用了实例方法或 lambda**：IL2CPP 报错或崩溃。
4. **忘了 link.xml**：反射加载的类型被裁剪，真机找不到。
5. **在 IL2CPP 上使用 `dynamic` 或 `Reflection.Emit` 库**：不支持，构建或运行失败。
6. **以为 IL2CPP 的 GC 不同**：GC 仍是 Boehm，只是对象布局和分配代码由生成的 C++ 完成。

## 面试追问

**Q：IL2CPP 的流程是什么？为什么 iOS 必须用？**
C# 编译成 IL，IL2CPP 工具把 IL 转成 C++，再用平台编译器编成原生库，与 libil2cpp 运行时一起打包。iOS 等平台禁止运行时生成可执行代码，因此不能用 JIT，只能走 AOT。

**Q：Mono 和 IL2CPP 在 GC 上有什么共同点和问题？**
共用 Boehm GC：保守式、非分代、不压缩。共同问题是每次回收标记全堆、堆碎片、假保留；增量模式把停顿摊到多帧。

**Q：IL2CPP 下为什么会出现"编辑器正常，真机崩溃"的泛型问题？**
编辑器用 Mono JIT，运行时能按需生成泛型实例；IL2CPP 要在构建时看到所有值类型泛型实例，经反射或泛型虚方法才触发的实例构建期不可见，运行时无法生成，报错。

**Q：怎么提升 IL2CPP 下热点代码的速度？**
用 Burst + Job 迁移计算；用 `Il2CppSetOption` 关检查（需要确认安全）；避免异常、装箱、虚调用；选择 Release C++ 配置；减少泛型虚方法。

**Q：IL2CPP 的 `[MonoPInvokeCallback]` 是做什么的？**
IL2CPP 无法在运行时为任意托管委托生成到 native 的 thunk，只能为静态方法在构建期生成。属性告诉 IL2CPP 为该静态方法和指定的委托类型生成互操作代码。

## 参考资料

- [Unity Manual: IL2CPP overview](https://docs.unity3d.com/Manual/IL2CPP.html)
- [Unity Manual: Scripting backends](https://docs.unity3d.com/Manual/scripting-backends.html)
- [Unity Manual: IL2CPP limitations](https://docs.unity3d.com/6000.3/Documentation/Manual/scripting-restrictions.html)
- [Unity blog: IL2CPP Internals 系列](https://unity.com/blog/engine-platform/il2cpp-internals-generic-sharing-implementation)
- [Unity Manual: Managed code stripping](https://docs.unity3d.com/Manual/managed-code-stripping.html)
- [Path to CoreCLR, 2026: Upgrade Guide（Unity 官方论坛）](https://discussions.unity.com/t/path-to-coreclr-2026-upgrade-guide/1714279)
