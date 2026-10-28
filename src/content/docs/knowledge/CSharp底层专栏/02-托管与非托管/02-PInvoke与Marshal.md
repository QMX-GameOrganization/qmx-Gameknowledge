---
title: "2.2 P/Invoke 与 Marshal"
description: 托管到原生的调用边界:blittable 与封送成本、调用约定与 ABI 对齐、SetLastError、回调与委托生命周期,以及 Unity 的 DllImport、Native Plugin 与 IL2CPP 回调限制。
sidebar:
  order: 2
---

> 适用版本:P/Invoke 机制以 .NET Core/.NET 5+ 为准;`LibraryImport`、`UnmanagedCallersOnly`、`DisableRuntimeMarshalling` 是 .NET 5~7 之后的特性,Unity 6000.x(C# 9.0)中是否可用逐项标注。Unity 的结论以 6000.0 / 6000.2 手册为准。

## 要点

- 一次 P/Invoke 调用 = 参数封送 + 线程从协作模式切到抢占模式 + 原生调用 + 切回并检查 GC 挂起 + 返回值封送。只有 blittable 参数时,JIT 可以内联这段过渡,成本在个位数纳秒;含 `string`、`bool`、`char`、数组、委托、类时会生成 IL stub 做转换,可能分配并拷贝。
- 与 C/C++ 对接只走 `extern "C"` 导出的 C ABI:名字修饰、异常、`std::` 类型、虚函数表都不能跨边界。
- 调用约定在 x64 上基本只有一种,在 x86 上 cdecl 与 stdcall 不匹配会破坏栈。`bool`、`char`、`long`、`wchar_t`、`size_t` 的宽度在不同平台上不同,是跨平台插件出 bug 的头号来源。
- 把托管方法交给原生代码调用,要么保证委托实例存活,要么改用静态方法加函数指针。Unity 的 IL2CPP 要求回调是静态方法并带 `[MonoPInvokeCallback]`。
- `SetLastError = true` 的意义是在原生返回后立刻保存错误码,避免运行时自己的系统调用把它覆盖。

## 调用边界发生了什么

托管线程执行托管代码时处于协作模式(cooperative):GC 要挂起它,必须等它到达安全点。进入原生代码前线程切换到抢占模式(preemptive),表示"我现在不碰托管堆,GC 可以直接继续"。完整流程:

1. 参数封送:把托管值转换成原生表示。blittable 值直接按位拷贝;字符串可能 pin 住后传 `char*`,或转成 ANSI/UTF-8 临时缓冲。
2. 建立 `InlinedCallFrame`(记录托管栈帧与返回点,供 GC 与异常展开在这段原生代码期间遍历托管栈)。
3. 切换到抢占模式,执行 `call`。
4. 返回后切回协作模式;如果期间 GC 正在进行,线程在这里等待。
5. 返回值封送、`SetLastError` 处理、异常转换(如 `MarshalDirectiveException`、`PInvokeStackImbalance`)。

CoreCLR 对"仅 blittable 参数、无 SetLastError"的调用,JIT 直接把过渡代码内联在调用点,不经过 IL stub,这是 `[SuppressGCTransition]`(.NET 5+)能进一步省掉第 3、4 步的前提:它告诉运行时被调用的函数极短、不会阻塞、不回调托管代码,可以不切换模式。用错会让 GC 挂起被拖长,甚至死锁。

Unity 上的实现不同。Mono 后端用 `mono_marshal` 生成 wrapper;IL2CPP 在构建期为每个 P/Invoke 生成 C++ 包装函数,封送逻辑直接是生成的 C++ 代码。后者没有运行时 stub 生成,但同样要为非 blittable 参数做拷贝与内存分配。

## blittable 与封送成本

blittable 类型在托管与原生内存里有相同的位表示:`byte/sbyte/short/ushort/int/uint/long/ulong/float/double/IntPtr/UIntPtr`,以及只含 blittable 字段且布局为 `Sequential` 或 `Explicit` 的 struct,一维 blittable 数组。非 blittable:

| 类型 | 默认封送行为 | 原生侧常见对应 | 备注 |
|---|---|---|---|
| `bool` | 4 字节 `BOOL` | C++ `bool` 是 1 字节 | 与 C++ `bool` 对接必须写 `[MarshalAs(UnmanagedType.U1)]`,否则读到垃圾位或栈偏移错位 |
| `char` | 取决于 `CharSet`:Ansi 为 1 字节,Unicode 为 2 字节 | `char` / `wchar_t` | `wchar_t` 在 Windows 是 2 字节,在 Linux/macOS 是 4 字节 |
| `string` | 按 `CharSet` 转成 ANSI 或 UTF-16 临时缓冲 | `const char*` / `const wchar_t*` | 入参;`ref/out string` 由封送器分配内存,释放责任易出错 |
| `StringBuilder` | 分配临时缓冲,调用后拷回 | `char*` 输出缓冲 | 要提前设置足够 Capacity |
| 委托 | 生成 thunk 得到函数指针 | 函数指针 | 委托对象必须存活,见下文 |
| 含引用字段的 struct / class | 需要 layout 且逐字段封送 | struct 指针 | 不 blittable,成本高 |

性能上的实务结论:

- 高频调用(每帧成千上万次)的接口,参数全部设计成 blittable:`int`、`float`、指针、`byte*` 加长度、固定布局 struct。
- 字符串走 UTF-8 `byte*` 并自己管理缓冲,比让封送器逐次转换好控制;一次传一批数据,比循环里调用一次一个元素少得多的过渡次数。
- 数组入参会被 pin 后直接传指针(blittable 元素),不会拷贝;`[In, Out]` 语义和是否拷贝回依赖具体封送规则,不要想当然。

.NET 7 引入的源生成器 `LibraryImport` 和 .NET 7 的程序集特性 `DisableRuntimeMarshalling` 可以把封送逻辑搬到编译期、禁掉运行时封送,以便 AOT 友好,Unity 6000.x 的 C# 9.0 与 netstandard2.1 API 面不包含它们(待核实具体版本)。

## 调用约定与 ABI 对接

```csharp
using System;
using System.Runtime.InteropServices;

static unsafe class Native
{
    // C 侧: extern "C" __declspec(dllexport) int32_t add_i32(int32_t a, int32_t b);
    [DllImport("mylib", CallingConvention = CallingConvention.Cdecl)]
    public static extern int add_i32(int a, int b);

    // C 侧: extern "C" bool is_ready();  -> C++ bool 是 1 字节
    [DllImport("mylib", CallingConvention = CallingConvention.Cdecl)]
    [return: MarshalAs(UnmanagedType.U1)]
    public static extern bool is_ready();

    // C 侧: extern "C" int fill(uint8_t* dst, size_t cap);   size_t -> nuint / UIntPtr
    [DllImport("mylib", CallingConvention = CallingConvention.Cdecl)]
    public static extern int fill(byte* dst, UIntPtr cap);
}
```

对接 C++ 的规则:

- 导出必须是 `extern "C"`。C++ 函数名会被修饰(`?foo@@YAHH@Z` 这类),`DllImport` 里写不出来,也不稳定。
- x86 上 `DllImport` 默认 `CallingConvention.Winapi`,即 Windows 上的 stdcall;C 默认 cdecl。不一致时 x86 会调用后栈不平衡,.NET Framework 与 CoreCLR 在 Debug 下会抛 `PInvokeStackImbalance`/崩溃。x64 上 Windows 只有一种约定(Microsoft x64),标注会被忽略,这就是"x64 没事,切到 x86 就崩"的来源。
- 数据类型按固定宽度对应:`int32_t↔int`,`int64_t↔long`,`size_t↔nuint/UIntPtr`,`intptr_t↔IntPtr/nint`。C++ 的 `long` 在 Windows 是 32 位,在 Linux/macOS(LP64)是 64 位,**不要**让它出现在导出接口里。
- struct 对齐:C 侧可能有 `#pragma pack`,C# 侧用 `[StructLayout(LayoutKind.Sequential, Pack = N)]` 对齐;布局有疑问时用两端各自 `sizeof`/`offsetof` 与 `Marshal.SizeOf` 对比校验。
- C++ 异常不能越过边界(未定义行为,进程可能直接终止)。导出函数内部 `try/catch` 转成错误码。
- 内存所有权:原生分配的内存由原生提供释放函数,不要用 `Marshal.FreeHGlobal` 去释放 `malloc` 的内存(可能是不同堆)。返回 C++ 对象用不透明句柄(`void*`/`IntPtr`)加创建/销毁导出函数,在 C# 侧用 `SafeHandle` 包住(见 2.5 节)。

## SetLastError

```csharp
[DllImport("kernel32.dll", SetLastError = true)]
static extern IntPtr CreateFileW(string name, uint access, uint share,
    IntPtr sa, uint disp, uint flags, IntPtr tmpl);

var h = CreateFileW(...);
if (h == new IntPtr(-1))
    throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
```

没有 `SetLastError = true` 时,从原生函数返回到你调用 `GetLastError` 之间,运行时自己可能调用了 Win32 API(GC、JIT、类加载),把线程错误码覆盖掉。设为 true 后,封送 stub 在原生返回后立刻把错误码存入线程局部,`Marshal.GetLastWin32Error()`(.NET 6+ 起也叫 `GetLastPInvokeError`)读取的是这份拷贝。Unix 上对应 `errno`。代价是每次调用多一点保存开销,且它阻止了部分内联优化,所以只在真正需要错误码时开。

## 回调:委托、函数指针与生命周期

原生要调用托管代码,有三条路。

**1. 委托封送。** `Marshal.GetFunctionPointerForDelegate` 或把委托参数直接传给 `DllImport` 函数,封送器生成一个可被原生调用的 thunk。这个 thunk 只持有委托的弱信息:委托对象被 GC 回收后,原生再回调就是调用已释放的内存,崩溃表现随机。

```csharp
delegate void LogCb(int level, IntPtr msg);

static LogCb s_keepAlive;                 // 必须被某个根引用,否则回调时可能已被回收

static void Init()
{
    s_keepAlive = OnLog;
    Native.set_logger(Marshal.GetFunctionPointerForDelegate(s_keepAlive));
}
static void OnLog(int level, IntPtr msg) { /* ... */ }
```

要点:委托存到静态字段或某个长期存活对象上;注销回调之前不能置空;实例方法委托还会让其 `Target` 对象存活,别忘了这是一个隐形的引用。.NET Framework 下有 `CallbackOnCollectedDelegate` 托管调试助手可以帮助定位。

**2. 函数指针加 `UnmanagedCallersOnly`(.NET 5+)。** 静态、非泛型、参数返回值全是 blittable 的方法标注后,直接 `&Method` 取地址,没有委托对象也没有 thunk 分配,调用成本最低,也没有"委托被回收"这个问题。方法内部不能让异常逃逸到原生。

```csharp
// 仅 CoreCLR / .NET 5+ 可用,Unity 6000.x 的 C# 9.0 + netstandard2.1 API 面里没有该特性(待核实)
[UnmanagedCallersOnly(CallConvs = new[] { typeof(CallConvCdecl) })]
static void OnLog(int level, IntPtr msg) { }
```

**3. Unity IL2CPP 的规则。** Unity 6000.0 的 IL2CPP 限制页明确:要被当作 C 函数指针交给原生调用的托管方法,在 AOT 平台上必须是静态方法,且带 `[MonoPInvokeCallback]` 特性;泛型方法需要用带 `Type` 的重载指定要支持的具体实例(可叠加多个特性)。IL2CPP 在构建期为这些方法生成"反向 P/Invoke 包装"。手册另说明:C# 9 的 unmanaged 函数指针语法 `delegate* unmanaged[Stdcall]<...>` 受支持,但不支持扩展调用约定。

```csharp
// Unity IL2CPP 回调写法(符合手册描述)
delegate void LogCb(int level, IntPtr msg);

[AOT.MonoPInvokeCallback(typeof(LogCb))]
static void OnLog(int level, IntPtr msg) { }
```

Unity 官方论坛上有开发者报告 C# 9 函数指针用于"托管调用原生"效果很好,但"原生回调托管"未能在 IL2CPP 下跑通。因此 `UnmanagedCallersOnly` 在 Unity IL2CPP 上是否可用不要假设,按手册走 `[MonoPInvokeCallback]`,并在目标平台实测。

回调线程问题:原生可能在非托管创建的线程上回调。这个线程需要先被运行时"附加"(CoreCLR 自动附加;Mono 需要 `mono_thread_attach`;IL2CPP 需 `il2cpp_thread_attach`)。回调里不能调 Unity 主线程 API(`UnityEngine.Object`、`Transform` 等),要入队到主线程处理。

## Unity 的 DllImport 与 Native Plugin

- 库名不带前缀和后缀:`[DllImport("mylib")]` 在 Windows 找 `mylib.dll`,在 Linux/Android 找 `libmylib.so`,在 macOS 找 `libmylib.dylib`。iOS 与 WebGL 上插件被静态链接进可执行文件,要写 `[DllImport("__Internal")]`。
- 插件的平台、CPU、编辑器可用性在 Inspector 的 Plugin Inspector 里设置。
- 编辑器里的原生插件被加载后,Unity 不会卸载它,改了 DLL 要重启编辑器才能重新加载;迭代期常用 `LoadLibrary/GetProcAddress/FreeLibrary` 自己管理加载和函数指针。注意示例中函数指针 `delegate* unmanaged[Stdcall]<UInt32>` 需要在 Player 设置中允许 unsafe 代码。
- Unity 也提供原生插件接口(`IUnityInterfaces`,导出 `UnityPluginLoad`/`UnityPluginUnload`)和 `GL.IssuePluginEvent`,用于渲染线程回调,属于另一套机制,和 DllImport 不是一回事。
- IL2CPP 下 `MarshalAs` 与 `FieldOffset` 特性在编译期生效,但不支持通过反射读取;`Marshal.Prelink`、`Marshal.PrelinkAll` 不支持。

## 常见坑

- `bool` 默认 4 字节,与 C++ `bool` 对接错位。
- `char`/`wchar_t` 宽度、`long` 宽度跨平台不一致。
- 委托被回收后原生回调,崩溃现场与真实原因相隔很远。
- 原生线程回调托管后调用 Unity API。
- 在 `string` 入参里传原生保留的指针(原生持有 `const char*` 到下一次调用)。封送器给的缓冲只在调用期间有效。
- `Marshal.AllocHGlobal` / `UnsafeUtility.Malloc` / 原生 `malloc` 混用释放函数。
- x86 与 x64 的约定混淆;Android 的 armeabi-v7a 与 arm64-v8a 要分别构建插件。

## 面试追问

1. **P/Invoke 一次调用的开销来自哪里?如何降低?** 要点:参数封送、协作/抢占模式切换、GC 挂起检查、可能的 IL stub 与内存拷贝。降低手段:blittable 参数、批量传输而不是逐元素调用、避免 `string`/`bool`/`char`、必要时 `SuppressGCTransition`(仅限极短函数)。
2. **为什么与 C++ 的 `bool` 对接要加 `MarshalAs(U1)`?** 要点:托管默认把 `bool` 封送为 4 字节 Win32 `BOOL`,C++ `bool` 是 1 字节;不标注会错读返回值或错位栈参数。
3. **托管委托传给原生后回调崩溃,怎么排查?** 要点:先看委托是否被 GC 回收(持有到静态字段);其次看调用约定是否匹配、回调线程是否已附加运行时、回调里是否抛了异常越过边界。改用静态方法加函数指针可根除第一类问题。
4. **`SetLastError = true` 解决什么问题?** 要点:原生返回到托管读取错误码之间,运行时可能调用别的系统 API 覆盖错误码;该选项让封送 stub 在返回后立即保存,后续用 `Marshal.GetLastWin32Error` 读取。
5. **Unity IL2CPP 下原生回调托管方法要满足什么条件?** 要点:静态方法、`[MonoPInvokeCallback]`,泛型需指定具体实例;AOT 平台没有运行时 thunk 生成;函数指针语法支持但不支持扩展调用约定。
6. **C++ 导出类对象给 C# 用,怎么设计?** 要点:`extern "C"` 的不透明句柄加 `create/destroy` 与成员函数的 C 包装;C# 用 `SafeHandle` 管理生命周期;不跨边界传 `std::string`、不抛异常、内存谁分配谁释放。

## 参考资料

- Microsoft Learn,Native interoperability 与 P/Invoke:https://learn.microsoft.com/en-us/dotnet/standard/native-interop/pinvoke
- Microsoft Learn,Blittable and non-blittable types:https://learn.microsoft.com/en-us/dotnet/framework/interop/blittable-and-non-blittable-types
- Unity 手册,IL2CPP limitations(Calling managed methods from native code):https://docs.unity3d.com/6000.0/Documentation/Manual/scripting-restrictions.html
- Unity 手册,Callback from native code:https://docs.unity3d.com/6000.0/Documentation/Manual/ios-native-plugin-call-back.html
- Unity 手册,C# compiler and language version reference(Unmanaged function pointer support):https://docs.unity3d.com/6000.2/Documentation/Manual/csharp-compiler.html
- Unity 论坛,C# 9 function pointers - native-to-managed calls w/ IL2CPP?:https://discussions.unity.com/t/c-9-function-pointers-native-to-managed-calls-w-il2cpp/910113
