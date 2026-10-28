---
title: "2.1 CLR 执行模型与 JIT"
description: 从 IL 与元数据出发,讲清 JIT 首次调用路径、分层编译与 Tiered PGO、ReadyToRun、托管栈帧与 GC 安全点,并对照 Unity 的 Mono JIT 与 IL2CPP。
sidebar:
  order: 1
---

> 适用版本:CoreCLR 部分以 .NET 6~9 为准;Unity 部分以 Unity 6000.x(C# 9.0,Boehm GC 默认增量模式)为准。Unity 是否以及何时迁移到 CoreCLR 以官方发布为准,文中涉及处标"待核实"。

## 要点

- C# 编译产物是 IL 加元数据。IL 是基于求值栈的指令集,不是机器码;真正执行的是 JIT(CoreCLR 的 RyuJIT、Mono 的 JIT)或 AOT(IL2CPP 先转 C++ 再由平台编译器编译)的结果。
- CoreCLR 里方法第一次被调用时走 prestub,触发 JIT,然后回填入口。分层编译默认开启:先出 Tier0(几乎不优化)代码,热了再在后台线程出 Tier1。
- Tier0 到 Tier1 的触发条件有两个:调用满 30 次,且启动期的 100ms 计时器过期(期间只要还有 Tier0 JIT 发生就重置)。含循环的热点方法靠 OSR(栈上替换)补救。
- .NET 8 起 Dynamic PGO 默认开启:Tier0 阶段插桩,Tier1 按真实类型/分支频率做守卫式去虚化、热冷布局。
- 托管线程栈上没有"类型标签"。GC 靠 JIT 生成的 GC info(按安全点记录哪些寄存器/栈槽存活、哪些是内部指针)精确扫描根。Unity 的 Boehm 则是保守扫描,栈上任何像指针的整数都可能让对象存活。
- Unity 的 Mono JIT 与 IL2CPP 都不具备 CoreCLR 的分层编译、PGO、栈精确扫描。拿 CoreCLR 的性能结论套 Unity 是面试和线上调优里最常见的误判。

## IL 与元数据

一个程序集(PE 文件)里有三类东西:IL 方法体、元数据表(TypeDef、MethodDef、Field、MemberRef、TypeSpec、MethodSpec 等)、资源。IL 方法体里的 `call`、`newobj`、`ldfld` 等指令,操作数是元数据 token,运行时按 token 去元数据表里解析成具体的类型/方法/字段。这就是反射、热重载、裁剪(IL Linker/UnityLinker)能工作的前提。

```csharp
static int Sum(int[] a)
{
    int s = 0;
    for (int i = 0; i < a.Length; i++) s += a[i];
    return s;
}
```

Release 下的 IL(示意,具体指令序随编译器版本略有差异):

```text
ldc.i4.0        // s = 0
stloc.0
ldc.i4.0        // i = 0
stloc.1
br.s  CHECK
BODY:
ldloc.0
ldarg.0
ldloc.1
ldelem.i4       // 取 a[i],隐含数组边界检查
add
stloc.0
ldloc.1
ldc.i4.1
add
stloc.1
CHECK:
ldloc.1
ldarg.0
ldlen
conv.i4
blt.s BODY
ldloc.0
ret
```

IL 的求值栈是抽象概念,JIT 会把它消解成虚拟寄存器再做寄存器分配,所以不要用 IL 指令条数估算运行时间。几个对底层理解有用的点:

- `ldelem.i4` 语义上包含空检查和边界检查,是否保留由 JIT 决定。RyuJIT 对 `for (i = 0; i < a.Length; i++)` 这种形态能消除边界检查,写成 `i < n` 且 `n` 来自别处则通常不能。
- `box`、`unbox.any`、`constrained.`、`callvirt` 对值类型的处理决定了装箱是否发生(见 1.2 节)。
- `tail.` 前缀、`localloc`、`ldflda`、`ldind` 等是 unsafe/ref 特性对应的指令。
- 泛型在 IL 里是"开放"的:`List<T>` 只有一份 IL,实例化发生在运行时(CoreCLR/Mono)或 AOT 时(IL2CPP)。

## 方法的首次调用:prestub 与回填

CoreCLR 中每个方法有一个 `MethodDesc`,其入口(precode)最初指向 prestub。第一次调用的过程:

1. 调用方 `call [precode]` 进入 prestub。
2. prestub 检查是否已有可用机器码(ReadyToRun 镜像里的预编译代码,或之前已 JIT 的版本);没有就调用 JIT,把 IL 编译为机器码。
3. 把方法入口回填成新代码(或让 precode 跳转到新代码),之后的调用不再经过 JIT。
4. 开启分层编译时,Tier0 代码的入口还会插入调用计数,见下一节。

对照 C++:C++ 的函数地址在链接期(或 dlopen 时的 PLT/GOT 绑定)就确定,没有"首次调用才编译"这一步。C# 的代价是启动与首次调用抖动;好处是 JIT 能看到运行时信息(实际加载了哪些类、CPU 支持哪些指令集,例如在支持 AVX2 的机器上把 `Vector<T>` 宽度定为 256 位)。

## 分层编译与 OSR

dotnet/runtime 设计文档(Tiered Compilation,Noah Falk)描述的 2.1 RTM 策略如下(阈值是当时的经验值,后续版本的策略有调整,具体以所用版本为准):

- Tier0:ReadyToRun 镜像里的预编译代码,或 JIT 以最小优化快速生成的代码。
- Tier1:完整优化的代码,等价于未启用分层编译时 JIT 的产物。
- 晋升条件一:方法被调用至少 30 次。
- 晋升条件二:启动时有一个 100ms 的计时器;计时期间只要发生任何 Tier0 JIT 就重置;只有计时器正常走完,调用计数才开始。所以一个方法在前 100ms 内被调用 1000 次也不会晋升,计时结束后还需再满 30 次。
- 晋升后进入队列,由线程池里的后台线程编译(每次最多占用约 10ms,超时归还再请求),编译完成后切换入口。

这套机制的已知缺陷就是文档里写的:调用计数对"只调一次但循环很热"的方法无效。.NET 7 引入 OSR(On-Stack Replacement):Tier0 方法里的循环带有回边计数,超过阈值后在循环头处从 Tier0 帧"迁移"到一个为该循环入口特化的优化版本。这样 `Main` 里一个跑很久的大循环不会一直停留在 Tier0。

```csharp
// 启动后第一次跑的热循环:没有 OSR 时会一直是 Tier0 代码
static long Hot()
{
    long s = 0;
    for (int i = 0; i < 1_000_000_000; i++) s += i ^ (i >> 3);
    return s;
}
```

Dynamic PGO(.NET 8 默认开启):方法在 Tier0 阶段被插桩,记录分支走向和虚调用/接口调用点上的实际类型;晋升 Tier1 时据此做 guarded devirtualization(先比较对象类型是否是热点类型,是则直接调用并可内联,否则回退到虚调用)、热冷块重排等。结果是 `IEnumerable<T>` 上的 `foreach`、委托调用这类以前不可内联的位置,在稳态下可能被优化掉。

三点实用结论:

- 基准测试必须预热,并区分 Tier0 / Tier1 / OSR 阶段;BenchmarkDotNet 默认会做预热和多次迭代。
- `[MethodImpl(MethodImplOptions.AggressiveOptimization)]` 会让方法绕过分层、直接按完全优化 JIT,代价是不参与 PGO、没有 Tier0 插桩;适合已知很热且想避开预热的小方法,不要滥用。
- `TieredCompilation`、`TieredPGO`、`TC_QuickJitForLoops`、`ReadyToRun` 等都能通过 runtimeconfig 或环境变量(`DOTNET_TieredPGO=0` 等)调整,用于排查性能退化是不是分层引起的。

## ReadyToRun(R2R)

R2R 是 CoreCLR 的半 AOT:crossgen2 提前把 IL 编译成机器码放进程序集,启动时无需 JIT。R2R 代码为了可移植,不会假设具体 CPU 指令集、跨版本边界(跨程序集内联)受限,质量低于 Tier1,所以它在分层模型里充当 Tier0:热了仍会重新 JIT 为 Tier1。它解决的是启动,不是稳态性能。

对照:Native AOT(.NET 7+)是完全提前编译、无 JIT、无反射 Emit,与 IL2CPP 的取舍更接近;IL2CPP 则不是 R2R 这种"带回退的预编译"。

## 托管栈帧与 GC 安全点

JIT 编译方法时除了机器码,还会输出 GC info,描述在每个"可停下的位置"哪些寄存器、栈槽、栈偏移里放着托管引用,哪些是内部指针(interior pointer,指向对象内部字段/数组元素的 `ref`),哪些栈槽已经"死"。要点:

- 常规方法是"部分可中断":只在调用点等安全点才保证有精确 GC info。GC 想挂起线程时,运行中的线程要先到达安全点。
- CoreCLR 通过几种方式让线程停下:线程在 P/Invoke 里已处于抢占模式,无需配合;线程在托管代码里则靠劫持返回地址(hijack)、GC poll、或对"完全可中断"的代码直接用信号/挂起线程再查 GC info。紧凑的无调用循环会被 JIT 插入 GC poll 或编译成完全可中断,否则会拖住整个 GC 的挂起阶段。
- 对象引用的存活按 JIT 的活跃性分析,而不是作用域。优化代码里,一个局部变量最后一次使用之后,它指向的对象就可以被回收,即使变量还在作用域里。这是 2.5 节会展开的 `GC.KeepAlive` 问题的根源。Debug 代码不做这种缩短,所以"Debug 没事,Release 偶发崩溃"是经典现象。

Unity 的对照:

- Mono(Boehm)与 IL2CPP(Boehm)都是保守式栈扫描。GC 把线程栈和寄存器里"值落在堆范围内"的字长当作可能的指针,不需要 GC info,也不会移动对象(因为不确定它是不是真指针)。代价是可能出现误保留:一个恰好长得像指针的整数让大对象无法回收。
- 因为不移动,Unity 里 `fixed` 和 `GCHandle.Alloc(..., Pinned)` 在当前实现里几乎没有运行时成本,但可移植代码仍然必须按规范 pin,见 2.3 节。

## Unity 的执行后端:Mono JIT 与 IL2CPP

| 维度 | CoreCLR | Unity Mono(编辑器及选用 Mono 后端的平台) | Unity IL2CPP |
|---|---|---|---|
| 编译时机 | JIT + 可选 R2R/Native AOT | JIT(Mono 自己的 JIT) | 构建期 IL 转 C++,再由平台 C++ 编译器编译 |
| 分层/PGO | 有,.NET 8 默认含 Dynamic PGO | 无 | 无(靠 C++ 编译器的 -O 优化与 LTO) |
| GC | 精确、分代、压缩 | Boehm,保守、非分代、非压缩,可增量 | 同样是 Boehm |
| 运行时代码生成 | Reflection.Emit、`dynamic` 可用 | 可用 | 不可用(Unity 6 手册明确不支持 `dynamic` 与 Reflection.Emit) |
| 泛型 | 值类型各自特化,引用类型共享 | 类似 | 值类型特化,引用类型共享;运行时才出现的实例需预先引用,否则落到较慢的通用路径 |
| 语言版本 | 随 SDK | C# 9.0 | C# 9.0 |

Unity 6000.2 手册给出:C# 编译器为 Roslyn,语言版本 C# 9.0;不支持 `init` 只写属性(需要自己声明 `IsExternalInit`)、协变返回类型、模块初始化器、`SkipLocalsInit`、unmanaged 函数指针的扩展调用约定。GC 默认是 Boehm 且默认增量模式。IL2CPP 手册另说明:引用类型实例共享同一份泛型代码,值类型每个实例单独生成;在运行期才出现、编译期推断不到的泛型实例会退回"可处理任意类型"的慢速通用代码。

IL2CPP 的流水线是:IL → (il2cpp.exe)C++ 源文件 → 平台工具链(MSVC/clang/NDK)→ 原生库。生成代码里每个托管方法对应一个 C++ 函数,值类型对应 C++ struct,引用类型对应带对象头的 struct 指针,虚调用走生成的 vtable/接口表,类型与方法元数据放在 `global-metadata.dat`。这意味着:

- 热点性能由 C++ 编译器和生成代码的形状决定,不存在"热了再优化"。
- 每次读写引用字段,生成代码会带上空检查;数组访问带边界检查;静态构造函数检查(`il2cpp_codegen_...` 一类辅助调用)。这些可以在 Player 设置里按需关闭一部分(如 `Il2CppSetOption` 特性),具体选项随版本变化,待核实。
- 泛型虚方法、接口泛型等路径在 IL2CPP 上会比 JIT 后端更依赖预先生成的代码,构建期找不到的实例会在运行时变慢甚至失败。

## 常见坑

- 用 CoreCLR 的 BenchmarkDotNet 数据去判断 Unity 上的取舍。分层编译、PGO、去虚化、边界检查消除在 Mono/IL2CPP 上要么没有,要么实现完全不同。
- 在 Release 下依赖局部变量延长对象寿命。被 P/Invoke 引用的对象在最后一次使用后就可能被 CoreCLR 判定为不可达,需要 `GC.KeepAlive` 或 `SafeHandle`(见 2.5 节)。Unity 的保守扫描会"碰巧"让这类 bug 很难复现,迁移运行时时才暴露。
- 认为"IL2CPP 就是 C++ 所以一定比 Mono 快"。它快在去掉了 JIT 与更强的优化器,但托管语义(空检查、边界检查、GC 分配、泛型共享)仍在,内存模型与 GC 行为没有变。
- 忽略首次调用成本:冷路径(第一次打开某界面、第一次解析某配置)出现掉帧,往往是 JIT 或 IL2CPP 下泛型/反射元数据初始化,而不是业务代码慢。

## 面试追问

1. **IL 是怎么变成机器码的?为什么有 Tier0/Tier1?** 要点:方法首次调用走 prestub 触发 JIT;Tier0 追求编译快、代码质量低,热点(调用满 30 次且启动稳定 100ms 后)在后台线程重编为 Tier1;循环热点靠 OSR;.NET 8 起带 Dynamic PGO。说出 R2R 在这里充当 Tier0 并能被替换会加分。
2. **Dynamic PGO 能优化什么?** 要点:Tier0 插桩收集分支频率和虚/接口调用点的类型分布;Tier1 据此做 guarded devirtualization 与内联、冷热块重排。对 Unity 无效,因为 Mono/IL2CPP 没有这套机制。
3. **GC 怎么知道栈上哪些是引用?** 要点:CoreCLR 靠 JIT 生成的 GC info 精确扫描,在安全点处记录活跃的引用槽与内部指针;Unity 的 Boehm 是保守扫描,不依赖类型信息,因此不能移动对象,可能误保留。
4. **为什么 Release 下对象会"提前"被回收?** 要点:JIT 的活跃性分析使局部变量最后一次使用后即视为死亡;与 `this` 同理,实例方法执行期间 `this` 也可能不可达,所以持有原生资源的类要用 SafeHandle 或在调用后 `GC.KeepAlive(this)`。
5. **IL2CPP 和 Mono 的本质区别?对泛型有什么影响?** 要点:IL2CPP 是 AOT(IL→C++→原生),不支持运行时代码生成;引用类型泛型共享代码、值类型泛型每个实例单独生成;运行时才出现的泛型实例会退到慢速通用路径,需要在代码里预先引用。
6. **和 C++ 相比,C# 的"首次调用"多了什么?** 要点:JIT/类型加载/静态构造函数/元数据解析;C++ 的函数地址在链接期或加载期绑定,没有这一步,但也没有运行时 PGO 与跨模块内联的机会。

## 参考资料

- dotnet/runtime,Tiered Compilation 设计文档:https://github.com/dotnet/runtime/blob/main/docs/design/features/tiered-compilation.md
- Microsoft Learn,Compilation config settings:https://learn.microsoft.com/en-us/dotnet/core/runtime-config/compilation
- Unity 手册,C# compiler and language version reference(6000.2):https://docs.unity3d.com/6000.2/Documentation/Manual/csharp-compiler.html
- Unity 手册,IL2CPP limitations(6000.0):https://docs.unity3d.com/6000.0/Documentation/Manual/scripting-restrictions.html
- dotnet/runtime,OSR 与 Dynamic PGO 设计文档:https://github.com/dotnet/runtime/tree/main/docs/design/features
